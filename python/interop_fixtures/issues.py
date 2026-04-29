from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


TAG_RULES: dict[str, dict[str, Any]] = {
    "type-preservation": {
        "key": "type-preservation",
        "title": "Capability `type` field is not preserved in canonical payloads",
        "summary": "The implementation appears to drop or mishandle the capability `type` field during payload canonicalization.",
        "labels": ["interop", "canonicalization", "model-shape"],
        "acceptance_criteria": [
            "`capability-type-preservation` matches the reference JCS manifest.",
            "Capability payload canonicalization preserves the `type` field instead of silently omitting it.",
        ],
    },
    "allowed-action": {
        "key": "allowed-action-presence",
        "title": "Missing and empty `allowedAction` are not handled distinctly",
        "summary": "The implementation appears to conflate a missing `allowedAction` field with an explicitly empty `allowedAction` array.",
        "labels": ["interop", "model-defaults", "field-presence"],
        "acceptance_criteria": [
            "`capability-allowed-action-missing` and `capability-allowed-action-empty` behave distinctly and match reference JCS output.",
            "Missing fields are not rewritten to empty arrays during canonicalization.",
        ],
    },
    "caveat": {
        "key": "caveat-presence",
        "title": "Missing and empty `caveat` are not handled distinctly",
        "summary": "The implementation appears to conflate a missing `caveat` field with an explicitly empty `caveat` array.",
        "labels": ["interop", "model-defaults", "field-presence"],
        "acceptance_criteria": [
            "`capability-caveat-missing` and `capability-caveat-empty` behave distinctly and match reference JCS output.",
            "Missing caveat fields are not rewritten to empty arrays during canonicalization.",
        ],
    },
    "capability-action-empty-string": {
        "key": "capability-action-empty-string",
        "title": "Empty `capabilityAction` is conflated with a missing field",
        "summary": "The implementation appears to treat an explicit empty `capabilityAction` string the same as a missing `capabilityAction` field.",
        "labels": ["interop", "model-defaults", "invocation"],
        "acceptance_criteria": [
            "`invocation-empty-capability-action-edge` and `invocation-missing-capability-action-edge` behave distinctly or fail consistently for documented reasons.",
            "Invocation canonicalization does not silently replace missing fields with `string.Empty` defaults.",
        ],
    },
    "numeric-normalization": {
        "key": "numeric-normalization",
        "title": "Numeric canonicalization diverges from the JCS reference",
        "summary": "The implementation produces different canonical output for numeric edge cases than the JCS reference behavior.",
        "labels": ["interop", "canonicalization", "numeric"],
        "acceptance_criteria": [
            "Numeric stress fixtures match the reference JCS manifest or fail for a documented unsupported-shape reason.",
            "Boundary values such as negative zero and exponent notation canonicalize consistently.",
        ],
    },
    "controller-array": {
        "key": "controller-array",
        "title": "Controller arrays do not round-trip through neutral fixtures",
        "summary": "The implementation does not correctly deserialize or canonicalize controller arrays from the neutral fixture format.",
        "labels": ["interop", "model-shape", "controller"],
        "acceptance_criteria": [
            "`capability-controller-array-unicode` deserializes successfully and matches the reference JCS manifest.",
            "Capability controller values preserve array semantics instead of collapsing to a single string path.",
        ],
    },
    "null-handling": {
        "key": "null-handling",
        "title": "Explicit `null` handling diverges from the reference behavior",
        "summary": "The implementation does not handle explicit `null` values the same way as the reference canonicalization flow.",
        "labels": ["interop", "null-handling", "canonicalization"],
        "acceptance_criteria": [
            "Explicit-null fixtures behave consistently with reference output or fail consistently for documented reasons.",
        ],
    },
    "capability-chain": {
        "key": "embedded-capability-chain",
        "title": "Embedded capability-chain objects diverge from the reference payload",
        "summary": "The implementation does not canonicalize embedded capability-chain objects the same way as the reference flow.",
        "labels": ["interop", "capability-chain", "nested-objects"],
        "acceptance_criteria": [
            "Embedded capability-chain fixtures match the reference JCS manifest.",
        ],
    },
    "capability-proof-object": {
        "key": "embedded-proof-capability",
        "title": "Embedded proof capability objects diverge from the reference payload",
        "summary": "The implementation does not canonicalize embedded capability objects inside invocation proofs the same way as the reference flow.",
        "labels": ["interop", "invocation", "nested-objects"],
        "acceptance_criteria": [
            "Embedded proof capability fixtures match the reference JCS manifest.",
        ],
    },
}

