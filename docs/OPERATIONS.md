# Operations

## Normal schedule

`.github/workflows/daily.yml` runs at 08:30 UTC (3:30 AM EST / 4:30 AM EDT). A backup run at 09:30 UTC does nothing if the day's post already exists. Each run tests, generates the US Eastern day's essay, commits `data/posts/` and `data/history.json`, and deploys the site to https://masonnicoletti.github.io/daily-excellence/.

- **Run now:** go to Actions, then Daily Excellence, then Run workflow. If today's post already exists, this only rebuilds and deploys, so it's free.
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
