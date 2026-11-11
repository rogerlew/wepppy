# Pickle artifact restriction

**Status**: Open (2026-11-11 UTC); M0-M3 complete; implemented and locally validated; rollout pending

**Timezone**: UTC

## Overview

Remediate security audit finding F2 by removing request-time deserialization of
project-controlled Python pickle artifacts and rejecting new `.pkl` and `.pickle`
files at the Bootstrap Git boundary. A Bootstrap user can currently push a
NUL-free pickle that passes the binary check, after which browse preview or
D-Tale calls `pandas.read_pickle`. Python pickle is executable serialization, so
loading a project-controlled file crosses from project write authority to server
process execution.

The operator selected a narrow restriction instead of a migration or replacement
format: existing pickle files remain visible and downloadable as raw bytes, but
WEPPcloud will not preview, forward, or deserialize them. Validation is limited
to the changed Bootstrap, browse, D-Tale, documentation, and stub surfaces. The
full repository suite is explicitly not required for this package.

## Objectives

- Reject `.pkl` and `.pickle` paths case-insensitively in every introduced
  Bootstrap commit before blob parsing or push-log publication.
- Remove pickle from browse preview availability and directory D-Tale actions.
- Return an explicit unsupported-media response for pickle preview and D-Tale
  requests without calling a pickle reader or D-Tale loader.
- Remove pickle readers from the D-Tale service, including its dispatch table and
  public type surface.
- Preserve listing and byte-for-byte download of existing legacy pickle files.
- Prove ordinary allowed Bootstrap text inputs and supported tabular previews
  continue to work using focused tests only.

## Scope

### Included

- `wepppy/weppcloud/bootstrap/pre_receive.py` and its focused Git-hook tests.
- Browse preview dispatch, preview metadata, directory action links, D-Tale
  bridge suffix admission, and their focused microservice tests.
- D-Tale eager-reader dispatch and its focused loader/freshness tests and stubs.
- Canonical Bootstrap and browse filesystem contracts plus service documentation.
- A scoped deployment/rollback check for the wepp1 application services when
  separately authorized.

### Explicitly Out of Scope

- Converting, deleting, quarantining, or opening historical pickle artifacts.
- Blocking raw authorized downloads of existing pickle files.
- Magic-byte inspection or content classification of non-pickle extensions.
- Internal trusted pickle uses for Redis session compatibility, RQ/process
  transport, tests, or application-owned temporary files.
- Audit findings F1 and F3-F8, dependency upgrades, a new file format, or a new
  scanning dependency.
- The full Python or frontend test suites.

## Complexity Budget

- **Existing mechanisms reused**: Bootstrap path validation, browse suffix
  dispatch, HTTP 415 responses, D-Tale reader registry, and current tests.
- **New mechanisms permitted**: one shared constant per process boundary for
  denied pickle suffixes, where that avoids drift without cross-service coupling.
- **Simplest plausible change tested first**: suffix denial before any reader or
  loader dispatch; remove pickle from advertised capability lists.
- **Real acceptance condition**: no project-controlled `.pkl`/`.pickle` request
  reaches `pandas.read_pickle`, while allowed formats and raw downloads work.
- **Evidence required before escalation**: a focused failing test showing suffix
  restriction cannot close a confirmed request-time pickle reader.
- **Explicitly prohibited expansion**: new services, queues, datastores,
  dependencies, content scanners, migration jobs, or deployment topology.

## Generated Artifact Validation Gate

- **Applicable**: yes, narrowly, because Bootstrap writes Git artifacts and
  browse/download consumes project artifacts.
- **User-visible outcome**: pickle pushes and interactive parsing fail clearly;
  authorized raw legacy downloads remain byte-identical.
- **Intent evidence**: exact pushed Git path or requested browse/D-Tale path.
- **Persisted-state evidence**: rejected commit is not accepted/logged; allowed
  control commit remains valid.
- **Generated-intermediate evidence**: N/A; the change creates no conversion.
- **Prepared/consumed-input evidence**: loader spies prove pickle readers and the
  D-Tale internal loader are not called.
- **Execution/output evidence**: focused response status/body and Git-hook error.
- **User-facing result evidence**: listing lacks preview/D-Tale actions, direct
  parse requests return 415, and download bytes match the source.
- **Direct unmocked boundary**: temporary real Git repository and real file bytes.
- **Actual-project/environment gate**: scoped Compose/wepp1 route smoke only when
  deployment is authorized; no live malicious payload execution.
- **Highest completion claim currently supported**: diagnosed.

## Stakeholders

- **Primary**: WEPPcloud maintainers and wepp1 operator.
- **Reviewers**: Bootstrap, browse, D-Tale, correctness/UX, QA, and security.
- **Security Reviewer**: required and independent of the implementation author.
- **Informed**: users with legacy pickle artifacts, who retain raw download.

## Success Criteria

