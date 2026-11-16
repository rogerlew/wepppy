# Independent correctness review: candidate implementation

Reviewer: Codex reviewer agent, independent of the implementer.
Date: 2026-11-16 (UTC).
Revision: `7755822d78f79a5830c0d85d1319dfe83c40568e` plus the uncommitted
candidate helper, logging, tests, documentation, and package artifacts.

## Verdict

No remaining medium/high implementation finding in the reviewed candidate.
**Forest acceptance is pending.** This review does not close the package or
ratify ADR-0143. Complete the dated review's runtime evidence matrix after the
fresh RQ replay and generated/consumed artifact checks.

## Findings

- **R1 — Medium, resolved in source:** the map-mode log rounded cell size with
  `%.2f` at `wepppy/rq/culvert_rq.py:281`, preventing the plan's required raw
  resolution evidence. The implementer changed that formatter to `%r`; review
  confirms the arguments, mapping, override precedence, and queue wiring are
  unchanged. Runtime readback of the raw Santee value remains pending.
- **R2 — Low, open documentation organization:** the new normative range text
  appears below `References` in the developer README and below `Open questions`
  in the integration spec. Move it beside the pruning table/model-parameter
  notes so readers can find the formula and provisional status together.

## Coverage and evidence inspected

The helper changes only the first inclusive boundary from 1.0 to named 1.5 m.
The effective-resolution formula, 4 m boundary, signature, missing/nonpositive
input handling, and payload override path are preserved. Repository search
finds one production consumer, `culvert_rq.py`, which passes raster pixel width
into the helper and applies explicit payload overrides afterward.

Focused regressions cover the observed 1.0000000000089009 m value, 1.3, 1.5,
1.51, 2.0, either side of 4.0, the exact 4.0 boundary, non-default threshold
scaling, and missing/zero thresholds. Existing tests cover missing resolution
and a larger threshold. Reviewed execution transcripts show six expected
pre-change failures, then 23 passing helper/orchestration tests and successful
stubtest. These are local regression evidence, not terrain calibration.

Independently reopened both disposable ZIPs and compared parsed feature
collections, model parameters, metadata counts, CRCs, and raster SHA-256 hashes.
`payload-review-semantic.json` records that both collections contain precisely
the original Point_ID 1040 feature; both rasters are byte-identical; threshold
100 is preserved; and no pruning override is present. Raster spatial semantics
still require the runtime readback specified by the plan.

The uncached SDA probe uses a new temporary SQLite database, real collection
synchronization/build, and native soil validation. Its inspected pre-restart
transcript reports component=2, horizon=4, fragment=2, texture=4, and a valid
soil for MUKEY 131939. Empty optional restriction rows are supported by the
existing collection API; empty component or horizon responses fail the probe.
The post-restart probe and admission timing remain pending.

## Residual risks and outstanding gates

- A third pass may still miss the twofold count target or remove valid drainage.
  Only the replay can resolve this; unit tests cannot ratify the 1.5 m heuristic.
- Explicit override and per-run full-stream fallback are unchanged. The focused
  suite does not independently establish all override/fallback variants; retain
  their disposition and inspect fallback activation during the replay.
- Nonpositive cell sizes and negative thresholds preserve existing branches but
  lack explicit new cases. This is a low coverage gap, not an observed regression.
- Required restart identity, RQ tree, generated/consumed raster semantics,
  channel/subcatchment counts, connected outlet, browse/download readback, and
  final ADR disposition remain open. Existing production batches are untouched.
