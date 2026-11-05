# Daily Excellence

A daily motivational essay. Every morning (before 5 AM US Eastern) a GitHub Actions workflow picks a random idea from a small collection of list articles, has Claude research and write a short essay about it, and publishes it to GitHub Pages along with the full archive.

## How it works

1. **Ingest** (manual, once per article): paste an article's text into `data/raw/`, then run `ingest` to turn it into `data/sources/<slug>.json`.
2. **Select**: a random item that hasn't been used yet (`data/history.json`).
3. **Research**: Claude Haiku runs 2 web searches and returns short notes. Only pages the search actually returned are kept.
4. **Write**: Claude Sonnet writes a 300–600 word essay from those notes, following a randomly varied structure plan.
5. **Publish**: the post is saved to `data/posts/<date>.json`, and the site is rebuilt from all posts and deployed.

Estimated cost is about $0.04 per essay, and each post records its own estimate.

## Commands

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env        # never committed

export PYTHONPATH=src
.venv/bin/python -m daily_excellence.ingest data/raw/<file>.txt --title "<Article Title>" --source-url "<url>"
.venv/bin/python -m daily_excellence.generate --random --dry-run    # show prompts (free)
.venv/bin/python -m daily_excellence.generate --random              # test essay -> data/drafts/
.venv/bin/python -m daily_excellence.render --drafts                # preview drafts -> site_preview/
.venv/bin/python -m daily_excellence.pipeline                       # the real daily run
.venv/bin/python -m pytest -q
```

In the raw file, prefix nested sub-items with `- ` so they stay with their parent item.

## Prompt versions

Prompts live in `prompts/essay_vN/`. To experiment, copy the latest folder, edit it, and set `ACTIVE_PROMPT` in `src/daily_excellence/config.py`. Every post records the prompt version, models, and structure plan that produced it.

- `essay_v1`: one model searches and writes (Opus, about $0.36 per essay)
- `essay_v2`: Haiku researches, Sonnet writes (about $0.04 per essay)

## Attribution

Daily ideas are adapted from free articles by [Personal Excellence](https://personalexcellence.co/), used under the license in their Terms of Use. Each post links to the specific article it draws from. This is an independent project, not affiliated with or endorsed by Personal Excellence. See [docs/COMPLIANCE.md](docs/COMPLIANCE.md).
