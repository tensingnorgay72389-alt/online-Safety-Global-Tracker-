"""Official-first intake with GNews as the secondary source.

Classifier output is written only to the Signals review queue. Regulations,
market scores and heatmap or database data are not updated.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ts_monitor.dedup import deduplicate, load_seen, remember, save_seen
from ts_monitor.gnews import fetch_gnews
from ts_monitor.official_intake import collect_official, sources_to_collect
from ts_monitor.official_inventory import load_official_inventory
from ts_monitor.paths import data_dir, default_official_inventory_path, repo_root
from ts_monitor.signal_routing import route_record, write_review_queue
from ts_monitor.xai_classifier import XaiClassifier, compact_regulations


def _articles_from_file(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        return list(raw.get("articles") or raw.get("items") or [])
    return list(raw)


def _regulations_path() -> Path:
    return repo_root() / "dashboard" / "data" / "regulations.json"


def _dated_on_or_after(article: dict[str, Any], since: str | None) -> bool:
    if not since:
        return True
    raw = str(article.get("publishedAt") or article.get("published_at") or "")
    if len(raw) >= 10 and raw[4:5] == "-" and raw[7:8] == "-":
        return raw[:10] >= since
    return True


def run_intake(
    *,
    out_dir: Path,
    since: str | None = None,
    seen_path: Path | None = None,
    article_file: Path | None = None,
    skip_official: bool = False,
    skip_gnews: bool = False,
    skip_classify: bool = False,
    inventory_path: Path | None = None,
) -> dict[str, Any]:
    seen_file = seen_path or (data_dir() / "seen_urls.json")
    seen = load_seen(seen_file)
    official_errors: list[dict[str, Any]] = []
    official_count = 0
    gnews_count = 0

    if article_file is not None:
        articles = _articles_from_file(article_file)
    else:
        official_articles: list[dict[str, Any]] = []
        if not skip_official:
            inventory = load_official_inventory(inventory_path or default_official_inventory_path())
            rows = sources_to_collect(inventory)
            official_articles, official_errors = collect_official(rows)
            official_count = len(official_articles)
        gnews_articles: list[dict[str, Any]] = []
        if not skip_gnews:
            gnews_articles = fetch_gnews()
            gnews_count = len(gnews_articles)
        articles = [
            article
            for article in deduplicate(official_articles + gnews_articles, seen)
            if _dated_on_or_after(article, since)
        ]

    classified: list[dict[str, Any]] = []
    classify_errors = 0
    classifier = XaiClassifier()
    if not skip_classify and classifier.available():
        context = compact_regulations(_regulations_path())
        for article in articles:
            try:
                item = classifier.classify(article, context)
            except Exception:
                classify_errors += 1
                continue
            if item:
                classified.append(item)
    elif not skip_classify:
        classify_errors = 0

    routed = []
    discarded = 0
    for item in classified:
        decision = route_record(item)
        if decision is None:
            discarded += 1
        else:
            routed.append(decision)

    queue_path = out_dir / "signals" / "review_queue.json"
    payload = write_review_queue(queue_path, routed, discarded=discarded)
    error_path = out_dir / "signals" / "official_fetch_errors.json"
    error_path.parent.mkdir(parents=True, exist_ok=True)
    error_path.write_text(json.dumps(official_errors, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if article_file is None:
        save_seen(seen_file, remember(seen, articles))
        save_seen(out_dir / "signals" / "seen_urls.json", load_seen(seen_file))

    summary = {
        "official_articles": official_count,
        "gnews_articles": gnews_count,
        "unique_articles": len(articles),
        "official_errors": len(official_errors),
        "classified": len(classified),
        "signals": len(payload["signals"]),
        "review": len(payload["review"]),
        "discarded": discarded,
        "classify_errors": classify_errors,
        "classifier": "xai" if classifier.available() and not skip_classify else "skipped",
        "queue": str(queue_path),
    }
    summary_path = out_dir / "signals" / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary
