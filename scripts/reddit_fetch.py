#!/usr/bin/env python3
"""Poll a subreddit for new posts, filter, classify, emit matrix JSON.

Used by `.github/workflows/reddit-qa.yml`. Reads config from environment
variables, writes a JSON array to `$GITHUB_OUTPUT` as ``matrix`` for
downstream matrix-call jobs.

Env vars (all required unless marked):

  SUBREDDIT             subreddit name (without `r/`)
  BOT_USERNAME          bot's Reddit username (for already-replied check)
  POST_LIMIT            how many newest posts to scan (default 25)
  MIN_POST_AGE_HOURS    skip posts younger than this (default 6)
  MAX_POST_AGE_HOURS    skip posts older than this (default 24)
  MAX_POSTS_PER_RUN     hard cap on matrix size (default 3)
  CLASSIFIER_MODEL      OpenRouter model slug for the cheap sentiment
                        classifier (default 'anthropic/claude-haiku-4.5')
  OPENROUTER_API_KEY    for the classifier call
  SELFTEXT_MAX_CHARS    truncate selftext to this length (default 2000)
  TITLE_MAX_CHARS       truncate title (default 300)

  Reddit auth (one of two modes):
    Password mode (default):
      REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME,
      REDDIT_PASSWORD, REDDIT_USER_AGENT
    Refresh-token mode (opt-in):
      REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_REFRESH_TOKEN,
      REDDIT_USER_AGENT

Output to $GITHUB_OUTPUT:

  matrix    JSON array (possibly empty) of {id, id_sanitized, title, selftext_sanitized}
  count     length of the array (string)

  Also emits stats lines to stdout for log visibility.
"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path

import requests

# Reuse the sanitiser from PR #1.
sys.path.insert(0, str(Path(__file__).parent))
from sanitize_text import sanitize_field, strip_controls, wrap_in_sentinel  # noqa: E402

logger = logging.getLogger("reddit_fetch")

TEMPLATE_DIR = Path(__file__).parent / "prompt_templates"
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)

# Artifact names must match [A-Za-z0-9._-]; Reddit post IDs are base36 so
# already safe, but we run the same sanitiser as LDR's reusable does on
# the artifact-suffix input to guarantee a clean round-trip.
_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9._-]")

VALID_LABELS = {"OK", "SKIP_SENTIMENT", "SKIP_LOWINFO", "SKIP_NSFW"}


@dataclass
class Candidate:
    id: str
    id_sanitized: str
    title: str
    selftext_sanitized: str
    query: str


def load_template(template_ref: str) -> str:
    if not template_ref.replace("_", "").isalnum():
        raise ValueError(f"Invalid template ref: {template_ref!r}")
    path = TEMPLATE_DIR / f"{template_ref}.txt"
    if not path.is_file():
        raise FileNotFoundError(f"Template not found: {path}")
    return path.read_text(encoding="utf-8")


def render_reddit_query(template_ref: str, subreddit: str, title: str, body: str) -> str:
    """Substitute placeholders in the Reddit prompt template."""
    template = load_template(template_ref)
    return (
        template.replace("{{SUBREDDIT}}", subreddit)
        .replace("{{POST_TITLE}}", title)
        .replace("{{POST_BODY}}", wrap_in_sentinel(body, "REDDIT_POST"))
    )


def sanitize_id(post_id: str) -> str:
    return _SAFE_ID_RE.sub("_", post_id)


def build_reddit_client():
    """Construct a PRAW Reddit client from env. Prefers refresh-token if set."""
    import praw  # imported here so importing reddit_fetch doesn't require PRAW

    common = {
        "client_id": os.environ["REDDIT_CLIENT_ID"],
        "client_secret": os.environ["REDDIT_CLIENT_SECRET"],
        "user_agent": os.environ["REDDIT_USER_AGENT"],
    }
    refresh_token = os.environ.get("REDDIT_REFRESH_TOKEN", "").strip()
    if refresh_token:
        return praw.Reddit(refresh_token=refresh_token, **common)
    return praw.Reddit(
        username=os.environ["REDDIT_USERNAME"],
        password=os.environ["REDDIT_PASSWORD"],
        **common,
    )


def already_replied(submission, bot_username: str) -> bool:
    """Walk the submission's comment tree, return True if a comment by
    ``bot_username`` is found.

    Known blind spot: if the bot's own comment was mod-removed, it will
    appear as ``author=None`` and we can't distinguish it from any other
    removed comment. Mitigated upstream by the ``MIN_POST_AGE_HOURS``
    filter — we don't re-attempt posts older than the window.
    """
    submission.comments.replace_more(limit=0)
    target = bot_username.lower()
    for c in submission.comments.list():
        if c.author and c.author.name.lower() == target:
            return True
    return False


def classify_post(title: str, selftext: str, model: str, api_key: str) -> str:
    """Cheap-model classifier returning one of VALID_LABELS.

    Fail-open (returns 'OK') on any error so the bot doesn't go silent
    just because OpenRouter blipped.
    """
    if not api_key:
        logger.warning("OPENROUTER_API_KEY missing; defaulting to OK")
        return "OK"

    prompt = f"""Classify this Reddit post into ONE of these four categories:

