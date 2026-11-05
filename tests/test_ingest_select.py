import ast
import json
import random
from pathlib import Path

import pytest

from daily_excellence import ingest, select_item

SAMPLE = """Intro paragraph about the article that should be ignored.

1. Wake up early
Starting the day early gives you quiet time.

It compounds over weeks.

2) Read a book
Reading widens your perspective.

3. Exercise
Move your body every day.
"""
URL = "https://personalexcellence.co/blog/sample/"


def test_parse_items():
    items, warnings = ingest.parse_items(SAMPLE)
    assert [i["number"] for i in items] == [1, 2, 3]
    assert items[0]["title"] == "Wake up early"
    assert "compounds" in items[0]["body"]
    assert warnings == []


def test_parse_warns_on_gaps_and_empty_body():
    _, warnings = ingest.parse_items("1. A\ntext\n3. C\n")
    assert any("missing=[2]" in w for w in warnings)
    assert any("no body" in w for w in warnings)


LINES = """3 Ways To Test
by Someone
Intro paragraph.

Here goes:

Be Bold. Life is an adventure. Read: How To Overcome Fear
Be Committed... to your goals. Stick to it.
Be Curious.
- Ask questions — often. The more you ask, the more you learn.
- Get feedback. Others see our blind spots.
"""


def test_line_mode_nests_subitems():
    items, warnings = ingest.parse_items(LINES)
    assert [i["number"] for i in items] == [1, 2, 3]
    assert items[0]["title"] == "Be Bold"
    assert items[0]["body"] == "Life is an adventure."
    assert items[0]["related_read"] == "How To Overcome Fear"
    assert items[1]["title"] == "Be Committed... to your goals"
    assert [s["title"] for s in items[2]["subitems"]] == ["Ask questions — often", "Get feedback"]
    assert warnings == []  # bare heading with subitems is fine
    src, w = ingest.build_source(LINES, "3 Ways To Test", URL)
    assert src["items"][2]["id"] == "3-ways-to-test-003"
    assert w == []


TERMS = """2 Life Principles
Intro paragraph that is long, ending with a colon, the way some articles introduce lists:
Ability: is more of a function of time. Read: 10,000 Hours To Develop Talent
Beauty, #2: There is no one standard of beauty. You are beautiful as you are.
"""


def test_term_style_splits_at_colon():
    items, warnings = ingest.parse_items(TERMS)
    assert [(i["title"], i.get("joiner")) for i in items] == [("Ability", ": "), ("Beauty, #2", ": ")]
    assert items[0]["body"] == "is more of a function of time."
    assert items[0]["related_read"] == "10,000 Hours To Develop Talent"
    assert warnings == []


def test_split_title_quote_and_stray_number():
    assert ingest.split_title("Rather than think “what if,” think “next time.” Don’t dwell.") == (
        "Rather than think “what if,” think “next time.”", "Don’t dwell.")
    items, _ = ingest.parse_items("Here goes:\n1. Live fresh. Every day.\nBe proactive. Act.\n")
    assert [i["title"] for i in items] == ["Live fresh", "Be proactive"]


QUESTIONS = """3 Questions
Some things to note:
A note.
I present to you, 3 questions:
What are you grateful for? (Read: 14-Day Gratitude Challenge)
Is there a grudge you are holding on to?
+ …Why are you holding on to it?
+ …Is it time to let it go?
"""


def test_follow_up_questions_get_context():
    items, _ = ingest.parse_items(QUESTIONS)
    assert [i["number"] for i in items] == [1, 2, 3, 4]       # starts after the LAST intro colon line
    assert items[0]["body"] == "" and items[0]["related_read"] == "14-Day Gratitude Challenge"
    assert "context" not in items[1]
    assert ingest.split_related("Find it. Read: Life Purpose (7-part series)") == ("Find it.", "Life Purpose (7-part series)")
    assert items[2]["context"] == ["Is there a grudge you are holding on to?"]
    assert items[3]["context"] == ["Is there a grudge you are holding on to?", "…Why are you holding on to it?"]


def test_line_mode_count_mismatch_warns():
    flat = LINES.replace("- ", "")
    _, w = ingest.build_source(flat, "3 Ways To Test", URL)
    assert any("Title says 3" in x for x in w)


def test_build_source_requires_pe_url():
    with pytest.raises(ValueError):
        ingest.build_source(SAMPLE, "Sample", "https://example.com/x")
    src, _ = ingest.build_source(SAMPLE, "Sample List", URL)
    assert src["items"][0]["id"] == "sample-list-001"
    assert URL in src["attribution"]


def test_article_cap(tmp_path):
    for n in range(ingest.MAX_SOURCE_ARTICLES):
        src, _ = ingest.build_source(SAMPLE, f"Article {n}", URL)
        ingest.write_source(src, tmp_path)
    src, _ = ingest.build_source(SAMPLE, "Article 0", URL)
    ingest.write_source(src, tmp_path)  # overwriting an existing one is allowed
    src, _ = ingest.build_source(SAMPLE, "Eleventh", URL)
    with pytest.raises(ValueError, match="cap"):
        ingest.write_source(src, tmp_path)


def test_ingest_has_no_network_imports():
    banned = {"urllib.request", "requests", "httpx", "http.client", "aiohttp", "socket", "anthropic"}
    tree = ast.parse(Path(ingest.__file__).read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported |= {node.module} | {f"{node.module}.{a.name}" for a in node.names}
    assert not imported & banned


def _setup(tmp_path):
    src, _ = ingest.build_source(SAMPLE, "Sample", URL)
    ingest.write_source(src, tmp_path / "sources")
    return tmp_path / "sources", tmp_path / "history.json"


def test_pick_no_repeats_then_reset(tmp_path):
    sources, hist = _setup(tmp_path)
    rng = random.Random(0)
    ids = [select_item.pick(f"2026-11-0{d}", sources_dir=sources, history_file=hist, rng=rng)["id"]
           for d in range(1, 4)]
    assert len(set(ids)) == 3
    fourth = select_item.pick("2026-11-04", sources_dir=sources, history_file=hist, rng=rng)
    assert json.loads(hist.read_text())[-1].get("cycle_reset") is True
    fifth = select_item.pick("2026-11-05", sources_dir=sources, history_file=hist, rng=rng)
    assert fifth["id"] != fourth["id"]


def test_pick_is_idempotent_per_date(tmp_path):
    sources, hist = _setup(tmp_path)
    a = select_item.pick("2026-11-04", sources_dir=sources, history_file=hist)
    b = select_item.pick("2026-11-04", sources_dir=sources, history_file=hist)
    assert a["id"] == b["id"]
    assert len(json.loads(hist.read_text())) == 1
    assert a["source_url"] == URL
