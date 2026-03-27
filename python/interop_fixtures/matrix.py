from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

from .adapters import load_python_adapter_from_config
from .comparison import compare_manifests, load_manifest
from .fixtures import iter_fixture_paths
from .manifest import build_manifest, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an interop matrix and emit a scorecard.")
    parser.add_argument("--config", required=True, help="Path to a JSON matrix configuration file.")
    parser.add_argument("--output-root", help="Override the output root from the config file.")
    parser.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="Exit non-zero if any adapter fails or any comparison contains findings.",
    )
    return parser.parse_args()


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)

    if not isinstance(config.get("adapters"), list) or not config["adapters"]:
        raise ValueError(f"{path}: adapters must be a non-empty array")
    adapter_ids = []
    for index, adapter in enumerate(config["adapters"]):
        if not isinstance(adapter, dict):
            raise ValueError(f"{path}: adapters[{index}] must be an object")
        for key in ("id", "runner", "adapter"):
            if key not in adapter:
                raise ValueError(f"{path}: adapters[{index}] is missing required key: {key}")
        adapter_ids.append(str(adapter["id"]))

    duplicates = sorted({adapter_id for adapter_id in adapter_ids if adapter_ids.count(adapter_id) > 1})
    if duplicates:
        raise ValueError(f"{path}: duplicate adapter ids are not allowed: {duplicates}")

    return config


def resolve_path(base_dir: Path, raw_path: str | None) -> Path | None:
    if raw_path is None:
        return None
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


def slugify(value: str) -> str:
    allowed = []
    for char in value:
        if char.isalnum():
            allowed.append(char.lower())
        elif char in {"-", "_"}:
            allowed.append(char)
        else:
            allowed.append("-")
    return "".join(allowed).strip("-") or "comparison"


