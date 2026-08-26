# Security Review - Direct OpenFileGDB cutover

## Metadata

- **Package**: `docs/work-packages/20260821_openfilegdb_cutover/`
- **Reviewer**: Codex preliminary self-review; independent review pending
- **Date**: 2026-08-21
- **Scope reviewed**: worker subprocess, artifact filesystem writes, archive
  creation, Compose/build/deployment subtraction
- **Commit/branch context**: uncommitted local `master` based on `ed2b222fe`
- **Related artifact**: `2026-08-21_correctness_review.md`

## Security Triage Decision

- **Security impact level**: high
- **Dedicated security review required**: yes
- **Triage rationale**: worker subprocess and run-tree artifact creation change,
  and deployment/build wiring is removed.
- **Threat model assumptions**:
  - Source and target paths are generated inside an authorized run's artifact
    directory, not accepted as direct HTTP parameters.
  - The common worker image supplies the trusted `ogr2ogr` executable.
  - The worker identity already has required access to the selected run tree.
- **Valid states controls must preserve**: populated, geometryless/nullable,
  legacy alias, and existing cached artifact states in the correctness review.

## Findings

| ID | Severity | Surface | Description | Evidence | Required action | Status |
| --- | --- | --- | --- | --- | --- | --- |
| SEC-01 | Low | Deployment residue | Deployed `wepppy-f-esri` containers will remain until stack reconciliation removes orphans. | Current host inventory | Include exact orphan check/removal in rollout. | Open |

## Verdict

- **Gate status**: fail pending independent review and rollout disposition
- **Unresolved findings**: High 0; Medium 0; Low 1
- **Release recommendation**: implementation may proceed to forest; hold
  production rollout

## Surface Checks

### Valid-State Non-Interference and User Experience

- [x] Correctness review enumerates relevant states and open evidence gaps.
- [x] Capability and cleanup controls preserve populated valid output.
- [x] Direct unmocked valid-state conversion runs.
- [ ] Independent correctness approval remains pending.

### Auth, Session, Secrets, and Network

- [x] Routes, authorization, sessions, CSRF, tokens, secrets, and proxy/network
  exposure are unchanged.
- [x] No new secret, mount, external call, or dependency is introduced.

### Input, Filesystem, and Output Safety

- [x] Subprocess arguments are a fixed array with no shell interpolation.
- [x] Source and target paths are resolved; callers generate them under the
  existing artifact directory contract.
- [x] Cleanup targets only the exact `.gdb` and `.gdb.zip` paths.
- [x] Symlinks are not traversed by permission repair.
- [x] Generated content remains group-readable/writable as before.
- [x] ZIP contains only the generated `.gdb` tree.

### Queue, Worker, and Subprocess Surfaces

- [x] Enqueue sites and RQ dependency edges are unchanged; RQ graph regeneration
  is not required.
- [x] Conversion has a 1,800-second default timeout and contextual diagnostics.
- [x] No silent fallback to an absent SDK driver exists.
- [x] Timeout/nonzero/packaging failures remove partial publishable state.
- [x] Docker-socket mounts remain because `weppcloudr` still uses Docker exec;
  removing them is outside this migration.

### CI/CD and Supply Chain

- [x] The external f-esri repository and Esri SDK download are removed.
- [x] Workflow permissions and runner scope are unchanged.
- [x] No new dependency is introduced; GDAL is already pinned in the image.
- [ ] Forest and production/Kubernetes promotion remain operator-controlled.

### Data Integrity and Incident Readiness

- [x] Cache keys, validators, publication registry, and NoDb/RQ mutations are
  unchanged.
- [x] Errors are not swallowed and contain no credential material.
- [x] Rollback is the prior common image/Compose revision until orphan sidecar
  retirement completes.

## Validation Evidence

- Focused exporter/service/backend tests: 98 passed before subtraction; final
  backend selection: 6 passed.
- Broad suite: 4,528 passed before unrelated missing Topanga manifest; remaining
  WEPP/WEPPcloud selection 1,630 passed with that exact case deselected.
- Host canary contract: 2 passed; seven supported Compose renders passed.
- Stub completeness, vulture, shell syntax, broad-exception enforcement, and
  code-quality observation passed.

## Residual Risk

- Orphan sidecar removal and external-client compatibility require forest
  rollout evidence.
- Independent correctness/security reviewers must disposition the preliminary
  findings before production rollout.

## Sign-off

- **Security reviewer**: Codex preliminary self-review, 2026-08-21
- **Package owner**: pending independent/operator disposition
