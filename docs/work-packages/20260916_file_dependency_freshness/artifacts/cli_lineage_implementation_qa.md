# PF-R02 implementation QA

Review after contract checkpoint `166c8f79d`. **Scoped code/test quality and
explicitly amended performance acceptance PASS.** The original budget failure
remains recorded below; full-state/runtime gates remain open. No production
or test edits by this reviewer. This is not full-package closure.

## Maintainability and meaningful coverage

The bounded `wepppy/climates/cli_parquet.py` collaborator keeps snapshot ownership,
proof parsing, publication and attempt outcomes together. The two producers keep
their existing native dataframe calculations and distinct selection/error rules.
This adds no dependency or persistent cache and avoids duplicating the new
publication protocol. The existing duplicated scientific transformation blocks
remain residual debt; changing those calculations is unnecessary for this wave.

`tests/nodb/test_cli_parquet_lineage.py` uses real ClimateFile/Arrow data and real
NoDb owners. Selection-race coverage persists through a separately hydrated owner,
rather than mutating only the exporter's retained object. Deterministic parser and
publication hooks cover lasting changes, change-and-restore, overlapping outputs,
native partial-write failure, uncaught parser errors and postcommit diagnostic
failure. The latter checks both accepted output and readiness. Mode/authorization
tests run unprivileged and assert old bytes survive failure.

Legacy and metadata-only cases assert meaningful outcomes: existing tables remain
readable, the interchange fast path still returns them, proofless rows do not
certify a new execution, and touch/link/chmod do not revoke matching proof.
The cleanup/skeleton/archive test preserves actual failed snapshots and statuses
through the normal helpers and canonical archive/restore code, rather than merely
testing an allowlist literal. Source/output symlinks and an aliased project root
have native compatibility coverage. Existing service tests continue exercising
breakpoint intensity values and nullable columns; their owner-selection seam is
explicitly limited to formatting unit tests, while integration tests use the real
owner loader.

Reviewed `cli_lineage_focused_revision4.log`: **91 passed**. The broader initial
run retained one obsolete analytical fixture failure after 583 passes: that fixture
replaced generated Parquet with proofless synthetic rows. Its correction uses an
actual breakpoint CLI export and needs the retained combined rerun. Independent
correctness and security artifacts cover observable replacement between footer
read and source validation, oversize rejection before Arrow decoding, disappearing
interchange hints and real denied reads.

The low-priority durable-coverage request is closed in code: the retained
content=True/False footer-replacement probes and disappearing-hint probe are now
normal regression tests. They assert the structured changed_source rejection or
absence of a published fallback generation. The final affected gate must include
these additions. Security also verified private 0600 snapshot/status files through
actual archive/restore, rather than relying on attempt-directory privacy alone.

## Implemented benchmark evidence

[Script](benchmark_cli_lineage_implementation.py) invokes the actual exporter with
copied real `climate.nodb` owners, including unmodified publication-time
`Climate.getInstance`. It compares native rows/types to the preimplementation
outputs, checks preserved 0640 output mode and private retained attempts, and
uses actual production digest caches for readiness and 512-entry eviction.

The preliminary [JSON](cli_lineage_implementation_performance.json) and
[log](cli_lineage_implementation_performance.log) remain evidence, not the final
timing gate: affected tests overlapped execution. Its copied directory basenames
also initially matched the named projects' NoDb logging runids, so normal exports
could emit informational Redis status messages on those channels. No named file
writes occurred; audited owner inputs retained identical bytes/generations, and
CLI input came from the already retained disposable copy. The benchmark now uses
unique QA basenames as well as unique directory roots. This preserves actual
owner behavior without touching named output files or borrowing named status
identities.

Final measurements must separately label the actual new lineage predicate and
the wider two-file source inventory slice. The predicate measurement includes
all strict path/open guards, bounded footer parsing, CLI digest, generation and
signature checks, and portable selection resolution; it receives already acquired
source records, as it does in production, with an empty hash map so the active
digest remains inside the measured call. The inventory slice additionally includes
the preexisting source signature and optional full-content inventory checks.
Neither label means full `postfire.sources` or accepted-result validation.

## Actual performance result and open finding

The isolated [final JSON](cli_lineage_implementation_performance_final.json) and
[log](cli_lineage_implementation_performance_final.log) retain stable start/end
module hashes and disposable outputs under
`/wc1/batch/qa-cli-lineage-implementation-57cc2da157e1`. Root tests were paused for
this run. The mount is NFS4; OS caches were warm, without cache dropping. This is
measured warm NFS behavior, not cold-storage evidence.

| Actual mean | 46 years | 120 years |
| --- | ---: | ---: |
| Full export including owner rehydration | 411.15 ms | 948.29 ms |
| Full export, settled owner, 3 calls | 370.49 ms | 863.95 ms |
| Interchange generation plus disposable input copy, 3 calls | 393.31 ms | 930.87 ms |
| New lineage predicate, cold digest | 14.37 ms | 23.34 ms |
| New lineage predicate, first admitted digest | 21.22 ms | 29.48 ms |
| New lineage predicate, settled, 100 calls | **8.28 ms** | **10.78 ms** |
| New lineage predicate, 3 actual eviction cycles | 17.95 ms | **43.85 ms** |
| Existing two-file inventory plus lineage, content=False, settled | 8.83 ms | 12.64 ms |
| Existing two-file inventory plus lineage, content=True, settled | 19.47 ms | 15.44 ms |

Both producer outputs match original rows/types exactly; existing output mode is
0640 and all four Climate attempts per case finish complete inside 0700
directories. Named owner input bytes/generations remain unchanged. Real owner
selection callback cost is 4.14/4.45 ms on rehydration and 0.24–0.40 ms on warm
reload. Full export passes the 1.5-second budget, with settled overhead
32.78/53.65 ms versus original producer means, within 200 ms.

