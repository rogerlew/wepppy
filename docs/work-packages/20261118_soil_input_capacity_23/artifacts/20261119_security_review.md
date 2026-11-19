# Security review — soil input capacity 23

## Findings and verdict

No concrete security finding was identified in the reviewed change. Unresolved
security findings: high 0, medium 0, low 0. Security code-review gate: **pass**.
Release recommendation: **hold until independent correctness/QA and required
full validation gates pass**. This security verdict is not deployment approval,
production environment parity, or resolution of the original incident.

## Metadata

- Package: `docs/work-packages/20261118_soil_input_capacity_23/`.
- Reviewer: independent `/root/security_review` agent, 2026-11-19 UTC.
- Python base: `d228fe0a5`; reviewed committed contracts plus working candidate.
  Exact reviewed production-file hashes: `independent-security-scope.json` in
  `/workdir/soil-input-capacity-23-evidence/`.
- Native revision: `464a5e5e15e1fbcdd4e8232260ecf79ad2645200`, compared with
  `7d4cf4b5ab24bbc825515d54f25a035062b826bb`.
- Related review: independent correctness artifact remains the separate
  valid-state/user-outcome authority. Full Python validation remains pending at
  this review checkpoint; the implementer must record its final receipt.
- Contracts: `docs/schemas/wepp-executable-selection-contract.md`, section
  “Soil input capacity”; `docs/schemas/soil-horizon-boundary-contract.md`;
  unchanged `docs/schemas/single-user-defined-inputs-contract.md` admission policy.

## Security triage and trust assumptions

Security impact is high and dedicated review is warranted: newly accepted input
counts cross Python-to-native process boundaries and release metadata controls
those bounds. The native reader is memory-unsafe Fortran, so explicit count
rejection and separate input/calculation arrays are material controls.

The installed binary directory and sidecars are operator-controlled deployment
assets. Project users cannot mint release declarations, replace executables, or
supply arbitrary executable paths through this feature. Run decks are generated
by existing trusted writers; this change does not admit user-supplied decks.
Soil uploads remain governed by existing bounded parsing and native-format
admission. Relative deck references to Omni parent/sibling resources are existing
supported behavior; this guard is not a new path-authorization interface.

## Surface checks

| Surface | Assessment and evidence |
| --- | --- |
| Valid-state non-interference | Missing capacity declarations retain ten; matching declarations permit 1–23, with booleans rejected as integers. Supported legacy defaults and uploaded admission limits are unchanged. Direct valid/invalid probes and retained native legacy parity support the reviewed dimensions; this is not exhaustive valid-state coverage. |
| Auth, session, JWT, CSRF | N/A: no entry point, authorization rule, role, token or session code changed. |
| Secrets | No new secret dependency or repository secret introduced. Reviewed disposable launchers copy existing mounted secret files to a private temporary directory inside the one-shot container, mode 0600, then drop to UID 1002/GID 130. No secret values were inspected or included in this artifact. |
| Input validation | Capacity is strict integer 1–23; malformed types, conflicting roles/capacities/source identity and stale executable hashes fail. Actual soil files are parsed before subprocess creation. Python rejects excess counts, inconsistent records and nonfinite/decreasing depths. |
| Native bounds | `src/input.for` validates `nslfile` within 1–23 before reading source horizons; input arrays use `mxhzin`, calculation arrays retain `mxnsl`. Reviewed all source-indexed arrays and conversion sites; no remaining source-count indexing of calculation arrays was identified. Retained bounds-checked reader matrix and independently executed count24 probe pass. |
| Upload preservation | Guard performs reads only. `preserve_input_format` remains a separate serializer path; no new admission expansion or automatic 200 mm insertion into accepted upload bytes. Independent CRLF validation probe preserved bytes. |
| Files and paths | No new upload name/path acceptance or production write location. Guard reads the same generated `.sol` references the existing native deck consumes; missing references fail explicitly. Publication validation remains before destination opening on generated paths. |
| Queue/worker/subprocess | Existing five launch paths call the guard before `Popen`; no new shell interpolation or subprocess mode. Queue wiring/auth boundaries unchanged, so an RQ graph regeneration is not applicable. |
| Agent/tooling | Independent review was explicitly authorized. Review made no candidate edits; all probe files were external and task-owned. No agent-facing production tool surface changed. |
| Network and dependencies | No new outbound integration, service, dependency or production network behavior. |
| Supply chain | Matched role sidecars bind installed role/name, SHA-256 and source/release identity. Both final hashes were independently recomputed and match. Native source lineage is locally integrated on the resolved default branch; remote integration/deployment is explicitly unclaimed. |
| Data integrity and concurrency | No NoDb locking, persistence, Redis scope or identity policy changed. Capacity travels through existing worker arguments. Rollback explicitly prevents silently running oversized artifacts with a historical binary; no truncation/merge repair is added. |
| Logging and recovery | New failures are explicit and contextual, with no new broad catch. Existing historical artifacts/default selections remain. Rollout docs require coherent prior project artifacts and matched role binaries for rollback. |

