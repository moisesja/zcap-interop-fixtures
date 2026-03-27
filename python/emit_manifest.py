#!/usr/bin/env python3
"""Emit canonicalization manifests for interop fixtures."""

from __future__ import annotations

import argparse
from pathlib import Path

from interop_fixtures.adapters import PYTHON_ADAPTER_CHOICES, load_python_adapter
from interop_fixtures.manifest import build_manifest, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", required=True, choices=PYTHON_ADAPTER_CHOICES)
    parser.add_argument("--module-root")
    parser.add_argument("--fixtures-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    adapter = load_python_adapter(args.adapter, module_root=args.module_root)
    fixtures_dir = Path(args.fixtures_dir).resolve()
    output_path = Path(args.output).resolve()

    manifest = build_manifest(adapter, fixtures_dir)
    write_json(output_path, manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
