import json

from daily_excellence import ingest, pipeline, render

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
    archive = (tmp_path / "site" / "archive.html").read_text()
    for page in (post, index, archive):
        assert 'href="https://personalexcellence.co/' in page
        assert "not affiliated with or endorsed by Personal Excellence" in page
        assert "nofollow" not in page
    assert f'href="{URL}"' in post                      # link to the specific source article
    assert "<script>x</script>" not in post             # model output can't inject HTML
    assert "&lt;script&gt;x" in post                    # ...it is shown as text instead
    assert (tmp_path / "site" / ".nojekyll").exists()


def _seven_posts(tmp_path):
    posts = tmp_path / "posts"
    posts.mkdir()
    item = {"number": 1, "title": "Be Bold", "body": "", "subitems": [], "source_title": "S", "source_url": URL}
    for day in range(1, 8):
        post = fake_generate(item)
        post.update(title=f"Essay {day}", date=f"2026-11-0{day}", generated_at=f"2026-11-0{day}T08:31:00+00:00")
        (posts / f"2026-11-0{day}.json").write_text(json.dumps(post))
    render.build(posts, tmp_path / "site")
    return tmp_path / "site"


def test_home_shows_favorites_and_five_recent(tmp_path):
    site = _seven_posts(tmp_path)
    index = (site / "index.html").read_text()
    recent = index.split('id="recent-h"')[1].split("</section>")[0]
    # 6 rows are rendered; the 6th only shows while the newest essay is unreleased.
    assert recent.count("<li ") == 6 and recent.count("recent-extra") == 1
    assert "Essay 7" in recent and "Essay 1" not in recent
    assert '<li data-release="2026-11-02" class="recent-extra">' in recent
    assert 'data-total="7" data-dates="2026-11-07 2026-11-06">7</span> essays in the archive' in recent
    assert index.index('id="favorites-h"') < index.index('id="recent-h"')    # Favorites above Recent
    cards = json.loads(index.split('id="posts-data">')[1].split("</script>")[0])
    assert len(cards) == 7 and set(cards[0]) == {"slug", "title", "subtitle", "date", "date_short"}
    assert (site / "favorites.js").exists()


def test_archive_page_and_star_button(tmp_path):
    site = _seven_posts(tmp_path)
    index, archive = (site / "index.html").read_text(), (site / "archive.html").read_text()
    post = (site / "posts" / "2026-11-03.html").read_text()
    assert archive.count("<li ") == 7 and 'href="archive.html"' in index
    assert 'class="fav-button" type="button" data-slug="2026-11-03"' in post      # star at the top
    assert post.index("fav-button") < post.index("post-title")
    assert 'class="masthead-button" href="../archive.html"' in post                # header button on posts
    assert 'class="masthead-button" href="archive.html"' in index                 # same header button on home
    assert "button-secondary" not in index                                         # big Archive button removed


def test_newest_essay_can_be_hidden_until_release(tmp_path):
    site = _seven_posts(tmp_path)
    index = (site / "index.html").read_text()
    assert '<section class="hero" data-release="2026-11-07">' in index
    assert '<section class="hero hero-fallback" data-release="2026-11-06">' in index   # shown while 11-07 is hidden
    assert "window.DE_UNRELEASED" in index and "hourCycle" in index
    post = (site / "posts" / "2026-11-06.html").read_text()
    assert 'class="newer" data-release="2026-11-07"' in post                         # "Next" hides too


def test_edition_date_prepares_tomorrow_in_the_evening():
    import datetime as dt
    from zoneinfo import ZoneInfo
    et = ZoneInfo("America/New_York")
    at = lambda *a: dt.datetime(*a, tzinfo=et)
    assert pipeline.edition_date(at(2026, 11, 10, 16, 59)) == "2026-11-10"   # afternoon: today (catch-up)
    assert pipeline.edition_date(at(2026, 11, 10, 17, 0)) == "2026-11-11"    # from 5 PM: tomorrow
    assert pipeline.edition_date(at(2026, 11, 10, 23, 47)) == "2026-11-11"
    assert pipeline.edition_date(at(2026, 11, 11, 3, 47)) == "2026-11-11"    # overnight: the same morning
    # A UTC time converts correctly: 22:47 UTC in November is 5:47 PM EST.
    assert pipeline.edition_date(dt.datetime(2026, 11, 10, 22, 47, tzinfo=dt.timezone.utc)) == "2026-11-11"


def test_icons_are_linked_and_published(tmp_path):
    site = _seven_posts(tmp_path)
    for page, root in [(site / "index.html", ""), (site / "posts" / "2026-11-03.html", "../")]:
        html = page.read_text()
        assert f'rel="apple-touch-icon" href="{root}icons/apple-touch-icon.png"' in html
        assert f'rel="icon" href="{root}icons/favicon.svg"' in html
        assert f'rel="manifest" href="{root}site.webmanifest"' in html
    manifest = json.loads((site / "site.webmanifest").read_text())
    for icon in manifest["icons"]:
        assert (site / icon["src"]).exists()
    for name in ["favicon.svg", "favicon-32.png", "apple-touch-icon.png"]:
        assert (site / "icons" / name).exists()


def test_item_is_the_headline_and_essay_title_is_secondary(tmp_path):
    site = _seven_posts(tmp_path)          # item "Be Bold"; essay titles "Essay 1".."Essay 7"
    post = (site / "posts" / "2026-11-03.html").read_text()
    h1 = post.split("<h1")[1].split("</h1>")[0]
    assert "Be Bold" in h1 and "Essay 3" not in h1
    assert '<h2 class="essay-title">Essay 3</h2>' in post
    assert post.index("<h1") < post.index('class="essay-title"') < post.index('class="essay"')
    assert "<title>Be Bold · Daily Excellence</title>" in post
    index = (site / "index.html").read_text()
    assert '<p class="hero-subtitle">Essay 7</p>' in index
    row = index.split('id="recent-h"')[1].split("</li>")[0]
    assert row.index('archive-title">Be Bold') < row.index('archive-idea">Essay 7')


def test_follow_up_questions_read_on_their_own_in_lists(tmp_path):
    posts = tmp_path / "posts"; posts.mkdir()
    item = {"number": 48, "title": "…Is it time to let it go?", "body": "", "subitems": [], "source_title": "Q",
            "source_url": URL, "context": ["Is there a grudge you are holding on to?", "…Why are you holding on to it?"]}
    post = fake_generate(item); post["date"] = "2026-11-05"
    (posts / "2026-11-05.json").write_text(json.dumps(post))
    render.build(posts, tmp_path / "site")
    archive = (tmp_path / "site" / "archive.html").read_text()
    assert 'archive-title">Is there a grudge you are holding on to? …Is it time to let it go?' in archive
    page = (tmp_path / "site" / "posts" / "2026-11-05.html").read_text()
    assert ">…Is it time to let it go?</h1>" in page and 'class="idea-context"' in page


def test_asset_links_carry_a_content_version(tmp_path):
    import hashlib
    site = _seven_posts(tmp_path)
    css = hashlib.sha256((render.TEMPLATES_DIR / "style.css").read_bytes()).hexdigest()[:10]
    for page in [site / "index.html", site / "archive.html", site / "posts" / "2026-11-03.html"]:
        html = page.read_text()
        assert f'style.css?v={css}"' in html          # changes whenever style.css changes
        assert "favorites.js?v=" in html
