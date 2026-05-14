"""Input sanitisation for untrusted-ish user content.

Used by the issue-helper, pr-code-review, and reddit-qa meta-reusables to
prep user-provided text (issue bodies, PR descriptions, Reddit posts)
before it's embedded in an LLM prompt.

This is best-effort defence-in-depth, not a security boundary. Prompt
injection is fundamentally an LLM-side problem; we just make it harder.
"""

from __future__ import annotations

import string

# Strip C0 and DEL control chars but keep \t \n \r (the typical "useful"
# whitespace). Anything else from \x00-\x1F is suspect (BiDi overrides,
# null bytes, etc.) and gets dropped.
_ALLOWED_CONTROLS = {"\t", "\n", "\r"}
_CONTROL_RANGE = set(chr(c) for c in range(0x00, 0x20)) | {chr(0x7F)}
_STRIP_CHARS = _CONTROL_RANGE - _ALLOWED_CONTROLS

# Translation table: each char in _STRIP_CHARS → None (delete).
_STRIP_TABLE = str.maketrans({c: None for c in _STRIP_CHARS})


def strip_controls(text: str) -> str:
    """Remove control characters except for \\t \\n \\r."""
    return text.translate(_STRIP_TABLE)


def truncate(text: str, max_chars: int) -> str:
    """Truncate to ``max_chars``. Returns text unchanged if shorter."""
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    return text[: max_chars]


def wrap_in_sentinel(text: str, name: str) -> str:
    """Wrap *text* in a sentinel block the LLM is instructed to treat as data.

    Example: ``wrap_in_sentinel("foo", "ISSUE_BODY")`` returns
    ``"<<<ISSUE_BODY\\nfoo\\nISSUE_BODY>>>"``. The opening and closing
    markers are intentionally asymmetric (``<<<NAME`` vs ``NAME>>>``)
    so the model can't easily mimic them with a naive payload.
    """
    if not name.replace("_", "").isalnum():
        raise ValueError(
            f"Sentinel name must be alphanumeric or underscore, got: {name!r}"
        )
    return f"<<<{name}\n{text}\n{name}>>>"


def sanitize_field(text: str, max_chars: int) -> str:
    """One-stop call for caller workflows: strip controls + truncate."""
    return truncate(strip_controls(text), max_chars)


__all__ = [
    "strip_controls",
    "truncate",
    "wrap_in_sentinel",
    "sanitize_field",
]
