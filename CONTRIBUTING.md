# Contributing

This repository is meant to be a neutral interoperability harness for draft
Authorization Capabilities for Linked Data implementations. Contributions should
improve fixture quality, adapter clarity, and the repeatability of comparison
results.

## What Belongs Here

- Neutral fixtures that expose interoperability or canonicalization edge cases
- Harness code that emits portable manifests and reports
- Adapter plumbing that lets outside implementations be measured consistently
- Documentation that makes results easier to interpret or reproduce

## What Does Not Belong Here

- Product-specific business logic
- Fixture assertions that assume one implementation is normative without stating why
- Environment-specific absolute paths in committed manifests or docs

## Adding Fixtures

1. Add a JSON fixture under `fixtures/capability/` or `fixtures/invocation/`.
2. Follow `schema/interop-fixture.schema.json`.
3. Keep `notes` concrete about the behavior under test.
4. Add meaningful `tags` such as `interop-core`, `nulls`, `unicode`, or `field-presence`.
5. Prefer small fixtures that isolate one risk over large fixtures that mix many concerns.

## Adapter Expectations

Adapters are expected to consume the neutral fixture shape and emit manifests
with:

- `status`
- canonical bytes when successful
- structured error information when unsuccessful
- relative `fixture_path` values so reports are portable

If an implementation requires reflection or app-specific glue, document that in
the adapter description and in `deficiencies.md`.

## Running The Matrix

Use the self-check first:

```bash
python3 python/run_matrix.py --config config/self-check.matrix.json
```

Then create a real local config from `config/local.example.json` and point it at
your Python and .NET implementation checkouts.

## Reporting Changes

When a change affects interoperability behavior, include:

- which fixtures changed behavior
- whether the change closes a known gap or introduces one
- the relevant `artifacts/runs/<timestamp>/REPORT.md` path if you generated one

