from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def iter_fixture_paths(fixtures_dir: Path) -> list[Path]:
    return sorted(fixtures_dir.rglob("*.json"))


def load_fixture(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        fixture = json.load(handle)
    validate_fixture(path, fixture)
    return fixture


def validate_fixture(path: Path, fixture: dict[str, Any]) -> None:
    required = {"schema_version", "name", "kind", "profile", "tags", "document", "proof", "notes"}
    missing = sorted(required - set(fixture))
    if missing:
        raise ValueError(f"{path}: missing required keys: {missing}")
    unexpected = sorted(set(fixture) - required)
    if unexpected:
        raise ValueError(f"{path}: unexpected keys: {unexpected}")

    if fixture["schema_version"] != 1:
        raise ValueError(f"{path}: schema_version must be 1")
    if not isinstance(fixture["name"], str) or not fixture["name"].strip():
        raise ValueError(f"{path}: name must be a non-empty string")
    if fixture["kind"] not in {"capability", "invocation"}:
        raise ValueError(f"{path}: kind must be capability or invocation")
    if fixture["profile"] != "jcs-signing-payload-v1":
        raise ValueError(f"{path}: profile must be jcs-signing-payload-v1")
    if not isinstance(fixture["tags"], list) or any(not isinstance(tag, str) or not tag for tag in fixture["tags"]):
        raise ValueError(f"{path}: tags must be an array of non-empty strings")
    if not isinstance(fixture["document"], dict):
        raise ValueError(f"{path}: document must be an object")
    if not isinstance(fixture["proof"], dict):
        raise ValueError(f"{path}: proof must be an object")
    if not isinstance(fixture["notes"], str) or not fixture["notes"].strip():
        raise ValueError(f"{path}: notes must be a non-empty string")


def relative_fixture_path(fixtures_dir: Path, fixture_path: Path) -> str:
    relative = fixture_path.resolve().relative_to(fixtures_dir.resolve())
    return relative.as_posix()
