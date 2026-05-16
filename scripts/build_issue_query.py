#!/usr/bin/env python3
"""Assemble an LDR research query from a GitHub issue's title and body.

Reads inputs from environment variables (set by the calling workflow):

  ISSUE_TITLE         the issue title
  ISSUE_BODY          the issue body (may be empty for title-only issues)
  TEMPLATE_REF        prompt template name without extension (e.g.
                      ``issue_open_ended``, ``issue_reporter_and_maintainer``)
  AUDIENCE            ``reporter`` | ``maintainer`` | ``both``
  PROJECT_NAME        injected verbatim into the template (e.g. ``My Project``)
  MAX_BODY_CHARS      integer; body is truncated to this length
  PROMPT_PREFIX       optional extra text prepended to the assembled prompt
  PROMPT_SUFFIX       optional extra text appended to the assembled prompt

Writes three lines to GITHUB_OUTPUT via randomised-delimiter heredocs:

  query    the full assembled LLM prompt
  header   the comment header (markdown)
  subheader  the comment subheader (markdown)

If GITHUB_OUTPUT is unset (e.g. running locally for dev), writes to stdout
in the same heredoc format for inspection.
"""

from __future__ import annotations

import os
import secrets
import sys
import textwrap
from pathlib import Path

from sanitize_text import sanitize_field, wrap_in_sentinel

TEMPLATE_DIR = Path(__file__).parent / "prompt_templates"

VALID_AUDIENCES = {"reporter", "maintainer", "both"}

# Reporter-only block: instructs the LLM to address the issue reporter
# directly with a brief, cautious answer.
REPORTER_BLOCK = textwrap.dedent(
    """\
    **For the reporter** — a brief, cautious, 2–4 sentence summary of likely
    diagnostic directions, framed as suggestions and not authoritative
    diagnosis. If you don't have enough context to be useful, say so plainly.
    """
).strip()

# Maintainer-only block: research context for triage.
MAINTAINER_BLOCK = textwrap.dedent(
    """\
    **For maintainers** — adjacent external context: similar reports in
    other projects, relevant upstream library documentation, known issues
    with the components mentioned, and related discussions. Treat the
    maintainer as the primary audience for the substantive research.
    """
).strip()


def load_template(template_ref: str) -> str:
    """Read ``<template_ref>.txt`` from the prompt_templates dir."""
    if not template_ref.replace("_", "").isalnum():
        raise ValueError(f"Invalid template ref: {template_ref!r}")
    path = TEMPLATE_DIR / f"{template_ref}.txt"
    if not path.is_file():
        raise FileNotFoundError(f"Template not found: {path}")
    return path.read_text(encoding="utf-8")


def render_audience_blocks(audience: str) -> str:
    """Return the audience-specific instruction block(s)."""
    if audience == "reporter":
        return REPORTER_BLOCK
    if audience == "maintainer":
        return MAINTAINER_BLOCK
    if audience == "both":
        return f"(1) {REPORTER_BLOCK}\n\n(2) {MAINTAINER_BLOCK}"
    raise ValueError(f"Invalid audience: {audience!r} (expected one of {VALID_AUDIENCES})")


def build_query(
    title: str,
    body: str,
    template_ref: str,
    audience: str,
    project_name: str,
    max_body_chars: int,
    prompt_prefix: str = "",
    prompt_suffix: str = "",
) -> str:
    """Assemble the final LLM prompt string."""
    safe_title = sanitize_field(title, 500)
    safe_body = sanitize_field(body or "", max_body_chars)
    template = load_template(template_ref)

    audience_blocks = render_audience_blocks(audience)
    project_phrase = f"the {project_name} project" if project_name else "this project"

    rendered = (
        template.replace("{{PROJECT_PHRASE}}", project_phrase)
        .replace("{{AUDIENCE_BLOCK}}", audience_blocks)
        .replace("{{ISSUE_TITLE}}", safe_title)
        .replace("{{ISSUE_BODY}}", wrap_in_sentinel(safe_body, "ISSUE_BODY"))
    )

    parts = []
    if prompt_prefix:
        parts.append(sanitize_field(prompt_prefix, 2000))
    parts.append(rendered)
    if prompt_suffix:
        parts.append(sanitize_field(prompt_suffix, 2000))
    return "\n\n".join(parts).strip() + "\n"


def emit_output(name: str, value: str) -> None:
    """Write a single multi-line value to GITHUB_OUTPUT (or stdout)."""
    delim = f"EOF_{secrets.token_hex(8)}"
    line = f"{name}<<{delim}\n{value}\n{delim}\n"
    out_path = os.environ.get("GITHUB_OUTPUT")
    if out_path:
        with open(out_path, "a", encoding="utf-8") as f:
            f.write(line)
    else:
        sys.stdout.write(line)


def main() -> int:
    title = os.environ.get("ISSUE_TITLE", "").strip()
    body = os.environ.get("ISSUE_BODY", "")
    template_ref = os.environ.get("TEMPLATE_REF", "issue_open_ended").strip()
    audience = os.environ.get("AUDIENCE", "both").strip()
    project_name = os.environ.get("PROJECT_NAME", "").strip()
    max_body = int(os.environ.get("MAX_BODY_CHARS", "4000"))
    prefix = os.environ.get("PROMPT_PREFIX", "")
    suffix = os.environ.get("PROMPT_SUFFIX", "")

    if not title:
        print("::error::ISSUE_TITLE is empty", file=sys.stderr)
        return 1

    query = build_query(
        title=title,
        body=body,
        template_ref=template_ref,
        audience=audience,
        project_name=project_name,
        max_body_chars=max_body,
        prompt_prefix=prefix,
        prompt_suffix=suffix,
    )

    # Header and subheader for the eventual comment.
    header = "## 🤖 LDR Research"
    if audience == "reporter":
        subheader = (
            "_Auto-generated research suggestions for the reporter — review "
            "before treating as authoritative._"
        )
    elif audience == "maintainer":
        subheader = "_Auto-generated context for maintainer triage._"
    else:
        subheader = (
            "_Auto-generated context for maintainer triage and the "
            "reporter — see disclaimer below._"
        )

    emit_output("query", query)
    emit_output("header", header)
    emit_output("subheader", subheader)
    return 0


if __name__ == "__main__":
    sys.exit(main())