## Direct validation evidence

Reviewer independently executed read-only application functions and temporary
external fixtures, with bytecode writing disabled. Results are retained in
`/workdir/soil-input-capacity-23-evidence/independent-security-probes.json`:

- Actual vendored matched pair resolves to capacity 23. Recomputed SHA-256:
  watershed `bd421e39dfe742ed500c69596ef91a6232254587001ec49b09b2ec0ca5ec9f32`;
  hillslope `9843f250b25f2f2dab342d2418cd9d5b5b43d9e685b6db1216031c1a0958fa81`.
- Actual metadata reader accepts a consistent temporary capacity23 pair and
  rejects `null`, booleans, 0, -1, 24, float, string, list and object declarations.
- Modified executable bytes reject a stale sidecar hash. Removing both optional
  sidecars retains historical capacity ten.
- Existing bounds-checked native reader independently invoked against a copied
  count24 fixture exits 1 with the explicit horizon-count error.
- Capacity23 soil text passes validation without changing its CRLF bytes;
  the same actual text rejects capacity ten.

Retained implementation evidence inspected: native full suite 1824 passed;
reader matrix 72 passed; tests cover source counts 9/10/11/21/22/23 across eight
formats, mixed OFE counts, the 23rd material, and 0/24/100 rejection. Legacy
state/output parity and the real 21-horizon Puaulu tests exercise valid states.
The disposable project readback records 355 hillslopes, 144 channels, 100 years,
and 5,259,456 finite channel records with complete climate-matching calendars.
The actual report consumers loaded expected rows. This evidence was inspected,
not independently rerun in full by this reviewer.

## Artifact observability and remaining gates

Production soil files, prepared inputs, errors, native outputs, interchange,
exports and reports remain in their established run locations and authorization
model. No newly hidden production record or archive exclusion is introduced.
The hidden raw-output hardlinks in the disposable validation copy are retained
study evidence after existing interchange cleanup, not a production policy change.

The replay demonstrates report-consumer readback in a development worker under
the production UID/GID and run mount conventions. It does not demonstrate a
production browser session or exact production image/configuration. Browser,
archive and production deployment gates are not certified by this review; any
activation must satisfy the canonical deployment preflight. The package scope
prepares the release, and production activation/original-project recovery remain
separate actions. These limits are not waived by the security pass.

## Residual risk and sign-off

The existing installed-assets trust boundary permits operator modification of
binaries/sidecars between validation and execution; no atomic deployment snapshot
is introduced here. No user-reachable ability to perform such replacement was
identified. This review does not certify arbitrary malformed scientific inputs,
future SSURGO maxima beyond 23, or native Windows builds.

No security risk-acceptance exception is requested. Independent security reviewer:
`/root/security_review`, 2026-11-19 UTC. Package-owner release sign-off and
independent correctness/QA closure remain separate required records.

## Follow-up review — derivative consumers

Reviewed the subsequent correctness fix in Treatments (both soil utility
initializers), LocationMixin (disturbed-soil initializer), and AgFields
Concept 1/hybrid synthesis. The five added production files are now included in
`independent-security-scope.json`. All previously reviewed production files
retain their recorded hashes, so the direct metadata/native/guard probes remain
applicable to their reviewed implementations.

Treatments and LocationMixin take capacity from the existing Soils controller's
validated executable property. AgFields retains a standalone ten-horizon default
and both production integrators resolve capacity from the same selected binary
used for their native runs. No untrusted request field becomes capacity authority;
source paths, write destinations, upload policy, locks and queue topology are
unchanged. The existing canonical serializer enforces the supplied limit before
opening the soil destination. No additional security finding was identified.

Security code-review verdict remains pass. New derivative-consumer regressions,
independent correctness closure and the final full-suite receipt remain separate
validation gates; this addendum does not claim those tests have passed.
