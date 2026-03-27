# Periodic Runs

The matrix runner is designed so you can measure interoperability repeatedly and
keep a historical record of progress.

## Local Recurring Run

After creating a real local config, schedule:

```bash
python3 python/run_matrix.py --config config/local.json
```

Each run creates:

- `artifacts/runs/<timestamp>/REPORT.md`
- `artifacts/runs/<timestamp>/summary.json`
- `artifacts/runs/<timestamp>/manifests/*.json`
- `artifacts/runs/<timestamp>/comparisons/*.json`

If `history_file` is configured, the runner also appends one JSON line per run
to that file. This is useful for trend tracking in a spreadsheet, notebook, or
dashboard.

## Suggested Cron Entry

```cron
0 6 * * 1 cd /path/to/zcap-interop-fixtures && python3 python/run_matrix.py --config config/local.json
```

## CI Gating

Use:

```bash
python3 python/run_matrix.py --config config/local.json --fail-on-findings
```

That mode exits non-zero if:

- an adapter fails to emit a manifest
- a configured comparison contains interoperability findings

## Recommended Interpretation

- `Reference JCS vs Python app`: application payload-shape drift
- `Reference JCS vs .NET library`: .NET library or model-default drift
- `Python app vs .NET library`: deployment-facing interoperability gap

