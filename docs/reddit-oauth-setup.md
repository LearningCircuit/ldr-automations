# Reddit OAuth setup

This page covers Reddit's developer-side setup. For the workflow setup, see [quickstart-reddit.md](quickstart-reddit.md).

## Account checklist

You'll need:

- A Reddit account dedicated to the bot. **Aged** (at least a few weeks old with normal posting/commenting history) to avoid Reddit's anti-spam detection.
- Reddit API access for your app (Reddit's 2024 policy requires per-app approval; submit early, wait 1–4 weeks).

## 1. Create the Reddit app

1. Sign in to <https://www.reddit.com> as the bot account (or your own account — the app owner doesn't have to be the bot user).
2. Go to <https://www.reddit.com/prefs/apps>.
3. Scroll to **"create another app..."** at the bottom.
4. Fill in:
   - **Name**: e.g. `my-ldr-bot` (purely cosmetic).
   - **App type**: **`script`**. Not `web app`. Not `installed app`. Script apps can use refresh tokens and don't require a public redirect URI.
   - **Description**: optional, brief.
   - **About URL**: optional.
   - **Redirect URI**: `http://localhost:8080`. Only used by the bootstrap script if you opt into refresh-token mode.
5. Click **create app**.

After creation, you'll see:

- A short string just under the app name (e.g. `abcXYZ_-1234567`). This is your **client ID**.
- A "secret" field. This is your **client secret**. Click "edit" if needed to reveal it.

Save both. You'll add them as `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` in your GitHub Actions secrets.

## 2. Pick a user agent string

Reddit **requires** a unique, descriptive user agent. Generic ones (`python-requests/2.x`, etc.) get throttled or banned.

Use this format:

```
python:<your-app-name>:<version> (by /u/<your-reddit-username>)
```

Example: `python:my-ldr-bot:v0.3 (by /u/learningcircuit)`

Save this as `REDDIT_USER_AGENT` in your secrets. (It's not technically secret, but storing it as a secret keeps it out of logs.)

## 3. Submit your app for Reddit API access

Since June 2023, Reddit requires per-app approval for non-personal use. Even for your own bot account.

1. Go to <https://support.reddithelp.com/hc/en-us/requests/new>.
2. Pick the "Developer" category.
3. Fill in the form with your app's name, intended use case, expected volume, and the subreddit(s) you'll operate in.

Approval can take **1–4 weeks**. **Start this before you need it.** Without approval, your authenticated API calls may be rate-limited aggressively or blocked.

## 4. Authentication mode

The workflow supports two modes. Pick one.

### Password mode (default, simpler)

Just add these secrets to your GitHub repo:

- `REDDIT_USERNAME` — bot account username
- `REDDIT_PASSWORD` — bot account password

PRAW handles authentication on every run using the script app's credentials.

**Pros**: minimal setup; no bootstrap step; survives Reddit's single-use refresh token policy.
**Cons**: password sits in your repo's secrets. For a single-purpose bot account this is acceptable risk, but use a unique password (not your personal Reddit password).

### Refresh-token mode (more secure)

1. Locally on your machine (NOT in CI), run:
   ```bash
   pip install praw==7.8.1
   export REDDIT_CLIENT_ID=...
   export REDDIT_CLIENT_SECRET=...
   export REDDIT_USER_AGENT='python:my-ldr-bot:v0.3 (by /u/your-username)'
   python scripts/reddit_oauth_bootstrap.py
   ```
2. A browser opens to Reddit's authorisation page. Sign in **as the bot account** (not your personal account) and click "allow".
3. Reddit redirects to `http://localhost:8080?code=...`. The bootstrap script catches the code, exchanges it for a refresh token, and prints the token.
4. Copy the printed token. Add as `REDDIT_REFRESH_TOKEN` in your GitHub repo's secrets.
5. **Do not** also set `REDDIT_USERNAME` / `REDDIT_PASSWORD` — the workflow prefers refresh-token mode when both are present.

**Pros**: no password in secrets; revocable by deauthorising the app at <https://www.reddit.com/prefs/apps>.
**Cons**: Reddit's single-use refresh token policy means PRAW gets a new token on each call. Workflow runs **can't update GitHub secrets**, so the stored token can become invalidated. If runs start failing with auth errors, re-bootstrap.

For most users, **password mode is simpler and we recommend starting there**. Switch to refresh-token mode only if your threat model requires it.

## 5. Verify it works

Once your secrets are set in the repo and your caller workflow exists, trigger a run with `workflow_dispatch` and **`dry-run: true`**. Watch the logs. The bot should:

- Authenticate to Reddit successfully (no `OAuthException`)
- Fetch posts from your subreddit
- Print what it would have posted

If you see auth errors:

- Double-check the four secrets are present and spelled correctly.
- For password mode: verify the password is right by logging into Reddit manually as the bot account.
- For refresh-token mode: re-run `reddit_oauth_bootstrap.py` and update the secret.
- For "user agent" errors: confirm `REDDIT_USER_AGENT` matches the required format.
- For "API access not approved" errors: wait for Reddit's developer team to approve your app.
