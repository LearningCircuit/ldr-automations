"""Tests for scripts/build_pr_query.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from build_pr_query import (  # noqa: E402
    build_diff_query,
    build_static_query,
    main,
    read_diff,
)


class TestReadDiff:
    def test_reads_full_diff_when_under_limit(self, tmp_path):
        p = tmp_path / "diff.txt"
        p.write_text("diff --git a/foo b/foo\n+hello\n")
        out = read_diff(str(p), 1000)
        assert "hello" in out
        assert "truncated" not in out

    def test_truncates_when_over_limit(self, tmp_path):
        p = tmp_path / "diff.txt"
        p.write_text("x" * 5000)
        out = read_diff(str(p), 100)
        # 100 chars of x's + truncation marker
        assert out.count("x") == 100
        assert "... (truncated)" in out

    def test_zero_max_bytes_returns_empty(self, tmp_path):
        p = tmp_path / "diff.txt"
        p.write_text("anything")
        assert read_diff(str(p), 0) == ""

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            read_diff("/tmp/this-file-does-not-exist-x9z.txt", 1000)


class TestBuildDiffQuery:
    def _build(self, **kwargs):
        defaults = {
            "diff": "diff --git a/foo b/foo\n+hello\n",
            "template_ref": "pr_diff_review",
            "project_name": "",
        }
        defaults.update(kwargs)
        return build_diff_query(**defaults)

    def test_wraps_diff_in_sentinel(self):
        out = self._build()
        assert "<<<PR_DIFF" in out
        assert "PR_DIFF>>>" in out

    def test_project_name_injected(self):
        out = self._build(project_name="MyApp")
        assert "the MyApp project" in out

    def test_no_project_name_default_phrase(self):
        out = self._build(project_name="")
        assert "this project" in out

    def test_prefix_and_suffix(self):
        out = self._build(prompt_prefix="PREFIX", prompt_suffix="SUFFIX")
        assert "PREFIX" in out
        assert "SUFFIX" in out

    def test_invalid_template(self):
        with pytest.raises(FileNotFoundError):
            self._build(template_ref="nonexistent")


class TestBuildStaticQuery:
    def test_basic(self):
        out = build_static_query("Test query")
        assert "Test query" in out

    def test_truncates_huge_input(self):
        out = build_static_query("x" * 10000)
        # sanitize_field truncates to 5000
        assert len(out.strip()) <= 5000


class TestMainDiffMode:
    def test_diff_mode_happy_path(self, tmp_path, monkeypatch):
        diff_file = tmp_path / "diff.txt"
        diff_file.write_text("diff --git a/foo b/foo\n+hello world\n")
        out_file = tmp_path / "output.txt"

        monkeypatch.setenv("GITHUB_OUTPUT", str(out_file))
        monkeypatch.setenv("MODE", "diff")
        monkeypatch.setenv("DIFF_PATH", str(diff_file))
        monkeypatch.setenv("TEMPLATE_REF", "pr_diff_review")
        monkeypatch.setenv("PROJECT_NAME", "ldr-automations")
        monkeypatch.setenv("MAX_DIFF_BYTES", "8000")
        rc = main()
        assert rc == 0
        content = out_file.read_text()
        assert "query<<EOF_" in content
        assert "header<<EOF_" in content
        assert "subheader<<EOF_" in content
        assert "hello world" in content
        assert "## 🔬 LDR PR research" in content

    def test_diff_mode_empty_diff_errors(self, tmp_path, monkeypatch, capsys):
        diff_file = tmp_path / "empty.txt"
        diff_file.write_text("")
        monkeypatch.setenv("MODE", "diff")
        monkeypatch.setenv("DIFF_PATH", str(diff_file))
        rc = main()
        assert rc == 1
        assert "Diff is empty" in capsys.readouterr().err

    def test_diff_mode_missing_file_errors(self, monkeypatch, capsys):
        monkeypatch.setenv("MODE", "diff")
        monkeypatch.setenv("DIFF_PATH", "/tmp/nonexistent-xyz.txt")
        rc = main()
        assert rc == 1
        assert "Diff file not found" in capsys.readouterr().err


class TestMainStaticMode:
    def test_static_mode_happy_path(self, tmp_path, monkeypatch):
        out_file = tmp_path / "output.txt"
        monkeypatch.setenv("GITHUB_OUTPUT", str(out_file))
        monkeypatch.setenv("MODE", "static")
        monkeypatch.setenv("STATIC_QUERY", "What is LDR?")
        rc = main()
        assert rc == 0
        content = out_file.read_text()
        assert "What is LDR?" in content
        assert "## 🧪 LDR static query result" in content

    def test_static_mode_empty_query_errors(self, monkeypatch, capsys):
        monkeypatch.setenv("MODE", "static")
        monkeypatch.setenv("STATIC_QUERY", "")
        rc = main()
        assert rc == 1
        assert "STATIC_QUERY is empty" in capsys.readouterr().err


class TestMainInvalidMode:
    def test_invalid_mode_errors(self, monkeypatch, capsys):
        monkeypatch.setenv("MODE", "nonsense")
        rc = main()
        assert rc == 1
        assert "Invalid MODE" in capsys.readouterr().err
