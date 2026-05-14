#!/usr/bin/env python3
"""Post a comment to a Reddit submission.

Reads the comment body from a file (default ``comment.md``), posts it to
the submission identified by ``POST_ID``. Honours ``DRY_RUN``.

Env vars:

  POST_ID           Reddit submission ID (e.g. "1abc2def")
  COMMENT_PATH      path to the comment markdown (default "comment.md")
  DRY_RUN           "true" to skip posting (just print what would happen)
  SLEEP_SECONDS     sleep this long before posting (default 30, for
                    matrix-call API courtesy)
  REDDIT_*          auth vars same as scripts/reddit_fetch.py
"""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from reddit_fetch import build_reddit_client  # noqa: E402

logger = logging.getLogger("reddit_post")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)


def main() -> int:
    post_id = os.environ.get("POST_ID", "").strip()
    if not post_id:
        print("::error::POST_ID is empty", file=sys.stderr)
        return 1

    comment_path = os.environ.get("COMMENT_PATH", "comment.md")
    body_path = Path(comment_path)
    if not body_path.is_file():
        print(f"::error::Comment file not found: {comment_path}", file=sys.stderr)
        return 1
    body = body_path.read_text(encoding="utf-8").strip()
    if not body:
        print("::error::Comment body is empty", file=sys.stderr)
        return 1

    dry_run = os.environ.get("DRY_RUN", "false").lower() == "true"
    sleep_seconds = float(os.environ.get("SLEEP_SECONDS", "30"))

    if dry_run:
        logger.info("DRY RUN — would post to submission %s:", post_id)
        logger.info("%s", body[:500] + ("..." if len(body) > 500 else ""))
        return 0

    if sleep_seconds > 0:
        logger.info("Sleeping %.0fs before posting (API courtesy)...", sleep_seconds)
        time.sleep(sleep_seconds)

    try:
        reddit = build_reddit_client()
        submission = reddit.submission(id=post_id)
        comment = submission.reply(body=body)
        logger.info("Posted: https://reddit.com%s", comment.permalink)
        print(f"::notice::Posted comment to r/{submission.subreddit.display_name}: https://reddit.com{comment.permalink}")
    except Exception as exc:
        print(f"::error::Failed to post comment to {post_id}: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
