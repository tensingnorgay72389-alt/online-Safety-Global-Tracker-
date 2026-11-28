"""Command-line interface for the monitoring backend."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ts_monitor.intake import run_intake
from ts_monitor.paths import (
    default_official_inventory_path,
    default_out_dir,
    default_register_path,
    default_regulators_path,
    default_sources_path,
)
from ts_monitor.pipeline import ingest_path, load_context, run_pipeline
from ts_monitor.fetchers import Fetcher
from ts_monitor.matcher import match_all
from ts_monitor.official_inventory import load_official_inventory, sources_for_poll
from ts_monitor.regulators import load_regulator_map, merge_source_catalog, sources_from_regulators
from ts_monitor.sources import Source
from ts_monitor.weekday_scope import restrict_catalog_to_weekday_run
from ts_monitor.writers import dump, write_inbox, write_proposals


def _out_dir(value: str | None) -> Path:
    return Path(value).resolve() if value else default_out_dir()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ts-monitor",
        description="Fetch and classify Trust and Safety regulatory items, then emit typed register patches.",
    )
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--register", type=Path, default=None, help="Path to the register snapshot JSON.")
    common.add_argument("--sources", type=Path, default=None, help="Path to sources.yaml.")
    common.add_argument("--regulators", type=Path, default=None, help="Path to regulators.yaml.")
    common.add_argument("--out", type=Path, default=None, help="Output directory (default: ./out).")

    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", parents=[common], help="Fetch or ingest, classify, and write inbox and proposals.")
    run.add_argument("--since", required=True, help="Inclusive start date, YYYY-MM-DD.")
    run.add_argument("--until", default=None, help="Optional inclusive end date, YYYY-MM-DD.")
    run.add_argument("--file", type=Path, default=None, help="Ingest this JSON file or fixture directory instead of fetching.")
    run.add_argument("--offline", action="store_true", help="Do not fetch the network. Requires --file unless the inbox already exists.")
    run.add_argument("--official-only", action="store_true", help="When fetching, only request official sources.")
    run.add_argument("--skip-regulators", action="store_true", help="Do not add scrape targets from the regulator map.")
    run.add_argument(
        "--include-official-inventory",
        action="store_true",
        help=(
            "Also poll data/official_sources.json on this fetch. "
            "Blocked official URLs stay in the poll set. "
            "Hits are not auto-apply eligible and are not written into the register."
        ),
    )

    ingest = sub.add_parser("ingest", parents=[common], help="Ingest a Word-report-like JSON file or fixture items.")
    ingest.add_argument("--file", type=Path, required=True, help="Path to a JSON file or a directory of JSON files.")

    sub.add_parser("match", parents=[common], help="Rematch the written inbox against the register snapshot.")

    propose = sub.add_parser("propose", parents=[common], help="Emit patches only from the written inbox.")
    propose.add_argument("--file", type=Path, default=None, help="Optional inbox file or fixture path. Defaults to out/inbox/items.json.")

    regs = sub.add_parser("regulators", parents=[common], help="Show the regulator map counts or write a JSON summary.")
    regs.add_argument("--json", action="store_true", help="Write a JSON summary to standard output.")

    inventory = sub.add_parser(
        "inventory",
        help="Show the official-source inventory counts without fetching or editing the register.",
    )
    inventory.add_argument("--json", action="store_true", help="Write the counts as JSON.")

    intake = sub.add_parser(
        "intake",
        help=(
            "Collect official sources and GNews into a Signals review queue. "
            "Does not edit regulations or market scores."
        ),
    )
    intake.add_argument("--since", default=None, help="Keep items dated on or after YYYY-MM-DD when a date is present.")
    intake.add_argument("--out", type=Path, default=None, help="Output directory (default: ./out).")
    intake.add_argument("--seen", type=Path, default=None, help="Seen URL file. Defaults to data/seen_urls.json.")
    intake.add_argument("--file", type=Path, default=None, help="Classify this JSON file instead of fetching.")
    intake.add_argument("--skip-official", action="store_true", help="Do not poll the official-source inventory.")
    intake.add_argument("--skip-gnews", action="store_true", help="Do not call GNews.")
    intake.add_argument("--skip-classify", action="store_true", help="Fetch only. Do not call the xAI classifier.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "inventory":
        return _inventory_command(args)
    if args.command == "intake":
        return _intake_command(args)
    out_dir = _out_dir(str(args.out) if args.out else None)
    register_path = Path(args.register) if args.register else default_register_path()
    sources_path = Path(args.sources) if args.sources else default_sources_path()
    regulators_path = Path(args.regulators) if getattr(args, "regulators", None) else default_regulators_path()
    register, catalog = load_context(register_path, sources_path)
    regulator_map = load_regulator_map(regulators_path) if regulators_path.is_file() else None

    if args.command == "regulators":
        if regulator_map is None:
            print(f"No regulator map found at {regulators_path}", file=sys.stderr)
            return 1
        counts = regulator_map.counts()
        if args.json:
            payload = {
                "version": regulator_map.version,
                "as_of": regulator_map.as_of,
                "counts": counts,
                "bodies": [
                    {
                        "id": body.id,
                        "jurisdiction": body.jurisdiction,
                        "body_type": body.body_type,
                        "official_name": body.official_name,
                        "official_homepage": body.official_homepage,
                        "spokespersons": [person.name for person in body.spokespersons],
                        "scrape_targets": len(body.scrape_targets),
                        "spokesperson_status": body.spokesperson_status,
                    }
                    for body in regulator_map.bodies
                ],
            }
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(
                f"Regulator map {regulator_map.version} (as of {regulator_map.as_of}): "
                f"{counts['bodies']} bodies, {counts['spokespersons']} sourced spokespersons, "
                f"{counts['personal_handles']} personal handles listed on official pages, "
                f"{counts['scrape_targets']} scrape targets."
            )
        return 0

    if args.command == "run":
        errors = []
        if args.file:
            items = ingest_path(Path(args.file))
        elif args.offline:
            inbox_path = out_dir / "inbox" / "items.json"
            if not inbox_path.is_file():
                parser.error("--offline requires --file or an existing out/inbox/items.json")
            items = ingest_path(inbox_path)
        else:
            extras: list[Source] = []
            if regulator_map is not None and not args.skip_regulators:
                extras.extend(sources_from_regulators(regulator_map))
            if args.include_official_inventory:
                extras.extend(sources_for_poll(load_official_inventory()))
            catalog = merge_source_catalog(catalog, extras)
            # Matching still sees every sourced official URL. The weekday fetch does not request
            # official URLs outside the approved market set.
            fetcher = Fetcher(catalog=restrict_catalog_to_weekday_run(catalog))
            items = fetcher.fetch_all(since=args.since, official_only=bool(args.official_only))
            errors = fetcher.errors
            if args.until:
                items = [
                    item
                    for item in items
                    if not item.published_date or item.published_date <= args.until
                ]
        proposals = run_pipeline(items, register, catalog, out_dir, errors=errors)
        _print_summary(items, proposals, errors)
        return 0

    if args.command == "ingest":
        items = ingest_path(Path(args.file))
        write_inbox(items, out_dir)
        print(f"Ingested {len(items)} item(s) to {out_dir / 'inbox' / 'items.json'}")
        return 0

    if args.command == "match":
        inbox_path = out_dir / "inbox" / "items.json"
        if not inbox_path.is_file():
            print(f"No inbox found at {inbox_path}. Run ingest or run first.", file=sys.stderr)
            return 1
        items = ingest_path(inbox_path)
        paired = match_all(items, register)
        payload = [
            {
                "inbox_item_id": item.id,
                "headline": item.headline,
                "instrument_id": match.instrument.id if match.instrument else None,
                "score": match.score,
                "reason": match.reason,
            }
            for item, match in paired
        ]
        path = out_dir / "inbox" / "matches.json"
        dump(payload, path)
        print(f"Wrote {len(payload)} match row(s) to {path}")
        return 0

    if args.command == "propose":
        source = Path(args.file) if args.file else out_dir / "inbox" / "items.json"
        if not source.exists():
            print(f"No inbox found at {source}. Run ingest or run first.", file=sys.stderr)
            return 1
        items = ingest_path(source)
        proposals = run_pipeline(items, register, catalog, out_dir)
        _print_summary(items, proposals, [])
        return 0

    parser.error(f"unknown command {args.command}")
    return 2


def _intake_command(args) -> int:
    out_dir = _out_dir(str(args.out) if args.out else None)
    summary = run_intake(
        out_dir=out_dir,
        since=args.since,
        seen_path=Path(args.seen) if args.seen else None,
        article_file=Path(args.file) if args.file else None,
        skip_official=bool(args.skip_official),
        skip_gnews=bool(args.skip_gnews),
        skip_classify=bool(args.skip_classify),
    )
    print(
        f"Signals intake: {summary['unique_articles']} unique article(s), "
        f"{summary['signals']} queued signal(s), {summary['review']} review item(s), "
        f"{summary['discarded']} discarded. Classifier: {summary['classifier']}. "
        "Regulations and market scores were not changed."
    )
    return 0


def _inventory_command(args) -> int:
    path = default_official_inventory_path()
    if not path.is_file():
        print(f"No official-source inventory at {path}", file=sys.stderr)
        return 1
    inventory = load_official_inventory(path)
    counts = inventory.counts()
    if args.json:
        print(json.dumps({"path": str(path), "as_of": inventory.as_of, "counts": counts}, indent=2))
        return 0
    print(
        f"Official-source inventory as of {inventory.as_of}: "
        f"{counts['rows']} rows ({counts['original']} original and {counts['added']} added). "
        f"{counts['pollable']} rows are pollable. "
        f"Added rows: {counts['verified']} verified, "
        f"{counts['unverified_blocked']} unverified-blocked and {counts['unverified']} unverified."
    )
    return 0


def _print_summary(items, proposals, errors) -> None:
    significant = [p for p in proposals if p.significant]
    auto = [p for p in proposals if p.auto_apply_eligible]
    print(
        f"Processed {len(items)} item(s), {len(proposals)} proposal(s), "
        f"{len(significant)} significant, {len(auto)} auto-apply eligible, {len(errors)} fetch error(s)."
    )
    for proposal in significant:
        print(f"  significant: {proposal.proposal_id} action={proposal.action} instrument={proposal.instrument_id or proposal.proposed_id}")


if __name__ == "__main__":
    raise SystemExit(main())
