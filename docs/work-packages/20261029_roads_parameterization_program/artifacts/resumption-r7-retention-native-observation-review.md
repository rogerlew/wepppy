# Bounded retention trial: installed native observation review

**Verdict: the existing marker supports the selected initialized-FC/UL evidence design without native source changes or a build.** The selected design is eight ordinary full-period arms plus eight exact observer replicas: B2/B3/B4/B5, each default/optional policy. Require a separate successful preparation/companion gate and a frozen runner declaration before any model call. This is design review, not execution approval or outcome acceptance.

## What the existing hook establishes

The selected r7 source is `e0abe0581f77c6f66917e90daf8f8f429e9315c8`. The reviewed source units match that revision; the later repository HEAD does not change them. In `watbal.for:253–255`, `ui_run=1` selects `watbal_hourly`. The initialization branch in `watbal_hourly.for:267–317` computes, for each internal layer `i` of OFE `iplane`:

- `FC = dg × (theta_fc − theta_dry)` and `UL = dg × (porosity − theta_dry)`, in meters of water depth.
- `WBH_HK_FCUL`: actual initialized `FC` in `v1`, actual `UL` in `v2`.
- `WBH_HK_RATIO`: actual pre-assignment `FC/UL` in `v1`, or the existing `−1` sentinel if `UL <= 0`.
- The next statements assign `HK = −2.655/log10(ratio)` when the ratio is positive; the existing nonpositive branch assigns zero and emits `WBH_G_HKDOM`.

Trace fields are `e=iplane`, `c=0`, and `s=i`. Initialization dates may be `y=0,d=0`; they are not simulation daily-calendar rows. `contin.for:487–514` establishes the initialization call and then changes `iflag` to one. Require the expected initialization inventory per OFE/internal layer; do not count arbitrary later lines as replacement evidence for missing initialization.

The hook does **not** emit stored HK, volumetric theta_fc/WP individually, layer thickness/depth, POR separately, or direct PERC/PURK operand values. `perc.for:133–138` uses HK in the conditional `stz ** hk(k1,iplane)` expression, but has no ordinary trace of that execution. Therefore an HK value derived from the printed ratio is explicitly a **source-derived estimate**, not an observed stored coefficient or proof that the power branch executed. The same limitation applies to attributing an output change uniquely to drainage, ET, a guard, or a particular layer.

