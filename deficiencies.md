# Current Deficiencies To Track

These are not failures of this fixture repository. They are existing
interoperability risks or tooling gaps that the fixtures are intended to expose.

## Cross-Library JCS Payload Shape

- The dominant interop divergence in the current ecosystem is the JCS
  signing-payload shape: `zcap-dotnet` wraps the capability/invocation in a
  `{capability|invocation, proof}` envelope, while `zcap-py` (matching the W3C
  Verifiable Credentials Data Integrity convention) canonicalizes the flat
  document with a `proof` field at the top level. `moisesja/zcap-dotnet#34`
  tracks the upstream fix.
- This repo's `reference-jcs` adapter is now the W3C-flat shape — see issue
  #1. The `wrapper-vs-flat-isolation` fixture pair guards against future
  drift; until `zcap-dotnet#34` lands, the matrix will (correctly) report
  DIVERGENCE for the .NET adapter.
- Secondary divergence: `zcap-dotnet`'s `ProofSigningPayloadBuilder` uses a
  hand-picked proof-field whitelist that silently drops fields (e.g. `nonce`,
  `domain`) which `zcap-py` preserves verbatim under the `proof - proofValue`
  rule. The `proof-field-whitelist` fixture pair isolates this case.

## zcap-dotnet

- `ProofSigningPayloadBuilder` is internal, so an external neutral runner cannot
  call it through a stable public API. The current .NET runner therefore uses
  reflection.
- `JsonCanonicalizer` is described as simplified rather than a formal RFC 8785
  implementation, so strict JCS parity is not guaranteed for all JSON values.
- The current `Capability` model path drops the fixture `type` field from the
  canonical payload, which changes the bytes relative to Python/reference
  output.
- `Capability.controller` currently behaves as a single string in the model
  path; controller arrays do not deserialize from neutral fixture JSON.
- `Capability.AllowedAction` defaults to `Array.Empty<string>()`, which can
  erase the distinction between a missing field and an explicitly empty array.
- `Capability.Caveat` also defaults to `Array.Empty<Caveat>()`, with the same
  field-presence risk.
- Generic caveat fixture objects cannot currently be deserialized through the
  model path because `Caveat` is abstract.
- `Invocation.CapabilityAction` defaults to `string.Empty`, which can mask a
  missing field in edge fixtures.

## Python

- `zcap-py` does not currently expose a public capability/invocation payload
  canonicalization API analogous to the application payload builders.
- The current Python application adapter is therefore tied to
  `identity_authorization_service.crypto`, which is app-specific rather than a
  neutral library contract.

## Cross-Repo

- Shared fixtures only prove interoperability if both systems are run against
  the exact same fixture inputs and their manifest outputs are preserved in CI.
- Passing simple fixtures is not enough; numeric and field-presence stress cases
  are required to catch the risky differences.
