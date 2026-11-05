"""The daily run: pick today's item, generate the essay, save it, rebuild the site.

    PYTHONPATH=src .venv/bin/python -m daily_excellence.pipeline            # today (US Eastern)
    PYTHONPATH=src .venv/bin/python -m daily_excellence.pipeline --render-only

Idempotent: if a post for today already exists, it only re-renders the site.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

from . import config, render, select_item

POSTS_DIR = config.POSTS_DATA_DIR
SITE_DIR = config.ROOT / "site"


def today() -> str:
    return dt.datetime.now(ZoneInfo(config.TIMEZONE)).date().isoformat()


def post_exists(date: str, posts_dir: Path = POSTS_DIR) -> bool:
    return any(posts_dir.glob(f"{date}*.json"))


def run(date: str | None = None, *, posts_dir: Path = POSTS_DIR, site_dir: Path = SITE_DIR,
        history_file: Path = select_item.HISTORY_FILE, sources_dir: Path = select_item.SOURCES_DIR,
        generate_fn=None) -> Path | None:
    """Create the post for `date` if missing, then render. Returns the new post path, or None if skipped."""
    from .generate import generate  # imported lazily so --render-only needs no API setup

    date = date or today()
    created = None
    if post_exists(date, posts_dir):
        print(f"Post for {date} already exists; skipping generation.")
    else:
        item = select_item.pick(date, sources_dir=sources_dir, history_file=history_file)
        print(f"{date}: #{item['number']} {item['title']}")
        post = (generate_fn or generate)(item)
        post["date"] = date
        posts_dir.mkdir(parents=True, exist_ok=True)
        created = posts_dir / f"{date}.json"
        created.write_text(json.dumps(post, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Saved {created} (est. ${post['api']['estimated_cost_usd']:.3f})")
        for w in post.get("warnings", []):
            print(f"WARNING: {w}", file=sys.stderr)
    render.build(posts_dir, site_dir)
    print(f"Rendered site -> {site_dir}/index.html")
    return created


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", help="YYYY-MM-DD (default: today in US Eastern)")
    ap.add_argument("--render-only", action="store_true")
    args = ap.parse_args(argv)
    if args.render_only:
        render.build(POSTS_DIR, SITE_DIR)
        print(f"Rendered site -> {SITE_DIR}/index.html")
    else:
        run(args.date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
