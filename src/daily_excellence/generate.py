"""Generate a Daily Excellence essay for one item.

Two prompt layouts are supported (see prompts/):
* single-stage (essay_v1): the writer model searches the web and writes in one call.
* two-stage (essay_v2+, has research_system.md): a cheap research model searches and
  returns short notes; the writer model drafts from verified notes with no tools.

Test run (doesn't touch selection history):
    PYTHONPATH=src .venv/bin/python -m daily_excellence.generate --item-id 101-ways-to-be-a-better-person-072
    PYTHONPATH=src .venv/bin/python -m daily_excellence.generate --random --dry-run   # print prompts only, no API call
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import jinja2

from . import config
from .select_item import load_pool

LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
NOTE_HEADER_RE = re.compile(r"^##\s+(.+?)\s*\|\s*(https?://\S+)\s*$")


# ---------- prompt building ----------

def load_prompt(version: str = config.ACTIVE_PROMPT) -> dict:
    d = config.PROMPTS_DIR / version
    prompt = {
        "version": version,
        "system": (d / "system.md").read_text(encoding="utf-8").strip(),
        "user_template": (d / "user.md.j2").read_text(encoding="utf-8"),
        "variation": json.loads((d / "variation.json").read_text(encoding="utf-8")),
        "research_system": None,
        "research_template": None,
    }
    if (d / "research_system.md").exists():
        prompt["research_system"] = (d / "research_system.md").read_text(encoding="utf-8").strip()
        prompt["research_template"] = (d / "research_user.md.j2").read_text(encoding="utf-8")
    return prompt


def sample_variation(spec: dict, rng: random.Random) -> dict:
    """Randomly choose today's structure so essays don't share one skeleton."""
    secs = spec["sections"]
    lo, hi = secs["optional_count"]
    optional = rng.sample(secs["optional"], rng.randint(lo, hi))
    sections = optional + list(secs["required"])
    rng.shuffle(sections)
    # Keep "how to apply" late; it reads best near the end.
    apply = [s for s in sections if s.startswith("how to apply")]
    sections = [s for s in sections if s not in apply] + apply
    return {
        "length": rng.choice(spec["length"]),
        "sections": sections,
        "use_headings": rng.random() < spec["use_headings_probability"],
        "opening": rng.choice(spec["opening"]),
        "tone": rng.choice(spec["tone"]),
        "closing": rng.choice(spec["closing"]),
    }


def render(template: str, **ctx) -> str:
    env = jinja2.Environment(undefined=jinja2.StrictUndefined)
    return env.from_string(template).render(**ctx).strip()


def render_user_prompt(template: str, item: dict, variation: dict, notes: str = "") -> str:
    return render(template, item=item, v=variation, notes=notes)


# ---------- response handling ----------

def is_blocked(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(host == d or host.endswith("." + d) for d in config.BLOCKED_DOMAINS)


def extract(content: list) -> tuple[str, dict[str, str]]:
    """Return (final text after the last search, {url: title} of pages web search actually returned)."""
    retrieved: dict[str, str] = {}
    last_tool_idx = -1
    for idx, block in enumerate(content):
        if block.type == "web_search_tool_result":
            last_tool_idx = idx
            if isinstance(block.content, list):  # an error result is an object, not a list
                for r in block.content:
                    retrieved[r.url] = r.title
    text = "".join(b.text for b in content[last_tool_idx + 1:] if b.type == "text")
    return text.strip(), retrieved


def essay_from_text(text: str) -> str:
    start = text.find("# ")
    return (text[start:] if start >= 0 else text).strip()


def _norm(url: str) -> str:
    return url.rstrip("/")


def parse_notes(text: str, retrieved: dict[str, str]) -> tuple[str, dict[str, str], list[str]]:
    """Keep only note blocks whose URL web search actually returned. Returns (notes, {url: title}, warnings)."""
    retrieved_norm = {_norm(u) for u in retrieved}
    blocks: list[tuple[str, str, list[str]]] = []
    for line in text.splitlines():
        m = NOTE_HEADER_RE.match(line.strip())
        if m:
            blocks.append((m.group(1), m.group(2), []))
        elif blocks and line.strip():
            blocks[-1][2].append(line.rstrip())

    kept, sources, warnings = [], {}, []
    for title, url, lines in blocks:
        if is_blocked(url):
            warnings.append(f"Research: dropped note on blocked domain {url}")
        elif _norm(url) not in retrieved_norm:
            warnings.append(f"Research: dropped note with URL not returned by search {url}")
        elif lines:
            kept.append(f"## {title} | {url}\n" + "\n".join(lines))
            sources[url] = title
    return "\n\n".join(kept), sources, warnings


def _split_sources(markdown: str) -> tuple[str, str]:
    m = re.search(r"(?m)^##\s+Sources\s*$", markdown)
    if not m:
        return markdown, ""
    return markdown[: m.start()], markdown[m.end():]


def clean_essay(markdown: str, allowed: dict[str, str]) -> tuple[str, list[dict], list[str]]:
    """Validate source links against `allowed` URLs, strip blocked domains. Returns (essay, sources, warnings)."""
    warnings: list[str] = []
    allowed_norm = {_norm(u) for u in allowed}

    def fix_link(m: re.Match) -> str:
        label, url = m.group(1), m.group(2)
        if is_blocked(url):
            warnings.append(f"Removed link to blocked domain: {url}")
            return label
        return m.group(0)

    body, sources_md = _split_sources(markdown)
    body = LINK_RE.sub(fix_link, body).strip()

    sources: list[dict] = []
    for label, url in LINK_RE.findall(sources_md):
        if is_blocked(url):
            warnings.append(f"Dropped source on blocked domain: {url}")
        elif _norm(url) not in allowed_norm:
            warnings.append(f"Dropped source not found in research: {url}")
        elif url not in {s["url"] for s in sources}:
            sources.append({"title": label, "url": url})
    return body, sources, warnings


def word_count(markdown: str) -> int:
    text = LINK_RE.sub(r"\1", markdown)
    text = re.sub(r"(?m)^#+\s.*$", "", text)  # headings don't count
    return len(re.findall(r"\b[\w’'-]+\b", text))


def validate(body: str, sources: list[dict]) -> list[str]:
    problems = []
    n = word_count(body)
    lo, hi = config.WORD_RANGE
    if not lo <= n <= hi:
        problems.append(f"word count {n} outside {lo}-{hi}")
    if not sources:
        problems.append("no verified sources")
    if not body.startswith("# "):
        problems.append("missing title heading")
    return problems


# ---------- API calls ----------

def search_tool(model: str) -> dict:
    dynamic = model in config.DYNAMIC_SEARCH_MODELS
    return {
        "type": "web_search_20260209" if dynamic else "web_search_20250305",
        "name": "web_search",
        "max_uses": config.MAX_SEARCHES,
        "blocked_domains": config.BLOCKED_DOMAINS,
    }


def estimate_cost(meta: dict) -> float:
    """USD estimate from usage. Cache reads bill at 0.1x input, cache writes at 1.25x."""
    inp, out = config.PRICING.get(meta["model_served"] or meta["model"], config.PRICING[meta["model"]])
    tokens = (meta["input_tokens"] + 0.1 * meta["cache_read_tokens"] + 1.25 * meta["cache_write_tokens"]) * inp
    return round((tokens + meta["output_tokens"] * out) / 1e6 + meta["web_searches"] * config.WEB_SEARCH_USD, 4)


def call_claude(model: str, effort: str, system: str, user: str, tools: list | None = None) -> tuple[list, dict]:
    import anthropic

    config.load_dotenv()
    client = anthropic.Anthropic()
    messages: list = [{"role": "user", "content": user}]
    content: list = []
    meta = {"model": model, "request_ids": [], "input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0,
            "cache_write_tokens": 0, "web_searches": 0, "model_served": None}
    kwargs: dict = {}
    if tools:
        kwargs["tools"] = tools
    if model in config.FALLBACK_MODELS:
        # If a safety classifier declines, the API retries on a fallback model in the same call.
        kwargs.update(betas=["server-side-fallback-2026-07-01"], fallbacks="default")

    for _ in range(4):  # resume on pause_turn (long server-tool turns)
        resp = client.beta.messages.create(
            model=model,
            max_tokens=config.MAX_TOKENS,
            system=system,
            messages=messages,
            output_config={"effort": effort},
            **kwargs,
        )
        meta["request_ids"].append(resp._request_id)
        meta["input_tokens"] += resp.usage.input_tokens
        meta["output_tokens"] += resp.usage.output_tokens
        meta["cache_read_tokens"] += getattr(resp.usage, "cache_read_input_tokens", 0) or 0
        meta["cache_write_tokens"] += getattr(resp.usage, "cache_creation_input_tokens", 0) or 0
        stu = getattr(resp.usage, "server_tool_use", None)
        meta["web_searches"] += getattr(stu, "web_search_requests", 0) or 0
        meta["model_served"] = resp.model
        content.extend(resp.content)

        if resp.stop_reason == "refusal":
            raise RuntimeError(f"Model declined the request: {resp.stop_details}")
        if resp.stop_reason == "max_tokens":
            raise RuntimeError("Response hit max_tokens before finishing")
        if resp.stop_reason != "pause_turn":
            meta["estimated_cost_usd"] = estimate_cost(meta)
            return content, meta
        messages = messages + [{"role": "assistant", "content": resp.content}]
    raise RuntimeError("Gave up after repeated pause_turn responses")


def research(prompt: dict, item: dict, variation: dict) -> tuple[str, dict[str, str], list[str], dict]:
    user = render(prompt["research_template"], item=item, v=variation)
    model = config.RESEARCH_MODEL
    content, meta = call_claude(model, config.RESEARCH_EFFORT, prompt["research_system"], user, [search_tool(model)])
    text, retrieved = extract(content)
    notes, sources, warnings = parse_notes(text, retrieved)
    return notes, sources, warnings, meta


def generate(item: dict, *, rng: random.Random | None = None, prompt_version: str = config.ACTIVE_PROMPT,
             retries: int = 1) -> dict:
    rng = rng or random.Random()
    prompt = load_prompt(prompt_version)
    variation = sample_variation(prompt["variation"], rng)
    two_stage = prompt["research_system"] is not None
    calls: list[dict] = []
    warnings: list[str] = []

    notes, allowed = "", {}
    if two_stage:
        for _ in range(retries + 1):
            notes, allowed, w, meta = research(prompt, item, variation)
            calls.append({"stage": "research", **meta})
            warnings += w
            if allowed:
                break
        if not allowed:
            warnings.append("Research found no verified sources; essay written without them")

    user = render_user_prompt(prompt["user_template"], item, variation, notes)
    problems: list[str] = []
    for attempt in range(retries + 1):
        tools = None if two_stage else [search_tool(config.MODEL)]
        content, meta = call_claude(config.MODEL, config.EFFORT, prompt["system"], user, tools)
        calls.append({"stage": "write", **meta})
        text, retrieved = extract(content)
        body, sources, w = clean_essay(essay_from_text(text), allowed if two_stage else retrieved)
        problems = validate(body, sources)
        if two_stage and not allowed:
            problems = [p for p in problems if p != "no verified sources"]
        if not problems:
            break
        print(f"Write attempt {attempt + 1} failed validation: {problems}", file=sys.stderr)

    title_line, _, rest = body.partition("\n")
    return {
        "title": title_line.lstrip("# ").strip(),
        "essay_markdown": rest.strip(),
        "sources": sources,
        "word_count": word_count(rest),
        "item": item,
        "prompt_version": prompt_version,
        "model": config.MODEL,
        "research_model": config.RESEARCH_MODEL if two_stage else None,
        "research_notes": notes or None,
        "variation": variation,
        "warnings": warnings + w + [f"validation: {p}" for p in problems],
        "api": {
            "calls": calls,
            "web_searches": sum(c["web_searches"] for c in calls),
            "estimated_cost_usd": round(sum(c["estimated_cost_usd"] for c in calls), 4),
        },
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--item-id")
    g.add_argument("--random", action="store_true", help="random item, without recording history")
    ap.add_argument("--dry-run", action="store_true", help="print the prompts; no API call")
    ap.add_argument("--out", type=Path, help="output JSON (default data/drafts/<item-id>.json)")
    args = ap.parse_args(argv)

    pool = {i["id"]: i for i in load_pool()}
    item = random.choice(list(pool.values())) if args.random else pool[args.item_id]

    if args.dry_run:
        prompt = load_prompt()
        v = sample_variation(prompt["variation"], random.Random())
        if prompt["research_system"]:
            print("=== RESEARCH SYSTEM ===\n" + prompt["research_system"])
            print("\n=== RESEARCH USER ===\n" + render(prompt["research_template"], item=item, v=v) + "\n")
        print("=== WRITER SYSTEM ===\n" + prompt["system"])
        print("\n=== WRITER USER ===\n" + render_user_prompt(prompt["user_template"], item, v, "<research notes go here>"))
        return 0

    post = generate(item)
    out = args.out or config.ROOT / "data" / "drafts" / f"{item['id']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(post, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"# {post['title']}\n\n{post['essay_markdown']}\n")
    for c in post["api"]["calls"]:
        print(f"  {c['stage']:<8} {c['model_served']:<18} in/out {c['input_tokens']}/{c['output_tokens']} "
              f"searches {c['web_searches']}  ${c['estimated_cost_usd']:.4f}")
    cost = post["api"]["estimated_cost_usd"]
    print(f"Sources: {len(post['sources'])} | words: {post['word_count']} | est. total cost: ${cost:.3f}")
    if cost > config.COST_TARGET_USD:
        print(f"WARNING: cost above ${config.COST_TARGET_USD:.2f} target", file=sys.stderr)
    for w in post["warnings"]:
        print(f"WARNING: {w}", file=sys.stderr)
    print(f"Saved -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
