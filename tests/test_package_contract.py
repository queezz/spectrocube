"""Tests for synchronized public package and installed-resource surfaces."""

from __future__ import annotations

import importlib.metadata
import importlib.resources
import re
from pathlib import Path

import spectrocube

ROOT = Path(__file__).resolve().parents[1]


def _project_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', text, flags=re.MULTILINE)
    assert match is not None
    return match.group(1)


def test_public_versions_are_synchronized():
    version = _project_version()
    assert version == "0.2.0"
    assert spectrocube.__version__ == version
    assert spectrocube.SPECTROCUBE_VERSION == version
    assert f"version is **{version}**" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"Version: {version}" in (ROOT / "SPEC.md").read_text(encoding="utf-8")
    assert f"Version: {version}" in (ROOT / "docs" / "spec.md").read_text(encoding="utf-8")
    assert f"## {version}" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")


def test_installed_specification_resource_matches_public_spec():
    public = (ROOT / "SPEC.md").read_text(encoding="utf-8")
    installed = (
        importlib.resources.files("spectrocube").joinpath("SPEC.md").read_text(encoding="utf-8")
    )
    assert installed == public
    assert (ROOT / "docs" / "spec.md").read_text(encoding="utf-8") == public


def test_installed_changelog_resource_matches_public_changelog():
    installed = (
        importlib.resources.files("spectrocube")
        .joinpath("CHANGELOG.md")
        .read_text(encoding="utf-8")
    )
    assert installed == (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")


def test_console_entry_points_are_registered():
    scripts = {
        entry.name: entry.value
        for entry in importlib.metadata.entry_points(group="console_scripts")
        if entry.name.startswith("spectrocube-")
    }
    assert scripts["spectrocube-info"] == "spectrocube.cli:info_main"
    assert scripts["spectrocube-validate"] == "spectrocube.cli:validate_main"
