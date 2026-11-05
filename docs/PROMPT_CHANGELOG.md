# Prompt changelog

Prompts live in `prompts/essay_vN/`, and `ACTIVE_PROMPT` in `src/daily_excellence/config.py` selects one. Every post records its `prompt_version`, models, and structure plan (`variation`), so posts can be compared across versions. For a meaningful change, add a new version rather than editing one that already has posts.

Costs are the measured `api.estimated_cost_usd` values.

## essay_v2 (active since 2026-11-04)

**Layout:** two stages. Haiku 5.5 runs at most 2 web searches and returns short notes, keeping only pages the search actually returned. Sonnet 5.5 at low effort writes from those notes with no tools.

**Why:** the essay_v1 setup cost about $0.36 per essay, against a target under $0.05. Search results were most of the input tokens, so the cheaper model now reads them and the writer reads only the notes.

**Other changes from v1:**
- Lengths are 300, 400, 500 or 600 words, instead of up to 800.
- The writer may use only facts, quotes and people found in the notes.

**Measured:** $0.039 for #39, Be Empathetic (research $0.024, of which searches $0.020; writing $0.015).

**Edits made in place:**
- **2026-11-04:** added "never mention the notes or how the essay was made". The first v2 essay included the sentence "The research notes add a useful detail."; that sentence was removed by hand from post `2026-11-04-2`.
- **2026-11-05:** template changes for new source formats. Items now join title and body with their own `joiner`, and follow-up questions carry `context`. Output for existing items is unchanged.
- **2026-11-05:** items may carry a writer's `note`, used by both prompts. It was added for 101 Questions #101.

## essay_v1 (2026-11-04)

**Layout:** one call. Opus 5.5 at medium effort searches (up to 5 times) and writes the essay.

**Measured:** $0.36 for #72, Be Optimistic / Positive ("The Optimist Is Made, Not Born", post `2026-11-04`), with 8 verified sources.

**Also tried:** the same layout on Sonnet 5.5 at low effort with 2 searches measured $0.135. It was never saved as a version, because most of the cost was still the 50K tokens of search results.

## Template for new entries

```
## essay_vN (active since YYYY-MM-DD)
Layout:
Why:
Other changes from v(N-1):
Measured: $X.XXX on <item>; observations on quality
```
