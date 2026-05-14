# LDR Automations

Drop-in **reusable GitHub Actions workflows** that wrap [Local Deep Research](https://github.com/LearningCircuit/local-deep-research) for common CI use cases. Each workflow takes a few inputs and a handful of secrets, runs an LDR research call against the relevant context, and posts a comment back to the trigger.

| Use case | Workflow | Trigger in your repo | Status |
|---|---|---|---|
| **Issue helper** — research labeled issues, post research as a comment | `issue-helper.yml` | `issues: types: [labeled]` | available (v0.1.x) |
| **PR code review** — research labeled PR diffs, post research as a comment | `pr-code-review.yml` | `pull_request: types: [labeled]` | available (v0.2.x) |
| **Reddit QA** — poll a subreddit, research new posts, reply | `reddit-qa.yml` | `schedule: cron` | follow-up (v0.3.x) |

## How it works

Your caller workflow lives in your own repo. It invokes one of the meta-reusables in this repo via `uses:`. That meta-reusable internally calls LDR's own [`ldr-research-reusable.yml`](https://github.com/LearningCircuit/local-deep-research/blob/main/.github/workflows/ldr-research-reusable.yml) workflow, then posts the result to the right place (issue comment, PR comment, Reddit reply).

```
your-repo/.github/workflows/foo.yml
   ↓ uses: LearningCircuit/ldr-automations/.github/workflows/issue-helper.yml@v0.1.0
   ldr-automations issue-helper.yml
      ↓ uses: LearningCircuit/local-deep-research/.github/workflows/ldr-research-reusable.yml@v1.6.10
      LDR research runs
   meta-reusable downloads artifact + posts comment to your issue
```

## Prerequisites

You'll need API keys for the services LDR calls:
- **OpenRouter** (LLM provider). Sign up at <https://openrouter.ai/>. Store as repo secret `OPENROUTER_API_KEY`.
- **Serper.dev** (Google search API). Sign up at <https://serper.dev/>. Store as repo secret `SERPER_API_KEY`.

Reddit QA also needs Reddit API credentials. See [docs/reddit-oauth-setup.md](docs/reddit-oauth-setup.md) when that workflow ships.

## Quickstarts

- [Issue helper](docs/quickstart-issue-helper.md) — research GitHub issues on demand
- [PR code review](docs/quickstart-pr-review.md) — research PRs on demand
- Reddit QA — coming with v0.3.x

## Versioning

Caller workflows pin to a release tag, not `@main`:

```yaml
uses: LearningCircuit/ldr-automations/.github/workflows/issue-helper.yml@v0.1.0
```

See [CHANGELOG.md](CHANGELOG.md) for what's in each release.

## Security

The workflows in this repo process semi-trusted input (GitHub issue bodies, PR diffs, Reddit posts). See [SECURITY.md](SECURITY.md) and [docs/threat-model.md](docs/threat-model.md) for the security model and how to report vulnerabilities.

## License

MIT. See [LICENSE](LICENSE).
