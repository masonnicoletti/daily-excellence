# Adding a source article

Each source is one free Personal Excellence list article, pasted by hand and turned into `data/sources/<slug>.json`. The daily pipeline then draws ideas from all sources at random.

## Rules (from the site's Terms of Use, see [COMPLIANCE.md](COMPLIANCE.md))

- **Copy by hand only.** No scripts, scrapers, or fetch tools on personalexcellence.co.
- **Free blog articles only.** No ebooks, courses, or other paid material.
- **At most 10 articles in total.** `ingest` refuses an 11th.

## Steps

1. Create `data/raw/<slug>.txt`, named after the article (for example `101-ways-to-be-a-better-person.txt`). This folder is gitignored, so pastes stay on your machine.
2. Paste the article text from the browser and save it.
3. **Trim the end.** Delete everything after the last list item: author bio, related posts, comments, newsletter boxes. Every line after the intro becomes an item.
4. Mark structure, if any (see the next section).
5. Run:
   ```bash
   PYTHONPATH=src .venv/bin/python -m daily_excellence.ingest data/raw/<slug>.txt \
       --title "<exact article title>" --source-url "<article url>"
   ```
6. Check the output. A message like "Title says 101 items but N were found" usually means sub-items are unmarked or there's leftover footer text. If the article cross-references its own items ("see #44"), confirm those numbers match.
7. Commit only `data/sources/<slug>.json`.

## Formats it understands

The format is detected automatically.

| Paste looks like | Example | Notes |
|---|---|---|
| Numbered items | `12. Be Bold` + body lines | Used when the numbers survive the paste |
| One item per line | `Be Bold. Life is an adventure.` | The title is the first sentence. A stray leading `1. ` is dropped |
| Term: text | `Ability: is more of a function of…` | Split at the colon. The post page reads it as one sentence |
| Questions | `Who are you? How would you describe yourself?` | The title is the first question |

**Where the list starts:** after the last short line ending in `:` in the first half of the file, such as "Here goes:" or "I present to you, 101 …:". If an article has no such line, pass `--start-after "<the line just before item 1>"`.

**Trailing reading links** like `Read: X` or `(Read: X)` are moved out of the body into `related_read`.

## Markers you can add

| Prefix | Meaning | Used in |
|---|---|---|
| `- ` | **Sub-item.** Nested inside the item above. Never a daily message by itself, but given to the writer as related practices | 101 Ways To Be a Better Person (41 sub-items), 101 Ways To Live Your Life To The Fullest (2) |
| `+ ` | **Follow-up.** Its own daily item and number, with the question(s) before it attached as context | 101 Questions To Ask Yourself in Life (41 follow-ups) |

To leave out an item, such as "What are you going to do differently after reading this article?", delete its line. Before hand-editing a paste, save a backup as `<slug>.original.txt`.

## Current sources (4 of 10)

| Article | Items | Notes |
|---|---|---|
| 101 Ways To Be a Better Person | 101 | 41 nested sub-items |
| 101 Life Principles To Live By Daily | 101 | Term: text format |
| 101 Ways To Live Your Life To The Fullest | 101 | 2 sub-items under #10 |
| 101 Questions To Ask Yourself in Life | 100 | 41 follow-ups; #101 left out |
