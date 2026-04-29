# Changelog

## Unreleased

- Initialized changelog for tracked harness changes.
- Added new isolation fixtures for capability `type`, missing-vs-empty `allowedAction`, missing-vs-empty `caveat`, explicit empty invocation `capabilityAction`, and numeric JCS boundary cases.
- Added issue-ready reporting artifacts so matrix runs now emit `ISSUES.md` and `issue-candidates.json` when findings can be assigned to a configured repository.
- Updated the sample config and README to document `issue_repo` and the issue-drafting workflow.
- Flipped the `reference-jcs` adapter from the wrapped `{capability|invocation, proof}` envelope to the W3C Verifiable Credentials Data Integrity flat shape (document fields at top level, `proof` minus `proofValue`). Aligns the harness reference with `zcap-py`'s `verify_document_proof` so the matrix can detect the dominant cross-library divergence (issue #1). Every existing fixture's canonical bytes are intentionally regenerated under the new reference; the wrapped `dotnet-zcap` adapter is now expected to report DIVERGENCE until `moisesja/zcap-dotnet#34` lands.
- Added `capability-wrapper-vs-flat-isolation` and `invocation-wrapper-vs-flat-isolation` fixtures that isolate the JCS payload-shape divergence with a one-line failure when an adapter uses the wrong envelope.
- Added `capability-proof-field-whitelist` and `invocation-proof-field-whitelist` fixtures that isolate the secondary divergence from `zcap-dotnet`'s hand-picked proof-field whitelist (drops `nonce`/`domain` that the W3C `proof - proofValue` rule preserves).
- Added a `Cross-Library JCS Payload Shape` section to `deficiencies.md` and a `Release-Blocking Fixtures` section to `docs/periodic-runs.md` documenting the four new fixtures as a precondition for cutting either `zcap-dotnet` or `zcap-py` releases.
