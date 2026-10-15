# M7 validation remediation correctness review

## Metadata and outcome

- Reviewer: independent `validation_correctness` agent, 2026-10-15 UTC.
- Candidate: working changes above `88cc1fafa`, re-reviewed after direct
  runner-02 acceptance; hosted workflow and broad-suite acceptance pending.
- Scope: optional dev PostgreSQL data source, Forest storage migration evidence,
  WEPP stub annotations, generated Stubtest workflow, standalone CI Compose,
  and isolated cross-service authentication test accounts.
- Authority: `docs/schemas/run-catalog-projection-contract.md`, promotion targets
  and matched performance baselines; `docker/AGENTS.md`; workflow generation and
  builder separation in `.github/workflows/AGENTS.md`.
- Related evidence: [validation follow-up](20261015_validation_followup.md).

The requested outcome is unchanged interactive notification latency below the
50 ms added-p95 limit, with durable PostgreSQL commits, plus an executable
stubtest gate on an available runner. Changing thresholds, bypassing isolation,
or making a job merely start does not satisfy that outcome.

## Findings

| ID | Severity | Finding and evidence | Required action | Status |
| --- | --- | --- | --- | --- |
| COR-01 | Medium | Initial workflow checked out LFS pointers while the source bind hid materialized image assets. Real station SQLite and test TIFF readers require those assets. | Both jobs now set `lfs: true`, explicitly run `git lfs checkout`, then fsck and verify tracked inputs. Direct runner qualification passed with 648 materialized assets, eight stubtest modules and 77 focused tests. Corrected hosted stubtest job passed in run `38763492543`. | Resolved |
| COR-02 | Low | Initial follow-up retained pending approval and the wrong proposed volume name. | Follow-up now records explicit approval, actual `docker_forest-postgres-ssd` volume, stopped-copy verification, retained original data, exact table-count readback, preserved durability, latency results, and current-data rollback rules. | Resolved |

No implementation defect found in the optional dev mount expression or the two
stub annotation changes. Production Compose files are unchanged. An absent or
empty `POSTGRES_DATA_SOURCE` retains the existing bind mount. No latency test,
durability setting, catalog algorithm, or WMesque default changed.

## Valid states and errors

| State | Required behavior | Evidence or remaining gap |
| --- | --- | --- |
| Storage override absent or empty | Retain `../.docker-data/postgres`. | Compose `${POSTGRES_DATA_SOURCE:-../.docker-data/postgres}` inspected. |
| Existing populated Forest database | Quiesce, stop, copy bytes and metadata, then reopen the same database. | Execution receipt retains stopped-copy byte/owner/mode verification; independent review of `/tmp/m7-db-before.txt` and `/tmp/m7-db-after.txt` confirms matching database names and all 15 public-table counts. |
| Fresh, empty database deployment | PostgreSQL may initialize according to its existing entrypoint. | Existing behavior; not a supported migration method for populated Forest. |
| Supported legacy dev deployment | Continue using the original bind source. | Default expression preserved; production volumes unaffected. |
| Invalid or missing selected source | Surface Compose/PostgreSQL startup errors; do not claim a migration. | No fallback wrapper added. Arbitrary new named volumes require Compose declarations. |
| Clean CI checkout | Runtime and fixture assets must be materialized and readable. | `/tmp/m7-runner-lfs.log`: fsck clean, 648 tracked assets materialized. `/tmp/m7-runner-stubtest.log`: eight modules pass; focused runtime tests pass. |
| Empty CI account database | Transport tests supply their declared account independently of deployment state. | Function-scoped SQLite schema seeds active user 42 and its User role; real shared account resolution reads it. Ten cross-service integration tests pass on runner-02. |
| Unwritable production lock directory in CI | Use existing lock-directory configuration without bypassing locks. | CI-only `/tmp/rq-lifecycle-locks` override; existing directory creation, file mode and flock path remain active. Transport test rerun passes. |
| Partial CI failure | Preserve diagnostics and remove this job's containers/volumes. | Unique project names and cleanup guarded by `always() && steps.wctl.outcome == 'success'` inspected. Failures before installer success cannot start this runtime; partial runtime startup still reaches cleanup. Live runtime-failure cleanup evidence pending. |

Database writes resume against the migrated current volume. The original bind
directory becomes stale after that point; rollback must copy the current stopped
database back. Application/API error contracts are unchanged. CI setup failures
remain explicit failed checks rather than being suppressed.

## Artifact and boundary evidence

