# M7 validation remediation correctness review

## Metadata and outcome

- Reviewer: independent `validation_correctness` agent, 2026-10-15 UTC.
- Candidate: working changes above `88cc1fafa`, re-reviewed after direct
  runner-02 acceptance; hosted workflow and broad-suite acceptance pending.
- Scope: optional dev PostgreSQL data source, Forest storage migration evidence,
  WEPP stub annotations, generated Stubtest workflow, standalone CI Compose.
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
| COR-01 | Medium | Initial workflow checked out LFS pointers while the source bind hid materialized image assets. Real station SQLite and test TIFF readers require those assets. | Both jobs now set `lfs: true`, run `git lfs fsck`, and verify tracked inputs. Runner-02 fetched `88cc1fafa`; all 648 tracked LFS files verified, all eight stubtest modules passed, and 77 focused runtime tests passed. | Resolved |
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
| Partial CI failure | Preserve diagnostics and remove this job's containers/volumes. | Unique project names and `if: always()` cleanup inspected; live failure/cleanup evidence pending. |

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
| CI consumer inputs | Clean runner Git fetch and LFS verification; corrected stub mounted over pinned image. | Pass |
| CI execution | `/tmp/m7-runner-stubtest.log`: all eight modules pass. `/tmp/m7-runner-stubs.log`: completeness passes. `/tmp/m7-runner-runtime-tests.log`: 77 PostgreSQL/catalog/NoDb tests pass in 25.74 s. | Focused runner environment validated |
| User-facing result | Full suite on Forest, full isolation and hosted workflow job results not yet available at this checkpoint. | Pending |

No project output, report, archive membership, or project authorization changes
are introduced here. The artifact-observability gate applies to operational
evidence and generated CI inputs; no new project browser surface is required.

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
