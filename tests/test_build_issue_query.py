"""Tests for scripts/build_issue_query.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from build_issue_query import (  # noqa: E402
    build_query,
    emit_output,
    main,
    render_audience_blocks,
)


class TestRenderAudienceBlocks:
    def test_reporter_only(self):
        out = render_audience_blocks("reporter")
        assert "**For the reporter**" in out
        assert "**For maintainers**" not in out

    def test_maintainer_only(self):
        out = render_audience_blocks("maintainer")
        assert "**For maintainers**" in out
        assert "**For the reporter**" not in out

    def test_both(self):
        out = render_audience_blocks("both")
        assert "**For the reporter**" in out
        assert "**For maintainers**" in out
        assert out.startswith("(1)")

    def test_invalid(self):
        with pytest.raises(ValueError):
            render_audience_blocks("nobody")


class TestBuildQuery:
    def _build(self, **kwargs):
        defaults = {
            "title": "Login button does nothing",
            "body": "Clicking the login button has no effect.",
            "template_ref": "issue_open_ended",
            "audience": "both",
            "project_name": "",
            "max_body_chars": 4000,
        }
        defaults.update(kwargs)
        return build_query(**defaults)

    def test_includes_title(self):
        out = self._build()
        assert "Login button does nothing" in out

    def test_body_wrapped_in_sentinel(self):
        out = self._build()
        assert "<<<ISSUE_BODY" in out
        assert "ISSUE_BODY>>>" in out
        assert "Clicking the login button has no effect." in out

    def test_project_name_injected(self):
        out = self._build(project_name="My Project")
        assert "the My Project project" in out

    def test_no_project_name_default_phrase(self):
        out = self._build(project_name="")
        assert "this project" in out

    def test_audience_reporter_only_blocks(self):
        out = self._build(audience="reporter")
        assert "**For the reporter**" in out
        assert "**For maintainers**" not in out

    def test_strips_control_chars_in_body(self):
        out = self._build(body="bad\x00body\x07here")
        assert "\x00" not in out
        assert "\x07" not in out

    def test_truncates_long_body(self):
        long_body = "x" * 10_000
        out = self._build(body=long_body, max_body_chars=100)
        # Allow up to 100 'x' chars; should not contain 200+ in a row.
        assert "x" * 101 not in out

    def test_prefix_and_suffix_included(self):
        out = self._build(prompt_prefix="PREFIX_TEXT", prompt_suffix="SUFFIX_TEXT")
        assert "PREFIX_TEXT" in out
        assert "SUFFIX_TEXT" in out

    def test_invalid_template_ref(self):
        with pytest.raises(FileNotFoundError):
            self._build(template_ref="does_not_exist")

    def test_invalid_audience(self):
        with pytest.raises(ValueError):
            self._build(audience="invalid")


class TestEmitOutput:
    def test_emits_heredoc_to_github_output(self, tmp_path, monkeypatch):
        out_file = tmp_path / "output.txt"
        monkeypatch.setenv("GITHUB_OUTPUT", str(out_file))
        emit_output("query", "first line\nsecond line")
        content = out_file.read_text()
        # Format: name<<DELIM\nvalue\nDELIM\n
        assert content.startswith("query<<EOF_")
        assert "first line\nsecond line" in content
        # Delimiter line + closing delimiter
        lines = content.strip().split("\n")
        assert lines[0].startswith("query<<EOF_")
        delim = lines[0].removeprefix("query<<")
        assert lines[-1] == delim

    def test_emits_to_stdout_when_no_github_output(self, capsys, monkeypatch):
        monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
        emit_output("query", "hello")
        captured = capsys.readouterr()
        assert "query<<EOF_" in captured.out
        assert "hello" in captured.out


class TestMain:
    def test_full_run_with_defaults(self, tmp_path, monkeypatch):
        out_file = tmp_path / "output.txt"
        monkeypatch.setenv("GITHUB_OUTPUT", str(out_file))
        monkeypatch.setenv("ISSUE_TITLE", "Bug in foo")
        monkeypatch.setenv("ISSUE_BODY", "Steps to reproduce: ...")
        monkeypatch.setenv("TEMPLATE_REF", "issue_open_ended")
        monkeypatch.setenv("AUDIENCE", "both")
        monkeypatch.setenv("PROJECT_NAME", "Foo")
        monkeypatch.setenv("MAX_BODY_CHARS", "4000")
        rc = main()
        assert rc == 0
        content = out_file.read_text()
        assert "query<<EOF_" in content
        assert "header<<EOF_" in content
        assert "subheader<<EOF_" in content
        assert "Bug in foo" in content

    def test_empty_title_errors(self, monkeypatch, capsys):
        monkeypatch.setenv("ISSUE_TITLE", "")
        rc = main()
        assert rc == 1
        err = capsys.readouterr().err
        assert "ISSUE_TITLE is empty" in err
