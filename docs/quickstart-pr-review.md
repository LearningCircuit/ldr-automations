# Quickstart: PR code review

Add an LDR-powered "research this PR" command to your own repo, triggered by applying a label to a Pull Request.

## 1. API keys

Same as the issue helper. Add as repo secrets:

- `OPENROUTER_API_KEY` — <https://openrouter.ai/keys>
- `SERPER_API_KEY` — <https://serper.dev/api-key>

See [secrets-and-vars.md](secrets-and-vars.md) for the full list.

## 2. Trigger labels

Create labels in your repo: **Issues → Labels → New label**. The example workflow expects two:

- `research` — runs LDR research against the PR's diff
- `research-static` — runs a fixed smoke-test query (cheap; ignores the PR content). Optional.

You can rename either by editing the `if:` condition in the caller.

## 3. Copy the caller workflow

Save as `.github/workflows/pr-research.yml` in your repo:

```yaml
name: PR Research

on:
  pull_request:
    types: [labeled]

permissions: {}

jobs:
  diff:
    if: github.event.label.name == 'research'
    permissions:
      contents: read
      pull-requests: write
      issues: write
      actions: write
    uses: LearningCircuit/ldr-automations/.github/workflows/pr-code-review.yml@v0.2.0
    with:
      toolkit-ref: v0.2.0
      mode: diff
      project-name: ''            # ← your project name
    secrets:
      OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
      SERPER_API_KEY: ${{ secrets.SERPER_API_KEY }}
```

Pin to a tag. The two refs (`@v0.2.0` and `toolkit-ref: v0.2.0`) must match.

## 4. Try it

1. Open a real or test PR in your repo.
2. Apply the `research` label.
3. Wait 1–5 min. The bot posts a research comment, then removes the label.

## Two modes

### `mode: diff` (default)

Fetches the PR's diff via git, truncates to `max-diff-bytes` (default 8000), embeds in a research prompt asking LDR to find relevant docs, gotchas, known issues, and best practices for the changed code.

Useful for substantive PRs where reviewers benefit from adjacent context they might not have in mind.

### `mode: static`

Runs a fixed `static-query` regardless of the PR's content. Useful as a cheap smoke test for the whole pipeline (does the bot actually post comments? does the LDR call work? is the model responding?) without spending tokens on diff analysis.

The default `static-query` is `"What is Local Deep Research and how does it work?"` — answerable, low-cost, content-agnostic.

## Permissions

The calling job MUST declare these explicitly:

```yaml
permissions:
  contents: read        # for checkout
  pull-requests: write  # for `gh pr comment`
  issues: write         # for label removal (PRs use the issues API)
  actions: write        # for the LDR reusable's artifact upload
```

Without `actions: write`, the workflow will fail at startup with zero jobs.

## Customising

- `max-diff-bytes`: increase if your PRs are typically large. The LLM still has a token budget, so very large diffs will get truncated by LDR's own length cap regardless.
- `prompt-template-ref`: defaults to `pr_diff_review`. You can supply your own template (see `scripts/prompt_templates/pr_diff_review.txt` for the format).
- `model`: override the default LDR model. See the [issue-helper quickstart](quickstart-issue-helper.md#model) for the same details.
- `prompt-prefix` / `prompt-suffix`: inject custom text before / after the assembled prompt without forking the template.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `startup_failure` with zero jobs | Missing `actions: write` permission on the calling job |
| Diff extraction fails | The caller workflow can't fetch the base ref — happens on PRs from forks. The fix: trigger only on label events from same-repo branches, or use `pull_request_target` (carefully) |
| Diff is empty / always truncated | Increase `max-diff-bytes` (default 8000); confirm the PR actually has changes |
| Comment posts but is just a sources list | Known LDR issue under context pressure; track [LDR PR #4041](https://github.com/LearningCircuit/local-deep-research/pull/4041) |
