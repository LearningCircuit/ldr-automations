# Secrets and variables reference

Every meta-reusable in this toolkit expects these to live in **your own repo's** GitHub Actions secrets (Settings → Secrets and variables → Actions). Caller workflows pass them through explicitly — `secrets: inherit` won't work across organisation boundaries.

## Required for all workflows

| Secret | Purpose | Source |
|---|---|---|
| `OPENROUTER_API_KEY` | LLM provider for LDR research | <https://openrouter.ai/keys> |
| `SERPER_API_KEY` | Google search API used by LDR | <https://serper.dev/api-key> |

`GITHUB_TOKEN` is automatically provided by GitHub Actions; you don't need to add it.

## Required for Reddit QA (v0.3.x — coming soon)

In addition to the above:

| Secret | Purpose |
|---|---|
| `REDDIT_CLIENT_ID` | Reddit OAuth app client ID |
| `REDDIT_CLIENT_SECRET` | Reddit OAuth app client secret |
| `REDDIT_USERNAME` | Bot account username |
| `REDDIT_PASSWORD` | Bot account password |
| `REDDIT_USER_AGENT` | Reddit-required UA string. Format: `python:my-bot:v1 (by /u/bot-user)` |

See [reddit-oauth-setup.md](reddit-oauth-setup.md) (ships with v0.3.x) for the full Reddit app creation walkthrough.

## Optional repository variables

Some inputs to the meta-reusables can be set repository-wide via Actions Variables (Settings → Secrets and variables → Actions → Variables tab) so multiple caller workflows share the same default:

| Variable | Used by | Default |
|---|---|---|
| `LDR_RESEARCH_MODEL` | `issue-helper`, `pr-code-review` | (LDR's own default, currently `google/gemini-2.0-flash-001`) |
| `LDR_RESEARCH_CHEAP_MODEL` | `reddit-qa` classifier | `anthropic/claude-haiku-4.5` (planned for v0.3.x) |
| `LDR_REDDIT_KILLSWITCH` | `reddit-qa` | unset → bot runs; set to `'true'` → bot aborts |

The meta-reusable workflows themselves read these via `vars.X || 'fallback'` patterns in the relevant input defaults.

## Where do these resolve from?

Secrets and variables are **always resolved from the caller workflow's repo**, never from this toolkit repo. The toolkit's reusable just receives whatever the caller passes in.

This means:

- If your caller has `REDDIT_PASSWORD: ${{ secrets.REDDIT_PASSWORD }}`, the value comes from **your** repo.
- If a secret name is misspelled in your caller, the value will be empty and the workflow fails at the next step that needs it.
- If you fork this toolkit repo and want to run its `self-test.yml`, **you'll need your own API keys** in the fork.
