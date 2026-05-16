# Quickstart: gitleaks secret scan

Detect accidentally-committed secrets (API keys, tokens, passwords) in your repo.

Wraps the official [`gitleaks/gitleaks-action`](https://github.com/gitleaks/gitleaks-action). Sensible defaults; mirrors the pattern from LDR's `gitleaks.yml`.

## 1. Copy the caller workflow

Save as `.github/workflows/gitleaks.yml`:

```yaml
name: gitleaks secret scan

on:
  pull_request:
  push:
    branches: [main]
  workflow_dispatch:
  schedule:
    - cron: '0 3 * * *'

permissions: {}

jobs:
  scan:
    permissions:
      contents: read
      security-events: write
      actions: read
    uses: LearningCircuit/ldr-automations/.github/workflows/gitleaks.yml@v0.7.0
```

No secrets needed beyond the automatic `GITHUB_TOKEN`.

## Trigger pattern

Three layers, all worth keeping:

- **`pull_request`** — catch secrets before they land. Fast-fail.
- **`push: branches: [main]`** — also catch direct pushes (e.g. via Web UI edits) and re-scan after PR merges.
- **`schedule`** (daily 03:00 UTC) — re-scan the whole history against gitleaks' updated rule packs. New regex patterns for newly-disclosed secret formats catch leaks that pre-date the rule.
- **`workflow_dispatch`** — manual one-off scans.

Drop any of these you don't want.

## What gitleaks detects

100+ built-in patterns. Highlights:

| Provider | Examples |
|---|---|
| AWS | `AKIA...` keys, secret access keys |
| GCP | service account JSON |
| Azure | storage keys, SAS tokens |
| GitHub | personal access tokens (`ghp_`, `gho_`, `ghs_`), classic tokens |
| Stripe | `sk_live_`, `pk_live_` |
| OpenAI / Anthropic / OpenRouter | API keys (`sk-...`, `sk-ant-...`) |
| Generic | private keys (RSA, EC, OpenSSH), `password=`, `Bearer ...` |

Full list: <https://github.com/gitleaks/gitleaks/blob/master/config/gitleaks.toml>

## Customising rules

If gitleaks' defaults produce false positives or you want to add custom patterns, create `.gitleaks.toml` in your repo's root:

```toml
title = "my-project gitleaks config"

[extend]
useDefault = true

[[rules]]
id = "my-custom-pattern"
description = "Internal API token format"
regex = '''myapi_[A-Za-z0-9]{32}'''
keywords = ["myapi_"]
```

Then point the workflow at it:

```yaml
with:
  gitleaks-config: .gitleaks.toml
```

See the [gitleaks docs](https://github.com/gitleaks/gitleaks#configuration) for the full config schema.

## Accepting known findings (baselines)

If gitleaks flags something you've reviewed and accepted (e.g. an intentionally-public example key in docs), add it to a `.gitleaksignore` file:

```
# format: <commit-sha>:<file-path>:<rule-id>:<line-number>
# Generate one by running gitleaks locally with `--report-path .gitleaksignore`
abc123def:docs/example.md:openai-api-key:42
```

Then point the workflow at it:

```yaml
with:
  gitleaks-baseline: .gitleaksignore
```

## Inputs

| Input | Default | Purpose |
|---|---|---|
| `fetch-depth` | `0` (full history) | Larger repos can drop to `1` for PR-only scans; loses history coverage |
| `gitleaks-config` | (none) | Path to a `.gitleaks.toml` in your repo |
| `gitleaks-baseline` | (none) | Path to a `.gitleaksignore` of accepted findings |
| `gitleaks-version` | v2.3.9 SHA | Documents the pinned action version |
| `runner` | `ubuntu-latest` | Runner label |

Bumping `gitleaks-version` requires editing the workflow file (GitHub Actions can't use a templated `uses:` ref) — Dependabot in this toolkit repo handles version bumps automatically.

## License note

gitleaks-action v2 is **commercial-use restricted**. From the [gitleaks-action README](https://github.com/gitleaks/gitleaks-action#-license):

> This is a paid product for organizations with > $1MM USD annual revenue.

Personal projects, OSS projects, and small commercial users can run it for free; larger orgs should obtain a license. Read the upstream README for current terms before adopting.

## Permissions

The caller job needs:

```yaml
permissions:
  contents: read
  security-events: write   # for SARIF upload
  actions: read            # for the upstream action's repo metadata fetch
```

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Workflow fails with `GITLEAKS_LICENSE` error | You're in the paid-license tier. Either obtain a license or use a fork of gitleaks-action v1 (which was unrestricted). |
| False positive on a string that's not actually a secret | Add it to `.gitleaksignore` (see above) |
| Scan times out on a huge repo | Set `fetch-depth: 1` to scan only the latest commit. Schedule a separate `schedule:`-triggered job with `fetch-depth: 0` weekly for full-history coverage. |
| Findings don't appear in the Security tab | Check the workflow log — SARIF upload only happens when the upstream action is configured to emit it. May require GitHub Advanced Security on private repos. |
