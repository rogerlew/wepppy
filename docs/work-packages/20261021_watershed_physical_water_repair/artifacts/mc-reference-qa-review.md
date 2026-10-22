# MC4 reference and fixed-point secondary QA

Date: 2026-10-21. Independent read-only review of isolated
`mc-reference-candidate-v5`, following the scientific review in
[mc-reference-state-review.md](mc-reference-state-review.md).
This reviewer made no production edits. After the source review, this reviewer
authored the portable lifecycle tests described below; the scientific reviewer
independently reviewed those tests.

## Disposition

**The bounded reference cache and exact fixed-point shortcut pass this source
and lifecycle review, conditional on the remaining full native gate.** The exact
previously failing 100-year gate now passes against v5 at the unchanged
900-second timeout: two passed, two existing tarfile warnings, 580.64 seconds.
The run reached year 100/day 365/channel 31. The retained retest log is
`mc-reference-v5-failed-gate-retest.log` under the external evidence root.
The full native suite is still running at this checkpoint; see the historical
failure in [mc-runtime-state-qa-review.md](mc-runtime-state-qa-review.md).
The continuity diagnostic adaptation below has passed its bounded reproduction. This approval does not close signed source/sink coupling, clipping, or
the full physical-water package.

Reviewed candidate source SHA256 values:

- `src/wshchr.for`:
  `52ab00eda3f5bd44ae652ed2e199b04c97e48f56a1de41a5b1d18dcbca096369`.
- `src/chrstate.for`:
  `649943add6c9b9eb8809f536d640ee3fb7fe963eb5052e8066d690eb1247d863`.

## Lifecycle and isolation

The new `CHRSTATE_LIVE` entry uses only its own dummy arguments and saved
`oldn`/`last` arrays. It initializes the result on every call, ignores node zero,
and never mutates retained state. A first-call query returns false; the normal
phase-one call still performs the reset. Negative and subnormal interior state
remains live. Signed zero is empty under the existing nonzero-state predicate.

The MC4 reference is per channel, initialized to zero, and reset on `nt0=0`
before the state query. Degenerate references do not overwrite a valid cache.
The fallback requires both live retained state and a prior reference above the
existing epsilon. It makes no new reference when that history is absent.
MC3 and MC5 do not read or update the cache. Cache and retained-state resets use
the same existing channel-initialization sentinel; this coupling should remain
visible if the initialization lifecycle is ever changed.

An independent native harness passes **26 checks**: 11 ENTRY/storage checks and
15 cache scenarios. These cover fresh state, boundary-only state, negative and
minimum subnormal state, signed zero, read-only queries, normal phase-one reset,
no valid reference history, no live interior, zero/epsilon references, two
independent channels, new-call cache reset, and MC3/MC5 exclusion. The cache
harness executes the actual WSHCHR cache block with a prescribed reference and
then returns. This isolates lifecycle behavior; it is not a
replacement for full routing dynamics tests.

External evidence is under
`/workdir/watershed-physical-water-repair-20261021/mc-reference-lifecycle-qa-v1/`:
`check.py`, generated native drivers, compiler commands, stdout and
`receipt.json`. Receipt SHA256:
`a5b52901699dd36014c8235b1027dab97093084cdc687689116fe5cb55c78557`.

## Shortcut proof and boundary conditions

The last-change scan compares every adjacent assembled qin and normalized qlat
value by storage bits. At `it > lastchange`, forcing from `it-1` through the
final endpoint is constant. This is sufficient for both lateral modes:
point mode uses the preceding and current qlat values, while interval mode
uses the current value. A change at the final interval prevents the shortcut;
a future pulse cannot be skipped. The additional `it < ntchr` condition avoids
copying an empty remainder.

After a complete native MC4 interval, the shortcut requires bit-identical full
spatial profiles, including node zero, and bit-identical clipped outlet values.
The latter preserves the previous-outlet input to the recurrence eligibility
guard. Together with unchanged forcing and fixed MC4 coefficients, these are
all inputs needed to reproduce the next interval. Induction then permits exact
copies of the remaining states and outlet rates. Ordinary CHRSTATE saving,
publication, peak selection and downstream handoff still consume the complete
arrays. No post-loop consumer depends on the abbreviated loop counter.

MC5 remains excluded because its coefficients change within the cell loop.
The shortcut does not erase subnormal state and cannot repair the K=0
period-two sign cycle; the reference repair addresses that separate defect.
TRANSFER distinguishes positive and negative zero, unlike the rejected numeric
equality implementation. The independent harness confirms 32-bit default REAL
and INTEGER storage for the pinned compiler contract.

