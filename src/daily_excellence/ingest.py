"""Convert hand-pasted list articles into JSON items.

Compliance (docs/COMPLIANCE.md): this module reads ONLY local files the user
pasted by hand. It must never import a network library or fetch any URL.

Two paste formats are supported:

* Numbered: items start with "12." or "12)" on their own line, body follows.
* Line-per-item (what a browser copy of an HTML list usually produces): after
  the intro (ending at a short line like "Here goes:"), every non-blank line is
  one item, written as "Title sentence. Body text...". Prefix a line with "- "
  to mark it as a sub-item; it is nested inside the previous top-level item
  (its "subitems" list) rather than becoming a daily message of its own.
  Prefix a line with "+ " to mark a follow-up question: it stays its own
  item, and the question(s) it follows are stored in its "context" list.
  End a line with "[[note: ...]]" to give the writer guidance for that item
  (stored as "note"; used in prompts, never shown on the page).

Usage:
    python -m daily_excellence.ingest data/raw/<slug>.txt \
        --title "101 Ways To Be a Better Person" \
        --source-url "https://personalexcellence.co/blog/..."
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

MAX_SOURCE_ARTICLES = 10
SOURCES_DIR = Path(__file__).resolve().parents[2] / "data" / "sources"
ATTRIBUTION = "Adapted from {title} by Personal Excellence ({url})"
ALLOWED_HOSTS = {"personalexcellence.co", "www.personalexcellence.co"}

NUMBERED_RE = re.compile(r"^\s*(\d{1,3})[.)]\s+(.+?)\s*$")
SUB_RE = re.compile(r"^(?:\s*[-*•]\s+|\t+)(.*)$")
FOLLOW_RE = re.compile(r"^\s*\+\s+(.*)$")  # follow-up question: own item, earlier question(s) as context
NOTE_RE = re.compile(r"\s*\[\[note:\s*(.+?)\]\]\s*$")  # trailing writer's note; prompts only, never shown
# First sentence end: . ? or ! (optionally inside a closing quote) followed by space/end, not an ellipsis.
TITLE_END_RE = re.compile(r"(?<!\.)([.?!])([\"”’]?)(?=\s|$)")
ABBREV_RE = re.compile(r"\b(?:vs|e\.g|i\.e|Mr|Mrs|Ms|Dr|St)$", re.I)  # "." here is not a sentence end
LEADING_NUM_RE = re.compile(r"^\d{1,3}[.)]\s+")  # a stray "1. " that survived the paste
TERM_RE = re.compile(r"^([^:]{1,40}):\s+(\S.*)$")
# Trailing "(Read: X)" or "Read: X". The wrapped form is tried first so a title
# ending in ")" (e.g. "Life Purpose (7-part series)") keeps its parenthesis.
READ_RE = re.compile(r"\s*\(Read:\s*([^()]+(?:\([^()]*\)[^()]*)*)\)\s*$|\s*Read:\s*(.+?)\s*$")


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def split_title(line: str) -> tuple[str, str]:
    """Split "Be Bold. Life is an adventure." into ("Be Bold", "Life is an adventure.").

    A period after an abbreviation ("Focus on WHAT vs. How.") doesn't end the title, and
    a one-word question ("Why? How can you...?") keeps the question that follows it.
    """
    for m in TITLE_END_RE.finditer(line):
        punct, quote = m.group(1), m.group(2)
        head = line[: m.start()].strip()
        if punct == "." and not quote and ABBREV_RE.search(head):
            continue
        title = head + (punct + quote if quote else punct if punct in "?!" else "")
        if punct == "?" and len(title.split()) == 1 and line[m.end():].strip():
            nxt = TITLE_END_RE.search(line, m.end())
            if nxt and nxt.group(1) == "?":
                return line[: nxt.end()].strip(), line[nxt.end():].strip()
        return title, line[m.end():].strip()
    return line.strip(), ""


def split_related(body: str) -> tuple[str, str | None]:
    """Pull a trailing 'Read: <article name>' (an internal link on the site) out of the body."""
    m = READ_RE.search(body)
    if not m:
        return body, None
    return body[: m.start()].rstrip(), m.group(1) or m.group(2)


def _parse_numbered(lines: list[str]) -> list[dict]:
    items: list[dict] = []
    body: list[str] = []

    def flush():
        if items:
            items[-1]["body"] = "\n\n".join(
                p.strip() for p in "\n".join(body).split("\n\n") if p.strip()
            )

    for line in lines:
        m = NUMBERED_RE.match(line)
        if m:
            flush()
            items.append({"number": int(m.group(1)), "title": m.group(2).strip()})
            body = []
        elif items:
            body.append(line.rstrip())
    flush()
    return items


def _find_start(lines: list[str], start_after: str | None) -> int:
    if start_after:
        for idx, line in enumerate(lines):
            if line.strip().lower() == start_after.strip().lower():
                return idx + 1
        raise ValueError(f"Start marker {start_after!r} not found in the pasted text")
    # The last short line ending in ":" in the first half, e.g. "Here goes:" or
    # "I present to you, 101 ...:" (an earlier "Some things to note:" is skipped).
    candidates = [idx for idx, line in enumerate(lines[: len(lines) // 2 + 1])
                  if line.strip().endswith(":") and len(line.strip()) <= 120]
    if candidates:
        return candidates[-1] + 1
    raise ValueError(
        "Could not find where the list starts. Pass --start-after with the line just "
        "before the first item (for example 'Here goes:')."
    )


def _parse_lines(lines: list[str], start_after: str | None) -> list[dict]:
    """Top-level lines become items; '- ' lines nest under the previous item as subitems."""
    items: list[dict] = []
    body_lines = [l for l in lines[_find_start(lines, start_after):] if l.strip()]
    # "Term: text" articles (e.g. "Ability: is more of a function of...") split at the colon.
    term_style = bool(body_lines) and sum(bool(TERM_RE.match(l.strip())) for l in body_lines) >= 0.8 * len(body_lines)
    chain: list[str] = []  # the current question and its follow-ups so far
    for raw in body_lines:
        fm = FOLLOW_RE.match(raw)
        m = None if fm else SUB_RE.match(raw)
        text = LEADING_NUM_RE.sub("", (fm or m).group(1).strip() if (fm or m) else raw.strip())
        nm = NOTE_RE.search(text)
        note = nm.group(1).strip() if nm else None
        if nm:
            text = text[: nm.start()].rstrip()
        tm = TERM_RE.match(text) if term_style else None
        title, body = (tm.group(1).strip(), tm.group(2).strip()) if tm else split_title(text)
        if m and items:
            items[-1]["subitems"].append({"title": title, "body": body})
        else:
            item = {"number": len(items) + 1, "title": title, "body": body, "subitems": []}
            if tm:
                item["joiner"] = ": "  # how prompts rejoin title and body ("Ability: is more of...")
            if note:
                item["note"] = note
            if fm and chain:
                item["context"] = list(chain)
                chain.append(text)
            else:
                chain = [text]
            items.append(item)
    return items


def parse_items(text: str, start_after: str | None = None) -> tuple[list[dict], list[str]]:
    """Return (items, warnings)."""
    lines = text.splitlines()
    numbered = sum(bool(NUMBERED_RE.match(l)) for l in lines) >= 2
    items = _parse_numbered(lines) if numbered else _parse_lines(lines, start_after)

    for item in items:
        item.setdefault("subitems", [])
        for entry in [item, *item["subitems"]]:
            entry["body"], related = split_related(entry["body"])
            if related:
                entry["related_read"] = related

    warnings: list[str] = []
    if numbered:
        numbers = [i["number"] for i in items]
        expected = list(range(1, len(items) + 1))
        if numbers != expected:
            missing = sorted(set(expected) - set(numbers))
            dupes = sorted({n for n in numbers if numbers.count(n) > 1})
            warnings.append(f"Numbering not sequential (missing={missing}, duplicates={dupes})")
    for i in items:
        if not i["body"] and not i["subitems"]:
            warnings.append(f"Item {i['number']} ('{i['title']}') has no body text")
    return items, warnings


def build_source(text: str, title: str, source_url: str,
                 start_after: str | None = None) -> tuple[dict, list[str]]:
    if urlparse(source_url).netloc.lower() not in ALLOWED_HOSTS:
        raise ValueError(f"source_url must be a personalexcellence.co article, got {source_url!r}")
    slug = slugify(title)
    items, warnings = parse_items(text, start_after)
    if not items:
        raise ValueError("No items found. Check the pasted text format.")
    for i in items:
        i["id"] = f"{slug}-{i['number']:03d}"

    m = re.match(r"\s*(\d+)\b", title)
    if m and int(m.group(1)) != len(items):
        warnings.append(
            f"Title says {m.group(1)} items but {len(items)} top-level items were found. "
            "If the article has nested sub-items, prefix those lines with '- ' in the raw file."
        )
    return {
        "slug": slug,
        "source_title": title,
        "source_url": source_url,
        "attribution": ATTRIBUTION.format(title=title, url=source_url),
        "items": items,
    }, warnings


def write_source(source: dict, sources_dir: Path = SOURCES_DIR) -> Path:
    sources_dir.mkdir(parents=True, exist_ok=True)
    out = sources_dir / f"{source['slug']}.json"
    existing = set(sources_dir.glob("*.json"))
    if out not in existing and len(existing) >= MAX_SOURCE_ARTICLES:
        raise ValueError(
            f"Refusing to add an article: the {MAX_SOURCE_ARTICLES}-article cap from the "
            "source Terms of Use has been reached (see docs/COMPLIANCE.md)."
        )
    out.write_text(json.dumps(source, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("raw_file", type=Path)
    ap.add_argument("--title", required=True)
    ap.add_argument("--source-url", required=True)
    ap.add_argument("--start-after", help="Line just before the first item (line-per-item pastes)")
    args = ap.parse_args(argv)

    source, warnings = build_source(
        args.raw_file.read_text(encoding="utf-8"), args.title, args.source_url, args.start_after
    )
    out = write_source(source)
    subs = sum(len(i["subitems"]) for i in source["items"])
    print(f"Parsed {len(source['items'])} items (+{subs} nested sub-items) -> {out}")
    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
