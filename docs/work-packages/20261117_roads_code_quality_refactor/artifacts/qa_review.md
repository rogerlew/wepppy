# Roads refactor secondary QA review

## Verdict and review identity

**Source quality and scoped native/project validation: accepted; no medium/high findings.** This is a secondary review
after the accepted [correctness](correctness_review.md) and
[security](security_review.md) source reviews. Exact-candidate native/project parity
is closed by the runtime addendum below. Final package acceptance remains
conditional on the required broad-suite receipt; that gate is still pending.

Reviewer: `roads_final_qa`, 2026-11-17 UTC. Baseline:
`96555f2f95326350d2d7007c19327378ea831ab0`; candidate source HEAD:
`5ef26481068cada863371d34b2d62ffd2c6e77fa`. Production scope is `roads.py` and the
17 extracted modules enumerated with SHA-256 in [quality_metrics.json](quality_metrics.json).
All 18 hashes also match the latest per-file hashes in
[security_source_manifest.json](security_source_manifest.json); that manifest's
older HEAD label predates committing its reviewed literal `__all__` additions.

The review also covers the current-policy project harness and archive fixture
isolation repair, initially uncommitted and subsequently captured unchanged in
`d6ecf9a2a`. Reviewed test SHA-256 values:

| Path | SHA-256 |
| --- | --- |
| `tests/roads/unrutted_project.py` | `6a8e9ed608c2d172cb8cd53ce18b3a3b927c153b4eb75a0a90ed12d57827c72d` |
| `tests/roads/test_roads_project.py` | `7ff4de831cc04e5cee9c54779e3f168af0177072a4a546b2f8ed16d651c8b73f` |
| `tests/rq/test_project_rq_archive.py` | `30edd6851404a1cf1bd7c8a4a2deb0a3d1fffdbd5be6b8b39f36861383fa5b35` |
| `tests/nodb/mods/test_roads_execution_mixed.py` | `021008af6f8dd94910bf7c9c7ef7efccf9f48c4485f909be677d8faa051d67dc` |
| `tests/nodb/mods/test_roads_execution_diagnostics.py` | `1281a2c342aa48dfc5a5bac78993ba306b21c4271a0e25a1989eb909b31c7119` |

## Maintainability and cohesion

The extraction has recognizable responsibilities: input normalization,
preparation, native soil/management/slope construction, spatial selection, routing,
report publication and queries. Execution separates point contributors, unrutted
planning, native strip/remainder execution and summary assembly. The original
2,069-line execution method was decomposed into named stages, not relocated intact.
`Roads.run_roads_wepp` retains lifecycle, persistence, publication and cleanup.

An independent AST comparison in this review confirms all 143 facade method
signatures, return annotations and decorators remain unchanged. Explicit adapters
retain callable and monkeypatch seams; native runner functions are injected from
the facade. No dynamic method installation, persistence proxy, speculative service
framework or new runtime dependency was introduced.

`ExecutionResults`, `SegmentTerrain` and `TraceState` represent run-local state;
they are not attached to the serialized controller. Dataset ownership remains
visible in context managers. Shared sequence numbers, pass registries and counters
have one accumulator across deferred and immediate contributors. These boundaries
are easier to inspect than the prior nested method.

The tradeoff is substantial adapter and argument repetition: total compared source
is **7,739 SLOC versus 5,907 (+31.0%)**, despite the facade falling to 1,888.
Helpers still depend on the facade and mutable record dictionaries; they are not
independent domain services. This explicit coupling is acceptable for preserving
the existing NoDb and compatibility contracts. Avoid adding generic result/schema
abstractions merely to reduce the metric. See [quality_metrics.md](quality_metrics.md)
for reproducible per-file measurements and unchanged hotspot complexity.

## Observability and tests

The moved broad exception handlers retain deliberate native/diagnostic boundaries.
The actual inventory remains 19 before and after extraction; new boundary comments
do not represent handler removal. The formerly silent candidate-membership update
catch now records a bounded, sanitized warning while retaining legacy continuation.
The real secret-profile/caplog regression exercises redaction, length bounds,
continued status recording and the quiet valid case.