- [ ] `.pkl`, `.pickle`, and mixed-case variants are rejected by Bootstrap for
      every introduced commit and allowed directory.
- [ ] A NUL-free pickle-shaped test fixture is rejected by suffix without being
      deserialized or written to the push log.
- [ ] Browse never calls `pd.read_pickle`; pickle preview returns HTTP 415.
- [ ] Directory and files API metadata do not advertise pickle preview or D-Tale.
- [ ] Browse D-Tale routes reject pickle before materialization or HTTP forwarding.
- [ ] D-Tale internal load rejects pickle and has no pickle reader/dispatch entry.
- [ ] Existing pickle files remain listable and downloadable byte-for-byte.
- [ ] CSV/TSV/Feather/Arrow/Parquet controls and allowed Bootstrap inputs pass.
- [ ] Focused tests, stub checks, scoped docs lint, and independent reviews pass.
- [ ] No full-suite result is required or presented as package evidence.

## Parameterization ADR Gate

- **Parameterization change present**: no.
- **ADR required**: no.
- **ADR links**: N/A.
- **Decision provenance captured**: yes, in the contract decision.

## Dependencies

### Prerequisites

- Contract-first checkpoint covering Bootstrap admission and browse/download
  representation behavior before implementation.
- Independent review of the exact list/download-only compatibility rule.

### Blocks

- Closure of security audit finding F2/SEC-02.

## Related Packages

- **Related**:
  [Bootstrap Git maintenance](../20260821_bootstrap_git_maintenance/package.md)
  is historical operational precedent, not current authorization.
- **Related**:
  [Browse filesystem transparency](../20261026_browse_worker_timeout/package.md)
  establishes raw artifact availability expectations.
- **Canonical browse contract**:
  [Browse filesystem contract](../../schemas/browse-filesystem-contract.md).

## Timeline Estimate

- **Expected duration**: 2-4 focused implementation/review days.
- **Complexity**: low implementation complexity across three service boundaries.
- **Risk level**: high security impact, low compatibility risk under the explicit
  list/download-only rule.

## Security Impact and Review Gate

- **Security impact triage**: high.
- **Dedicated security review required**: yes.
- **Triage rationale**: untrusted Git/file input and unsafe deserialization are
  public application security boundaries.
- **Security review artifact**:
  [artifacts/20261110_security_review.md](artifacts/20261110_security_review.md).

## Hardening and Callus Softening

- **Failure signature**: project-controlled `.pkl` reaches
  `pandas.read_pickle` through browse preview or D-Tale.
- **Scope boundary**: remove these exact artifact parsing paths without redesigning
  generic file access or internal serialization.
- **Health signals**: zero pickle reader call sites in request paths; consistent
  415s; Bootstrap rejections; unchanged raw-download hashes.
- **Danger signals**: legacy file disappearance, allowed-format regression,
  inconsistent case handling, loader call before rejection, or hidden fallback.
- **Observation model**: stateless recurrence trigger. Any future request-time
  pickle reader or pickle capability advertisement opens a new incident package.
- **Temporary calluses introduced**: none.

## Validation Scope Decision

The operator explicitly requested focused tests and no full-suite run. Required
validation is therefore limited to:

- `tests/weppcloud/bootstrap/test_pre_receive.py`
- `tests/microservices/test_browse_routes.py`
- `tests/microservices/test_files_routes.py`
- `tests/microservices/test_browse_dtale.py`
- `tests/microservices/test_dtale_freshness.py`
- applicable D-Tale stub/API checks, scoped documentation lint, and direct source
  search for remaining request-time pickle readers.

Frontend-wide npm gates are not required unless implementation unexpectedly
touches frontend source. Such expansion requires a recorded scope decision.

## References

- `wepppy/weppcloud/bootstrap/pre_receive.py`
- `wepppy/microservices/browse/flow.py`
- `wepppy/microservices/browse/browse.py`
- `wepppy/microservices/browse/listing.py`
- `wepppy/microservices/browse/dtale.py`
- `wepppy/webservices/dtale/dtale.py` and `.pyi`
- [Active ExecPlan](prompts/active/implementation_execplan.md)
- [Contract decision](artifacts/20261110_contract_decision.md)
- [Failure-class matrix](artifacts/20261110_failure_class_matrix.md)
- [Correctness review](artifacts/20261110_correctness_review.md)

## Deliverables

- Canonical pickle artifact restriction in Bootstrap and browse contracts.
- Minimal code change with focused regression coverage.
- Updated service/operator documentation and D-Tale type surface.
- Correctness, QA/code, and security review artifacts with findings closed.
- Scoped deployment and rollback evidence when rollout is authorized.

## Follow-up Work

Historical pickle migration or deletion is not required. If users later need an
interactive representation, propose an offline trusted conversion to Parquet in
a separate package; do not restore request-time pickle loading.
