# Open Source Release Checklist

This repository now has the core harness structure, but a few release choices
should still be made intentionally before publishing broadly.

## Before Publishing

- `Apache-2.0` has been selected for this repository
- Add issue and pull request templates if you want structured gap reports
- Decide whether generated reports belong in version control or only in build artifacts
- Decide whether external implementation repos will be checked out as siblings,
  git submodules, or CI-installed dependencies

## Recommended Nice-To-Haves

- `CODE_OF_CONDUCT.md`
- a small GitHub Actions workflow that builds the harness and runs the self-check
- a published sample report in `docs/` once real adapters are wired in
