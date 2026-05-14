"""Tests for scripts/sanitize_text.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from sanitize_text import (  # noqa: E402
    sanitize_field,
    strip_controls,
    truncate,
    wrap_in_sentinel,
)


class TestStripControls:
    def test_preserves_tab_newline_carriage_return(self):
        text = "line1\nline2\tcolumn\r\nline3"
        assert strip_controls(text) == text

    def test_strips_null_byte(self):
        assert strip_controls("hello\x00world") == "helloworld"

    def test_strips_del(self):
        assert strip_controls("a\x7fb") == "ab"

    def test_strips_bidi_override_range(self):
        # \x1b is ESC, often used in ANSI escape sequences.
        assert strip_controls("\x1b[31mred") == "[31mred"

    def test_no_op_on_normal_text(self):
        text = "The quick brown fox. Über coñtent. 日本語."
        assert strip_controls(text) == text


class TestTruncate:
    def test_returns_text_when_short(self):
        assert truncate("hello", 100) == "hello"

    def test_truncates_when_long(self):
        assert truncate("hello world", 5) == "hello"

    def test_zero_or_negative_returns_empty(self):
        assert truncate("hello", 0) == ""
        assert truncate("hello", -1) == ""

    def test_exact_length(self):
        assert truncate("hello", 5) == "hello"


class TestWrapInSentinel:
    def test_basic(self):
        out = wrap_in_sentinel("foo", "ISSUE_BODY")
        assert out == "<<<ISSUE_BODY\nfoo\nISSUE_BODY>>>"

    def test_preserves_internal_whitespace(self):
        out = wrap_in_sentinel("line1\nline2", "REDDIT_POST")
        assert "line1\nline2" in out

    def test_rejects_invalid_name(self):
        with pytest.raises(ValueError):
            wrap_in_sentinel("x", "with spaces")
        with pytest.raises(ValueError):
            wrap_in_sentinel("x", "has-dash")

    def test_allows_underscore(self):
        out = wrap_in_sentinel("x", "MY_BLOCK_NAME")
        assert out.startswith("<<<MY_BLOCK_NAME\n")


class TestSanitizeField:
    def test_combined_strip_and_truncate(self):
        text = "hello\x00world this is long"
        out = sanitize_field(text, 11)
        assert out == "helloworld "

    def test_empty_string(self):
        assert sanitize_field("", 100) == ""
