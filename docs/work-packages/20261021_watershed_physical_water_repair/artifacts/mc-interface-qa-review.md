# MC interface candidate independent QA

Date: 2026-10-21. Reviewer: independent secondary QA agent.
Reviewed isolated candidate: `mc-interface-candidate-v2`, WSHCHR SHA256
`a1256946fba32df368db16bb2dc051bfaf78667d9d2c56d4c010e68717265dff`.
Comparator WSHCHR SHA256:
`1b3a5d7dc2c6aa9837230667d4e3ba9c203e05b1992c197c3a9ccafb6f1e9bad`.
No production or repository test source was edited by this reviewer.

## Scoped disposition

The reviewed source/publication correction is suitable for promotion after
the required native gates pass. Portable regression review is complete, including
causal mutation controls described below. No blocking QA finding
remains in the bounded controls for one-time deferred baseflow admission,
separate direct hillslope baseflow, the narrowed local-source predicate, or MC
publication of accepted outlet rates. This disposition does not establish full
watershed closure or approve a replacement routing/storage authority.

The accepted-outlet publication branch is restricted to MC4/MC5. The source
assembly fixes are shared with KW3: targeted `lr_bf=1` behavior changes there too,
and its threshold controls pass. Describe that shared scope explicitly; only the
unaffected KW3 paths are claimed unchanged. Signed exchange, clipping, source
projection and midnight endpoint accounting remain separate acceptance work.

## Independent native controls

An isolated three-channel driver calls actual WSHCQI followed by actual WSHCHR
for each channel and day. It does not seed `bflw` manually, replace the source
arrays, override grids/coefficient selection, or change the recurrence. Native
CHRSTATE, CHRQIN, MIXPASS, EQROOT and MANN are linked. Diagnostic writes observe
assembled sources, initialization and completed calls; the driver reads COMMON
publication values separately. GNU Fortran 13.3.0 builds use fixed-form 72-column
source, native initialization flags and invalid/zero/overflow traps.

There are 54 candidate and 54 checkpoint executions: KW3/MC4/MC5, both source
modes, seven source configurations, and all three upstream connection positions
for the deferred-only configuration. Each has three channels and three days.
The parser requires the exact nine channel/day keys, 145 ordered source and
outlet samples per key, unique scalar observations, expected field counts and
finite values. Native dependency sources match between lanes. The capacity
include profiles initially differed; rebuilding all 54 checkpoint controls with
the candidate profile produced exactly identical observations. Compiler commands,
all include hashes, source hashes and binary hashes are retained.

| Control | Independent result |
| --- | --- |
| Upstream area 4 ha, threshold 5 ha, hillslope baseflow 100→0→200 m³ | Actual WSHCQI defers exactly that amount; no upstream source rate or outlet volume admits it |
| Middle channel area exactly 5 ha | Admits the deferred amount once through the top source; its first endpoint equals the single admitted rate |
| Downstream area 6 ha | No additional deferred admission; receives the middle channel's actual routed Q and published volume |
| Direct middle hillslope, side and top separately | Direct baseflow uses its ordinary path with zero deferred admission; initial outflow contains it once |
| Deferred source plus direct middle side baseflow | Both independent components occur once, without cross-scaling |
| Legacy `lr_bf=0`, including positive side-hill runoff | Source arrays and outlet rates match the checkpoint exactly for all three methods and both modes |
| Positive side impoundment with local channel input | New uniform-source predicate remains off; source arrays and outlet rates retain checkpoint behavior |

All 15,660 downstream rate samples and 108 daily-volume transfers match exactly
in the threshold/direct-source controls. Every one of the 324 candidate MC
publication observations equals the binary32-rounded double-precision
trapezoidal integral of accepted outlet Q; `runvol` and `tmpvol` agree. Complete
KW3 observations also match the checkpoint in the three legacy/non-target
configurations. These results distinguish unchanged source/rate behavior from
the intentional MC publication change.

On continuing days, the assertions retain the previous endpoint at time zero
and apply the new scheduled source to positive indices. For example, zero new
baseflow after 100 m³/day retains the prior endpoint contribution to the top
trapezoid. The tests do not incorrectly require zero outlet on that day or
renormalize the source to remove the carry term.

## Harness findings and limits

The earlier single-channel `probe_baseflow_routing.py` correctly demonstrates
first-call duplicate removal and 100→0→200 source admission. Its INITIAL field
`aavg*chnlen` is meaningful on the first call but is read before `aavg` is assigned
on continuing calls. Those later zeros are not the retained start geometry.
At that tap, `sfnl(ichan)` still contains the carried previous endpoint. Correct
or relabel that diagnostic before using it for a continuing-day geometry ledger;
the candidate's source and transfer evidence is unaffected.

The independent driver's initial impoundment control changed release from
100→0→200 m³. Its zero-release day legitimately enabled the intended local-only
correction, so it was unsuitable as an unchanged-path control. The final control
holds impoundment release positive on every day. Both versions are retained;
this fixture correction is not attributed to a production defect.

The impoundment exclusion proves containment, not correctness of the existing
impoundment routing path. The bounded review does not certify requested versus
accepted withdrawals, negative raw MC rates, clipping closure, H/C/J identities,
or full physical-water balance. Existing single-channel diagnostics and the
29 paired replays must retain their own interpretation and acceptance evidence.
Required native release gates were not rerun as part of this independent review.

