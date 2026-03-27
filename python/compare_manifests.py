#!/usr/bin/env python3
"""Compare two interop manifests and report canonicalization mismatches."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from interop_fixtures.comparison import compare_manifests, load_manifest, render_comparison_console


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left")
    parser.add_argument("right")
    parser.add_argument("--json-output", help="Optional path for structured comparison output.")
    args = parser.parse_args()

    result = compare_manifests(
        load_manifest(Path(args.left)),
        load_manifest(Path(args.right)),
    )

    if args.json_output:
        output_path = Path(args.json_output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write("\n")

    print(render_comparison_console(result))
    return 0 if result["status"] == "match" else 1


if __name__ == "__main__":
    raise SystemExit(main())