def build_output_dir(output_root: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return output_root / "runs" / timestamp


def resolve_comparisons(config: dict[str, Any], adapter_ids: list[str]) -> list[dict[str, str]]:
    adapter_id_set = set(adapter_ids)
    if "comparisons" not in config:
        return [
            {
                "id": f"{left}-vs-{right}",
                "left": left,
                "right": right,
                "label": f"{left} vs {right}",
            }
            for left, right in combinations(adapter_ids, 2)
        ]

    comparisons = []
    for index, item in enumerate(config["comparisons"], start=1):
        if not isinstance(item, dict):
            raise ValueError(f"comparisons[{index - 1}] must be an object")
        left = item["left"]
        right = item["right"]
        if left not in adapter_id_set or right not in adapter_id_set:
            raise ValueError(f"comparisons[{index - 1}] references an unknown adapter id")
        comparisons.append(
            {
                "id": item.get("id", f"{left}-vs-{right}"),
                "left": left,
                "right": right,
                "label": item.get("label", f"{left} vs {right}"),
            }
        )
    return comparisons


def missing_input_reason(base_dir: Path, adapter_config: dict[str, Any]) -> str | None:
    runner = adapter_config["runner"]
    if runner == "python" and adapter_config["adapter"] == "identity-authorization-service":
        module_root = resolve_path(base_dir, adapter_config.get("module_root"))
        if module_root is None or not module_root.exists():
            return f"module_root not found: {adapter_config.get('module_root')}"
        return None
    if runner == "dotnet":
        project = resolve_path(base_dir, adapter_config.get("project"))
        assembly = resolve_path(base_dir, adapter_config.get("assembly"))
        if project is None or not project.exists():
            return f"project not found: {adapter_config.get('project')}"
        if assembly is None or not assembly.exists():
            return f"assembly not found: {adapter_config.get('assembly')}"
        return None
    return None


def run_python_adapter(
    base_dir: Path,
    adapter_config: dict[str, Any],
    fixtures_dir: Path,
    output_path: Path,
) -> dict[str, Any]:
    resolved_config = dict(adapter_config)
    module_root = resolve_path(base_dir, adapter_config.get("module_root"))
    if module_root is not None:
        resolved_config["module_root"] = str(module_root)

    adapter = load_python_adapter_from_config(resolved_config)
    manifest = build_manifest(adapter, fixtures_dir)
    write_json(output_path, manifest)
    return manifest


def run_dotnet_adapter(
    base_dir: Path,
    adapter_config: dict[str, Any],
    fixtures_dir: Path,
    output_path: Path,
) -> dict[str, Any]:
    project = resolve_path(base_dir, adapter_config["project"])
    assembly = resolve_path(base_dir, adapter_config["assembly"])
    assert project is not None
    assert assembly is not None

    command = [
        "dotnet",
        "run",
        "--project",
        str(project),
        "--",
        "--adapter",
        str(adapter_config["adapter"]),
        "--assembly",
        str(assembly),
        "--fixtures-dir",
        str(fixtures_dir),
        "--output",
        str(output_path),
    ]
    subprocess.run(command, check=True, cwd=base_dir)
    return load_manifest(output_path)


def run_adapter(
    base_dir: Path,
    adapter_config: dict[str, Any],
    fixtures_dir: Path,
    output_dir: Path,
) -> dict[str, Any]:
    adapter_id = adapter_config["id"]
    manifest_path = output_dir / "manifests" / f"{slugify(adapter_id)}.json"

    reason = missing_input_reason(base_dir, adapter_config)
    if reason is not None and adapter_config.get("skip_if_missing", False):
        return {
            "id": adapter_id,
            "runner": adapter_config["runner"],
            "adapter": adapter_config["adapter"],
            "status": "skipped",
            "reason": reason,
        }
    if reason is not None:
        return {
            "id": adapter_id,
            "runner": adapter_config["runner"],
            "adapter": adapter_config["adapter"],
            "status": "error",
            "reason": reason,
        }

    try:
        runner = adapter_config["runner"]
        if runner == "python":
            manifest = run_python_adapter(base_dir, adapter_config, fixtures_dir, manifest_path)
        elif runner == "dotnet":
            manifest = run_dotnet_adapter(base_dir, adapter_config, fixtures_dir, manifest_path)
        else:
            raise ValueError(f"Unsupported runner: {runner}")

        return {
            "id": adapter_id,
            "runner": manifest["runner"],
            "adapter": manifest["adapter"],
            "status": "ok",
            "manifest_path": manifest_path.relative_to(output_dir).as_posix(),
            "fixture_count": manifest["fixture_count"],
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "id": adapter_id,
            "runner": adapter_config["runner"],
            "adapter": adapter_config["adapter"],
            "status": "error",
            "reason": str(exc),
        }


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Interop Run Report",
        "",
        f"- Generated: `{summary['generated_at_utc']}`",
        f"- Fixtures: `{summary['fixture_count']}`",
        f"- Adapters available: `{summary['scorecard']['available_adapters']}`",
        f"- Successful adapters: `{summary['scorecard']['successful_adapters']}`",
        f"- Comparisons with findings: `{summary['scorecard']['comparisons_with_findings']}`",
        "",
        "## Adapter Status",
        "",
        "| Adapter ID | Runner | Adapter | Status | Notes |",
        "| --- | --- | --- | --- | --- |",
    ]

    for adapter in summary["adapters"]:
        lines.append(
            "| "
            f"{adapter['id']} | {adapter['runner']} | {adapter['adapter']} | {adapter['status']} | "
            f"{adapter.get('reason', adapter.get('manifest_path', ''))} |"
        )

    lines.extend(
        [
            "",
            "## Comparison Scorecard",
            "",
            "| Comparison | Status | Match Rate | Matched | Findings | Notes |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )

    for comparison in summary["comparisons"]:
        if comparison["status"] == "skipped":
            lines.append(
                f"| {comparison['label']} | skipped | n/a | n/a | n/a | {comparison['reason']} |"
            )
            continue
        lines.append(
            "| "
            f"{comparison['label']} | {comparison['status']} | {comparison['match_rate']:.1%} | "
            f"{comparison['matched_fixture_count']}/{comparison['compared_fixture_count']} | "
            f"{comparison['finding_count']} | {comparison.get('report_path', '')} |"
        )

    findings = [
        comparison
        for comparison in summary["comparisons"]
        if comparison["status"] == "mismatch" and comparison["top_findings"]
    ]
    if findings:
        lines.extend(["", "## Gap Highlights", ""])
        for comparison in findings:
            lines.append(f"### {comparison['label']}")
            for finding in comparison["top_findings"]:
                lines.append(f"- `{finding['name']}`: {finding['message']}")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def append_history(history_path: Path, summary: dict[str, Any]) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot = {
        "generated_at_utc": summary["generated_at_utc"],
        "fixture_count": summary["fixture_count"],
        "scorecard": summary["scorecard"],
        "comparisons": [
            {
                "id": comparison["id"],
                "label": comparison["label"],
                "status": comparison["status"],
                "match_rate": comparison.get("match_rate"),
                "finding_count": comparison.get("finding_count"),
            }
            for comparison in summary["comparisons"]
        ],
    }
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(snapshot, sort_keys=True))
        handle.write("\n")


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve()
    base_dir = config_path.parent
    config = load_config(config_path)

    fixtures_dir = resolve_path(base_dir, config.get("fixtures_dir", "../fixtures"))
    if fixtures_dir is None or not fixtures_dir.exists():
        raise SystemExit(f"Fixtures directory not found: {config.get('fixtures_dir')}")

    output_root = Path(args.output_root).resolve() if args.output_root else resolve_path(base_dir, config.get("output_root", "../artifacts"))
    assert output_root is not None
    output_dir = build_output_dir(output_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    adapters = []
    adapter_ids = []
    adapter_results: dict[str, dict[str, Any]] = {}
    for adapter_config in config["adapters"]:
        adapter_id = adapter_config["id"]
        adapter_ids.append(adapter_id)
        result = run_adapter(base_dir, adapter_config, fixtures_dir, output_dir)
        adapters.append(result)
        adapter_results[adapter_id] = result

    comparisons = []
    comparison_specs = resolve_comparisons(config, adapter_ids)
    for comparison_spec in comparison_specs:
        left = adapter_results[comparison_spec["left"]]
        right = adapter_results[comparison_spec["right"]]

        if left["status"] != "ok" or right["status"] != "ok":
            comparisons.append(
                {
                    "id": comparison_spec["id"],
                    "label": comparison_spec["label"],
                    "left": comparison_spec["left"],
                    "right": comparison_spec["right"],
                    "status": "skipped",
                    "reason": "One or both adapters did not produce a manifest.",
                    "top_findings": [],
                }
            )
            continue

        left_manifest_path = output_dir / left["manifest_path"]
        right_manifest_path = output_dir / right["manifest_path"]
        result = compare_manifests(load_manifest(left_manifest_path), load_manifest(right_manifest_path))

        comparison_path = output_dir / "comparisons" / f"{slugify(comparison_spec['id'])}.json"
        write_json(comparison_path, result)

        comparisons.append(
            {
                "id": comparison_spec["id"],
                "label": comparison_spec["label"],
                "left": comparison_spec["left"],
                "right": comparison_spec["right"],
                "status": result["status"],
                "match_rate": result["match_rate"],
                "matched_fixture_count": result["matched_fixture_count"],
                "compared_fixture_count": result["compared_fixture_count"],
                "finding_count": result["finding_count"],
                "report_path": comparison_path.relative_to(output_dir).as_posix(),
                "top_findings": result["findings"][:5],
            }
        )

    summary = {
        "run_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "fixture_count": len(iter_fixture_paths(fixtures_dir)),
        "fixtures_dir": config.get("fixtures_dir", "../fixtures"),
        "adapters": adapters,
        "comparisons": comparisons,
        "scorecard": {
            "available_adapters": len(adapters),
            "successful_adapters": sum(1 for adapter in adapters if adapter["status"] == "ok"),
            "comparisons_run": sum(1 for comparison in comparisons if comparison["status"] != "skipped"),
            "comparisons_with_findings": sum(1 for comparison in comparisons if comparison["status"] == "mismatch"),
            "fully_matching_comparisons": sum(1 for comparison in comparisons if comparison["status"] == "match"),
        },
    }

    summary_path = output_dir / "summary.json"
    write_json(summary_path, summary)

    report_path = output_dir / "REPORT.md"
    report_path.write_text(render_report(summary), encoding="utf-8")

    history_file = config.get("history_file")
    if history_file:
        history_path = resolve_path(base_dir, history_file)
        assert history_path is not None
        append_history(history_path, summary)

    print(f"Interop report written to {report_path}")

    if args.fail_on_findings:
        if any(adapter["status"] == "error" for adapter in adapters):
            return 1
        if any(comparison["status"] == "mismatch" for comparison in comparisons):
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
