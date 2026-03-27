from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def index_manifest(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entry["name"]: entry for entry in manifest["fixtures"]}


def compare_manifests(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_index = index_manifest(left)
    right_index = index_manifest(right)
    names = sorted(set(left_index) | set(right_index))

    findings: list[dict[str, Any]] = []
    matched_fixture_count = 0
    kind_totals: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "findings": 0})
    tag_totals: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "findings": 0})

    for name in names:
        left_entry = left_index.get(name)
        right_entry = right_index.get(name)
        kind = (left_entry or right_entry or {}).get("kind", "unknown")
        tags = sorted(
            {
                *[(tag) for tag in (left_entry or {}).get("tags", [])],
                *[(tag) for tag in (right_entry or {}).get("tags", [])],
            }
        )

        kind_totals[kind]["total"] += 1
        for tag in tags:
            tag_totals[tag]["total"] += 1

        finding: dict[str, Any] | None = None
        if left_entry is None:
            finding = {
                "name": name,
                "kind": kind,
                "tags": tags,
                "category": "missing-left",
                "message": "Fixture missing from left manifest.",
            }
        elif right_entry is None:
            finding = {
                "name": name,
                "kind": kind,
                "tags": tags,
                "category": "missing-right",
                "message": "Fixture missing from right manifest.",
            }
        elif left_entry["status"] != right_entry["status"]:
            finding = {
                "name": name,
                "kind": kind,
                "tags": tags,
                "category": "status-mismatch",
                "message": f"Status mismatch: {left_entry['status']} vs {right_entry['status']}.",
                "left_status": left_entry["status"],
                "right_status": right_entry["status"],
            }
        elif left_entry["status"] == "error":
            if (
                left_entry.get("error_type") != right_entry.get("error_type")
                or left_entry.get("error") != right_entry.get("error")
            ):
                finding = {
                    "name": name,
                    "kind": kind,
                    "tags": tags,
                    "category": "error-mismatch",
                    "message": (
                        "Both adapters errored, but not in the same way: "
                        f"{left_entry.get('error_type')}: {left_entry.get('error')} vs "
                        f"{right_entry.get('error_type')}: {right_entry.get('error')}."
                    ),
                    "left_error_type": left_entry.get("error_type"),
                    "left_error": left_entry.get("error"),
                    "right_error_type": right_entry.get("error_type"),
                    "right_error": right_entry.get("error"),
                }
        elif left_entry["canonical_base64"] != right_entry["canonical_base64"]:
            finding = {
                "name": name,
                "kind": kind,
                "tags": tags,
                "category": "canonical-mismatch",
                "message": (
                    "Canonical bytes differ: "
                    f"{left_entry['canonical_sha256']} vs {right_entry['canonical_sha256']}."
                ),
                "left_sha256": left_entry["canonical_sha256"],
                "right_sha256": right_entry["canonical_sha256"],
            }

        if finding is None:
            matched_fixture_count += 1
            continue

        findings.append(finding)
        kind_totals[kind]["findings"] += 1
        for tag in tags:
            tag_totals[tag]["findings"] += 1

    compared_fixture_count = len(names)
    finding_count = len(findings)

    return {
        "comparison_version": 1,
        "left_runner": left.get("runner"),
        "left_adapter": left.get("adapter"),
        "right_runner": right.get("runner"),
        "right_adapter": right.get("adapter"),
        "status": "match" if finding_count == 0 else "mismatch",
        "compared_fixture_count": compared_fixture_count,
        "matched_fixture_count": matched_fixture_count,
        "finding_count": finding_count,
        "match_rate": round(matched_fixture_count / compared_fixture_count, 4) if compared_fixture_count else 1.0,
        "kind_breakdown": [
            {
                "kind": kind,
                "total": counts["total"],
                "findings": counts["findings"],
                "match_rate": round((counts["total"] - counts["findings"]) / counts["total"], 4)
                if counts["total"]
                else 1.0,
            }
            for kind, counts in sorted(kind_totals.items())
        ],
        "tag_breakdown": [
            {
                "tag": tag,
                "total": counts["total"],
                "findings": counts["findings"],
                "match_rate": round((counts["total"] - counts["findings"]) / counts["total"], 4)
                if counts["total"]
                else 1.0,
            }
            for tag, counts in sorted(
                tag_totals.items(),
                key=lambda item: (-item[1]["findings"], item[0]),
            )
        ],
        "findings": findings,
    }


def render_comparison_console(result: dict[str, Any]) -> str:
    heading = (
        f"{result['left_adapter']} vs {result['right_adapter']}: "
        f"{result['matched_fixture_count']}/{result['compared_fixture_count']} fixtures match "
        f"({result['match_rate']:.1%})"
    )

    if not result["findings"]:
        return f"{heading}\nNo interoperability findings."

    lines = [heading, "Findings:"]
    for finding in result["findings"]:
        lines.append(f"- {finding['name']}: {finding['message']}")
    return "\n".join(lines)

