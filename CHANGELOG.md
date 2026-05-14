# Changelog

All notable changes to this project will be documented here. Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows [semver](https://semver.org/).

## [Unreleased]

## [0.1.0] — initial release

### Added

- `issue-helper.yml` reusable workflow: research a labeled GitHub issue and post the result as a comment. Supports two prompt templates (`issue_open_ended`, `issue_reporter_and_maintainer`) and three audience modes (`reporter`, `maintainer`, `both`).
- `scripts/sanitize_text.py`: shared input sanitiser (control-char strip, length cap, sentinel-block wrapper).
- `scripts/build_issue_query.py`: generalised issue prompt assembly used by `issue-helper.yml`.
- `scripts/prompt_templates/`: starter templates.
- `examples/issue-helper-caller.yml`: copy-pasteable caller workflow.
- `docs/quickstart-issue-helper.md`, `docs/secrets-and-vars.md`, `docs/threat-model.md`: setup + reference docs.
- Internal: `self-test.yml`, `zizmor.yml`, `pre-commit.yml` for repo-side CI.
