"""Project settings. Change ACTIVE_PROMPT to switch prompt versions."""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = ROOT / "prompts"
POSTS_DATA_DIR = ROOT / "data" / "posts"

ACTIVE_PROMPT = "essay_v2"

# Writer: drafts the essay. In two-stage prompts (v2+) it never reads raw search results.
MODEL = "claude-sonnet-5-5"
EFFORT = "low"              # low | medium | high | xhigh | max (higher = more thinking tokens = more cost)

# Researcher (two-stage prompts only): runs the web searches and returns short notes.
RESEARCH_MODEL = "claude-haiku-5-5"
RESEARCH_EFFORT = "low"

MAX_SEARCHES = 2            # each search costs $0.01 and adds its results to the input tokens
MAX_TOKENS = 8000           # output ceiling per request (thinking + essay)
COST_TARGET_USD = 0.05      # per essay; runs above this print a warning

# Models that take the dynamic-filtering web search tool and the server-side refusal fallback.
DYNAMIC_SEARCH_MODELS = {"claude-opus-5-5", "claude-sonnet-5-5"}
FALLBACK_MODELS = {"claude-opus-5-5", "claude-sonnet-5-5"}

# USD per million tokens (input, output) and per search. Source: Anthropic pricing, Oct 2026.
PRICING = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}
WEB_SEARCH_USD = 0.01
TIMEZONE = "America/New_York"
BLOCKED_DOMAINS = ["personalexcellence.co"]  # ToS: no automated access (subdomains covered)
WORD_RANGE = (200, 1100)


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Minimal .env loader: KEY=VALUE lines; real environment variables win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