## Portable regression recommendation

Retain the small actual three-channel driver and its ordered SOURCE/OUTLET plus
ADMIT/PUBLISH observations in the native tests. The smallest core matrix is
MC4/MC5 × source modes 1/2 × deferred-only, direct-side, direct-top and combined
sources over the same three-day sequence. Assert exact threshold equality,
initial single-count behavior, no downstream re-admission, exact Q/tmpvol
transfer, finite observations and independently integrated MC publication.
Add left/right upstream-connection controls and explicit positive side-hill,
positive side-impoundment and `lr_bf=0`/KW3 controls for the changed predicates.

Keep the existing compiler helper and unique-anchor checks. The committed tests
need neither the full experimental build orchestrator nor generated stdout.
Name observation fields rather than spreading positional offsets through tests;
compare the rounded publication value explicitly instead of fitting a tolerance
to observed differences. Historical checkpoint builds and large traces can stay
in retained review evidence. These are maintainability recommendations, not a
request for broader routing redesign.

## Portable tests: final review

Reviewed `tests/test_channel_interfaces.py`,
`tests/native/channel_interface_driver.for` and the four local-source cases
promoted from strict expected failures in `tests/test_physical_water.py`.
Independent final execution passes all 55 interface tests. The preceding scoped
execution also passed those tests and the six local-source assembly controls
(61 passes). Production source remained unchanged throughout this test review.

Two consequential test gaps were demonstrated and corrected:

1. The initial 37 tests passed an intentionally broken native build that injected
   deferred baseflow only on the first call, dropping later admitted water.
   Adding per-day SOURCE observations, expected direct/deferred source rates and
   downstream Q equality makes this mutant fail 24 cases.
2. The expanded tests initially still passed a mutant that started the new
   baseflow loop at zero every day, adding new water to the inherited inlet
   endpoint. Explicit inlet/lateral endpoint carry assertions now reject this
   mutant in the intended 24 cases; the unchanged candidate passes all 55 tests.

The final parser checks finite values, source/outlet sample order, 145 samples
per channel/day and unique scalar records. First-day source checks include the
initial endpoint; later days check the inherited endpoint separately from new
positive-index source rates. Previously dormant driver configurations now
exercise legacy baseflow, positive side-hill runoff and positive side-impoundment
exclusion. These controls close the portable coverage findings for this change.

The q0-only regression seeds an admissible small outlet state before the native
recurrence, then lets actual routing and clipping run. Positive-time accepted
outlet rates become zero; the retained endpoint must still contribute `dt*q0/2`
and define the daily peak. Two independent mutants that omit the volume endpoint
or omit the peak endpoint each fail the corresponding assertion. This is causal
coverage of the shared MC publication/metadata branch, not general clipping
closure. Driver replacements and source tap anchors now have count guards.

The promoted local-source tests deliberately return after source assembly;
removing their expected-failure markers does not certify solver consumption or
signed-loss closure. Their names and package disposition retain that boundary.
Positional metadata fields and numeric scenario IDs remain minor readability
debt; named fields/IDs would ease future additions but are not a blocker.

Final reviewed test SHA256:
`7644407d521c67156273eb5b6f5f268be8e2ab6c9e0c222fef89bc7693b44297`.
Driver SHA256:
`87b62b67e4e572c59b7b860db3720cdc706ab6c06e712467a6b3ddf806d1ffa1`.
Mutation snapshots, manifests and logs are retained under
`/workdir/watershed-physical-water-repair-20261021/mc-interface-portable-qa-v1/`
through `mc-interface-portable-qa-v3/`; the final `review-receipt.json` pins all
reviewed files and log hashes (SHA256
`c4d45e8efba883e577d81ba28b968c0b0014518563b21378e604b4aa08951f58`).
No additional production/test edits are requested by this review. Full-package
source/exchange acceptance remains open.

## Retained evidence

Root: `/workdir/watershed-physical-water-repair-20261021/mc-interface-qa-v2/`.

| Artifact | SHA256 |
| --- | --- |
| `run_review.py` | `7c3a371aa1fcc42577ea3b6177ec6c1c8d279fb57f5e6e94eee4bbd2afe46b72` |
| `validate.py` | `fd47ab8a9c61bd0b277af7f6b1952de4f1422863a9ff08678c004b211d170f5c` |
| `assertion-receipt.json` | `3a42436a9a67e9c0ef3444c1d5d5ebddc7b6e52cbaea60e2dd378d92cb5f3d24` |
| `observations.json` | `faf37c6fce8edc32228b4c219a6ec11ca4dde3d16314ec9a78de09d9e5b86321` |
| `checkpoint/manifest.json` | `420c126c622cf574282b2631d84f82480c4c1a191246d2bbd88cd30c8a16fb44` |
| `candidate/manifest.json` | `d1b5388568f843da4c29ad0b27f6879a1ebab3447c64de218bfa22fbe99bda87` |

`profile-parity-receipt.json` retains the additional 54 exact comparisons under
the candidate capacity profile, with all source/include/binary provenance.
