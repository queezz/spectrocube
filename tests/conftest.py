"""Keep pytest's default temporary tree outside the Dropbox checkout."""

from __future__ import annotations

import tempfile
from pathlib import Path

_PYTEST_TEMP: tempfile.TemporaryDirectory[str] | None = None


def pytest_configure(config) -> None:
    """Choose a unique OS-local basetemp unless the caller supplied one."""
    global _PYTEST_TEMP
    if config.option.basetemp:
        return
    _PYTEST_TEMP = tempfile.TemporaryDirectory(prefix="spectrocube-pytest-")
    config.option.basetemp = str(Path(_PYTEST_TEMP.name) / "run")
    config.add_cleanup(_PYTEST_TEMP.cleanup)
