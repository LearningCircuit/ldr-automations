# Changelog

All notable changes to this project will be documented here. Format loosely follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows [semver](https://semver.org/).

## [Unreleased]

## [0.3.0] — Reddit QA bot

### Added

- `reddit-qa.yml` reusable workflow: polls a subreddit on cron, classifies new posts with a cheap LLM, runs LDR research on the survivors, posts a reply via PRAW. Three independent gates (age window, already-replied check, sentiment/topic classifier) before any reply lands.
- `scripts/reddit_fetch.py`: subreddit polling + filtering + classification + matrix emission (with full assembled query per candidate).
- `scripts/reddit_post.py`: PRAW comment poster with dry-run support and inter-post API-courtesy sleep.
- `scripts/reddit_oauth_bootstrap.py`: one-shot local helper to generate a refresh token (for users opting into refresh-token mode instead of password auth).
- `scripts/prompt_templates/reddit_qa.txt`.
- `examples/reddit-qa-caller.yml`: drop-in caller, cron-triggered with dry-run dispatch.
- `docs/quickstart-reddit.md`, `docs/reddit-oauth-setup.md`: setup walkthroughs.
- `tests/test_reddit_fetch.py`: 26 unit tests covering filtering, classification, age/replied gates, with fully-mocked PRAW + OpenRouter.
- `requirements.txt`: pinned `praw==7.8.1`, `requests==2.32.3` (now needed at workflow runtime).

### Notes

- Default auth mode is **password** (script-app username + password). Refresh-token mode is supported but requires a one-time local bootstrap and is sensitive to Reddit's single-use refresh-token policy.
- Reddit requires per-app API access approval since 2024. Allow 1–4 weeks for approval before going live.

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
