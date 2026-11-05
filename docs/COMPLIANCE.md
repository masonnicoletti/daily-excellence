# Source Terms of Use Compliance

Source: personalexcellence.co. Terms of Use last modified **February 1, 2025** (version reviewed). Recheck periodically; the Terms can change at any time.

## Rules this project follows
1. **No automated access.** Source articles are copied and pasted by hand into `data/raw/`. No code fetches personalexcellence.co. Claude's web search is configured with `blocked_domains` for the domain, and citations on it are stripped.
2. **Free Content only.** No products, courses, ebooks or coaching material.
3. **Attribution on every use.** Each post, the index and the README carry a visible, plain `<a href>` link (no `nofollow`) to the specific source article, plus attribution to Personal Excellence.
4. **Maximum 10 source articles.** Enforced by `ingest.py`.
5. **Stay true to the message.** Essays must faithfully reflect the selected item. No satire or hate.
6. **No implied relationship.** Footer disclaimer on every page: independent project, not affiliated with or endorsed by Personal Excellence.
7. **No copying of Site Design or trademarks.** Original HTML, CSS and layout. No logos, images or fonts from the site, and nothing hotlinked.
8. **No unreasonable reproduction.** Posts show only the selected item. Raw pasted text is gitignored.

## Open risks
- The committed `data/sources/*.json` contains full item text in a public repo. If the site owner objects, move it to a private repo that feeds a public site-only repo.
- The name "Daily Excellence" is close to "Personal Excellence". Rename if requested.
