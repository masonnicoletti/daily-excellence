# Prompt changelog

Prompts live in `prompts/essay_vN/`, and `ACTIVE_PROMPT` in `src/daily_excellence/config.py` selects one. Every post records its `prompt_version`, models, and structure plan (`variation`), so posts can be compared across versions. For a meaningful change, add a new version rather than editing one that already has posts.

Costs are the measured `api.estimated_cost_usd` values.

## essay_v3 (active since 2026-11-24; first post expected 2026-11-25)

**Layout:** same two stages as v2 (Haiku 5.5 researches with at most 2 searches; Sonnet 5.5 at low effort writes). No model or effort changes.

**Why:** v2 essays were pleasant but shallow. The 2026-11-24 essay ("Find a role model") packed 4 sections into 400 words and argued nothing beyond the idea itself. It used a story that didn't support its point, named its own parts ("Here's the reframe:"), and cited a commercial herbal-remedy site.

**Other changes from v2:**
- **One depth angle per essay** instead of 1–3 shuffled optional sections. The angle is one of five: why it works, a common misconception, the cost or tension, done well vs. done badly, or where it comes from. Each angle has a `research` and a `writer` instruction, so it steers both stages. The order is fixed: story, then angle, then application.
- **Writer rules for depth:**
  - one central insight beyond the idea's own text
  - the story must support it
  - one honest objection answered
  - precise actions (when, where, how)
  - no signposting the structure
  - a final one-sentence check
  - fairness to real people (no judging private choices, no title that criticizes a real person)
- **Research:** one detailed story (situation, choice, cost, result) plus material for the angle. A source-quality bar (prefer interviews, established outlets, journals, universities; avoid sales pages, content farms, unproven-treatment sites). Cap raised from 250 to 400 words.
- **Lengths:** 450, 550 or 650 words (300 dropped).

**Measured:** $0.041 for #4, Find a role model (angle "the cost or tension"; research $0.025, writing $0.017; 594 words). The sources were The Hollywood Reporter and TODAY. The essay argued one clear point and gave specific actions. That test also showed the angle could slip into judging a real person, so the fairness rule was added before the first post. The researcher also cited a misinformation-site page that wasn't in its search results; the existing URL check dropped it.

## essay_v2 (2026-11-04 to 2026-11-24)

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
