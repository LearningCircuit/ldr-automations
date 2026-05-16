"""Tests for scripts/reddit_fetch.py.

PRAW and requests are fully mocked — these tests don't hit the network.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from reddit_fetch import (  # noqa: E402
    Candidate,
    already_replied,
    classify_post,
    fetch_candidates,
    load_config_from_env,
    render_reddit_query,
    sanitize_id,
)


def _mock_submission(
    *,
    id_="abc123",
    title="t",
    selftext="b",
    age_hours=12,
    bot_already_commented=False,
    bot_username="ldr-bot",
):
    sub = MagicMock()
    sub.id = id_
    sub.title = title
    sub.selftext = selftext
    sub.created_utc = time.time() - age_hours * 3600

    # comments.replace_more is a no-op for our purposes
    sub.comments.replace_more = MagicMock(return_value=None)
    comments = []
    if bot_already_commented:
        c = MagicMock()
        c.author = MagicMock()
        c.author.name = bot_username
        c.body = "previous bot reply"
        comments.append(c)
    # Add a couple of non-bot comments to verify we iterate
    for name in ("alice", "bob"):
        c = MagicMock()
        c.author = MagicMock()
        c.author.name = name
        c.body = "human reply"
        comments.append(c)
    sub.comments.list.return_value = comments
    return sub


class TestSanitizeId:
    def test_alphanumeric_passes_through(self):
        assert sanitize_id("abc123") == "abc123"

    def test_replaces_unsafe_chars(self):
        assert sanitize_id("ab/cd?") == "ab_cd_"


class TestAlreadyReplied:
    def test_returns_true_when_bot_commented(self):
        sub = _mock_submission(bot_already_commented=True)
        assert already_replied(sub, "ldr-bot") is True

    def test_returns_false_when_bot_absent(self):
        sub = _mock_submission(bot_already_commented=False)
        assert already_replied(sub, "ldr-bot") is False

    def test_skips_comments_with_no_author(self):
        sub = _mock_submission()
        deleted = MagicMock()
        deleted.author = None
        deleted.body = "[deleted]"
        sub.comments.list.return_value = [deleted]
        # We can't tell who authored the deleted comment, so return False.
        # The min-post-age-hours filter is the upstream mitigation.
        assert already_replied(sub, "ldr-bot") is False

    def test_case_insensitive(self):
        sub = _mock_submission(bot_already_commented=True, bot_username="LDR-Bot")
        assert already_replied(sub, "ldr-bot") is True


class TestRenderRedditQuery:
    def test_substitutes_all_placeholders(self):
        out = render_reddit_query(
            template_ref="reddit_qa",
            subreddit="LocalLLM",
            title="How to run llama?",
            body="I have a 3090.",
        )
        assert "r/LocalLLM" in out
        assert "How to run llama?" in out
        assert "<<<REDDIT_POST" in out
        assert "I have a 3090." in out

    def test_invalid_template_raises(self):
        with pytest.raises(FileNotFoundError):
            render_reddit_query(
                template_ref="nonexistent",
                subreddit="x",
                title="x",
                body="x",
            )


class TestClassifyPost:
    def _mock_openrouter(self, label_text):
        """Return a function suitable as requests.post side_effect."""
        resp = MagicMock()
        resp.json.return_value = {"choices": [{"message": {"content": label_text}}]}
        resp.raise_for_status = MagicMock()
        return resp

    def test_classifier_returns_ok(self):
        with patch("reddit_fetch.requests.post") as mp:
            mp.return_value = self._mock_openrouter("OK")
            assert classify_post("t", "b", "model", "key") == "OK"

    def test_classifier_returns_skip_sentiment(self):
        with patch("reddit_fetch.requests.post") as mp:
            mp.return_value = self._mock_openrouter("SKIP_SENTIMENT")
            assert classify_post("t", "b", "model", "key") == "SKIP_SENTIMENT"

    def test_classifier_strips_markdown_wrapping(self):
        with patch("reddit_fetch.requests.post") as mp:
            mp.return_value = self._mock_openrouter("**OK**")
            assert classify_post("t", "b", "model", "key") == "OK"

    def test_classifier_unknown_label_falls_to_ok(self):
        with patch("reddit_fetch.requests.post") as mp:
            mp.return_value = self._mock_openrouter("NOT_A_REAL_LABEL")
            # Function defaults to OK when label invalid
            assert classify_post("t", "b", "model", "key") == "OK"

    def test_classifier_api_failure_fails_open_to_ok(self):
        with patch("reddit_fetch.requests.post") as mp:
            mp.side_effect = Exception("network error")
            assert classify_post("t", "b", "model", "key") == "OK"

    def test_classifier_no_api_key_returns_ok(self):
        assert classify_post("t", "b", "model", "") == "OK"


class TestFetchCandidates:
    def _config(self, **overrides):
        defaults = {
            "subreddit": "test",
            "bot_username": "ldr-bot",
            "post_limit": 25,
            "min_post_age_hours": 6,
            "max_post_age_hours": 24,
            "max_posts_per_run": 3,
            "classifier_model": "anthropic/claude-haiku-4.5",
            "openrouter_key": "fake-key",
            "title_max": 300,
            "selftext_max": 2000,
            "template_ref": "reddit_qa",
        }
        defaults.update(overrides)
        return defaults

    def _reddit_with(self, submissions):
        reddit = MagicMock()
        reddit.subreddit.return_value.new.return_value = iter(submissions)
        return reddit

    def test_returns_empty_when_subreddit_empty(self):
        reddit = self._reddit_with([])
        result = fetch_candidates(reddit, self._config())
        assert result == []

    def test_filters_too_young(self):
        sub = _mock_submission(id_="young", age_hours=1)  # younger than 6h
        reddit = self._reddit_with([sub])
        with patch("reddit_fetch.classify_post", return_value="OK"):
            result = fetch_candidates(reddit, self._config())
        assert result == []

    def test_filters_too_old(self):
        sub = _mock_submission(id_="old", age_hours=48)  # older than 24h
        reddit = self._reddit_with([sub])
        with patch("reddit_fetch.classify_post", return_value="OK"):
            result = fetch_candidates(reddit, self._config())
        assert result == []

    def test_filters_already_replied(self):
        sub = _mock_submission(id_="replied", bot_already_commented=True)
        reddit = self._reddit_with([sub])
        with patch("reddit_fetch.classify_post", return_value="OK"):
            result = fetch_candidates(reddit, self._config())
        assert result == []

    def test_filters_skip_sentiment(self):
        sub = _mock_submission(id_="ranty")
        reddit = self._reddit_with([sub])
        with patch("reddit_fetch.classify_post", return_value="SKIP_SENTIMENT"):
            result = fetch_candidates(reddit, self._config())
        assert result == []

    def test_includes_ok_posts(self):
        sub = _mock_submission(id_="good", title="Real question", selftext="Real body")
        reddit = self._reddit_with([sub])
        with patch("reddit_fetch.classify_post", return_value="OK"):
            result = fetch_candidates(reddit, self._config())
        assert len(result) == 1
        c = result[0]
        assert isinstance(c, Candidate)
        assert c.id == "good"
        assert c.id_sanitized == "good"
        assert c.title == "Real question"
        assert "Real body" in c.selftext_sanitized
        assert "<<<REDDIT_POST" in c.query

    def test_respects_max_posts_per_run(self):
        subs = [_mock_submission(id_=f"post{i}", title=f"q{i}", selftext="body") for i in range(10)]
        reddit = self._reddit_with(subs)
        with patch("reddit_fetch.classify_post", return_value="OK"):
            result = fetch_candidates(reddit, self._config(max_posts_per_run=2))
        assert len(result) == 2

    def test_sanitizes_title_and_body(self):
        sub = _mock_submission(
            id_="dirty",
            title="bad\x00title",
            selftext="bad\x07body",
        )
        reddit = self._reddit_with([sub])
        with patch("reddit_fetch.classify_post", return_value="OK"):
            result = fetch_candidates(reddit, self._config())
        assert "\x00" not in result[0].title
        assert "\x07" not in result[0].selftext_sanitized


class TestLoadConfigFromEnv:
    def test_required_vars(self, monkeypatch):
        monkeypatch.setenv("SUBREDDIT", "test")
        monkeypatch.setenv("BOT_USERNAME", "bot")
        cfg = load_config_from_env()
        assert cfg["subreddit"] == "test"
        assert cfg["bot_username"] == "bot"
        # Defaults
        assert cfg["post_limit"] == 25
        assert cfg["max_posts_per_run"] == 3
        assert cfg["template_ref"] == "reddit_qa"

    def test_overrides(self, monkeypatch):
        monkeypatch.setenv("SUBREDDIT", "x")
        monkeypatch.setenv("BOT_USERNAME", "y")
        monkeypatch.setenv("POST_LIMIT", "5")
        monkeypatch.setenv("MAX_POSTS_PER_RUN", "1")
        monkeypatch.setenv("MIN_POST_AGE_HOURS", "0")
        cfg = load_config_from_env()
        assert cfg["post_limit"] == 5
        assert cfg["max_posts_per_run"] == 1
        assert cfg["min_post_age_hours"] == 0.0

    def test_missing_required_raises(self, monkeypatch):
        monkeypatch.delenv("SUBREDDIT", raising=False)
        with pytest.raises(KeyError):
            load_config_from_env()


class TestSerialization:
    def test_candidate_to_dict_json_roundtrip(self):
        c = Candidate(
            id="abc",
            id_sanitized="abc",
            title="hello",
            selftext_sanitized="world",
            query="full prompt here",
        )
        json_str = json.dumps([asdict(c)])
        decoded = json.loads(json_str)
        assert decoded[0]["id"] == "abc"
        assert decoded[0]["query"] == "full prompt here"
