# ZCAP-LD Interop Fixtures

Neutral fixtures and runners for comparing Authorization Capabilities for Linked
Data implementations across languages.

The goal is simple: run the same fixture corpus through multiple
implementations, then see where they match, where they drift, and which gaps
still block interoperability.

This repository is licensed under [Apache-2.0](LICENSE).

## What This Repository Is For

Use this harness when you want to:

- measure parity between a Python implementation and a .NET implementation
- spot canonicalization drift before it becomes a production interop bug
- track compliance progress over time with repeatable reports
- add neutral fixtures for draft-spec edge cases without tying them to one codebase

This repository is currently focused on the payload-canonicalization boundary.
It is not yet a full end-to-end Authorization Capabilities for Linked Data
conformance suite.

## What Gets Tested

The current fixtures emphasize the places where interop usually breaks first:

- field presence and omission
- explicit `null` handling
- empty arrays vs absent fields
- numeric canonicalization risk
- unicode and escaping behavior
- embedded capabilities and proof chains

## Repository Layout

```text
zcap-interop-fixtures/
  README.md
  LICENSE
  CONTRIBUTING.md
  deficiencies.md
  config/
    self-check.matrix.json
    local.example.json
  docs/
    open-source-release-checklist.md
    periodic-runs.md
  schema/
    interop-fixture.schema.json
  fixtures/
    capability/
    invocation/
  python/
    interop_fixtures/
    emit_manifest.py
    compare_manifests.py
    run_matrix.py
    requirements.txt
  dotnet/
    InteropFixtures.Runner/
```

## Prerequisites

You need:

- Python 3.12+ recommended
- .NET SDK 10.0+ for the included .NET runner
- access to the Python implementation you want to measure
- a built `.NET` assembly for the .NET implementation you want to measure

Only the reference self-check works with this repository alone. A real
cross-implementation run requires paths to your external Python and .NET
projects.

## Quick Start

Create a virtual environment and install the Python dependency:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r python/requirements.txt
```

Run the built-in self-check:

```bash
python3 python/run_matrix.py --config config/self-check.matrix.json
```

That writes a timestamped report under `artifacts/runs/` and confirms the
reporting pipeline is working end to end.

## How To Run A Real Interop Comparison

### 1. Create a local config

Copy the sample matrix config:

```bash
cp config/local.example.json config/local.json
```

Then edit `config/local.json`.

### 2. Point the config at your implementations

The sample file defines three adapters:

- `python-reference`: strict reference JCS behavior inside this repo
- `python-app`: your Python implementation
- `dotnet-zcap`: your .NET implementation

Update these fields:

- `module_root`: path to the Python implementation root that exposes the payload builder module
- `assembly`: path to the built `.NET` assembly under test
- optionally `project`: keep or change the included runner project path if you move the runner
- optionally `issue_repo`: GitHub repository that should receive issue-ready findings for that adapter

The sample config assumes sibling checkouts. If your repos live elsewhere,
replace those relative paths with absolute paths.

### 3. Build the .NET implementation under test

The harness runner is included here, but the actual `.NET` implementation being
measured is external. Build that project first so the target assembly exists.

Then you can run the matrix:

```bash
python3 python/run_matrix.py --config config/local.json
```

### 4. Read the output

Each run creates a new directory like:

```text
artifacts/runs/20260327T150207Z/
```

Inside that directory you will find:

- `REPORT.md`: readable summary for humans
- `ISSUES.md`: issue-ready findings grouped by repository
- `summary.json`: machine-readable overall result
- `issue-candidates.json`: machine-readable issue candidates
- `manifests/*.json`: raw per-adapter outputs
- `comparisons/*.json`: structured pairwise findings

If `history_file` is configured, the runner also appends a compact summary line
to `artifacts/history.jsonl` so you can graph progress over time.

## Matrix Configuration

The matrix file is plain JSON. Each adapter entry has:

- `id`: stable name used in reports and comparisons
- `runner`: `python` or `dotnet`
- `adapter`: adapter name understood by that runner
- runner-specific fields such as `module_root`, `project`, or `assembly`
- optional `issue_repo`: GitHub repository name such as `moisesja/zcap-dotnet`
- optional `skip_if_missing`: skip that adapter instead of failing when a path is absent

Each comparison entry has:

- `id`: stable comparison identifier
- `left`: left adapter `id`
- `right`: right adapter `id`
- optional `label`: friendly report label

The sample config in [config/local.example.json](config/local.example.json) already encodes the most useful comparison set:

- reference JCS vs Python application adapter
- reference JCS vs .NET library adapter
- Python application adapter vs .NET library adapter

Issue-ready candidates are generated only when a comparison has a clear target
repository. In practice that means the most actionable path today is a
reference-vs-implementation comparison where the implementation adapter declares
`issue_repo`.

## Common Commands

Emit a manifest for the in-repo Python reference adapter:

```bash
python3 python/emit_manifest.py \
  --adapter reference-jcs \
  --fixtures-dir fixtures \
  --output /tmp/reference-python.json
```

Compare two manifests and also save structured comparison JSON:

```bash
python3 python/compare_manifests.py \
  /tmp/reference-python.json \
  /tmp/dotnet.json \
  --json-output /tmp/reference-vs-dotnet.json
```

Run the .NET reflection adapter directly:

```bash
dotnet run --project dotnet/InteropFixtures.Runner/InteropFixtures.Runner.csproj -- \
  --adapter zcap-dotnet-reflection \
  --assembly /path/to/ZcapLd.Core.dll \
  --fixtures-dir fixtures \
  --output /tmp/dotnet.json
```

Run the matrix in CI and fail if any findings appear:

```bash
python3 python/run_matrix.py --config config/local.json --fail-on-findings
```

## Issue-Ready Findings

If an adapter has `issue_repo` configured and a reference comparison finds
drift, the run emits:

- `ISSUES.md`: grouped draft issues with suggested titles, labels, and body text
- `issue-candidates.json`: the same information in structured form

The intended workflow is:

1. Run the matrix.
2. Review `REPORT.md` for the high-level picture.
3. Review `ISSUES.md` for issue-ready findings.
4. Tell me which candidates to publish, and I can open them in the configured repository.

## How To Interpret Results

Comparison results are categorized so you can tell what kind of failure you are
looking at:

- `match`: both adapters emitted the same canonical bytes or the same structured error
- `canonical-mismatch`: both adapters succeeded, but produced different bytes
- `status-mismatch`: one adapter succeeded and the other failed
- `error-mismatch`: both failed, but in different ways

As a rule of thumb:

- `reference JCS vs Python app` points to Python-side shape drift
- `reference JCS vs .NET library` points to .NET canonicalization or model drift
- `Python app vs .NET library` points to deployment-facing interoperability gaps

## Recommended Workflow

For day-to-day use:

1. Add or update fixtures under `fixtures/`.
2. Run the self-check if you changed harness code.
3. Run `config/local.json` against your real implementations.
4. Review `REPORT.md` first.
5. Open the per-comparison JSON if you need exact fixture-level findings.
6. Track persistent issues in [deficiencies.md](deficiencies.md).

For recurring measurement:

- run the matrix on a schedule
- keep `history.jsonl`
- alert on declining match rates or new status mismatches

More detail is in [docs/periodic-runs.md](docs/periodic-runs.md).

## Known Gaps

Current implementation-specific deficiencies are tracked in
[deficiencies.md](deficiencies.md).

## Contributing

Guidance for fixtures, adapters, and reporting changes is in
[CONTRIBUTING.md](CONTRIBUTING.md).
