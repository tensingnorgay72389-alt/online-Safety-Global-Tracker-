"""Command-line interface for the monitoring backend."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ts_monitor.paths import default_out_dir, default_register_path, default_sources_path
from ts_monitor.pipeline import ingest_path, load_context, run_pipeline
from ts_monitor.fetchers import Fetcher
from ts_monitor.matcher import match_all
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
    common.add_argument("--out", type=Path, default=None, help="Output directory (default: ./out).")

    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", parents=[common], help="Fetch or ingest, classify, and write inbox and proposals.")
    run.add_argument("--since", required=True, help="Inclusive start date, YYYY-MM-DD.")
    run.add_argument("--until", default=None, help="Optional inclusive end date, YYYY-MM-DD.")
    run.add_argument("--file", type=Path, default=None, help="Ingest this JSON file or fixture directory instead of fetching.")
    run.add_argument("--offline", action="store_true", help="Do not fetch the network. Requires --file unless the inbox already exists.")
    run.add_argument("--official-only", action="store_true", help="When fetching, only request official sources.")

    ingest = sub.add_parser("ingest", parents=[common], help="Ingest a Word-report-like JSON file or fixture items.")
    ingest.add_argument("--file", type=Path, required=True, help="Path to a JSON file or a directory of JSON files.")

    sub.add_parser("match", parents=[common], help="Rematch the written inbox against the register snapshot.")

    propose = sub.add_parser("propose", parents=[common], help="Emit patches only from the written inbox.")
    propose.add_argument("--file", type=Path, default=None, help="Optional inbox file or fixture path. Defaults to out/inbox/items.json.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    out_dir = _out_dir(str(args.out) if args.out else None)
    register_path = Path(args.register) if args.register else default_register_path()
    sources_path = Path(args.sources) if args.sources else default_sources_path()
    register, catalog = load_context(register_path, sources_path)

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
            fetcher = Fetcher(catalog=catalog)
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