- OK: A genuine question or substantive technical post worth researching.
- SKIP_SENTIMENT: A rant, complaint, or inflammatory post where research would be tone-deaf.
- SKIP_LOWINFO: Too vague or brief to research usefully (e.g. one-liner with no detail).
- SKIP_NSFW: Off-topic, NSFW, or harassment-adjacent.

Title: {title}

Body: {selftext[:1500]}

Respond with ONLY the category name (one of OK, SKIP_SENTIMENT, SKIP_LOWINFO, SKIP_NSFW). No other text."""

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://github.com/LearningCircuit/ldr-automations",
                "X-Title": "ldr-automations reddit classifier",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": 10,
            },
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip().upper()
        # Strip any markdown wrapping or trailing punctuation.
        content = re.sub(r"[^A-Z_]", "", content)
        if content in VALID_LABELS:
            return content
        logger.warning("Classifier returned unexpected label %r, treating as OK", content)
        return "OK"
    except Exception as exc:
        logger.warning("Classifier call failed (%s), fail-open to OK", exc)
        return "OK"


def emit_output(name: str, value: str) -> None:
    delim = f"EOF_{secrets.token_hex(8)}"
    line = f"{name}<<{delim}\n{value}\n{delim}\n"
    out_path = os.environ.get("GITHUB_OUTPUT")
    if out_path:
        with open(out_path, "a", encoding="utf-8") as f:
            f.write(line)
    else:
        sys.stdout.write(line)


def fetch_candidates(reddit, config: dict) -> list[Candidate]:
    """Pull newest-N from the subreddit, filter, classify, return survivors."""
    sub_name = config["subreddit"]
    sub = reddit.subreddit(sub_name)
    now = time.time()
    min_age_s = config["min_post_age_hours"] * 3600
    max_age_s = config["max_post_age_hours"] * 3600

    stats = {"total": 0, "too_new": 0, "too_old": 0, "already_replied": 0,
             "skip_sentiment": 0, "skip_lowinfo": 0, "skip_nsfw": 0, "ok": 0}
    out: list[Candidate] = []

    for submission in sub.new(limit=config["post_limit"]):
        stats["total"] += 1
        if len(out) >= config["max_posts_per_run"]:
            logger.info("Hit max_posts_per_run cap (%d)", config["max_posts_per_run"])
            break

        age_s = now - submission.created_utc
        if age_s < min_age_s:
            stats["too_new"] += 1
            continue
        if age_s > max_age_s:
            stats["too_old"] += 1
            continue

        if already_replied(submission, config["bot_username"]):
            stats["already_replied"] += 1
            continue

        title_clean = sanitize_field(submission.title or "", config["title_max"])
        selftext_clean = sanitize_field(submission.selftext or "", config["selftext_max"])

        label = classify_post(
            title=title_clean,
            selftext=selftext_clean,
            model=config["classifier_model"],
            api_key=config["openrouter_key"],
        )
        if label == "OK":
            stats["ok"] += 1
            query = render_reddit_query(
                template_ref=config["template_ref"],
                subreddit=sub_name,
                title=title_clean,
                body=selftext_clean,
            )
            out.append(Candidate(
                id=submission.id,
                id_sanitized=sanitize_id(submission.id),
                title=title_clean,
                selftext_sanitized=selftext_clean,
                query=query,
            ))
        elif label == "SKIP_SENTIMENT":
            stats["skip_sentiment"] += 1
        elif label == "SKIP_LOWINFO":
            stats["skip_lowinfo"] += 1
        elif label == "SKIP_NSFW":
            stats["skip_nsfw"] += 1

    logger.info("Subreddit r/%s scan results: %s", sub_name, stats)
    return out


def load_config_from_env() -> dict:
    return {
        "subreddit": os.environ["SUBREDDIT"].strip(),
        "bot_username": os.environ["BOT_USERNAME"].strip(),
        "post_limit": int(os.environ.get("POST_LIMIT", "25")),
        "min_post_age_hours": float(os.environ.get("MIN_POST_AGE_HOURS", "6")),
        "max_post_age_hours": float(os.environ.get("MAX_POST_AGE_HOURS", "24")),
        "max_posts_per_run": int(os.environ.get("MAX_POSTS_PER_RUN", "3")),
        "classifier_model": os.environ.get(
            "CLASSIFIER_MODEL", "anthropic/claude-haiku-4.5"
        ).strip(),
        "openrouter_key": os.environ.get("OPENROUTER_API_KEY", ""),
        "title_max": int(os.environ.get("TITLE_MAX_CHARS", "300")),
        "selftext_max": int(os.environ.get("SELFTEXT_MAX_CHARS", "2000")),
        "template_ref": os.environ.get("TEMPLATE_REF", "reddit_qa").strip(),
    }


def main() -> int:
    try:
        config = load_config_from_env()
    except KeyError as e:
        print(f"::error::Missing required env var: {e}", file=sys.stderr)
        return 1

    try:
        reddit = build_reddit_client()
    except Exception as exc:
        print(f"::error::Failed to build Reddit client: {exc}", file=sys.stderr)
        return 1

    candidates = fetch_candidates(reddit, config)
    matrix_payload = json.dumps([asdict(c) for c in candidates])
    emit_output("matrix", matrix_payload)
    emit_output("count", str(len(candidates)))
    logger.info("Emitting %d candidates", len(candidates))
    return 0


if __name__ == "__main__":
    sys.exit(main())
