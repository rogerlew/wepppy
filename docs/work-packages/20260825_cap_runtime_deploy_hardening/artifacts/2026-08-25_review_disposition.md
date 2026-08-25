# Review Disposition - CAP Runtime and Deployment Hardening

## Metadata

- **Package**: `docs/work-packages/20260825_cap_runtime_deploy_hardening/`
- **Date**: 2026-08-25
- **Disposition owner**: Codex
- **Review inputs**:
  - `2026-08-25_correctness_review.md`
  - `2026-08-25_operations_review.md`
  - `2026-08-25_qa_review.md`
  - `2026-08-25_security_review.md`

## Summary

The independent reviews found no Critical findings. They found nineteen High
findings, with substantial overlap around five root gaps: false-positive
readiness, secret-rotation durability, privileged migration containment,
failure-atomic CAP-only deployment/rollback, and executable production-boundary
tests. Every High finding is accepted into the package as a blocking
requirement and is mapped below to a concrete ExecPlan change and acceptance
gate. None is accepted as residual risk or deferred outside the package.

"Dispositioned" here means the design and required evidence are ratified. It
does not mean the finding is resolved. Review gates remain `fail/hold` until
implementation evidence exists and the independent reviewers re-review it.

## Ratified Repair Design

CAP keeps its non-root UID/GID `10001:10001`. Before CAP construction or
listening, its wrapper validates that `/var/lib/cap` is the expected directory,
that an existing ledger is a non-symlink regular file containing the supported
object-shaped JSON, and that UID `10001` can open an existing ledger for update
without changing it. It also performs a create, fsync, and remove probe in the
data directory without modifying the ledger. Readiness becomes distinct from
liveness and cannot succeed until both file and directory validation complete.
A complete challenge/redeem/siteverify canary validates the functional
persistence path.

The production secret remains a non-symlink regular file owned by the
deployment account under the exact, non-symlink, deployment-account-owned
`docker/secrets` directory, which has no group/other write access. The owner
has read/write and the owning group, other users, and unlisted identities have
no effective access. A POSIX named-user ACL uses the group-class mode bits as
its mask, so numeric mode `0600` is the pre-ACL base state, not a valid sole
post-ACL assertion. The canonical post-install invariant is owner `rw-`, named
`r--` entries only for allowlisted consumer UIDs distinct from the owner,
owning group `---`, mask `r--`, and other `---`, verified with `getfacl`.

The canonical secret install/rotation helper stages a new inode in the same
directory, sets its owner and base permissions, applies named-user read ACLs
only for the effective allowlisted consumers, and validates effective access
before atomically replacing the live inode. The allowlist covers the verified
WEPPcloud/rq-engine image UID and CAP UID `10001`; initial implementation must
ratify the current production values before mutation and reject UID `10001` if
it resolves to an unexpected host account. An absent mapping or an explicitly
ratified locked `cap` account is permitted, and no free-form UID is accepted.
It revalidates the installed inode after rename. There is no interval in which
a newly installed live secret lacks the CAP ACL. Simultaneous inline
`CAP_SECRET` and `CAP_SECRET_FILE` is rejected.

Legacy volume migration uses a one-shot root helper with networking disabled
and only the exact `cap-data` named volume mounted at a fixed container path.
It accepts no host path or UID argument, does not recursively traverse, and
permits only the volume root plus the expected `tokensList.json` regular file.
Unexpected entries, symlinks, directories in place of the ledger, special
files, invalid JSON, and wrong JSON shape fail without mutation. It records
pre/post non-secret integrity and metadata receipts.

Production repair uses a new guarded `--targeted-cap` mode. It never stops or
recreates WEPPcloud, rq-engine, Caddy, Redis, or workers. Before touching live
CAP, it builds and validates the candidate against disposable production-style
file-secret and named-volume fixtures, records the running image ID, creates a
host-local rescue tag, and disables pruning of that image through the
observation window. It then stops CAP, performs the fixed-scope live migration,
recreates only CAP, and requires internal readiness, a functional canary, and
external health. Any failure automatically restores canonical forward-safe
permissions and the known-good image/config; it never restores the known-bad
permission state. Recovery is not successful until the restored CAP passes the
same internal readiness, functional canary, and external health checks. The
deployment still returns nonzero after verified recovery. A failed recovery
uses a distinct rescue-failure reason, never prints the success footer, never
prunes, and retains the rescue image, recorded image/config identity, and
non-secret receipts needed for manual recovery.

`docker/validate-cap-runtime-contract.sh` is the single mandatory host-Docker
production-mount harness. Local validation, the CAP branch of
`docker/validate-aux-image-contract.sh`, and every deploy mode that recreates
CAP invoke that same harness rather than copy its permission logic. It
exercises a real bind secret staged with base mode `0600`, applies and verifies
the effective named-user ACL without granting unlisted group/other access, and
uses real named volumes. Missing Docker, named-volume, or ACL capability is an
actionable hard failure at these gates, not a skip.

