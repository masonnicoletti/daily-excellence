import random
from types import SimpleNamespace as NS

from daily_excellence import config, generate

ITEM = {
    "id": "x-072", "number": 72, "title": "Be Optimistic / Positive", "body": "For life is too short to be negative.",
    "source_title": "101 Ways To Be a Better Person", "source_url": "https://personalexcellence.co/blog/x/",
    "subitems": [{"title": "Smile", "body": "How often do you smile a day?"}],
}


def test_prompt_renders_with_variation():
    p = generate.load_prompt()
    v = generate.sample_variation(p["variation"], random.Random(1))
    assert v["sections"][-1].startswith("how to apply")
    assert any("real person" in s for s in v["sections"])
    user = generate.render_user_prompt(p["user_template"], ITEM, v)
    assert "#72" in user and "Smile" in user and str(v["length"]) in user


def test_variation_actually_varies():
    spec = generate.load_prompt()["variation"]
    plans = {str(generate.sample_variation(spec, random.Random(s))) for s in range(10)}
    assert len(plans) > 5


def test_web_search_blocks_source_site():
    assert "personalexcellence.co" in config.BLOCKED_DOMAINS
    assert generate.is_blocked("https://www.personalexcellence.co/blog/a")
    assert not generate.is_blocked("https://example.com/personalexcellence.co")


def _fake_content(essay):
    return [
        NS(type="text", text="Let me search for sources."),
        NS(type="server_tool_use"),
        NS(type="web_search_tool_result", content=[NS(url="https://good.example/story", title="Story")]),
        NS(type="text", text=essay),
    ]


def test_extract_and_clean():
    essay = (
        "# A Title\n\nBody text with [a link](https://good.example/story) and "
        "[PE](https://personalexcellence.co/blog/x/).\n\n## Sources\n"
        "- [Story](https://good.example/story/)\n- [Fake](https://made-up.example/)\n"
        "- [PE](https://personalexcellence.co/x)\n"
    )
    text, retrieved = generate.extract(_fake_content(essay))
    md = generate.essay_from_text(text)
    assert md.startswith("# A Title") and "Let me search" not in md
    body, sources, warnings = generate.clean_essay(md, retrieved)
    assert sources == [{"title": "Story", "url": "https://good.example/story/"}]
    assert "personalexcellence.co" not in body and "PE." in body
    assert len(warnings) == 3


def test_extract_tolerates_search_error_object():
    content = [NS(type="web_search_tool_result", content=NS(error_code="max_uses_exceeded")),
               NS(type="text", text="# T\n\nx")]
    md, retrieved = generate.extract(content)
    assert retrieved == {} and md.startswith("# T")


def test_parse_notes_keeps_only_retrieved_urls():
    text = (
        "## Real Story | https://good.example/story/\n- Fox said \"gratitude\".\n\n"
        "## Invented | https://made-up.example/x\n- fake\n\n"
        "## PE | https://personalexcellence.co/blog/x\n- source text\n"
    )
    notes, sources, warnings = generate.parse_notes(text, {"https://good.example/story": "Story"})
    assert list(sources) == ["https://good.example/story/"]
    assert "Fox said" in notes and "fake" not in notes and "source text" not in notes
    assert len(warnings) == 2


def test_v2_is_two_stage_and_v1_is_not():
    assert generate.load_prompt("essay_v2")["research_system"]
    assert generate.load_prompt("essay_v1")["research_system"] is None


def test_v2_prompts_render():
    p = generate.load_prompt("essay_v2")
    v = generate.sample_variation(p["variation"], random.Random(2))
    research_user = generate.render(p["research_template"], item=ITEM, v=v)
    assert "Be Optimistic" in research_user and "Smile" in research_user
    assert "No verified research" in generate.render_user_prompt(p["user_template"], ITEM, v, "")
    assert "NOTE-X" in generate.render_user_prompt(p["user_template"], ITEM, v, "NOTE-X")


def test_search_tool_matches_model():
    assert generate.search_tool("claude-haiku-5-5")["type"] == "web_search_20250305"
    assert generate.search_tool("claude-sonnet-5-5")["type"] == "web_search_20260209"
    assert generate.search_tool("claude-haiku-5-5")["blocked_domains"] == ["personalexcellence.co"]


def test_validate():
    long_body = "# T\n\n" + "word " * 300
    assert generate.validate(long_body, [{"url": "u", "title": "t"}]) == []
    assert any("no verified sources" in p for p in generate.validate(long_body, []))
    assert any("word count" in p for p in generate.validate("# T\n\nshort", [{"url": "u"}]))
