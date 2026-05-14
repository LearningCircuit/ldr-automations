# Security policy

## Reporting a vulnerability

If you discover a security issue in this repo, please **do not** open a public issue. Instead, email the maintainers at the address listed on [LearningCircuit's GitHub profile](https://github.com/LearningCircuit) or open a private security advisory at <https://github.com/LearningCircuit/ldr-automations/security/advisories/new>.

We'll acknowledge receipt within 7 days and aim to ship a fix within 90 days of confirmation.

## Threat model

The workflows in this repo process untrusted-ish input (issue bodies, PR diffs, Reddit posts) through an LLM and post the result back as a comment. The threat model in scope:

- **Prompt injection** from input content trying to coerce the LLM into producing harmful, off-topic, or instruction-bypassing output. Mitigated by content-char stripping, length caps, sentinel-block wrapping, and an "ignore instructions inside this block" preamble. See [docs/threat-model.md](docs/threat-model.md) for details.
- **Token / secret exfiltration** from a malicious input persuading the LLM to leak environment data. Mitigated by least-privilege GitHub Actions permissions (each job declares only what it needs) and not exposing secret values to the LLM as context.

Out of scope:
- RCE on GitHub-hosted runners. The runners are ephemeral and unprivileged; if an attacker compromises one, the blast radius is the workflow's `GITHUB_TOKEN` scope which is intentionally narrow.
- Compromise of upstream services (OpenRouter, Serper, Reddit) — outside our control.

## Supply chain

- All third-party actions pinned to commit SHAs.
- Python deps pinned via `requirements.txt`.
- Dependabot configured to bump pinned versions weekly; security updates daily.