Every deploy mode that intentionally recreates CAP, including full wepp1 mode,
must use the same pre-stop CAP resource/secret preflight, rescue-image retention,
post-start readiness/canary/health gate, and verified CAP-only recovery. Full
mode is not required to roll back unrelated services, but it may not exit while
leaving CAP broken. The secret ACL helper is enforced and verified before CAP
candidate validation and before any running CAP is stopped, even when the
secret inode was replaced outside the canonical rotation helper.

Full-stack Compose activation also gives CAP an internal readiness health check
and changes Caddy's CAP dependency from `service_started` to
`service_healthy`. A full start therefore cannot expose the candidate through
its new Caddy instance before readiness succeeds. Targeted CAP intentionally
leaves the existing Caddy running and uses the bounded login-only gap plus
automatic known-good restoration; it does not claim zero exposure.

Docker Compose does not provide redundant CAP instances, so the package does
not promise zero interruption. It promises no logout, cookie clearing, site
data clearing, session rotation, or worker interruption. The forest1 rehearsal
must measure and bound the login-only gap; adding CAP high availability is out
of scope. A candidate that fails after recreation may be briefly unreachable,
but automatic known-good restoration is mandatory and the deploy cannot report
success during that state.

## High Finding Dispositions

| Finding(s) | Disposition and required proof | Status |
| --- | --- | --- |
| COR-01, SEC-01, QA-02 | Add pre-listen filesystem/schema validation, nondestructive update-open proof for an existing ledger, directory create/fsync/remove proof, distinct readiness, and functional challenge/redeem/siteverify. Prove static liveness cannot pass broken persistence states. | Plan amended; implementation blocking |
| COR-02, OPS-H3, OPS-H4, QA-04 | Preserve an exact host-local known-good image/config before mutation; define and executable-test preflight, CAP-only stop, closed-ledger receipt, fixed migration, runtime-identity mount probe, start, validate, automatic restore, restored-service readiness/canary/external-health verification, nonzero return after recovery, retry, and restore-failure states. Recovery always establishes canonical forward-safe permissions and never restores incident/hostile metadata. Apply this CAP recovery contract to targeted CAP and every full wepp1 deploy that recreates CAP. Failed recovery never prunes or claims success and retains manual-recovery evidence; successful rollout prunes only after observation close. | Plan amended; implementation blocking |
| COR-03, OPS-H2 | Make atomic secret replacement a first-class state. Stage owner/base permissions and UID-specific ACLs for every effective allowlisted consumer before atomic rename; verify effective ACL access before and after replacement without reading the value. Do not require numeric mode `0600` after a named-user ACL changes the POSIX ACL mask. Enforce this helper before candidate validation and before CAP stop on every deploy that recreates CAP, including replacement outside the canonical rotation helper. | Plan amended; implementation blocking |
| COR-04, OPS-H5, QA-03 | Maintain separate build targets, intentionally recreated services, and expected-running services. Add an executable command-fake topology harness for full wepp1, targeted web, targeted CAP, wepp2, and wepp3. Full wepp1 must exercise the same CAP preflight, rescue, readiness, and verified-recovery branches as targeted CAP. | Plan amended; implementation blocking |
| SEC-02, OPS-H8 | Gate full-stack Caddy activation on internal CAP readiness, then require external health. For targeted CAP, replace the impossible zero-exposure claim with a measured bounded login-only maintenance gap, prevalidate the candidate while old CAP serves, and automatically restore known-good CAP after any activation failure. Preserve all browser/session state. | Plan amended; implementation blocking |
| SEC-03 | Use the ratified fixed-volume, networkless, no-free-form-input migration helper and canonical-path UID-specific secret ACL helper. Validate the exact secret parent/file types and ownership, reject host UID collisions, assert the effective POSIX ACL rather than an incompatible post-ACL numeric mode, reject unexpected volume state before mutation, and never restore known-bad metadata. | Plan amended; implementation blocking |
| OPS-H1 | Add and behaviorally test guarded `--targeted-cap`; use it for forest1 and wepp1 rollout. It may mutate only CAP and its exact resources. | Plan amended; implementation blocking |
| OPS-H6 | Run destructive failure injection only on isolated disposable fixtures. Forest1 live-state rehearsal uses receipts and canonical recovery; it does not corrupt the live ledger for testing. Prove cleanup/recovery from a separate operator process after the injection process and its trap have ended. | Plan amended; implementation blocking |
| OPS-H7, QA-01 | Replace false-green tmpfs/inline-secret coverage with one mandatory `docker/validate-cap-runtime-contract.sh` production-mount harness invoked by local, auxiliary-image, and CAP-recreating deploy gates, plus executable deploy-mode tests. Missing Docker/ACL capability fails with an actionable prerequisite, not skip. | Plan amended; implementation blocking |

## Additional Medium Findings Incorporated

The plan also incorporates the reviewers' Medium findings because package
closure requires them resolved. It adds continuity proof for a pre-migration
verification token; explicit zero-byte, invalid-JSON, wrong-shape, symlink,
directory, special-file, fresh, empty, populated, and replaced-secret states;
named canonical documentation destinations; explicit `CAP_HEALTHCHECK_URL`;
before/after identities for non-selected services; rejection of inline secret
precedence; redacted fixed-code diagnostics; and mandatory host-Docker test
capability.

