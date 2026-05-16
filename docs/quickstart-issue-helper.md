# Quickstart: Issue helper

Add an LDR-powered "research this issue" command to your own repo, triggered by applying a label to a GitHub issue.

## 1. Get API keys

You need two:

- **OpenRouter API key** — <https://openrouter.ai/keys>
- **Serper.dev API key** — <https://serper.dev/api-key>

Add both as repository secrets in your repo: **Settings → Secrets and variables → Actions → New repository secret**

- Name `OPENROUTER_API_KEY`, paste the OpenRouter key.
- Name `SERPER_API_KEY`, paste the Serper key.

## 2. Create the trigger label

In your repo: **Issues → Labels → New label**. Default name expected by the example workflow is `research`. You can use any name as long as you match it in step 3.

## 3. Copy the caller workflow

Save the following as `.github/workflows/issue-research.yml` in your repo:

```yaml
name: Issue Research

on:
  issues:
    types: [labeled]

permissions: {}

jobs:
  run:
    if: github.event.label.name == 'research'

    # Required. Don't change unless you know what you're doing.
    permissions:
      contents: read
      issues: write
      actions: write

    uses: LearningCircuit/ldr-automations/.github/workflows/issue-helper.yml@v0.1.0
    with:
      toolkit-ref: v0.1.0
      prompt-template-ref: issue_reporter_and_maintainer
      audience: both
      project-name: ''            # ← put your project's name here

    secrets:
      OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
      SERPER_API_KEY: ${{ secrets.SERPER_API_KEY }}
```

The two refs (`@v0.1.0` and `toolkit-ref: v0.1.0`) **must match**. Pin to a specific release tag, not `@main`.

## 4. Try it

1. Open a test issue in your repo with a real bug description.
2. Apply the `research` label.
3. Wait ~1–5 minutes (LLM call + search). The workflow posts a research comment and auto-removes the label.

## Customising

### Prompt template

`prompt-template-ref` accepts:

- `issue_open_ended` (default) — single-section research output.
- `issue_reporter_and_maintainer` — split into two sections.

### Audience framing

`audience` accepts:

- `reporter` — short cautious suggestions aimed at the issue's author.
- `maintainer` — adjacent external context for triage.
- `both` (default) — both sections.

### Model

By default LDR picks a sensible model for the task (gemini-2.0-flash class). Override with:

```yaml
with:
  model: anthropic/claude-sonnet-4   # any OpenRouter model slug
```

Larger models produce better research but cost more. See <https://openrouter.ai/models> for the catalogue.

### Other knobs

See the [`issue-helper.yml` inputs section](https://github.com/LearningCircuit/ldr-automations/blob/main/.github/workflows/issue-helper.yml) for the full list (max body chars, comment header/footer, custom prompt prefix/suffix, etc.).

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Workflow doesn't appear in the Actions tab when you label an issue | Label name doesn't match the `if:` condition. Check `github.event.label.name == '<your-label>'`. |
| Workflow runs but fails as `startup_failure` with zero jobs | Missing `actions: write` permission on the calling job. Re-paste the `permissions:` block above. |
| Run completes but no comment appears | Check the run logs — the LDR research call probably failed (missing/invalid API key, search rate limit). |
| Comment posts but is just a sources list with no prose | Known failure mode of langgraph-agent under context pressure ([LDR PR #4041](https://github.com/LearningCircuit/local-deep-research/pull/4041)). Update LDR to v1.6.11+ once available. |
