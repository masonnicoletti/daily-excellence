import json

from daily_excellence import ingest, pipeline

URL = "https://personalexcellence.co/blog/sample/"
RAW = "Intro.\n\nHere goes:\n\nBe Bold. Life is an adventure.\nBe Kind. Don't criticize.\n"


def fake_generate(item):
    return {
        "title": "A Test Essay", "essay_markdown": "First paragraph <script>x</script>.\n\n## Part\n\nMore.",
        "sources": [{"title": "Story", "url": "https://good.example/story"}], "word_count": 300,
        "item": item, "prompt_version": "essay_v2", "model": "claude-sonnet-5-5",
        "research_model": "claude-haiku-5-5", "warnings": [], "api": {"estimated_cost_usd": 0.04},
        "generated_at": "2026-11-05T08:31:00+00:00",
    }


def _setup(tmp_path, monkeypatch):
    src, _ = ingest.build_source(RAW, "2 Ways To Test", URL)
    ingest.write_source(src, tmp_path / "sources")
    return dict(posts_dir=tmp_path / "posts", site_dir=tmp_path / "site", sources_dir=tmp_path / "sources",
                history_file=tmp_path / "history.json", generate_fn=fake_generate)


def test_pipeline_creates_post_and_is_idempotent(tmp_path, monkeypatch):
    kw = _setup(tmp_path, monkeypatch)
    assert pipeline.run("2026-11-05", **kw) is not None
    calls = []
    kw["generate_fn"] = lambda item: calls.append(item)
    assert pipeline.run("2026-11-05", **kw) is None and calls == []  # second run: no new essay
    assert len(json.loads((tmp_path / "history.json").read_text())) == 1


def test_rendered_pages_meet_attribution_rules(tmp_path, monkeypatch):
    kw = _setup(tmp_path, monkeypatch)
    pipeline.run("2026-11-05", **kw)
    post = (tmp_path / "site" / "posts" / "2026-11-05.html").read_text()
    index = (tmp_path / "site" / "index.html").read_text()
    for page in (post, index):
        assert 'href="https://personalexcellence.co/' in page
        assert "not affiliated with or endorsed by Personal Excellence" in page
        assert "nofollow" not in page
    assert f'href="{URL}"' in post                      # link to the specific source article
    assert "<script>" not in post                       # model output can't inject HTML
    assert (tmp_path / "site" / ".nojekyll").exists()
