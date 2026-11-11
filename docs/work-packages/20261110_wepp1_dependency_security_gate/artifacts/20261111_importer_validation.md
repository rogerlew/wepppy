# Local manual-import validation

**Status**: Focused tests and independent correctness/security review pass.
Full pytest passes. This is an M3 component, not M3 acceptance.

The operator-selected manual handoff now has a local import utility,
`tools/security/import_dependency_evidence.py`. Its durable interface and limits
are documented in `docs/infrastructure/dependency-security-evidence.md`.
It does not approve findings or change the Compose deployment path.

## Observable evidence

`wctl run-pytest tests/tools/test_import_dependency_evidence.py --maxfail=1`
passes all 31 tests in 8.97 seconds. Cases cover private byte readback, schema and
identity mismatches, duplicate keys, unexpected members, traversal, symlinks,
directories/FIFOs, source mutation, alias replacement, exclusive retention,
copy failures and both post-rename directory-sync failures.

A real local trial collects the classified SBOM, no-symbol Grype report, Python
and Debian inventories, and v2 disposition packet from the protected baseline.
The importer retains all five files (72,245,902 bytes), and independent readback
verifies each hash/size, the manifest, image ID, and 0700/0600 permissions.

Private root: `.local/dependency-security/evidence/import-trial-20261111/`.

- Manifest: `3ec51e1b5f3153e669c6babcf35c89075d3d8b211ccd6a0e5314e62e614a6b73`.
- Final trial receipt `receipt-v2.json`:
  `8705c565a4a077b03e2db99e556ec3140a3c583b933e1e05ee73eb773e72a7e1`.
- Importer code:
  `c5bcbb8d6fdefeae138f2af1b4ccf8cac8c98e9912f67e6cecd45ae009bb6ebe`.

The independent security probes are retained in private
`evidence/m3-import-review-20261111/`; their original ignored `out/` location is
now a symlink. Review receipt hash:
`acc24020ac371ba595491f8d9b5e7b65e16f61e96eafa1a48d22e52e8d4963f0`.
The dedicated correctness and security artifacts record the closed alias-path
and durability/completion findings and the scoped passing verdicts.

## Other checks and limits

Scoped documentation lint and `wctl check-test-stubs` pass. Code-quality
observability runs successfully; its generated reports are retained privately.
The required broad-exception check against `origin/master` fails on an existing
catch in `wepppy/weppcloud/bootstrap/pre_receive.py:263`, outside this package's
changes. The reported merge base is `b3786ae7e`; this package introduces no broad
exception handler. Do not repair unrelated application code to obscure that
baseline result.

The exact full command `wctl run-pytest tests --maxfail=1` passes at
2026-11-11 08:52:38 UTC: 13,533 passed, 435 skipped, 6,029 warnings; exit zero,
4,228.12 seconds including the wrapper (4,216.26 seconds pytest time).
Importer, test, requirements and lock hashes match the starting receipt.
The complete log SHA-256 is
`2f3527c99490c68a9188968c02c5633711a70de5fc6f2b2058f6b96e6af63f6e`;
raw log and `pytest-full.json` are retained under the private trial root.
Fresh importer-stage
npm lint and full npm test runs both pass (124 suites, 1,069 tests), with the
frontend lock unchanged; receipts are `npm-lint.json` and `npm-test.json`.
This run uses the development runtime and does not prove final candidate parity.

No established authenticated runner-to-store collection route has been found.
Operator clarification is pending for that external prerequisite. A successful
local import does not prove remote collection before cleanup or 90-day/365-day
retention operations. Scanner producer, policy evaluator, CI wiring and the
pre-activation Compose hook remain unimplemented. M1 native coverage, advisory
dispositions, compatible repairs and final candidate gates remain open.