TAG_PRIORITY = [
    "type-preservation",
    "allowed-action",
    "caveat",
    "capability-action-empty-string",
    "numeric-normalization",
    "controller-array",
    "null-handling",
    "capability-proof-object",
    "capability-chain",
]


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _classify_finding(finding: dict[str, Any]) -> dict[str, Any]:
    tags = set(finding.get("tags", []))
    for tag in TAG_PRIORITY:
        if tag in tags:
            return TAG_RULES[tag]

    category = finding.get("category", "generic")
    kind = finding.get("kind", "unknown")
    return {
        "key": f"{kind}-{category}",
        "title": f"{kind.title()} finding: {category}",
        "summary": "The implementation differs from the reference manifest for this fixture cluster.",
        "labels": ["interop"],
        "acceptance_criteria": [
            "Affected fixtures match the reference JCS manifest or fail consistently for documented reasons.",
        ],
    }


def _derive_target_adapter(
    comparison: dict[str, Any],
    adapters: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any] | None, str | None]:
    left = adapters[comparison["left"]]
    right = adapters[comparison["right"]]

    left_is_reference = left.get("adapter") == "reference-jcs"
    right_is_reference = right.get("adapter") == "reference-jcs"

    if left_is_reference and right.get("issue_repo"):
        return right, None
    if right_is_reference and left.get("issue_repo"):
        return left, None
    if left_is_reference or right_is_reference:
        return None, "Reference comparison has findings, but the implementation adapter does not declare `issue_repo`."

    return None, "Comparison has findings, but there is no single reference side to assign direct blame."


def _render_issue_body(candidate: dict[str, Any], generated_at_utc: str) -> str:
    lines = [
        "## Summary",
        "",
        candidate["summary"],
        "",
        "## Evidence",
        "",
        f"- Adapter ID: `{candidate['adapter_id']}`",
        f"- Adapter: `{candidate['adapter']}`",
        f"- Generated: `{generated_at_utc}`",
        f"- Comparisons: {', '.join(f'`{label}`' for label in candidate['comparison_labels'])}",
        f"- Report artifacts: {', '.join(f'`{path}`' for path in candidate['report_paths'])}",
        "",
        "Affected fixtures:",
    ]

    for fixture in candidate["fixtures"]:
        lines.append(f"- `{fixture}`")

    lines.extend(["", "Observed categories:"])
    for category, count in candidate["categories"].items():
        lines.append(f"- `{category}`: {count}")

    lines.extend(["", "Example findings:"])
    for finding in candidate["sample_findings"]:
        lines.append(f"- `{finding['name']}`: {finding['message']}")

    lines.extend(["", "## Suggested Acceptance Criteria", ""])
    for criterion in candidate["acceptance_criteria"]:
        lines.append(f"- {criterion}")

    return "\n".join(lines)


