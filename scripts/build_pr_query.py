#!/usr/bin/env python3
"""Assemble an LDR research query from a GitHub Pull Request's diff.

Modes:
  diff    — fetch the PR's diff via git, embed in a research prompt
            asking LDR to research relevant docs / known issues / etc.
  static  — use a fixed query (from STATIC_QUERY env var). Useful as a
            cheap smoke test for the toolkit pipeline that doesn't depend
            on the PR's actual content.

Inputs (env vars set by the caller workflow):

  MODE              ``diff`` (default) or ``static``
  STATIC_QUERY      required when MODE=static
  TEMPLATE_REF      diff-mode prompt template name (e.g. ``pr_diff_review``)
  PROJECT_NAME      injected verbatim into the template
  DIFF_PATH         path to a file containing the PR diff
                    (caller workflow runs `git diff > diff.txt`)
  MAX_DIFF_BYTES    diff is truncated to this many bytes before embedding
  PROMPT_PREFIX     optional extra text prepended to the assembled prompt
  PROMPT_SUFFIX     optional extra text appended to the assembled prompt

Outputs (via GITHUB_OUTPUT heredoc, same shape as build_issue_query.py):

  query, header, subheader
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Reuse helpers from the issue-query script for consistency.
sys.path.insert(0, str(Path(__file__).parent))

from build_issue_query import emit_output  # noqa: E402
from sanitize_text import sanitize_field, wrap_in_sentinel  # noqa: E402

TEMPLATE_DIR = Path(__file__).parent / "prompt_templates"


def load_template(template_ref: str) -> str:
    if not template_ref.replace("_", "").isalnum():
        raise ValueError(f"Invalid template ref: {template_ref!r}")
    path = TEMPLATE_DIR / f"{template_ref}.txt"
    if not path.is_file():
        raise FileNotFoundError(f"Template not found: {path}")
    return path.read_text(encoding="utf-8")


def read_diff(diff_path: str, max_bytes: int) -> str:
    """Read the diff file and truncate to ``max_bytes``.

    Truncation works on the **decoded text** length so we don't risk
    splitting a multi-byte UTF-8 char in half. Appends a ``... (truncated)``
    marker if truncation actually happened.
    """
    if max_bytes <= 0:
        return ""
    p = Path(diff_path)
    if not p.is_file():
        raise FileNotFoundError(f"Diff file not found: {diff_path}")
    raw = p.read_text(encoding="utf-8", errors="replace")
    if len(raw) <= max_bytes:
        return raw
    return raw[:max_bytes] + "\n... (truncated)\n"


def build_diff_query(
    diff: str,
    template_ref: str,
    project_name: str,
    prompt_prefix: str = "",
    prompt_suffix: str = "",
) -> str:
    template = load_template(template_ref)
    project_phrase = (
        f"the {project_name} project" if project_name else "this project"
    )
    rendered = (
        template.replace("{{PROJECT_PHRASE}}", project_phrase)
        .replace("{{DIFF}}", wrap_in_sentinel(diff, "PR_DIFF"))
    )

    parts = []
    if prompt_prefix:
        parts.append(sanitize_field(prompt_prefix, 2000))
    parts.append(rendered)
    if prompt_suffix:
        parts.append(sanitize_field(prompt_suffix, 2000))
    return "\n\n".join(parts).strip() + "\n"


def build_static_query(static_query: str) -> str:
    return sanitize_field(static_query, 5000) + "\n"


def main() -> int:
    mode = os.environ.get("MODE", "diff").strip()
    project_name = os.environ.get("PROJECT_NAME", "").strip()
    prefix = os.environ.get("PROMPT_PREFIX", "")
    suffix = os.environ.get("PROMPT_SUFFIX", "")

    if mode == "static":
        static_query = os.environ.get("STATIC_QUERY", "").strip()
        if not static_query:
            print("::error::STATIC_QUERY is empty in static mode", file=sys.stderr)
            return 1
        query = build_static_query(static_query)
        header = "## 🧪 LDR static query result"
        subheader = f"_Static smoke-test query: {sanitize_field(static_query, 200)}_"
    elif mode == "diff":
        template_ref = os.environ.get("TEMPLATE_REF", "pr_diff_review").strip()
        diff_path = os.environ.get("DIFF_PATH", "diff.txt")
        max_bytes = int(os.environ.get("MAX_DIFF_BYTES", "8000"))
        try:
            diff = read_diff(diff_path, max_bytes)
        except FileNotFoundError as exc:
            print(f"::error::{exc}", file=sys.stderr)
            return 1
        if not diff.strip():
            print("::error::Diff is empty", file=sys.stderr)
            return 1
        query = build_diff_query(
            diff=diff,
            template_ref=template_ref,
            project_name=project_name,
            prompt_prefix=prefix,
            prompt_suffix=suffix,
        )
        header = "## 🔬 LDR PR research"
        subheader = "_Auto-generated research context for this PR's diff. Treat as suggestions, not authoritative review._"
    else:
        print(f"::error::Invalid MODE: {mode!r} (expected 'diff' or 'static')", file=sys.stderr)
        return 1

    emit_output("query", query)
    emit_output("header", header)
    emit_output("subheader", subheader)
    return 0


if __name__ == "__main__":
    sys.exit(main())
