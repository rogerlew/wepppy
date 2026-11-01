# Implementation design review: mapping history ownership

Disposition: **design accepted with the execution prerequisites below; execution approval withheld until the actual instrumenter and runner are reviewed.** This reviewer performed read-only source/provenance checks. No build, native invocation, old-artifact write or production edit occurred.

## Verified substrate and panel

All 978 members of the retained storage-observer build match its inventory. Build receipt SHA-256 is `ab8c57fc6a1786864cc581907e40aaa11673fe15cc925cad44b04786cbe27036`; executable SHA-256 is `5f6bcebac1c82111a6a7c9685cd0d2a04f2e6c3066a3637e533a1a8054ff38b1`. All five bound runtime-library hashes also match. Verified the complete 16-input inventory for each prior SIFT zero/normal/high history; each soil file declares KSFLAG 0. Preserve original files, hashes, sizes and modification times.

The proposed three original controls and three separately labeled KSFLAG-1 diagnostics are a bounded panel. Each new observer input set needs a fresh pinned-binary baseline with byte-identical seven ordinary outputs, full calendar coverage and retained process status. KSFLAG also affects conductivity, so enabled/disabled histories are not isolated frost treatments. Declare the exact invocation budget, including both baseline/observer histories and 29 synthetic observer controls; six input configurations do not mean six total invocations.

## Exact source and private build

Pinned FRWATC, FROSTN and WINTER bytes equal the current canonical versions inspected here. Pinned CONTIN, WATBAL and WATBAL_HOURLY differ because of prior observer instrumentation. Bind the pinned files and exact unique anchors for all edits; canonical line numbers cannot substitute for their identities. Source identities include:

- FRWATC: `a834dbe62497989e8f99945acc880cdb31ced4ccc88d31f215c91738a0a0f1c1`.
- FROSTN: `cdf107e59cd9a24e3e1898deb1f0791925c8a14de8fc3638e966a5f19628c5df`.
- WINTER: `6dca46e762611ddd93e030d7fcc619af92922d614a4ddc1c44576b90ee9d86ff`.
- Pinned CONTIN: `78adeaed5495910a61bfc06dc3f91481b51af2d8c6e95b6044b713e7393ab069`.
- Pinned WATBAL: `f1335d415e4c727a6b23fe542b9d4974f729ad956d7b87edd2a84268c8285ce8`.
- Pinned WATBAL_HOURLY: `dbfeed35c303c54037d130bc62852b59fcd76946e62addc30ff5ed5910abf986`.

Copy the entire build, including sibling fpm-src and include variants, into a fresh private destination without shared writable hard links. Run any cleanup/rebuild only there. Preserve the pinned makefile's compiler/linker, optimization, COMMON alignment, deterministic/portable math dependencies and fixed-form 72-column profile. The broad campaign must not silently inherit the different standalone scalar flags. New instrumentation must fit continuation/column rules and be present in the linked object inventory. Retain complete before/after source, includes, objects, executable, compiler and runtime provenance; retain failed attempts. No source excerpt or native patch belongs in public artifacts.

## Guards, initialization and clocks

CONTIN has a daily gate before WINTER. WINTER then evaluates its weather/frost gate and KSFLAG before actually calling FROSTN. Its existing `wfr_calls` increments before the KSFLAG test and therefore cannot prove an actual frost call. Record daily eligibility, hourly eligibility, runtime KSFLAG and actual call counts separately. Input KSFLAG alone is insufficient because SCON can set it to 1 in its model-conductivity cropland path.

FROSTN establishes NFINE and may rebuild fine state through its no-frost or initial-frost branches. Direction1 is an hour-1 elseif reached only after those branches are bypassed. Direction0 occurs after phase-change/distribution calls at hour24 or thaw completion; it is not necessarily once per day. Emit initialization-path events and real call-site context, including thaw flag and hour. FRWATC itself has no hour argument: supply observation-only context from callers without changing native COMMON layouts or algorithm arguments. Synthetic direct calls need their own declared caller/clock, never a fictitious history hour.

Do not inspect fine arrays at arbitrary CONTIN/WINTER entry just because coarse water exists. NFINE is profile-wide, while fine stocks are OFE-indexed; previous-OFE geometry is not proof of current support validity. Use observer-only per-OFE initialization markers and explicit availability masks. At safe boundaries require valid NSL/NFINE and initialized active support. INIDAT initializes coarse frozen references/NWFRZZ/YST, but that is not initialization evidence for every fine-grid field. Pre-initialization events should emit only proven-safe operands and validity status. Do not change native state to make an observation safe.

## Event architecture and accounting

Use a fresh trace per process, an explicit run identity and monotone event/invocation sequence, with actual year/day/OFE/caller/hour/direction/stage. Bind each entry to exactly one exit, including no-layer/no-fine/zero-ST paths. Include declared counts and a process-end completeness marker so an empty or truncated trace cannot be reported as zero recurrence. Emit active coarse/fine geometry, dry reference, liquid, adjusted ice, YST, NWFRZZ, UL and SOILW at safe boundaries with round-trippable REAL precision.

Instrument branch decisions at their actual execution points rather than inferring all decisions from exit state. Cover thin-support and near-zero-DG skips; direction0 dry-floor/WLCK carry and NWFRZZ clearing; direction1 zero-ST, absolute-delta, frozen allocation/spare-space/remainder, total-unfrozen and per-fine support gates; SAXFC removal; volumetric-change gate; dry-floor/LACKW carry and unresolved carry at routine exit. Emit native locals only after their assignment on that path. A blanket entry/exit dump of VARWAT, VARSW, NWINC, SPCAV, WLCK or LACKW would read unavailable values on some paths; encode unavailable fields explicitly instead. Do not change native arithmetic or force additional evaluation of branch operands to populate diagnostics.

Follow mapping events through the immediate FROSTN/WINTER return and the next relevant hydrologic producer/consumer boundary, with explicit call identity. Existing daily SOIL/INFPAR precedes WINTER; later infiltration and WATBAL occur on different clocks. WATBAL dispatches to hourly behavior under UI_RUN, so label actual entry/exit and time-step context rather than treating every call as daily. Coarse-only consumer observations may be valid where a fine snapshot is unavailable. If intermediate mutation ownership is unobserved, retain that gap instead of attributing the whole interval to FRWATC.

Readers should independently reconstruct signed fine/coarse liquid, ice and total stock, actual ST-minus-YST request, geometry and SOILW discrepancy. Count disjoint mapping changes separately from representation mismatches carried into later observations. Do not sum repeated snapshots of one mismatch as repeated annual losses, or assign an unmeasured residual to runoff/ET. Multi-coarse-layer carry in histories must retain layer ordering and cross-layer carry context; the previous single-coarse-layer fixtures did not establish it.

## Required execution review

Review the actual instrumenter, trace schema, reader and runner before invocation. Require unique anchored edits, declared output destinations/units, safe observation initialization, complete source/runtime manifests, retained timeout/failure outcomes and no model-state writes by logging. All 29 committed synthetic controls must recover unchanged ordinary final states and the five known discrepancy signatures; positive controls are necessary before interpreting absent history events. Require exact seven-output parity separately for every accepted complete history. Meaningful reader controls must reject duplicate/missing support, invalid clocks, unmatched entry/exit, identity drift and truncated traces.

No execution PASS is granted by this design note. Failure to activate frost in the finite diagnostic panel is a retained result, not permission to tune climate, inputs or thresholds after observing outcomes. Any extension requires a revised declaration and independent review. Public conclusions must remain bounded to the observed inputs and ownership actually traced.