Actual changed initialized FC/UL can demonstrate that the treatment reaches native initialization. A paired ordinary-output response can establish a response under the matched context. Neither establishes whole-system water closure, actual pore capacity, unique branch causality, or physical validity beyond the admitted checks. Native domain/guard evidence remains subject to the [whole-soil contract](../../../schemas/whole-soil-water-capacity-contract.md#native-consumer-domains); no new clamp or tolerance is introduced.

## Native layer and precision requirements

The native layer index is not the serialized horizon index. `input.for:703–930` remaps support to the existing 200 mm grid, and `tilage.for:604–668` constructs two tillage layers and the remaining lower layers. Bind the prepared soil, management/tillage settings, role/OFE order, and source-derived mapping before labeling any trace row “deeper than 200 mm.” Preserve any mapping uncertainty explicitly. The trace alone cannot supply the missing depth coordinate.

The logger prints `1pe12.4`, five significant decimal digits. Retain original tokens and their printed precision. Compare expected native values at this formatting boundary; do not invent a fitted numerical tolerance or treat the rounded tokens as recoverable exact binary32 state. A smaller-than-print-resolution difference is not an observed change. When FC and WP both change, examine FC **and** UL/ratio: their dry-reference offsets can change together, so a source FC change does not guarantee a detectable FC-depth change. If the required initialized response is absent, report that result without tuning it into existence.

## Selected marker, staging and execution protocol

1. Preserve the four existing case identities and both freshly prepared policies. Freeze exact native/model/auxiliary inputs, all source/treatment/stack/stage companions, role mappings, producer/helper hashes, runtime identity, and the selected r7 executable. The retained engine lane uses watershed executable SHA256 `4a9da3980d1a9249e566626c01de920de7dba5088ec25324dc1c6dd6eff8c825` in hillslope mode; do not silently substitute the distinct hillslope executable.
2. Copy each complete prepared per-case root, including `soils/` and the final stage under `runs/`, intact into the predeclared service-local `/tmp/roads-retention-native-v1` layout. This preserves relative companion-parent resolution. Validate all recursive companions again at their actual execution paths. Stage the unchanged non-soil model inputs and auxiliary files there. Reject unresolved parents, wrong hashes, escaping aliases, inherited output files, or an existing observer log. Do not symlink the writable observer log to source/evidence directories.
3. Create ordinary and observed replicas with the same relative layout, binary, mode, calendar, management, soils, companion provenance, sidecars and auxiliary inputs. The **only deliberate marker difference** is a new empty regular `wepp_observe.on` in the observed process working directory. Its bytes are part of the declared inventory. `wepp_observe_frost.on` must be absent: that filter suppresses both desired WBH tags. Do not add RAP/cover/simfire or other science/control markers to obtain these observations.
4. Execute all eight ordinary histories and their eight exact full-period observed replicas, with the same service UID/GID and local storage treatment. Freeze concurrency and preserve the existing 300-second per-call timeout. A timeout, nonzero status, incomplete native success/calendar, or failed artifact audit remains a failed retained attempt. Do not shorten a history, truncate its trace, toggle marker files mid-run, or silently retry with different observation settings.
5. Require **eight exact on/off parity pairs** across all seven ordinary outputs: 56 byte-equality comparisons, with hashes of all 112 actual output files. Verify inputs before and after execution. Run the established physical/calendar/strict particle checks on the actual outputs; unchanged ordinary-byte parity does not excuse a failed scientific predicate. No cross-case or same-soil-signature substitution supplies another arm's initialization evidence.
6. Parse each full trace by tag and OFE/layer key; retain raw logs, hash, byte/line counts, exact selected rows and guard counts. Require the expected FCUL/RATIO pair for every declared internal layer of every OFE, finite required values, and the expected hourly branch. Fail the observation claim on missing, malformed, duplicate/unexplained initialization records, wrong owner, or an unresolved mapping. Keep expected native sentinels/guard events visible instead of discarding them.
7. Archive each completed or failed local attempt into the fresh `/wc1` evidence root with source/destination inventories and checked hashes, preserving relative roots and provenance. Preserve the original local execution paths in the receipt; the archived path is not the execution mount. Do not claim production-mount parity from these local diagnostic runs. Independent readback follows, without rebuilding or instrumenting the native source.

The observer uses a cached enable flag at its first invocation and opens/appends/closes `wepp_observe.log` for each emitted line (`wepp_observe.for:22–45`). Removing `wepp_observe.on` after initialization would not disable the cached flag. The frost filter is not a general FC-only filter. Consequently full-period marker runs produce additional diagnostics beyond the initialization rows; retaining only selected FC lines is not an execution-volume reduction.

## Prior parity and runtime evidence

The installed-marker evidence is real but bounded. I independently rehashed all **56 ordinary outputs** in `/wc1/holdouts/mipa-native-r7-20261103/histories-final-v1`, verified the four daily/hourly and transformed/observed-cover on/off pairs, and confirmed that each input pair differs only by `wepp_observe.on`. All seven outputs match within each pair. That receipt has SHA256 `5b9e5395c818756d61ac6d28369bab3382950be2145e8fab0a309bc76f0e8720` and uses hillslope binary `210d48da09ff60707ba2404dd32af1f0a74e95437d2cb900c5408121141a1936`. It is supporting precedent, not an automatic neutrality certificate for the new watershed-binary execution and new soils.

Those three-OFE, 16-year traces are approximately 7.9–8.3 MB each. One retained hourly trace has 100,233 total lines but only 30 FCUL/RATIO rows. The configured observer review additionally records 1/11/2-OFE, 35-year local probes with 24 exact ordinary outputs; their general observer logs are approximately 11.3/124.3/24.4 MB. The earlier dense NFS observer attempt exceeded 300 seconds and remains a failure, while local replicas succeeded. These are observed sizes, not a guaranteed bound for the new climates or branch activity.

Use local disk for the already selected normal/observed layout, check available space, retain elapsed time and output/trace sizes per call, and archive before cleanup. Dense open/append/close traffic and additional snow/ET/event tags are the principal runtime risks. No source modification, filtering hack, changed physics flag, or increased timeout is authorized by this review.

## Source bindings and residual limits

- `watbal_hourly.for`: `3b1ef717359c5c92475ddc7396ed68533237274d9433f83fb7d89dff69c27162`.
- `wepp_observe.for`: `cf09555683b7ca16571fffccc5fa12f8e90bff861c2152b4dfc6c47db4473ba1`.
- `perc.for`: `856ce371bcf3f0691cae33ca8f70987ad193a8df96f60a82635e0e9fb4525ced`.
- `purk.for`: `0ec659960ad7a13bd4ca70866708f435322ba348997dd2c5ec863450b7f50705`.
- Configured observer receipt: `1af2a13e20d9c496536824a950d6108a10f07dd68aaf89b96f8508d35286a728`; its independent review is [configured artifact QA](../../20261102_mofe_input_producer_audit/artifacts/mipa03_configured_artifact_qa.md#isolated-configured-observer-probes).

All eight observed replicas are required by the selected claim; the earlier possible two-replica witness was not selected. Normal/observer exact parity must be established anew. Direct dynamic HK/PERC observation, accepted root withdrawal, full water/energy closure and real pore-capacity validation remain outside this hook's evidence. This review made no model call, native build, production edit or change to a frozen artifact.
