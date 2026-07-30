# SURF-14A Post-Remediation Final Governance/Correctness Review

## Metadata

- **Reviewer**: independent governance/correctness control agent
- **Date**: 2026-07-30 UTC
- **Package**:
  `docs/work-packages/20260729_user_preferences_wbt_boundary/`
- **Git base**: `b1f1f99c8f808528315abce001a70200ab068bc7`
- **Reviewed non-work-package source/test fingerprint**:
  `4aa271981f363b1a126e5fdf92fcb7d47d0f6804449ed92d0511494f4721ec73`
- **Forest, production, or product mutation by this reviewer**: none
- **Break-glass basis**: none requested or used

Fingerprint command:

```bash
git diff --cached --binary -- . \
  ':(exclude)docs/work-packages/20260729_user_preferences_wbt_boundary/**' \
  ':(exclude)PROJECT_TRACKER.md' | sha256sum
```

The exclusion keeps mutable review records and `PROJECT_TRACKER.md` outside
the stable source/test fingerprint. The tracker contains the staged SURF-14A
status update plus an unrelated unstaged Pure UI update. This reviewer
separately reviewed the staged SURF-14A tracker content.

This artifact is additive and immutable. Every earlier PASS and FAIL review
remains preserved as evidence for its own exact state.

## Verdict

**CONDITIONAL PASS — approve the governance/correctness substance of exact
fingerprint `4aa271981` for completion of its final exact-state gates.**

**Open findings**: 0 High, 0 Medium, 0 Low.

This is not yet Forest or release authorization. The exact full Python suite
and test-isolation gate were still running when this artifact was written.
They must both finish successfully against this same fingerprint, be recorded
truthfully in the active ExecPlan and tracker, and receive a new additive
confirmation. Any source/test drift or either gate failure voids this
conditional approval.

An independent operations/security final review remains a separate required
control. Production/wepp1 remains outside the package's authority.

## Prior Finding Closure

### GOV-PR-01 — Closed: the unratified public cleanup receipt was removed

The rejected fingerprint added public
`error.details={cleanup_required, runid}` behavior after implementation began.
The exact reviewed state removes that behavior completely:

- `docs/schemas/rq-response-contract.md` contains no failed-create cleanup
  receipt;
- `wepppy/microservices/rq_engine/project_routes.py` returns the existing
  sanitized creation error code and public `error_id` without a run ID or new
  details field;
- the route logs one internal cleanup-failure record containing the same
  `error_id` and exact generated run ID; and
- regressions prove the public body does not contain the run ID while the
  internal record remains correlated.

This is an acceptable scope reduction to the existing canonical response
contract. It does not retroactively ratify the rejected public field and does
not weaken the public error envelope. Operators recover through the existing
public correlation ID and restricted internal diagnostics.

### GOV-PR-02 — Closed: DB-11 and related failed-run state are explicit postconditions

The exact product cleanup now:

1. validates that the target is the canonical generated run directory beneath
   the primary run root;
2. refuses the root, a mismatched path, a top-level symlink, or platforms
   without descriptor-based symlink-resistant `rmtree`;
3. closes request-created NoDb instances;
4. clears run locks and strictly deletes/verifies DB-0 lock state;
5. clears NoDb file cache and strictly verifies no exact or descendant DB-13
   cache key remains;
6. strictly deletes/verifies the exact DB-11 working-directory key; and
7. only then removes the canonical directory.

Redis, postcondition, or filesystem failures remain visible. The public
response stays sanitized, while the internal record preserves the exact
recovery target.

The six stale disposable acceptance keys found by the prior review were
deleted by exact name and verified absent across Redis DB
0/2/9/11/13/14/15. The corrected canary then used Users 341/342, Run 1404,
run `pain-free-prospectus`, and four exact WBT job receipts. Its functional,
SQL, and strict Redis postconditions passed.

NFS retained zero-length open-handle files after that canary. The harness
correctly emitted `checks_passed_cleanup_pending` rather than PASS. The
operator restarted only the two handle-owning services, removed the exact
now-empty directory, verified the directory and adjacent access-log path
absent, and restored healthy workers. This is observable operator completion,
not silent cleanup fallback.

### GOV-PR-03 — Closed subject to terminal gates: source scope is exact

The requested fingerprint reproduces exactly with the command recorded above.
Other than the intentionally excluded `PROJECT_TRACKER.md`, staged and
unstaged path intersection is empty. Unstaged Command Bar and Pure UI source,
tests, package records, and generated documentation are outside the reviewed
SURF-14A source/test set.

The final full and isolation gates are conditions rather than findings because
they were started on the frozen state and remained in progress. They cannot be
represented as passing until their terminal results are available.

### GOV-PR-04 — Closed: hardening lifecycle evidence is durable

The package now records:

- the exact acceptance trigger and bounded cleanup-only scope;
- applicable precedent and what was deliberately not reused;
- a measurable zero-residue hypothesis;
- primary health and guardrail signals;
- a local canary plus 14-day post-Forest observation window;
- rollback and danger criteria;
- permanent-integrity-check sunset posture; and
- the requesting operator and WEPPcloud maintainer as observation owners.