def build_issue_report(summary: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    adapters = {adapter["id"]: adapter for adapter in summary["adapters"]}
    buckets: dict[tuple[str, str], dict[str, Any]] = {}
    triage: list[dict[str, Any]] = []

    for comparison in summary["comparisons"]:
        if comparison["status"] != "mismatch":
            continue

        target_adapter, triage_reason = _derive_target_adapter(comparison, adapters)
        if target_adapter is None:
            triage.append(
                {
                    "comparison_id": comparison["id"],
                    "comparison_label": comparison["label"],
                    "reason": triage_reason,
                }
            )
            continue

        comparison_path = output_dir / comparison["report_path"]
        comparison_result = _load_json(comparison_path)

        for finding in comparison_result["findings"]:
            rule = _classify_finding(finding)
            bucket_key = (target_adapter["issue_repo"], rule["key"])
            bucket = buckets.setdefault(
                bucket_key,
                {
                    "repo_full_name": target_adapter["issue_repo"],
                    "adapter_id": target_adapter["id"],
                    "adapter": target_adapter["adapter"],
                    "key": rule["key"],
                    "title": rule["title"],
                    "summary": rule["summary"],
                    "labels": list(rule["labels"]),
                    "acceptance_criteria": list(rule["acceptance_criteria"]),
                    "comparison_labels": set(),
                    "report_paths": set(),
                    "fixtures": set(),
                    "categories": Counter(),
                    "tags": set(),
                    "sample_findings": [],
                },
            )

            bucket["comparison_labels"].add(comparison["label"])
            bucket["report_paths"].add(comparison["report_path"])
            bucket["fixtures"].add(finding["name"])
            bucket["categories"][finding["category"]] += 1
            bucket["tags"].update(finding.get("tags", []))

            if len(bucket["sample_findings"]) < 5:
                bucket["sample_findings"].append(
                    {
                        "name": finding["name"],
                        "message": finding["message"],
                    }
                )

    candidates: list[dict[str, Any]] = []
    for bucket in sorted(buckets.values(), key=lambda item: (item["repo_full_name"], item["title"])):
        candidate = {
            "repo_full_name": bucket["repo_full_name"],
            "adapter_id": bucket["adapter_id"],
            "adapter": bucket["adapter"],
            "key": bucket["key"],
            "title": bucket["title"],
            "summary": bucket["summary"],
            "labels": bucket["labels"],
            "comparison_labels": sorted(bucket["comparison_labels"]),
            "report_paths": sorted(bucket["report_paths"]),
            "fixtures": sorted(bucket["fixtures"]),
            "categories": dict(sorted(bucket["categories"].items())),
            "tags": sorted(bucket["tags"]),
            "sample_findings": bucket["sample_findings"],
            "acceptance_criteria": bucket["acceptance_criteria"],
        }
        candidate["body_markdown"] = _render_issue_body(candidate, summary["generated_at_utc"])
        candidates.append(candidate)

    return {
        "issue_report_version": 1,
        "generated_at_utc": summary["generated_at_utc"],
        "candidate_count": len(candidates),
        "candidates": candidates,
        "triage": triage,
    }


def render_issue_report(issue_report: dict[str, Any]) -> str:
    lines = [
        "# Issue Candidates",
        "",
        f"- Generated: `{issue_report['generated_at_utc']}`",
        f"- Candidate count: `{issue_report['candidate_count']}`",
        "",
    ]

    if not issue_report["candidates"]:
        lines.append("No issue-ready candidates were generated for this run.")
    else:
        current_repo = None
        for candidate in issue_report["candidates"]:
            if candidate["repo_full_name"] != current_repo:
                current_repo = candidate["repo_full_name"]
                lines.extend([f"## {current_repo}", ""])

            lines.extend(
                [
                    f"### {candidate['title']}",
                    "",
                    f"- Suggested repo: `{candidate['repo_full_name']}`",
                    f"- Suggested labels: {', '.join(f'`{label}`' for label in candidate['labels'])}",
                    f"- Comparison scope: {', '.join(f'`{label}`' for label in candidate['comparison_labels'])}",
                    f"- Fixtures: {', '.join(f'`{fixture}`' for fixture in candidate['fixtures'])}",
                    "",
                    "Suggested issue body:",
                    "",
                    "```md",
                    candidate["body_markdown"],
                    "```",
                    "",
                ]
            )

    if issue_report["triage"]:
        lines.extend(["## Triage Needed", ""])
        for item in issue_report["triage"]:
            lines.append(f"- `{item['comparison_label']}`: {item['reason']}")

    return "\n".join(lines).rstrip() + "\n"
