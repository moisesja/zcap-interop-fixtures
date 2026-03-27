from __future__ import annotations

import base64
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .adapters import Adapter
from .fixtures import iter_fixture_paths, load_fixture, relative_fixture_path


def emit_entry(adapter: Adapter, fixture: dict[str, Any], *, fixture_path: Path, fixtures_dir: Path) -> dict[str, Any]:
    kind = fixture["kind"]
    document = fixture["document"]
    proof = fixture["proof"]

    try:
        if kind == "capability":
            canonical = adapter.canonicalize_capability_payload(document, proof)
        elif kind == "invocation":
            canonical = adapter.canonicalize_invocation_payload(document, proof)
        else:
            raise ValueError(f"Unknown fixture kind: {kind}")
        return {
            "name": fixture["name"],
            "kind": kind,
            "tags": fixture["tags"],
            "status": "ok",
            "fixture_path": relative_fixture_path(fixtures_dir, fixture_path),
            "canonical_base64": base64.b64encode(canonical).decode("ascii"),
            "canonical_sha256": hashlib.sha256(canonical).hexdigest(),
            "canonical_utf8": canonical.decode("utf-8"),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "name": fixture["name"],
            "kind": kind,
            "tags": fixture["tags"],
            "status": "error",
            "fixture_path": relative_fixture_path(fixtures_dir, fixture_path),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def build_manifest(adapter: Adapter, fixtures_dir: Path) -> dict[str, Any]:
    fixtures_dir = fixtures_dir.resolve()
    entries: list[dict[str, Any]] = []
    kind_counts: Counter[str] = Counter()

    for fixture_path in iter_fixture_paths(fixtures_dir):
        fixture = load_fixture(fixture_path)
        entries.append(emit_entry(adapter, fixture, fixture_path=fixture_path, fixtures_dir=fixtures_dir))
        kind_counts[fixture["kind"]] += 1

    return {
        "manifest_version": 1,
        "runner": adapter.runner,
        "adapter": adapter.name,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "fixture_count": len(entries),
        "fixture_kind_counts": dict(sorted(kind_counts.items())),
        "fixtures": entries,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")