The tracker records the baseline six-run DB-0/11/13 residue, the post-change
zero-state checks, the repeated canary, the remaining Forest risk, and the
closure criterion. If the Forest canary runs on 2026-07-30, observation review
is due 2026-08-13 UTC and may close only with zero reported DB-0/11/13
residue, uncorrelated cleanup failure, or out-of-scope deletion.

The strict postconditions are permanent integrity controls rather than a
temporary retry or fallback callus.

## User-Context Contract Assessment

### Authenticated viewing-user Unitizer

- Ordinary run authorization remains the access boundary. Account preferences
  are resolved only for an already-authorized authenticated viewer and never
  grant run access.
- `current_user.id` must resolve to an active positive numeric User. Invalid
  identity, stored preference, or database access fails closed with the
  sanitized `preference_resolution_failed` contract.
- `config` returns the exact durable project Unitizer. `si` and `english`
  construct detached request-local presentation views with copied preference
  mappings.
- The presentation view rejects preference, lock, dump, readonly, public,
  debug, and verbose mutation. It neither acquires a persistence lock nor
  writes `unitizer.nodb`.
- The finite report/control/conversion adoption inventory resolves the view
  after each route's ordinary authorization. The explicit Unitizer mutation
  endpoint and durable feature-export conversion remain project-scoped.
- Project creation no longer consults profile units. Explicit creation input
  and configuration alone determine durable project units.

Concurrent PostgreSQL evidence proves two authenticated users obtain SI and
English views over the same cached Unitizer while its identity, preferences,
bytes, modification time, and lock state remain unchanged. Both local
acceptance runs independently demonstrated byte-stable project units.

### Authenticated initiating-user WBT

- rq-engine authenticates and authorizes the run before preference lookup.
  Denied access cannot query account preferences.
- A verified `user` token or account-bearing session resolves the initiating
  User. Service/MCP, accountless session, direct worker, and batch paths use
  project/config policy. A malformed present account identity fails closed.
- Each new WBT submission synchronously resolves that initiator's current
  preference. `warn` or `error` becomes only that job's effective input;
  `config` uses the immutable project configuration baseline.
- The root stores the exact private initiator snapshot and passes only the
  bounded execution argument. Root and child validate exact schema,
  run/actor/policy/source consistency before WBT mutation.
- The child applies the policy as an execution-only
  `build_subcatchments` argument inside the directory-root lock. It does not
  persist account-derived policy to the Watershed controller.
- A new submission refreshes preferences. RQ retry reuses the original
  snapshot and exact committed tree without another account lookup.
- Open job status/info redacts private snapshot and actor state.

Route tests prove two initiators on one shared run enqueue `error` and `warn`
snapshots without changing durable project fields. The local acceptance
repeats User A `error`, User B `warn`, User A Auto/config, and
service/accountless fallback on one unchanged run.

## Validation Evidence

This reviewer independently obtained:

| Gate | Result |
| --- | --- |
| Exact non-work-package fingerprint | **PASS — `4aa271981...`** |
| Viewer/WBT/create-cleanup focused selection | **PASS — 135 tests** |
| Work-package documentation lint | **PASS — 33 files** |
| `PROJECT_TRACKER.md` documentation lint | **PASS** |
| Public cleanup-receipt absence | **PASS** |
| Diff/whitespace check, generated docs index excluded | **PASS** |

Supplied evidence also reports passing affected tests, frontend lint and 745
JavaScript tests, affected stubtest, test-stub completeness, RQ graph,
documentation, broad-exception, and diff gates. The repeated local two-user
acceptance and exact Redis DB 0/2/9/11/13/14/15 checks passed as described
above.

The following exact-state gates were not terminal at artifact creation:

| Pending gate | Required terminal result |
| --- | --- |
| `wctl run-pytest tests --maxfail=1` | exit 0 with final pass/skip counts |
| `wctl check-test-isolation` | exit 0 for the complete isolation procedure |

No older full-suite or isolation result may be substituted for those runs.

## Authority and Follow-Up

- **Exact source/correctness state**: conditionally approved.
- **Forest preflight/migration/canary**: blocked until both pending gates pass,
  an additive governance confirmation records them, and the separate final
  operations/security control approves the same state.
- **Production/wepp1**: unauthorized and outside scope.
- **Hardening observation**: mandatory for 14 days after Forest canary, with
  the named owners and zero-residue closure criterion above.
- **Revocation**: any fingerprint drift, gate failure, residue, lost
  correlation, out-of-scope deletion, identity crossover, durable Unitizer
  mutation, or account-derived Watershed persistence revokes this approval and
  stops progression.

## Conditional Control Decision

The earlier DB-11 and unratified-public-contract findings are closed for exact
fingerprint `4aa271981`. The user-context implementation conforms to the
approved viewing-user and initiating-user contracts, and the hardening
lifecycle is now accountable and measurable.

The conditional status may convert to final PASS only through a new immutable
confirmation after the exact full-suite and isolation results are terminal.
