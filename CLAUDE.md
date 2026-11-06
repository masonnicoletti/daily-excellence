# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Daily Excellence is a static site on GitHub Pages: https://masonnicoletti.github.io/daily-excellence/. Every morning a GitHub Actions cron job picks one item from hand-pasted personalexcellence.co list articles. Claude researches the item and writes a short essay about it, and the job publishes the essay as a blog post with a full archive.

## Commands

Local Python is 3.9 in `.venv`; CI uses 3.12. Outside pytest, modules need `PYTHONPATH=src`. Pytest gets it from `pyproject.toml`.

```bash
.venv/bin/python -m pytest -q                                   # all tests (no API calls)
.venv/bin/python -m pytest -q tests/test_generate.py::test_validate   # single test

export PYTHONPATH=src
.venv/bin/python -m daily_excellence.ingest data/raw/<file>.txt --title "<Article Title>" --source-url "<url>"
.venv/bin/python -m daily_excellence.generate --random --dry-run    # print rendered prompts, free
.venv/bin/python -m daily_excellence.generate --item-id <id>        # PAID test essay -> data/drafts/
.venv/bin/python -m daily_excellence.render --drafts                # drafts -> site_preview/ (local only)
.venv/bin/python -m daily_excellence.pipeline [--date YYYY-MM-DD]   # PAID real daily run -> data/posts/ + site/
.venv/bin/python -m daily_excellence.pipeline --render-only         # rebuild site/ from data/posts/
```

The API key comes from `.env` (`ANTHROPIC_API_KEY`) through `config.load_dotenv()`. There is no linter configured.

## Architecture

Data flows in one direction, and each stage is one module in `src/daily_excellence/`:

1. **`ingest.py`**: turns a raw paste (`data/raw/*.txt`, gitignored) into `data/sources/<slug>.json`.
   - Two paste formats are auto-detected: numbered (`12.`) and one item per line after a short `...:` line such as "Here goes:".
   - A `- ` prefix marks a sub-item. Sub-items are **nested inside the parent's `subitems`**; they are never standalone daily messages. Top-level `number` must match the article's own numbering.
   - A `+ ` prefix marks a follow-up question. It stays its own item, and the question(s) it follows go into its `context` list. Prompts and the post's idea card show that context.
   - A trailing `[[note: …]]` becomes the item's `note`. Prompts get it, and the page never shows it.
   - "Term: text" articles (e.g. "Ability: is more of…") split at the colon and set `joiner: ": "`. Templates rejoin title and body with `item.get("joiner", ". ")`.
   - The list starts after the last short line ending in ":" in the file's first half. Pass `--start-after` otherwise.
   - The parser warns when the count doesn't match the number in the title. That usually means some sub-items are missing their `- `.
2. **`select_item.py`**: picks at random without repeats, using `data/history.json` (`cycle_reset` marks a pool restart). Picking is idempotent per date.
   - Default path arguments are bound when the module is imported, so tests must pass `sources_dir` and `history_file` explicitly.
3. **`generate.py`**: builds the essay.
   - A prompt version is a folder `prompts/essay_vN/`. The folder layout decides the mode: if it has `research_system.md`, it's **two-stage**. In that mode `RESEARCH_MODEL` (Haiku) runs web search and returns `## title | url` notes, and `MODEL` (Sonnet) writes from those notes with no tools. Otherwise one model searches and writes (`essay_v1`).
   - `variation.json` is sampled randomly on each run (length, sections, tone, opening, closing) so essays don't share one structure.
   - Validation: source URLs must appear in the actual search results (`parse_notes` / `clean_essay`). Blocked domains are stripped. Word count and title are checked, with one retry.
   - The output records the prompt version, models, variation, research notes, and per-call token usage and estimated cost.
4. **`render.py`**: renders Jinja templates in `templates/` (`base`/`post`/`index`/`archive`, plus `style.css`, which is copied as-is) into `site/`. The home page shows only the latest essay; the full list is on `archive.html`.
   - The essay's Markdown has `<` escaped before conversion, so model output can't inject HTML.
   - Favorites are client-side only. `templates/favorites.js` (copied as-is) stores slugs in `localStorage` (`de-favorites`), per browser. The home page embeds every post's `card` as JSON (`#posts-data`), so the Favorites section can list any essay. Home shows Favorites, then the 5 most recent essays.
5. **`pipeline.py`**: the daily entry point. It uses the US Eastern date (`config.TIMEZONE`). If a post for that date already exists, it skips generation and only re-renders.
   - Posts are stored at `data/posts/<YYYY-MM-DD>[-N].json`. The date is the post's `date` field, falling back to the filename stem.

All tunable settings are in `config.py`: `ACTIVE_PROMPT`, models, effort levels, `MAX_SEARCHES`, pricing table, `COST_TARGET_USD`, and `BLOCKED_DOMAINS`. Only Opus and Sonnet get the dynamic `web_search_20260209` tool and the server-side refusal fallback (`DYNAMIC_SEARCH_MODELS`, `FALLBACK_MODELS`). Haiku uses the basic `web_search_20250305` and no fallback. The `anthropic` SDK is pinned to `<1` (the 0.x API).

## Deployment

`.github/workflows/daily.yml` runs on cron at 08:30 UTC, with a backup run at 09:30 that does nothing if the post exists, and on manual dispatch. It runs tests, then the pipeline, commits `data/posts` and `data/history.json` as a bot, and deploys `site/` to Pages.
- A push to `main` only re-renders and redeploys; no essay is generated.
- `site/` is built in CI and is **not committed**.
- The bot commits to `main` daily, so run `git pull --rebase` before pushing.

## Hard constraints: source Terms of Use (`docs/COMPLIANCE.md`)

These come from personalexcellence.co's Terms of Use and are covered by tests. Keep them intact when changing anything:
- No automated access to personalexcellence.co. `ingest.py` must not import any network library; a test checks this. The domain stays in the search tool's `blocked_domains`.
- At most 10 source articles. `ingest.write_source` enforces this.
- Every post page and the index carry a plain, followable link (no `nofollow`) to the specific source article and to Personal Excellence, plus the "not affiliated with or endorsed by" disclaimer.
- Pages show only the selected item, never whole articles. Raw pastes stay gitignored.
- The site design must be original. Don't copy their HTML, CSS, logos or images.
- Essays must stay true to the item's meaning. The writer's system prompt requires this.

## Cost

The target is under $0.05 per essay; the current measured cost is about $0.04. Most of it is web searches ($0.01 each) plus the search-result tokens the research model reads. Check the per-call cost that every `generate` run prints, or `api.estimated_cost_usd` in post JSON, before and after changing models, effort or search settings. `--dry-run` is the free way to iterate on prompt text.

## Prompt changes

For a meaningful change, create a new `prompts/essay_vN/` folder and switch `ACTIVE_PROMPT`, instead of editing a version that already has published posts. That keeps each post's recorded `prompt_version` accurate.
