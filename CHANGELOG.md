# Changelog

All notable changes to this project will be documented here. Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows [semver](https://semver.org/).

## [Unreleased]

## [0.5.0] — Welcome first-time contributors

### Added

- `welcome-first-time.yml` reusable workflow: posts a single welcome comment when a contributor opens their first PR. Filters per-author (skips repeat contributors) and skips bots.
- `examples/welcome-first-time-caller.yml`: drop-in caller with a generic welcome template.
- `docs/quickstart-welcome-first-time.md`: setup walkthrough.

### Notes

- No LLM, no API keys. Pure community automation.
- Uses `pull_request_target` so fork PRs can receive the welcome — see the quickstart for the safety rationale.

## [0.4.0] — AI code reviewer

### Added

- `ai-code-reviewer.yml` reusable workflow: wraps the [Friendly AI Reviewer](https://github.com/LearningCircuit/Friendly-AI-Reviewer) script. Runs an opinionated LLM code review on a PR, posts the review as a comment, applies any AI-suggested labels, optionally fails the workflow on a `fail` verdict (soft gate).
- `examples/ai-code-reviewer-caller.yml`: drop-in caller — runs on every PR open plus the `ai_code_review` label.
- `docs/quickstart-ai-code-reviewer.md`: setup walkthrough, with a comparison table against `pr-code-review.yml`.

### Notes

- This is structurally different from `pr-code-review.yml` (which uses LDR research). Many projects will run both — they're complementary.
- Needs only `OPENROUTER_API_KEY`. No `SERPER_API_KEY` and no LDR install.

## [0.2.0] — PR code review

### Added

- `pr-code-review.yml` reusable workflow: research a labeled GitHub Pull Request and post the result as a comment. Two modes: `diff` (research the PR's actual changes) and `static` (run a fixed query as a pipeline smoke test).
- `scripts/build_pr_query.py`: PR diff prompt assembly with both modes.
- `scripts/prompt_templates/pr_diff_review.txt`, `scripts/prompt_templates/pr_static_smoke.txt`: starter templates.
- `examples/pr-code-review-caller.yml`: drop-in caller with both diff and static job examples.
- `docs/quickstart-pr-review.md`: setup walkthrough.

## [0.1.0] — initial release

### Added

- `issue-helper.yml` reusable workflow: research a labeled GitHub issue and post the result as a comment. Supports two prompt templates (`issue_open_ended`, `issue_reporter_and_maintainer`) and three audience modes (`reporter`, `maintainer`, `both`).
- `scripts/sanitize_text.py`: shared input sanitiser (control-char strip, length cap, sentinel-block wrapper).
- `scripts/build_issue_query.py`: generalised issue prompt assembly used by `issue-helper.yml`.
- `scripts/prompt_templates/`: starter templates.
- `examples/issue-helper-caller.yml`: copy-pasteable caller workflow.
- `docs/quickstart-issue-helper.md`, `docs/secrets-and-vars.md`, `docs/threat-model.md`: setup + reference docs.
- Internal: `self-test.yml`, `zizmor.yml`, `pre-commit.yml` for repo-side CI.
