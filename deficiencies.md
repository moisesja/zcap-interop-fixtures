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
- `JsonCanonicalizer` is described in source as a simplified implementation
  rather than a formally audited RFC 8785 one. In practice it produces correct
  bytes for every fixture currently in the matched set on
  `zcap-dotnet ≥ 2.1.0` (the encoder fix in `zcap-dotnet#36/#38` closed the
  last known divergence), but no formal RFC 8785 conformance audit exists, so
  novel value shapes outside the current fixture corpus may still drift.
- `Capability.controller` currently behaves as a single string in the model
  path; controller arrays do not deserialize from neutral fixture JSON.
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

- `zcap-py` exposes the JCS canonicalization primitive publicly
  (`zcap_py.jcs.canonicalize.canonicalize(obj) -> bytes`), but does not expose
  a public *payload builder* analogous to .NET's `ProofSigningPayloadBuilder`.
  The W3C-flat assembly (proof minus `proofValue`, merged into the document)
  is inlined inside `verify_document_proof` in
  `src/zcap_py/proof/ed25519_2020.py`. Third parties wanting to canonicalize
  the same bytes have to copy that assembly logic by hand.
- The current Python application adapter is therefore tied to
  `identity_authorization_service.crypto`, which is app-specific rather than a
  neutral library contract.

## Cross-Repo

- Shared fixtures only prove interoperability if both systems are run against
  the exact same fixture inputs and their manifest outputs are preserved in CI.
- Passing simple fixtures is not enough; numeric and field-presence stress cases
  are required to catch the risky differences.
