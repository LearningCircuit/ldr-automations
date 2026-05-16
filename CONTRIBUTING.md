# Contributing

Thanks for your interest. This repo is small and the contribution surface is narrow:

- **Bug fix in an existing workflow or helper script** — file an issue or open a PR. If the fix changes input/output contract for a workflow, see "Versioning" below.
- **New use case** (new top-level workflow file) — open a discussion first. Adding a workflow is a maintenance commitment; not all proposals will land.
- **Prompt template tuning** — fine. Open a PR with the old vs. new template and a paragraph on why the new wording is better.

## Local development

```bash
# Clone
git clone https://github.com/LearningCircuit/ldr-automations
cd ldr-automations

# Install dev deps
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check .
ruff format --check .

# Workflow lint
actionlint .github/workflows/*.yml
zizmor --offline .github/workflows/*.yml
```

## PR conventions

- One PR per concern. A scaffolding PR is fine; a "rewrite half the repo" PR is not.
- Tests required for anything under `scripts/`. Workflow YAML changes don't need unit tests but should ideally be exercised by `self-test.yml`.
- Conventional commits aren't strictly enforced but are appreciated: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, etc.

## Versioning

This repo follows semver:

- **Major** (e.g. `v1` → `v2`): input rename/removal, required-input addition, secret rename, behaviour change to a default that materially affects output.
- **Minor** (e.g. `v0.1` → `v0.2`): new optional input, new optional secret, new optional output, new prompt template, new meta-reusable workflow file, bumping the pinned LDR ref.
- **Patch** (e.g. `v0.1.0` → `v0.1.1`): internal script changes, prompt template wording tweaks that preserve any output-contract markers, dependency bumps, docs.

When a release is cut, `CHANGELOG.md` gets a new section. Caller workflows should pin to a tag, not `@main`.

## Release process

Maintainer-only:

1. Merge all intended changes into `main` via PR.
2. Update `CHANGELOG.md` with the new version's section.
3. Create the tag: `git tag v0.X.Y && git push origin v0.X.Y`.
4. Create a GitHub Release from the tag, with the changelog section as the description.