The native predicate performs exactly one CLI digest check per call, zero settled
CLI payload reads, and 65,548 footer/framing bytes per call. Cold/evicted calls read
exactly one CLI payload. Three 512-path pressure/admission cycles per mode fill
both existing production caches to 512 and force source rereads. Export acquisition
streams one source copy and invokes two full live-source digest checks; native
parsing consumes the retained snapshot. Counted Path.open reads do not intercept
the native parser, whose cost remains inside full export elapsed time.

**CLI-QA-P01 — original performance acceptance finding; see final disposition below.**
`production.py:_cli_lineage_current` fails the ratified <=5-ms settled mean for
both inputs; the large case's eviction mean also exceeds <=40 ms. Correct byte
counts and passing export latency do not waive this failure.

[Profiler script](profile_cli_lineage_predicate.py), [JSON](cli_lineage_predicate_profile.json)
and [log](cli_lineage_predicate_profile.log) repeat the actual predicate without
benchmark stream wrappers: 7.60/9.72 ms, confirming the miss is not solely wrapper
overhead. Profiles retain [46-year](cli_lineage_profile_thespian-cleanness.txt) and
[120-year](cli_lineage_profile_plastic-bundling.txt) call counts. The two
`rainfall_io.open_local` traversals make **14 posix.open calls per predicate** and
account for 3.37–4.33 ms, about 46–49% of profiled elapsed time. Standalone metadata
plus local opener costs 4.18/4.43 ms; warm CLI digest plus local opener costs
3.55/2.93 ms. Selection resolution is only 0.59/0.53 ms, the initial safe pair
~0.29 ms, and the final signature pair ~0.49 ms. Independent component timings
have scheduling/NFS variability and must not be summed as an exact decomposition.

The smallest useful optimization target is repeated no-follow directory traversal,
with selection resolution a secondary saving. Reusing descriptor authority within
one validation needs independent correctness/security review and must preserve
containment, access checks, no-follow behavior, coherent generations and final
path/signature checks. Removing resolve alone cannot close the observed miss.
Do not substitute ordinary opens or silently change directory permission semantics
to meet timing. No optimization or budget change was made by this reviewer.

### First optimization recheck

The parent implemented same-call parent descriptor reuse, retained no-follow
directory traversal and added parent inode/path association checks. There is no
descriptor cache or reuse between requests. The post-fire predicate now compares
its strictly link-free selection directly, while generic exporter alias handling
remains separate. This is a bounded response to the measured hotspot; its new
parent replacement tests and independent authority review remain required.

The quick [profile JSON](cli_lineage_predicate_profile_parent_reuse.json) and
[log](cli_lineage_predicate_profile_parent_reuse.log), with per-case
[46-year](cli_lineage_profile_thespian-cleanness_parent_reuse.txt) and
[120-year](cli_lineage_profile_plastic-bundling_parent_reuse.txt) call profiles,
show **5.82/6.98 ms** settled actual predicates. The open count falls from 14 to
8 per check; remaining opens cost 2.43–2.63 ms per profiled check (39–42%). Four
safe calls, including final signatures, still account for about 1.3 ms profiled;
the proof reader costs about 0.66 ms. Profiling adds Python instrumentation cost,
so use the unprofiled 100-call means for the actual gate. Standalone metadata and
digest microtimings still perform separate opens and are not additive costs of
the newly shared path. The generic selection microbenchmark is retained for
comparison but no longer represents work performed by the revised predicate.

At this intermediate checkpoint CLI-QA-P01 remained open: the improvement did not reach the 5-ms budget. No full
producer rerun was made because this quick recheck already identifies the remaining
predicate miss. Correctness/security acceptance of the optional parent-descriptor
path, and any further bounded optimization, must precede final full measurement.

### Final explicit budget correction and acceptance

[Independent budget review](cli_lineage_performance_contract_qa.md) explicitly
ratifies <=10 ms settled / <=50 ms cold-or-evicted after profiling the prototype's
omitted required directory-open costs. The canonical contract and checkpoint
record preserve the original failure and record this amendment. No source-access
guard or payload-read invariant was waived, and export limits are unchanged.

The final [actual benchmark](cli_lineage_implementation_performance_budget_revision.json)
and [acceptance record](cli_lineage_budget_acceptance.json) pass: settled
4.85/6.14 ms, maximum cold/admission means 13.79/26.35 ms, and three-cycle actual
eviction means 14.69/27.86 ms. Full warm-owner exports take 394.14/876.46 ms,
adding 56.43/66.16 ms over original producers. Owner rehydration exports take
424.26/894.58 ms. All actual guards, footer checks and digest work are included;
module hashes remain stable. Settled checks read zero CLI payload and 65,548
footer/framing bytes each, with one CLI digest check per call.

Both native producers retain exact rows/types, 0640 outputs and complete private
attempts with 0600 snapshots/status. Named owner input files remain unchanged;
clones use unique QA runids. CLI-QA-P01 is **closed under the explicitly amended
contract**, while the original failed gate remains immutable evidence. This is
scoped component acceptance, not a substitute for whole-state or runtime evidence.

The final affected gate now passes **857 tests** in
`cli_lineage_affected_final.log`; final stub completeness and changed broad-exception
checks also pass. Pending: actual full-state and browser/runtime acceptance.
The corrected native M3 fixture gate passes all 36 cases; independent scoped security review passes after its three
verified corrections. Whole climate generation, NOAA/frequency
work and the existing one-second wrapper delay are outside the export-entrypoint
budget. Warm local storage measurements do not establish cold NFS performance.