| Stage | Direct evidence | Result |
| --- | --- | --- |
| Approved intent | Operator approved the prepared Forest mount migration; runner-02 is on the tailnet. | Confirmed |
| Database prepared input | Stopped-copy verification retained in execution receipt; public-table readback inspected before/after. | Pass |
| Database consumer | Real PostgreSQL latency tests, `/tmp/m7-ssd-latency.log`: all four passed in 18.11 s. No timing assertions edited. | Focused environment validation |
| Workflow generation | `python scripts/build_forest_workflows.py --check` and `git diff --check` passed independently. Two generator regressions pass in `/tmp/m7-generator-tests.log`; source fixture isolates the generator's PyYAML resolver mutation. | Source generation validated |
| CI consumer inputs | Direct runner Git fetch and LFS verification passed. Explicit materialization corrected hosted preflight; hosted stubtest job in run `38763492543` passed. | Pass |
| CI execution | Direct eight-module stubtest/completeness, 77 PostgreSQL/catalog/NoDb tests, and hosted stubtest pass. `/tmp/m7-runner-auth-tests.log`: 10 cross-service tests pass in 1.13 s after isolated account/lock configuration. | Focused runner environment validated |
| User-facing result | Full Forest suite and hosted baseline/full-isolation results remain pending; hosted stubtest passes. | Partial acceptance |

No project output, report, archive membership, or project authorization changes
are introduced here. The artifact-observability gate applies to operational
evidence and generated CI inputs; no new project browser surface is required.

### Hosted preflight correction

Reviewed `/tmp/m7-hosted-failure.log`: run `38762839809` failed with 648
unmaterialized working-tree files even though LFS object fsck passed. This
demonstrates that the direct runner qualification did not validate the Actions
checkout boundary. The verifier prevented incorrect inputs from reaching the
runtime. The correction explicitly materializes the already fetched objects
before fsck and pointer verification in both jobs; neither check is removed.

The same failed run attempted cleanup before `wctl` was installed, adding a
misleading command-not-found error. Giving the installer `id: wctl` and checking
its success in the always-run cleanup condition is appropriate: no runtime
creation step can run before that installation succeeds, and cleanup still runs
if subsequent startup is partial or tests fail. No correctness finding in these
two bounded corrections. Hosted run `38763492543` subsequently passed stubtest;
its baseline exposed the separate environment dependencies described next.

### CI account and lifecycle-lock correction

The hosted baseline could not create the production lock path under `/wc1`.
The CI Compose environment now selects the existing
`WEPPCLOUD_RQ_LIFECYCLE_LOCK_DIR` option with a writable per-container `/tmp`
location. This preserves the actual file-lock behavior and changes no deployed
production path or permissions.

The empty CI PostgreSQL instance also exposed undeclared deployment-account
dependencies in `tests/integration`. The new function-scoped fixture creates
the canonical lightweight account schema in a temporary SQLite database and
seeds the existing test identity, active user 42 with User role. Only the engine
provider is replaced for shared account resolution; principal construction,
active-account checks, role reads, transport JWT checks, and assertions remain
real. The legacy Flask `fs_uniquifier` lookup is an explicitly stubbed boundary:
fixture subject `42` maps to account 42 and unknown subjects return no mapping.
These tests establish transport behavior, not the legacy lookup's SQL dialect
or account-schema migration compatibility.

The first fixture draft left that legacy lookup connected to PostgreSQL;
`test_portability__mx_a5_wepp_signed_mcp_class_token_conditionally_allows_rq_engine`
returned 503 with a missing user table. After the explicit lookup fixture,
`/tmp/m7-runner-auth-tests.log` records all 10 integration tests passing in
1.13 seconds. Fixtures are restored by monkeypatch teardown and the temporary
engine is disposed. No correctness finding in the reviewed final changes;
full baseline and isolation must still exercise the complete CI environment.

## Coverage limitations

- The storage fix trades RAID6 device-failure resilience for SSD RAID0 latency
  under explicit operator approval. Keeping `fsync`/`synchronous_commit` on and
  RAID6 backups does not remove that hardware risk.
- The existing isolation checker can run without a randomization plugin and
  compares failures rather than requiring every iteration to pass. Identically
  failing runs can produce a clean isolation result. Do not equate its exit code
  with a passing broad suite or claim random-order coverage without a plugin.
- Preserve the full isolation command and its outcome; record any runtime or
  plugin limitation explicitly. Retain detailed logs for failures.
- The broad Forest suite is still running. Focused timing success alone does not
  close M7 or establish long-term latency under every workload.
- Security containment is reviewed separately and does not substitute for clean
  checkout/runtime parity or real runner execution.

## Verdict

Correctness review: **pass with validation conditions**. Unresolved findings:
zero high, zero medium, zero low. No new correctness finding in the updated
source. Forest storage remediation and runner-02 stubtest have focused live
evidence. Keep M7 closeout pending the broad Forest suite, full isolation and
hosted workflow outcomes; this sign-off does not claim those gates have passed.
