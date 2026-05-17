#!/usr/bin/env python3
"""Validate that the toolkit version is consistent across files.

Checked files:
  - ``version.py``         (single source of truth: ``__version__``)
  - ``pyproject.toml``     (reads version dynamically from ``version.py``;
                            we verify the dynamic-version wiring resolves
                            to the same string)
  - ``CHANGELOG.md``       (top non-``[Unreleased]`` heading must match)

Exits 0 on success, 1 on any mismatch with a human-readable diff.
"""

from __future__ import annotations

import re
import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_version_py() -> str:
    text = (ROOT / "version.py").read_text(encoding="utf-8")
    match = re.search(r'^\s*__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise SystemExit('::error::version.py is missing __version__ = "..."')
    return match.group(1)


def read_pyproject_version() -> str:
    """Resolve the dynamically-declared version via importlib.metadata.

    The package must be installed (``pip install -e .``) for this to work.
    The CI workflow installs the package as a prerequisite step.
    """
    try:
        return metadata.version("ldr-automations")
    except metadata.PackageNotFoundError as exc:
        raise SystemExit(
            "::error::ldr-automations is not installed. "
            "Run `pip install -e .` before invoking this check."
        ) from exc


def read_changelog_top_version() -> str:
    """Return the version from the first ``## [X.Y.Z]`` heading.

    Skips ``## [Unreleased]`` so an unreleased section between two
    real entries doesn't fail the check while a release PR is in
    flight.
    """
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    # Match "## [X.Y.Z]" possibly followed by " — title"
    pattern = re.compile(r"^##\s+\[([0-9]+\.[0-9]+\.[0-9]+)\]", re.MULTILINE)
    matches = pattern.findall(text)
    if not matches:
        raise SystemExit(
            "::error::CHANGELOG.md has no `## [X.Y.Z]` heading — every release needs an entry."
        )
    return matches[0]


def main() -> int:
    version_py = read_version_py()
    pyproject = read_pyproject_version()
    changelog = read_changelog_top_version()

    versions = {
        "version.py": version_py,
        "pyproject.toml (resolved)": pyproject,
        "CHANGELOG.md (top entry)": changelog,
    }

    unique = set(versions.values())
    if len(unique) == 1:
        print(f"✅ All version sources agree: {version_py}")
        return 0

    print("::error::Version mismatch across files:")
    width = max(len(k) for k in versions)
    for source, val in versions.items():
        print(f"  {source.ljust(width)}  =  {val}")
    print()
    print(
        "Fix: update all three (version.py + CHANGELOG.md heading) to the "
        "intended version. pyproject.toml uses dynamic version from "
        "version.py, so it will follow automatically after reinstall."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
