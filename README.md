# Daily Excellence

<p align="center"><b>One positive idea to start every day.</b></p>

<p align="center">
  <a href="https://masonnicoletti.github.io/daily-excellence/">
    <img src="https://img.shields.io/badge/Read_today%27s_essay-%E2%86%92-ef8a6f?style=for-the-badge" alt="Read today's essay">
  </a>
</p>

<p align="center"><a href="https://masonnicoletti.github.io/daily-excellence/">masonnicoletti.github.io/daily-excellence</a></p>

## Overview

Daily Excellence delivers one short, thoughtful essay every morning, each built around a single idea for living well from Personal Excellence's list articles. Instead of reading a hundred suggestions at once, you get one a day, explored through a real person's story and a few concrete ways to put it into practice. Behind the scenes, an automated pipeline runs before 5 AM Eastern: it picks an idea at random, has Claude research real sources on the web and write the essay, then publishes it to this site on GitHub Pages alongside an archive of every past essay.

## Motivation
It was years ago that I came across the Personal Excellence website. I remember stumbling across the article titled *101 Ways To Be a Better Person*, and being absolutely filled with good energy from each of the ideas the article offered. But there was a problem; I read all 101 of these items in bulk, and each individual suggestion had little room to register. I wanted each suggestion to resonate deeper with me. So I kept the article open in Safari for ages, and I went back to it on occasion to read some of the ideas, but for the most part it just sat in the back of my browser tabs unaddressed.

Then the solution came to me. I wanted consume a single idea consistently, and have enough time to let that single idea resonate with me so that I can truly focus on it. So I needed a way to absorb one item at a time without being burdened by the surroundedness of many brilliant ideas that would only dilute the potential of a single one to make an impact. And I specifically needed a system that would allow consuming these ideas to be routine.

That is where the idea for this project was born. Out of the hope to turn a repository of wonderful ideas into an elegant delivery system that would embed directed positivity in my life. From the desire to work on my own personal excellence on a daily basis, with meaningful focus.

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

For paste formats and the `- ` (sub-item) and `+ ` (follow-up) markers, see [docs/ADDING_SOURCES.md](docs/ADDING_SOURCES.md).

## Prompt versions

Prompts live in `prompts/essay_vN/`. To experiment, copy the latest folder, edit it, and set `ACTIVE_PROMPT` in `src/daily_excellence/config.py`. Every post records the prompt version, models, and structure plan that produced it.

- `essay_v1`: one model searches and writes (Opus, about $0.36 per essay)
- `essay_v2`: Haiku researches, Sonnet writes (about $0.04 per essay)

What changed in each version, and why, is in [docs/PROMPT_CHANGELOG.md](docs/PROMPT_CHANGELOG.md).

## Docs

- [ADDING_SOURCES.md](docs/ADDING_SOURCES.md): how to paste and ingest a new article
- [PROMPT_CHANGELOG.md](docs/PROMPT_CHANGELOG.md): prompt versions, the reasons for each, and measured costs
- [OPERATIONS.md](docs/OPERATIONS.md): manual runs, backfilling a missed day, billing locks, costs, and secrets
- [COMPLIANCE.md](docs/COMPLIANCE.md): the source site's Terms of Use and how this project follows them

## Attribution

Daily ideas are adapted from free articles by [Personal Excellence](https://personalexcellence.co/), used under the license in their Terms of Use. Each post links to the specific article it draws from. This is an independent project, not affiliated with or endorsed by Personal Excellence. See [docs/COMPLIANCE.md](docs/COMPLIANCE.md).