The science reviewer's actual-v5 receipt contains 26 optimized/unoptimized
pairs. This reviewer independently checked that all paired complete-state
hashes and publication records match. Its raw-array tests and their limitations
are detailed in the scientific review. Portable regression retention should
include the late pulse at 60 seconds, all-zero/no-history controls, a future
forcing change, minimum subnormal state, signed zero, MC5 exclusion, and the
ENTRY/cache lifecycle cases above. Keep exact raw-array comparisons; outlet
volume alone cannot detect erased or altered interior state.

## Confirmed diagnostic compatibility finding

The existing `tools/mc_continuity_probe.py:27` emits MCSTEP only for executed
recurrence cells, while its strict parser requires every interval/cell record.
`tools/mc_cascade_probe.py` shares this instrumentation. Against actual v5, a
steady MC4 top-source, fixed-eight-cell control emits 16, 8 and 8 cell records
on its three days instead of 1152 per day. The parser correctly raises
`Incomplete or reordered recurrence records 1`.

`probe_compat.py`, `diagnostic.stdout` and `diagnostic_receipt.json` in the
external QA evidence directory retain this reproduction and source identity.
Do not relax completeness checks or treat missing recurrence records as zero.
The smallest adaptation is to explicitly disable the shortcut only in the
instrumented diagnostic build using an exactly-once source replacement and
record that choice in provenance. The optimized/unoptimized full-array parity
controls then connect that diagnostic to production behavior. Reconstructing
all copied-cell records from MCFAST is another option but adds more audit code.
This finding blocked rerunning these diagnostics unchanged, not the fixed-point
source proof. The author applied the explicit diagnostic-only disable with an
exactly-once replacement and an `instrumentation.json` description in both
probes. Independent rerun of the same failing control now emits all 1152
records on each day, and the unchanged strict parser accepts it. The adapted
receipt is retained in `diagnostic-after-adaptation/diagnostic_receipt.json`.
Broader probe reruns remain the execution owner's gate responsibility.

## Residual quality debt

The change is cohesive and uses existing state ownership and initialization.
It adds no fitted cutoff, global numeric-mode change, or generalized reference
heuristic. The main maintenance risks are the shared reset sentinel, the
explicit 32-bit representation contract, and diagnostic source-insertion
anchors. Retain exactly-once replacement guards and complete source/compiler
provenance. Broader signed-exchange and clipping acceptance remains open; do
not interpret successful runtime and parity gates as that scientific closure.

## Portable lifecycle coverage

The independent controls are now retained in native
`tests/test_mc_reference_lifecycle.py` and
`tests/native/mc_reference_{lifecycle,cache}_driver.for`. All 26 tests pass
against the canonical v5 source in 1.09 seconds. They use only repository
sources and temporary compiled probes, with no private or external input paths.
The cache block instrumentation uses exactly-once replacement guards and
ordered calls within one process; preserving state between calls is essential
to the cache/reset assertions. The native fixtures stay within 72 columns.
Independent scientific review of these new tests found no blocker. Six isolated
mutants are rejected: omitted cache reset, shared channel history, destructive
state query, subnormal cutoff, exact-zero-only fallback, and a missing live-state
guard. Their receipts are retained in `portable-mutations-v2/receipt.json` under
the QA evidence directory.

## Independent review of portable fixed-point tests

The scientific reviewer authored native `tests/test_mc_fixed_point.py` and
`tests/native/mc_reference_driver.for`; this reviewer inspected both and found
no blocking test-quality issue. The author's complete targeted run reports
66 passed in 8.65 seconds. The 60 full-array pairs span both lateral modes,
144/1440 intervals, MC4 controls and MC5 exclusions; four tests exercise causal
reference selection and two preserve no-history behavior. The stream checks
complete day/grid/frame lengths and finite arrays before hashing every raw
spatial/time state and outlet value. Publication is compared separately.
Controlled seeding is explicit and uses the actual CHRSTATE save.

Independent causal mutation checks also pass: restoring numeric equality
causes four of eight signed-zero controls to fail, and removing the future
forcing guard causes four of eight future-pulse controls to fail. The unchanged
MC5 controls pass. Retained evidence is `parity-mutations/receipt.json` and its
pytest logs; `portable-coverage-receipt.json` pins all five test/driver hashes,
commands, review ownership and mutation outcomes. No broad suite was duplicated
by this reviewer.
