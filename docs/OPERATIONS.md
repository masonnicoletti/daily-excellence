# Operations

## Normal schedule

GitHub's scheduled runs are best-effort. In November 2026 they started 6–10 hours late, and some were dropped, so essays are **prepared the evening before and revealed at 5 AM Eastern**.

- `.github/workflows/daily.yml` has seven cron times, from about 6 PM to 4 AM Eastern plus a 6:47 AM catch-up run, all at :47 (off-peak).
- **Which essay a run writes** (`pipeline.edition_date`): from 5 PM Eastern on, tomorrow's; before 5 PM, today's (a catch-up if the evening runs never came). Only the first run that starts does any work. Later runs find the post, skip generation, and only redeploy.
- **The reveal:** a script in every page's `<head>` (`templates/base.html`) hides any essay whose date hasn't reached 5 AM Eastern: the home page's top essay, Recent, the archive, Favorites, and an essay page's "Next" link. Until then the previous essay stays on top. The hiding is visual only: an unreleased essay's page exists at its URL, but nothing links to it.
- Each run tests, runs the pipeline, commits `data/posts/` and `data/history.json`, and deploys to https://masonnicoletti.github.io/daily-excellence/.

- **Run now:** go to Actions, then Daily Excellence, then Run workflow. After 5 PM Eastern this prepares tomorrow's essay. Before 5 PM it creates today's if it's missing. If that post already exists, it only rebuilds and deploys, so it's free.
- **Checking the schedule:** the run history (Actions tab, or `https://api.github.com/repos/masonnicoletti/daily-excellence/actions/runs`) shows each run's trigger (`schedule`, `workflow_dispatch`, `push`) and start time.
- **Pushing code or templates** redeploys without writing an essay.
- **Failures** email you when GitHub's Actions notifications are on (GitHub, then Settings, then Notifications).

## Backfill a missed day

From a clean, up-to-date `main`, with `.env` holding the API key:

```bash
git pull --rebase
PYTHONPATH=src .venv/bin/python -m daily_excellence.pipeline --date 2026-11-06   # about $0.04
git add data/posts data/history.json && git commit -m "Backfill 2026-11-06" && git push
```

The push redeploys the site. To leave a gap instead, do nothing; the archive is fine with missing days.

## If Actions won't start: "account is locked due to a billing issue"

This happened on 2026-11-05. The pipeline itself costs nothing on GitHub: public-repo Actions and Pages are free, and billable usage was $0. The cause was the account.

1. **Cause:** an education coupon (GitHub Pro) expired with no payment method on file. The account then failed to charge for Pro, and Actions was blocked even though the plan showed GitHub Free.
2. **Fix:** re-verify student status at education.github.com, approved 2026-11-05 with benefits about 72 hours later. If the lock remains after that, contact GitHub Support (Billing) and explain that billable usage is $0 on a public repo.
3. **Prevent it:** set a reminder before the coupon's expiry date (shown on the billing page) to renew student status or switch to GitHub Free. This project never needs Pro.

## Costs and limits

- **Anthropic:** about $0.04 per essay, roughly $1.20 a month. Keep a monthly spend limit in the Anthropic Console (Settings, then Limits). Per-post estimates are in each post's `api.estimated_cost_usd`.
- **Changing models, effort, or searches:** edit `src/daily_excellence/config.py`. Measure one `generate --item-id <id>` run (paid) before relying on it.

## Secrets

- **Rotating the API key:** create a new key in the Anthropic Console, update `.env` locally and the `ANTHROPIC_API_KEY` repository secret (Settings, then Secrets and variables, then Actions), then delete the old key.

## Things to watch

- **Inactive repos:** GitHub may disable scheduled workflows in a repo it considers inactive for 60 days. If you get that email, re-enable the workflow from the Actions tab.
- **Pool size:** 404 ideas across 4 sources. Selection never repeats an item until all have been used (`data/history.json`).
