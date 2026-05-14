# Quickstart: Reddit QA

Run an LDR-powered bot that polls a subreddit, researches qualifying posts, and posts the result as a reply.

**This is the most complex of the three workflows.** Plan for ~30 minutes of setup, plus a multi-week wait for Reddit's API approval.

## Prerequisites

### Reddit-side setup (one-time, manual)

1. **Bot account.** Register a Reddit account dedicated to the bot. **Don't use a brand-new account** — Reddit's spam detection flags posting bots that use fresh accounts. Either age an account for a month with normal activity, or use an existing account you own.

2. **Reddit app.** Go to <https://www.reddit.com/prefs/apps>, click **"create another app"**. Choose type **"script"**. Set redirect URI to `http://localhost:8080` (only used if you opt into refresh-token mode).
   - Note the **client ID** (the short string under your app name).
   - Note the **client secret**.

3. **Reddit API access.** Since 2024, Reddit requires app approval. Submit your app via the Reddit developer portal. **Approval can take 1–4 weeks** — start this early.

4. **User agent string.** Pick a unique one in this format: `python:<your-app-name>:v0.3 (by /u/<your-username>)`. Reddit blocks generic user agents.

### API keys

Same as the other workflows. Sign up for:

- OpenRouter — <https://openrouter.ai/keys>
- Serper.dev — <https://serper.dev/api-key>

## 1. Add GitHub Actions secrets

In **your own repo** (where the caller workflow will live), go to **Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|---|---|
| `OPENROUTER_API_KEY` | Your OpenRouter key |
| `SERPER_API_KEY` | Your Serper.dev key |
| `REDDIT_CLIENT_ID` | From the Reddit app you registered |
| `REDDIT_CLIENT_SECRET` | From the Reddit app |
| `REDDIT_USER_AGENT` | The UA string you picked |

Then add **one of two auth modes**:

### Password mode (simpler, recommended for MVP)

| Secret | Value |
|---|---|
| `REDDIT_USERNAME` | Bot's Reddit username |
| `REDDIT_PASSWORD` | Bot's Reddit password |

### Refresh-token mode (more secure, no password in CI)

Run [`scripts/reddit_oauth_bootstrap.py`](../scripts/reddit_oauth_bootstrap.py) locally once to generate a refresh token, then add:

| Secret | Value |
|---|---|
| `REDDIT_REFRESH_TOKEN` | Output of the bootstrap script |

(Omit `REDDIT_USERNAME` and `REDDIT_PASSWORD` if using refresh-token mode.) See [reddit-oauth-setup.md](reddit-oauth-setup.md) for details.

## 2. Copy the caller workflow

Save as `.github/workflows/reddit-qa.yml` in your repo. Edit the marked lines (subreddit, bot username):

```yaml
name: Reddit QA Bot

on:
  schedule:
    - cron: '*/30 * * * *'
  workflow_dispatch:
    inputs:
      dry-run:
        type: boolean
        default: false

permissions: {}

jobs:
  run:
    permissions:
      contents: read
      actions: write
    uses: LearningCircuit/ldr-automations/.github/workflows/reddit-qa.yml@v0.3.0
    with:
      toolkit-ref: v0.3.0
      subreddit: LocalLLM           # ← your subreddit (without r/)
      bot-username: my-ldr-bot      # ← bot account's Reddit username
      max-posts-per-run: 3
      dry-run: ${{ inputs.dry-run || false }}
    secrets:
      OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
      SERPER_API_KEY: ${{ secrets.SERPER_API_KEY }}
      REDDIT_CLIENT_ID: ${{ secrets.REDDIT_CLIENT_ID }}
      REDDIT_CLIENT_SECRET: ${{ secrets.REDDIT_CLIENT_SECRET }}
      REDDIT_USER_AGENT: ${{ secrets.REDDIT_USER_AGENT }}
      REDDIT_USERNAME: ${{ secrets.REDDIT_USERNAME }}
      REDDIT_PASSWORD: ${{ secrets.REDDIT_PASSWORD }}
```

## 3. First run

**Always start with `dry-run: true`.** Use the **Actions tab → Reddit QA Bot → Run workflow** UI, check the dry-run box, run.

The bot will:
1. Poll the subreddit for newest posts.
2. Filter by age window (default: 6–24 hours old).
3. Skip posts where the bot has already commented.
4. Classify with a cheap LLM (`anthropic/claude-haiku-4.5` by default).
5. Run LDR research on each `OK` candidate (capped at `max-posts-per-run`).
6. **Print** what it would post. **No actual replies sent.**

Review the workflow logs. Check the research markdown looks reasonable. Then disable dry-run and let the cron schedule take over.

## How the gating works

There are three independent gates before a comment gets posted:

1. **Age window**: posts younger than `min-post-age-hours` (default 6) or older than `max-post-age-hours` (default 24) are skipped. The min-age window is also the primary mitigation against double-posting when the bot's earlier comment gets mod-removed (which appears as `author=None` and is indistinguishable from any other removed comment via the API).
2. **Already-replied check**: walks the submission's comment tree, skips if a comment by the bot's username is found.
3. **Cheap classifier**: a single cheap-model LLM call categorises each candidate as `OK | SKIP_SENTIMENT | SKIP_LOWINFO | SKIP_NSFW`. Only `OK` proceeds to research. The classifier is fail-open — if OpenRouter blips, the bot proceeds (treating the post as `OK`) rather than going silent.

## Cost

At default settings (every 30 min, max 3 posts per run, 1 subreddit), expect roughly **$5/month**:

- ~1,440 cron runs/month × ~3 classifier calls per run = ~4,300 cheap-model calls. At Haiku-tier pricing, ~$0.40/month.
- Of those, maybe ~5% pass all three gates → ~70 LDR research calls/month at ~$0.05 each = ~$3.50/month.
- Serper.dev's free tier covers ~2,500 queries/month; you'll likely stay within it.
- GitHub Actions minutes are free for public repos.

The `max-posts-per-run` cap is the cost fail-safe. If something goes wrong and a subreddit suddenly produces 50 candidates per run, the bot still tops out at 3.

## Killswitch

There are two ways to stop the bot:

1. **Per-run**: trigger via `workflow_dispatch` with `dry-run: true`.
2. **Per-deployment**: set a repository variable `LDR_REDDIT_KILLSWITCH=true`. (Wire this into the workflow's `if:` conditions when you adopt it.)
3. **Permanently**: disable the workflow under **Actions → Reddit QA Bot → … → Disable workflow**.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `startup_failure` with zero jobs | Missing `actions: write` permission on the calling job |
| Workflow runs but `count` is always 0 | All posts filtered out: check the age window, the bot-username (case-insensitive but must exist), or whether the classifier is over-skipping |
| `Reddit API approval required` errors | Your Reddit app hasn't been approved yet. Wait. |
| Single-use refresh token expired | Reddit invalidates refresh tokens on use; PRAW handles this if you re-bootstrap. Easier path: switch to password auth. |
| Bot got banned from a subreddit | Stop the workflow. Reach out to subreddit mods. |
