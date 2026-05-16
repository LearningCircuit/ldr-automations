# Quickstart: zizmor security scan

Lint your `.github/workflows/` for security issues — template injection, unpinned actions, excessive permissions, impostor commits, etc. — and upload findings to your repo's Security tab.

This is a thin wrapper around the official [`zizmorcore/zizmor-action`](https://github.com/zizmorcore/zizmor-action). The wrapper sets sensible defaults and matches the pattern used by LDR's own `zizmor-security.yml`.

## 1. Copy the caller workflow

Save as `.github/workflows/zizmor-security.yml`:

```yaml
name: zizmor security scan

on:
  pull_request:
    paths:
      - '.github/workflows/**'
      - '.github/actions/**'
  push:
    branches: [main]
    paths:
      - '.github/workflows/**'
      - '.github/actions/**'
  schedule:
    - cron: '0 9 * * 1'
  workflow_dispatch:

permissions: {}

jobs:
  scan:
    permissions:
      contents: read
      security-events: write
      actions: read
    uses: LearningCircuit/ldr-automations/.github/workflows/zizmor-security.yml@v0.6.0
    with:
      target: .github/workflows/
      min-severity: low
      advanced-security: true
```

No secrets needed. `GITHUB_TOKEN` is provided automatically.

## What zizmor finds

| Class | What it flags |
|---|---|
| Template injection | `${{ ... }}` expressions that interpolate attacker-controlled input directly into shell commands |
| ArtiPACKED | Workflows whose uploaded artifacts may contain credentials |
| Vulnerable actions | Third-party actions with known CVEs |
| Impostor commits | Hash-pinned actions whose commit SHA points to a fork, not the canonical repo |
| Hardcoded credentials | Plain-text secrets in workflow files |
| Excessive permissions | `permissions:` blocks granting more than the workflow needs |
| Unpinned uses | `uses:` referring to a tag or branch instead of a commit SHA |
| Cache poisoning | Unsafe `actions/cache` usage patterns |

## Inputs

| Input | Default | Purpose |
|---|---|---|
| `target` | `.github/workflows/` | Path (file or directory) to scan |
| `min-severity` | `low` | `unknown` / `informational` / `low` / `medium` / `high` |
| `advanced-security` | `true` | Enables additional audits; some require GitHub Advanced Security on the repo |
| `runner` | `ubuntu-latest` | Runner label |
| `timeout-minutes` | `30` | Job timeout |

## Permissions

The caller job must declare:

```yaml
permissions:
  contents: read         # for actions/checkout
  security-events: write # to upload SARIF to the Security tab
  actions: read          # for the zizmor-action's repo inspection
```

## Trigger choices

The example caller runs on three triggers:

- **PR + push to `main`** (path-filtered to workflow changes): catches issues at merge time
- **Weekly schedule**: catches new CVE advisories that affect previously-pinned actions
- **`workflow_dispatch`**: manual audits

You can drop any of these. The weekly schedule is highest-value if you only pick one.

## Interpreting findings

Findings appear in your repo's **Security → Code scanning** tab as SARIF results. Each finding includes:

- Severity (informational / low / medium / high)
- Affected file + line
- Audit name (e.g. `template-injection`, `unpinned-uses`) with a link to zizmor's docs

For specific advisories:

| Finding | Fix |
|---|---|
| `template-injection` | Move the expression into an `env:` block and reference `"$VAR"` inside the `run:`; don't `${{ ... }}` directly into shell |
| `unpinned-uses` | Change `uses: foo/bar@v1` to `uses: foo/bar@<sha> # v1` |
| `excessive-permissions` | Trim the `permissions:` block to only what the workflow needs |
| `impostor-commit` | The SHA you pinned doesn't exist on the canonical repo. Re-pin to the real one |

zizmor's [docs site](https://docs.zizmor.sh/audits/) explains each audit in detail.

## Suppressing false positives

If zizmor flags something you've reviewed and accepted, add a `# zizmor: ignore[<audit>]` comment on the relevant line. E.g.:

```yaml
on:
  # zizmor: ignore[dangerous-triggers]
  pull_request_target:
    types: [opened]
```

Use sparingly. Each suppression is a trust statement about that specific line.

## Comparing with `pre-commit.yml`'s actionlint

This toolkit's `pre-commit.yml` also runs `actionlint`. Different focus:

- `actionlint`: workflow YAML validity, syntax, semantic correctness, common mistakes
- `zizmor`: security-specific lints (template injection, supply chain, permission scope)

Run both. They overlap by <10% and catch different classes of issues.
