# Quickstart: AI code reviewer

Get an LLM-driven code review posted on every PR open (and re-runnable by applying a label). The review is structured: a free-text body, a verdict (`pass` / `fail` / `uncertain`), and any suggested labels.

This is a wrapper around the [Friendly AI Reviewer](https://github.com/LearningCircuit/Friendly-AI-Reviewer) script. The script does the actual model call; this workflow handles the GitHub-side plumbing (fetching the diff, posting the comment, applying labels, removing the trigger label).

**Different from `pr-code-review.yml`**: that one uses LDR's research to surface adjacent context (docs, known issues, similar reports). This one returns an opinionated review. They're complementary.

## 1. API key

You only need OpenRouter for this workflow (no LDR research, no Serper). Add as a repo secret:

- `OPENROUTER_API_KEY` — <https://openrouter.ai/keys>

## 2. Copy the caller workflow

Save as `.github/workflows/ai-code-review.yml` in your repo:

```yaml
name: AI Code Review

on:
  pull_request:
    types: [opened, labeled]

permissions: {}

jobs:
  review:
    if: github.event.action == 'opened' || (github.event.action == 'labeled' && github.event.label.name == 'ai_code_review')

    permissions:
      contents: read
      pull-requests: write
      issues: write

    uses: LearningCircuit/ldr-automations/.github/workflows/ai-code-reviewer.yml@v0.4.0
    with:
      ai-model: moonshotai/kimi-k2-thinking
      fail-on-requested-changes: false

    secrets:
      OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
```

Pin to a tag (`@v0.4.0`). Don't use `@main`.

## 3. Try it

Open any PR. The bot will:

1. Fetch the PR's diff vs. the base branch.
2. Download the Friendly AI Reviewer script.
3. Call the model with the diff.
4. Parse the JSON response (`review`, `fail_pass_workflow`, `labels_added`).
5. Post the review body as a PR comment.
6. Create + apply any labels the AI suggested.
7. Remove the `ai_code_review` label (so you can re-trigger by re-applying it).

## Customising

### Model

Default is `moonshotai/kimi-k2-thinking` — a reasoning-class model that gives substantive reviews without being prohibitively expensive. Common alternatives:

```yaml
with:
  ai-model: anthropic/claude-sonnet-4      # stronger, ~2-3x cost
  ai-model: openai/gpt-4o                  # OpenAI alternative
  ai-model: google/gemini-2.5-pro          # Google alternative
```

See <https://openrouter.ai/models> for the full catalogue.

### Trigger pattern

The default `if:` runs on every PR open AND on `ai_code_review` label. Change as needed:

```yaml
# Label-only (manual review)
if: github.event.action == 'labeled' && github.event.label.name == 'ai_code_review'

# Only on PRs labelled `needs-review`
if: github.event.action == 'labeled' && github.event.label.name == 'needs-review'

# Run on every PR open, no manual re-trigger
if: github.event.action == 'opened'
```

### Failing the workflow on `fail` verdict

```yaml
with:
  fail-on-requested-changes: true
```

The review still posts as a comment first; the workflow then fails afterwards. Use as a soft gate that branch protection rules can require.

### File exclusions

The reviewer skips files matching these globs by default:

```
*.lock, *.min.js, *.min.css, package-lock.json, yarn.lock, pnpm-lock.yaml,
*.svg, *.png, *.jpg, *.jpeg, *.gif, *.ico
```

Override:

```yaml
with:
  exclude-file-patterns: '*.lock,*.min.js,vendor/**,generated/**'
```

### Pinning the reviewer script for supply-chain safety

By default the workflow downloads the latest `ai-reviewer.sh` from the Friendly AI Reviewer repo's `main` branch. For production setups, pin to a commit SHA:

```yaml
with:
  reviewer-script-url: 'https://raw.githubusercontent.com/LearningCircuit/Friendly-AI-Reviewer/<commit-sha>/ai-reviewer.sh'
```

Or fork the script into your own repo and point at it.

### Debug mode

If reviews are weird or empty, enable debug logging:

```yaml
with:
  debug-mode: true
```

This logs the raw AI response in the workflow output. **Do not enable in repos with sensitive code paths in PR diffs** — the raw AI response may quote the diff back.

## Permissions

The calling job MUST declare:

```yaml
permissions:
  contents: read         # for actions/checkout + diff
  pull-requests: write   # for gh pr comment
  issues: write          # for label create/add/remove (PRs use the issues API)
```

No `actions: write` needed here (no artifacts).

## Cost

Per-PR cost depends on the model and diff size. Rough envelope at the defaults:

- Small PRs (<1 KB diff): ~$0.02–$0.05 per review
- Medium PRs (10–50 KB diff): ~$0.10–$0.30 per review
- Large PRs (>100 KB diff, after truncation): ~$0.50–$1.50 per review

`max-diff-size` defaults to 800 KB — diffs above this get truncated by the reviewer script before sending to the model. Adjust if your project regularly has bigger PRs and you're willing to pay.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Workflow fails with "AI response is not valid JSON" | Model returned a malformed response. Try a different model, or enable `debug-mode` to inspect. |
| Empty review body posted | Model went silent — usually a token-budget or rate-limit issue. Check OpenRouter dashboard. |
| Labels aren't being added | The bot user has insufficient permissions, or the `issues: write` permission is missing on the calling job. |
| Trigger label not being removed | Cosmetic — re-running the workflow on the same PR works regardless. Confirm `issues: write` is granted. |
| Reviewer script 404 | The Friendly AI Reviewer's `main` branch was renamed or moved. Pin `reviewer-script-url` to a known-good commit SHA. |

## How this differs from `pr-code-review.yml`

| | `ai-code-reviewer.yml` (this) | `pr-code-review.yml` |
|---|---|---|
| Purpose | Opinionated code review with a verdict | Adjacent context (docs, known issues) |
| Powered by | Friendly AI Reviewer script | Local Deep Research |
| Output | Review body + verdict + labels | Research with citations |
| Triggers on | PR open + label | Label only |
| Cost (typical PR) | $0.05–$0.30 | $0.05–$0.30 |
| Failure mode | Can fail the workflow on verdict | Always passes |
| When to use | You want a reviewer-like assistant | You want context the reviewer might miss |

Most projects benefit from running **both** — they overlap in scope by less than half.
