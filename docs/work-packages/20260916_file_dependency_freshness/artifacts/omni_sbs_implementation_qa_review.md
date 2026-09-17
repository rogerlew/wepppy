# S01 implementation QA and performance acceptance

**Scoped PASS: all45 original component/read gates pass.** No budget amendment
is required. Reviewer: `freshness_qa`, 2026-09-17. Production and repository tests
were read-only. Full native direct/RQ execution and inherited raster dependency
closure remain separate acceptance obligations.

## Retained benchmark and boundary

`benchmark_omni_sbs_implementation.py` calls the actual implemented helpers in
their direct/worker sequence. `omni_sbs_implementation_performance.json/.log`
retain every sample, read count, lock timing, module hash and limit;
`omni_sbs_implementation_budget_acceptance.json` enumerates all45 gates. Large
inputs and final consumed children are retained at
`/wc1/batch/qa-omni-sbs-implementation-7d7951e1b463/benchmark-manifest.json`.

The real599,196-byte Grizzly and747,242-byte Rattlesnake uploads and labeled
16,779,862-byte stress TIFF match the original reviewed fixture hashes. All work
uses unique copied inputs and real new Omni owners under UID1000/GID993. Named
projects are untouched. Input versions/hashes and every measured production
module remain unchanged. Copied inputs prime filesystem pages: helper-cold and
evicted measurements are not cold-storage guarantees.

Reuse includes initial signature, `SbsReuse.capture` and final admission
validation, for both a present upload and a consumed upload's accepted child.
Execution includes initial signature and receipt capture, both outer and reset
boundary `before_reset` checks, actual verified copy/consume, post-native
validation and final admission-equivalent validation. No security check is
removed. Native work is absent between those checks in this component benchmark.
Clone/reset, scientific validation/builds, live queue transport and HTTP are not
timed or simulated as completed runtime acceptance.

## Original gates and measured results

Times below are local means in milliseconds. Ranges cover present/consumed
reuse and initial/post-eviction settled measurements.

| Complete component | Grizzly | Rattlesnake | Stress | Ratified maximum |
| --- | ---: | ---: | ---: | --- |
| Settled reuse | 3.46–5.55 | 3.42–5.46 | 1.42–2.52 | 10 |
| Helper-cold/evicted reuse | 8.59–12.29 | 10.14–14.91 | 168.64–175.06 | 30 real /200 stress |
| Execution, helper-cold | 38.11 | 42.30 | 582.06 | 75 real /650 stress |
| Execution, initial upload settled | 37.32 | 30.93 | 313.71 | 75 real /650 stress |

There are18 actual512-entry pressure cycles, without substituting cache clearing
for eviction. Each evicted reuse reads three main-file equivalents. All settled
reuse samples read **zero payload bytes**, including those following eviction
and those inside actual admission locks. Present reuse makes three digest calls;
consumed reuse makes five calls, including two expected missing-upload checks.

Cold execution reads eight main-file equivalents: seven actual hash reads plus
the opened-source verified copy. It makes nine digest calls, including expected
missing-upload checks after consumption. With an already settled upload it reads
four equivalents because the newly written child remains recent. The prototype
read six equivalents; the final pass covers the additional required work.
All copied children match the input SHA-256, consumed uploads are absent, and
existing child0640 modes survive. Five samples cover cold/component execution,
three settled-upload execution and each eviction,30 initial settled reuse and10
post-eviction settled reuse. These are mean budgets, not per-request guarantees.

## Actual lock and persistence cost, reported separately

The separate sequence calls real `invalidate_sbs_association` and
`admit_sbs_association`, including Redis locking, detached durable refresh,
private-field updates and normal NoDb persistence. Its validation performs the
same receipt checks as the component gate. A durable readback verifies the new
association and state. The timing below is not compared with the component-only
budget, which explicitly excludes canonical locking/persistence.

| Measured sequence | Grizzly | Rattlesnake | Stress |
| --- | ---: | ---: | ---: |
| Execution plus reset/admission transactions and durable readback | 130.03 | 127.24 | 672.56 |
| Reset transaction acquired-to-exit | 48.68 | 40.83 | 99.26 |
| Admission transaction acquired-to-exit | 43.86 | 45.37 | 94.09 |
| Consumed settled reuse plus admission transaction | 43.37 | 53.87 | 55.87 |
| Its admission transaction acquired-to-exit | 40.55 | 49.40 | 51.71 |

Acquired-to-exit includes normal persistence/release. Separately retained body
means are4.06–4.57 ms for real reset and5.47–5.56 ms for real admission;
stress requires58.83/58.45 ms respectively. Settled reuse bodies take2.14–3.54 ms
with zero payload reads. Measured acquisition means are1.01–1.74 ms. These local
uncontended locks do not establish production contention or native-run duration.

## Maintainability and test quality

Receipt parsing, copied-file generation guards and coherent copying live in one
helper used by direct and queued paths. `SbsExecution` and `SbsReuse` distinguish
different admission obligations without adding a new transaction service.
The short locked functions refresh durable state before patching the affected
association/state; their comment explains why the lock token survives refresh.
This is clearer than independently rebuilding freshness rules in each caller.

Reviewed regression evidence includes61 affected tests in
`omni_sbs_tests_revision3.log`, the actual correctness probe's direct
execute/skip/changed-execute/skip sequence with GDAL class1→3 output, real NoDb
unrelated-state preservation, failed-reset retention and queued-drift rejection,
plus the final11-pass security probe. Same-file/hardlink rejection preserves
bytes, permitted aliases preserve prior copy authority, newly observed uploads
survive failed verification, and source observation cannot hide a changed child.
String/integer/enum dispatcher controls distinguish signature normalization from
changing persisted scenario definitions. The failed iterations remain evidence;
they are not relabeled successful.

`omni_sbs_implementation_correctness_review.md` records scoped PASS with ten
independent controls across its six-case direct/helper run, three-case actual
dispatcher/worker seam run and separate legacy missing-source control. These are
separate phases, not one unchanged-revision suite. The final security disposition
is retained in `omni_sbs_implementation_security_review.md`.

Nonblocking debt: the new helper uses untyped receipt dictionaries and physical
version tuples. A focused future typing pass could name these contracts without
generalizing the mechanism. Some generation/authority controls remain retained
independent probes rather than repository tests; promote those exact controls
when extending this boundary. Neither warrants another abstraction or broad
orchestration refactor now.

The benchmark does not establish complete native SBS scientific identity,
whole landuse/soil/WEPP output parity, live RQ/UI behavior or production mount
parity. Inherited destination sidecars and the documented writer-after-final-
check unlink limit remain explicit. The changed helper SHA-256 is:

```text
6f95a6f6f3bc8836259361fb5883697578b1a2392baee5540b87b2f3961e2832
```