`test_roads_execution_mixed.py` addresses the prior QA gap in shared execution
state. It runs actual coordinators, writers, unrutted planning, manifest assembly
and summary aggregation with deterministic terrain/profile/selection fixtures and
an injected native runner. Both successful and failed strip cases check common
IDs, additive/replacement pass lists, counters, failure accounting and remainder
continuation. This is useful integration coverage; it is not native WEPP parity.
The guarded candidate log `/tmp/roads-refactor-validation/execution-boundaries.log`
reports **4 passed**, covering the two mixed and two diagnostic cases. Its SHA-256
is `9ded90dd7e51a31b5a69b09b056fd992241cc20f2da14b0e213b7052617e4f2f`.

The new `tests/roads/unrutted_project.py` uses the approved current RUPC-02 oracle
without rewriting historical reports/readers. It pins all 55 source features,
declares synthetic geometry, rebases cloned NoDb paths before hydration, records
binary/input identities, and checks source/copied-baseline immutability. Positive
readback checks lifecycle admission, persisted summary/manifest, input hashes,
soil/management/slope OFE roles, per-hillslope area and independent daily water
reconciliation. Negative readback requires five specific oversize-geometry
failures, retained finite dimensions proving road-plus-fill overflow, 15 successful
profiles and no current receipt. These are explicit geometry controls, not site
predictions or a change in defaults. The immutable positive baseline contains 15
strips (six with no upstream landuse, five with no downstream landuse, four with
both) and nine remainders; the readback handles these different role layouts.

The archive fixture change clears ambient `VECTOR_UPLOAD_RUN_FILESYSTEM_ID` and
`VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT` using pytest's scoped monkeypatch. Production
reads those values at call time; tests exercising vector retention explicitly set
their own identity/root after fixture setup. The change makes ordinary unit tests
independent of the host configuration and does not weaken the dedicated boundary
tests. Its focused and broad runtime receipts remain separate from this inspection.

## Non-blocking residual debt and follow-ups

1. `wepppy/nodb/mods/roads/roads.py:1794` still has a 269-line execution facade and
   the file exceeds the SLOC triage band. Preserve visible transaction and
   publication ordering if extracting further stages; require a concrete
   readability benefit rather than a threshold-only split.
2. `wepppy/nodb/mods/roads/_queries.py:451` retains CC 61 in parameterization
   readback; `:191` retains a 157-line/CC 40 detail query.
   `wepppy/nodb/mods/roads/_inputs.py:361` retains CC 44 in parameter validation;
   `wepppy/nodb/mods/roads/_reporting.py:53` retains a 163-line report builder.
   Their bodies and complexity are unchanged from baseline. Characterize their
   distinct validation/readback branches before any later decomposition.
3. `tests/roads/unrutted_project.py:37` can make its top-placement purpose more
   robust by explicitly requiring at least one top-placed strip and nonempty
   source membership. Current role checks derive expected layouts from emitted
   records, and subset membership alone admits an empty list. This is a low-priority
   non-vacuity improvement, not a blocker given the pinned fixture, inspected
   baseline and existing placement coverage.
4. Execution modules retain long explicit keyword lists and repeated diagnostic
   dictionaries. Use future concrete branch changes to reassess those seams;
   wholesale deduplication now would enlarge the behavior-preservation review.

Root code-quality guidance is observe-only. Residual red metrics are recorded
honestly and do not override the absence of medium/high source-quality findings.

## Runtime and ledger closure

Final review binds commit `d6ecf9a2af77b4c39bdc834aba912cc3d1125c76` to the tested
bytes: all 37 production/harness fingerprints in
[candidate_source_receipt.json](candidate_source_receipt.json) independently match
both committed files and the working tree. All 18 production fingerprints from
this QA review also match that execution receipt. The receipt preserves the
original `5ef264810` execution HEAD and then-uncommitted harness hashes; the later
commit did not change those bytes.

Inspected [candidate_validation.md](candidate_validation.md), retained logs,
comparator scripts and machine-readable receipts establish:

- **527 native tests passed**, producing 516 profiles. All **6,192 native
  input/output files match baseline as raw bytes**, before permitted root-path
  substitution; binary and extension identities match.
- All **516 parsed case/scientific summaries match exactly**, excluding only
  elapsed time, in [candidate_analysis_comparison.json](candidate_analysis_comparison.json).
- All five real-controller project controls pass their declared positive/negative
  outcomes and **4,577 artifact comparisons** with no scientific or durable-summary
  differences. The comparator verifies referenced digests before normalizing
  links and limits other normalization to documented execution metadata. The
  supplemental field-metadata check matches all **92 Parquet schemas**.
