# Changelog

## Unreleased

### Foundation PR - repo hygiene and architecture scaffolding

- Removed generated artifacts from version control (`output/`, `tmp/`, test reports, generated evidence).
- Removed root-level demo scripts; demos will live in `examples/` or move to separate packages.
- Added module skeleton for new architecture (`protocols`, `profile`, `verifier`, `providers`). No runtime change yet.
- Added CI workflows for tests, type-check, lint, AERF conformance, security audit, example execution.
- Added pre-commit configuration.
- Added AERF v0.1 conformance test, currently `xfail`, to pass in PR 2 after the Notary refactor.
- Pre-1.0 versioning commitment: receipt format may change in 0.x; once 1.0 ships, receipt format is stable forever and library API follows semver.
- `mcp_server/` remains in this repository for now and will move to a separate `agentmint-mcp` package in a future release.
- Bundled `schemas/aerf-v0.1.json` from the upstream AERF specification with SHA-256 `3225416abf05cf3721f7a298900aafca18b779e6961cbd75955d4e110cb035b1`.
