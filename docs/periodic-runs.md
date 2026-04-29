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
- `artifacts/runs/<timestamp>/ISSUES.md`
- `artifacts/runs/<timestamp>/summary.json`
- `artifacts/runs/<timestamp>/issue-candidates.json`
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

If `issue_repo` is configured for an implementation adapter, the run also
prepares repository-targeted issue drafts in `ISSUES.md` so the next step can be
opening GitHub issues instead of rewriting the evidence by hand.

## Release-Blocking Fixtures

The following fixtures must report PARITY across all configured adapters in
the matrix run before either `zcap-dotnet` or `zcap-py` is cut to release:

- `capability-wrapper-vs-flat-isolation` /
  `invocation-wrapper-vs-flat-isolation` — exercise the JCS payload-shape
  divergence (wrapped `{capability|invocation, proof}` envelope vs W3C flat
  document with `proof`). See issue #1.
- `capability-proof-field-whitelist` /
  `invocation-proof-field-whitelist` — exercise the proof-field-whitelist
  divergence (hand-picked proof fields vs `proof` minus `proofValue`).

If any of these fixtures shows DIVERGENCE in the matrix, the implementing
library is not safe to release until the underlying canonicalization
disagreement is resolved. The harness's `reference-jcs` adapter is the
W3C-flat shape, so `dotnet-zcap` is expected to report DIVERGENCE on these
fixtures until `moisesja/zcap-dotnet#34` lands.
