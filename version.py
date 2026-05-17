"""Single source of truth for the toolkit's version.

Read by:
- ``pyproject.toml`` (dynamic version)
- ``.github/workflows/version-check.yml`` (CI consistency check)
- ``scripts/`` if any future tooling wants to inspect it

When bumping a release: edit this file, the ``## [X.Y.Z]`` heading
in ``CHANGELOG.md``, and update the ``toolkit-ref: vX.Y.Z`` example
in each ``examples/*-caller.yml``. The version-check workflow
catches the first two; example files are manually checked.
"""

__version__ = "0.7.2"
