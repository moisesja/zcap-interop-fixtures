# Current Deficiencies To Track

These are not failures of this fixture repository. They are existing
interoperability risks or tooling gaps that the fixtures are intended to expose.

## Cross-Library JCS Payload Shape

- The dominant interop divergence in the current ecosystem is the JCS
  signing-payload shape: pre-2.1.0 `zcap-dotnet` wrapped the
  capability/invocation in a `{capability|invocation, proof}` envelope, while
  `zcap-py` (matching the W3C Verifiable Credentials Data Integrity
  convention) canonicalizes the flat document with a `proof` field at the top
  level. **Resolved upstream** in `zcap-dotnet 2.1.0` (PRs #34, #36/#38, #37).
- This repo's `reference-jcs` adapter is the W3C-flat shape — see issue #1.
  The `wrapper-vs-flat-isolation` and `proof-field-whitelist` fixture pairs
  remain as regression guards; both report PARITY against `zcap-dotnet ≥ 2.1.0`.
- Secondary divergence: pre-2.1.0 `ProofSigningPayloadBuilder` used a
  hand-picked proof-field whitelist that silently dropped fields (e.g.
  `nonce`, `domain`) which `zcap-py` preserves verbatim under the
  `proof - proofValue` rule. **Resolved upstream** in `zcap-dotnet 2.1.0` —
  `Proof` now carries `[JsonExtensionData] AdditionalProperties` so unmodeled
  wire fields round-trip through canonicalization.

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
- Polymorphic `Caveat` deserialization is registry-based
  (`CaveatTypeRegistry.Default`, seeded with `Expiration`, `UsageCount`,
  `ValidWhileTrue`) rather than attribute-driven. Fixtures using a caveat
  `type` outside that registry cause the .NET adapter to throw
  `JsonException("No Caveat type registered for discriminator '<type>'")`.
  Resolved by zcap-dotnet#39 in 2.1.0; the prior abstract-type
  `NotSupportedException` is gone, but interop fixtures must either use a
  registered discriminator or accept the explicit error. See issue #1's
  release-blocker fixtures, which use `UsageCount` for that reason.
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