- [Positive placement readback](candidate_positive_placement_readback.json)
  confirms 15 strips, six top-placed, nine remainders and nonempty membership for
  all 15 strips. This supports the present acceptance case; adding corresponding
  permanent harness assertions remains the low-priority follow-up above.
- The archive fixture isolation regression passed **73 tests**. The historical
  publication check passed **3 tests**. Final ledger review is recorded in
  [provenance_review.md](provenance_review.md#ledger-and-runtime-closure).

These receipts validate the refactor against its immutable current-policy baseline.
They do not refresh historical published reports, establish site calibration or
authorize deployment. Retained metrics and residual debt above remain applicable.

## Remaining acceptance gate

The integrator's broad-suite run is still pending. Bind its final result and any
baseline failure assessment to the reviewed source/test hashes; an in-progress
run is not a pass. Re-review any later production change or material test-oracle
change. Documentation-only closeout does not invalidate this assessment. No
production files were modified by this QA review.

## Fork-route fixture isolation addendum

The additional change to
`tests/microservices/test_rq_engine_fork_archive_routes.py:49` is accepted with no
medium/high finding. Reviewed file SHA-256:
`4d6c2b61ea4393e9602b8b48cbcc6e4e73bb79f2dc5e156bea1056b27751d8ca`.
Commit `43cb4e78f` captures these exact reviewed bytes.
It removes inherited `VECTOR_UPLOAD_RUN_FILESYSTEM_ID` and
`VECTOR_UPLOAD_RUN_FILESYSTEM_ROOT` inside the existing autouse
`legacy_project_policy` fixture, using pytest's scoped monkeypatch restoration.
Production reads these values at call time. Ordinary fake-Redis/no-evidence tests
therefore retain their intended unconfigured environment rather than entering an
incidental managed-retention branch.

The dedicated private-archive deletion, partial-retry and real-Redis global
maintenance tests explicitly set their filesystem identity/root after fixture
setup. Their retention boundaries remain exercised. The production missing-config
check still rejects actual retained evidence; no production guard or test
assertion was removed. The separate replacement-ordering test injects its
retention boundary explicitly.

The broad run stopped after 1,769 passed and 41 skipped when inherited settings
sent an ordinary fork-target test through `DummyRedis.sismember`, which that fake
does not implement. The guarded immutable-baseline log
`/tmp/roads-refactor-validation/broad-baseline-fork.log` reproduces the same
failure in `test_fork_target_runid_bypasses_generate_runid`. This supports a bounded
fixture-isolation correction, not a Roads production regression or a waiver of
retention behavior. The scoped module run
`/tmp/roads-refactor-validation/fork-fixture-isolation.log` completed with
**65 passed**, six warnings, in 5.24 seconds. The broad v3 rerun remains pending.
The 37-file Roads execution receipt and production-source review remain valid.

## Final formatting disposition

Independent comparison of all 37 Roads production/harness files against both
`d6ecf9a2a` and the immutable candidate execution receipt finds exactly one delta:
`wepppy/nodb/mods/roads/_constants.py` lost two trailing newline bytes. The previous
bytes equal the final bytes plus `b"\n\n"`. AST comparison, including node location
attributes, is identical. The tested SHA-256
`a44595427152e3ab93d80f4d9cefe940430d7f7b732ab596ace9fd2c53f10561`
becomes
`545dc010950acea4dda274fc7cf2f81e78c3fb43f84c34dafda2da9eb7b2ecde`.
This formatting delta is accepted without changing the prior native/project
assessment or its historical source identity. No executable token changed.

The staleness ledger at SHA-256
`336aa0a5c43c21d0fb2154b54e4e0a469b9c8fda1a79ef7fdec663d03acee7a6`
differs from the previously accepted ledger only in that module's current hash
and one appended formatting review. All earlier entries and original recorded
hashes remain intact. Original source, matrix, parsed-analysis and project
comparison receipts are unchanged; this addendum does not relabel the files
actually used for native execution.

All nine retained console-log pairs independently match the original and retained
hashes in [candidate_logs/receipt.json](candidate_logs/receipt.json). Normalization
removes trailing line/end-of-file whitespace only; original runtime logs remain
intact. The scoped diff whitespace check passes. See
[final_source_disposition.md](final_source_disposition.md) for the integrator's
receipt. Final-format focused tests and the broad rerun were still in progress
when this source addendum was written; their runtime results remain separate gates.