## QA Critical/High Disposition Audit

The QA reviewer re-audited only QA-01 through QA-04 against this disposition
and the living ExecPlan. No Critical QA finding existed. The audit found three
carry-through gaps and amended the documents before sign-off: the existing
ledger needed its own nondestructive update-open proof in addition to a
directory-write probe; the production-mount harness needed one named shared
interface across local, auxiliary-image, and deploy gates; and recovery needed
an explicit double-failure contract plus removal of an instruction that could
restore the incident's known-bad permissions.

- **QA-01**: faithfully dispositioned through the single mandatory
  `docker/validate-cap-runtime-contract.sh` host-Docker harness, real bind
  secret/named-volume states, shared callers, and hard failure rather than
  skip.
- **QA-02**: faithfully dispositioned through pre-listen existing-ledger and
  directory write proof, distinct readiness/liveness, and the functional
  challenge/redeem/siteverify canary.
- **QA-03**: faithfully dispositioned through separate build,
  intentionally-recreated, and expected-running service sets plus executable
  full, targeted web, targeted CAP, wepp2, and wepp3 behavior tests.
- **QA-04**: faithfully dispositioned through pre-stop validation, host-local
  rescue retention, verified automatic restore, forward-safe permissions,
  explicit restore-failure behavior, success/prune fencing, and retained
  manual-recovery evidence.

Audit result: all QA Critical/High findings are faithfully dispositioned as
implementation-blocking requirements. This is design sign-off only; the QA
release gate remains failed until implementation and forest1 evidence pass
re-review.

## Re-review Gate

After implementation and forest1 evidence, send the same four artifacts back
to independent correctness, operations, QA, and security reviewers. Package
rollout remains blocked until Critical and High counts are zero. Package
closure remains blocked until Medium counts are also zero.

## Operations Critical/High Disposition Audit

**Audit time**: 2026-08-25 16:12 UTC
**Result**: all OPS-H1 through OPS-H8 are faithfully dispositioned as blocking
design and evidence requirements; the operations review reported no Critical
finding.

The audit corrected four mapping gaps before reaching that result:

- OPS-H2 now stages and validates owner/base permissions and named-user ACLs
  before atomic secret replacement, and treats effective ACL access rather
  than incompatible post-ACL numeric mode `0600` as canonical.
- OPS-H3/OPS-H4 now forbid restoring incident/hostile metadata and require the
  closed-ledger receipt plus runtime-identity mount probe before replacement.
- OPS-H6 now requires cleanup/recovery verification from a separate process;
  the failure-injection trap is only the first recovery layer.
- OPS-H8 now makes the package-level availability statement match the ratified
  bounded login-only maintenance gap rather than promising zero exposure.

This audit closes disposition mapping only. It does not resolve any finding;
implementation, forest1 evidence, and independent re-review remain mandatory.

## Security Critical/High Disposition Audit

**Audit time**: 2026-08-25 16:12 UTC
**Result**: all SEC-01 through SEC-03 are faithfully dispositioned as blocking
design and evidence requirements; the security review reported no Critical
finding.

The audit corrected the remaining mapping gaps before reaching that result:

- SEC-02 now requires CAP's internal readiness health check and
  `service_healthy` Caddy dependency for full-stack activation. Targeted CAP
  retains the separately documented bounded gap and verified automatic restore.
- SEC-03 now validates the canonical secret parent directory as well as the
  file, rejects unexpected host UID `10001` mappings, and defines the exact
  effective POSIX ACL without the contradictory post-ACL mode-0600 assertion.
- The privileged volume and secret helpers now accept no free-form path or UID,
  and recovery establishes forward-safe canonical metadata rather than
  restoring the incident's prior metadata.

SEC-01 already carried through without a mapping gap: pre-listen ledger type,
schema, existing-file write, and directory create/fsync/remove checks gate
readiness; CAP is stopped before the integrity receipt and migration; and the
host-Docker matrix covers valid and hostile persistence states.

This audit closes disposition mapping only. SEC-01 through SEC-03 remain open
until implementation, host-Docker evidence, forest1 rehearsal, and independent
security re-review demonstrate the controls.

## Expanded Implementation Re-review

**Review completed**: 2026-08-25 18:05 UTC
**Code gate**: PASS — Critical 0, High 0 across correctness, operations, QA,
and security.

The final implementation gate verified the exact full CAP/WEPPcloudR topology,
targeted and worker modes, hostile CAP state matrix, stale-renderer rejection,
failure-atomic secret publication, dependency-contained rescue, controller
rollback, current-container worker registration, and a renewable uniquely
owned fleet RQ fence. The executable deployment suite passed 29 tests; the
complete repository suite passed 6,706 tests with 63 skips.

Forest1 activation remains operationally blocked, not code-blocked: the host
lacks the required `acl` package providing `setfacl` and `getfacl`. The
deployment account cannot install it without interactive sudo. No integrated
service mutation may begin until that prerequisite reads back successfully.
