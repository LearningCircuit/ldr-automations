# Quickstart: Welcome first-time contributors

Auto-post a welcome comment when someone opens their first PR against your repo. Filters per-author (skips repeat contributors) and skips bots.

No LLM. No API keys. Just a polite comment with project-specific links.

## 1. Copy the caller workflow

Save as `.github/workflows/welcome-first-time.yml` in your repo:

```yaml
name: Welcome first-time contributors

on:
  pull_request_target:
    types: [opened]

permissions: {}

jobs:
  welcome:
    permissions:
      issues: write
      pull-requests: write
    uses: LearningCircuit/ldr-automations/.github/workflows/welcome-first-time.yml@v0.5.0
    with:
      welcome-message: |
        Welcome to **your-project-name**! Thanks for opening your first PR.

        **Get set up locally**
        - [Installation](https://github.com/YOUR_ORG/YOUR_REPO/blob/main/docs/installation.md)
        - [Developer guide](https://github.com/YOUR_ORG/YOUR_REPO/blob/main/CONTRIBUTING.md)

        A maintainer will take a look — if you don't hear back within 7 days, feel free to ping.
```

Edit `welcome-message` to be specific to your project. Markdown works as you'd expect.

## 2. Two things to know about `pull_request_target`

This workflow uses `pull_request_target` rather than the more common `pull_request`. Two reasons:

1. **Fork PRs need a writable token.** `pull_request` runs in the fork's context with a read-only token; it can't post comments. `pull_request_target` runs in the base repo's context with full permissions.
2. **The reusable never checks out PR content.** It only reads `sender.login` (operator-trusted metadata) and posts the static `welcome-message` you supplied here. There's no path for fork-controlled content to influence what the workflow does.

If you ever change this workflow to checkout the PR's code or run scripts from it, **stop and reconsider** — that's the classic pattern that has caused supply-chain incidents in the wild.

## 3. How the "first PR" check works

When a PR opens, the workflow:

1. Skips if the sender is a bot (`user.type === 'Bot'` or `login` ends in `[bot]`).
2. Queries the GitHub API: "list issues + PRs in this repo where `creator == sender.login`".
3. If any prior PR exists for this author (excluding the just-opened one), skips silently.
4. Otherwise, posts the welcome comment.

This is more robust than `actions/first-interaction`, which doesn't filter per-author and never fires on a repo with prior PR history.

## Limitations

- The check is a snapshot query; if two PRs by the same first-time author open within milliseconds (eventual consistency on `listForRepo`), it's possible (rare) for both to receive the welcome.
- No re-welcoming: if a contributor's first PR was closed without merging and they later open another, they won't get welcomed again.
- The welcome message is a static input — no per-PR interpolation. If you want personalised messages, fork the workflow.

## Permissions

The calling job MUST declare:

```yaml
permissions:
  issues: write
  pull-requests: write
```

`createComment` on a PR returns 403 with only `issues: write` — GitHub requires `pull-requests: write` when the issue resource is a PR.
