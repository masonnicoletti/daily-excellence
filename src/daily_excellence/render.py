"""Render post data (JSON) into the static GitHub Pages site.

    PYTHONPATH=src .venv/bin/python -m daily_excellence.render              # data/posts -> site/
    PYTHONPATH=src .venv/bin/python -m daily_excellence.render --drafts     # data/drafts -> site_preview/ (local preview)

Each post page carries the attribution and disclaimer required by the source
Terms of Use (docs/COMPLIANCE.md).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
from pathlib import Path

import jinja2
import markdown as md

from . import config

TEMPLATES_DIR = config.ROOT / "templates"
STATIC = ["style.css", "favorites.js", "site.webmanifest"]
STATIC_DIRS = ["icons"]  # favicons and home-screen icons (PNGs built by tools/make_icons.sh)
SITE_TITLE = "Daily Excellence"
DISCLAIMER = ("Daily Excellence is an independent project, not affiliated with or endorsed by Personal "
              "Excellence. Essays are AI-generated (see the colophon on each post) and are for "
              "inspiration only, not professional advice.")


def essay_html(markdown_text: str) -> str:
    # Escape raw HTML so model output can only produce Markdown formatting.
    return md.markdown(markdown_text.replace("<", "&lt;"), extensions=["sane_lists"])


def load_posts(src: Path, drafts: bool = False) -> list[dict]:
    posts = []
    for path in sorted(src.glob("*.json")):
        p = json.loads(path.read_text(encoding="utf-8"))
        # data/posts/YYYY-MM-DD.json (a suffix like -2 allows a second post on one day)
        p["date"] = p["generated_at"][:10] if drafts else p.get("date", path.stem[:10])
        p["slug"] = path.stem
        d = dt.date.fromisoformat(p["date"])
        p["date_long"] = f"{d:%A}, {d:%B} {d.day}, {d.year}"
        p["date_short"] = f"{d:%b} {d.day}, {d.year}"
        p["html"] = essay_html(p["essay_markdown"])
        p["reading_minutes"] = max(1, round(p["word_count"] / 220))
        first_para = next((b for b in p["essay_markdown"].split("\n\n") if b and not b.startswith("#")), "")
        p["excerpt"] = md.markdown(first_para.replace("<", "&lt;")).replace("<p>", "").replace("</p>", "")
        # The few fields favorites.js needs to list an essay (embedded as JSON on the home page).
        p["card"] = {"slug": p["slug"], "title": p["title"], "idea": p["item"]["title"],
                     "date": p["date"], "date_short": p["date_short"]}
        posts.append(p)
    posts.sort(key=lambda p: (p["date"], p.get("generated_at", "")), reverse=True)  # newest first
    return posts


def build(src: Path, out: Path, drafts: bool = False) -> list[Path]:
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATES_DIR),
                             autoescape=jinja2.select_autoescape(["html"]))
    env.globals.update(site_title=SITE_TITLE, disclaimer=DISCLAIMER, preview=drafts,
                       release_hour=config.RELEASE_HOUR, timezone=config.TIMEZONE)
    posts = load_posts(src, drafts)

    (out / "posts").mkdir(parents=True, exist_ok=True)
    for name in STATIC:
        shutil.copy(TEMPLATES_DIR / name, out / name)
    for name in STATIC_DIRS:
        shutil.copytree(TEMPLATES_DIR / name, out / name, dirs_exist_ok=True)
    (out / ".nojekyll").write_text("")

    written = []
    post_tpl = env.get_template("post.html")
    for i, p in enumerate(posts):
        newer = posts[i - 1] if i > 0 else None
        older = posts[i + 1] if i + 1 < len(posts) else None
        path = out / "posts" / f"{p['slug']}.html"
        path.write_text(post_tpl.render(post=p, newer=newer, older=older, root="../"), encoding="utf-8")
        written.append(path)

    for name in ("index.html", "archive.html"):
        page = out / name
        page.write_text(env.get_template(name).render(posts=posts, root=""), encoding="utf-8")
        written.append(page)
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--drafts", action="store_true", help="render data/drafts into site_preview/")
    args = ap.parse_args(argv)
    src = config.ROOT / "data" / ("drafts" if args.drafts else "posts")
    out = config.ROOT / ("site_preview" if args.drafts else "site")
    written = build(src, out, args.drafts)
    print(f"Rendered {len(written) - 2} posts + index + archive -> {out}/index.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
