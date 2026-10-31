# Roads research code and evidence provenance

The new research verifiers, mathematical probes, replay/build orchestration and
plot helpers in this continuation were authored by Codex and independent Codex
review agents during the2026-10-31 Roads investigation. They are research tools,
not shipped model routines or claims of an independently implemented WEPP model.
The source relationships and numerical limitations are stated in each associated
experiment/review. Original helpers may call owned native interfaces; that does
not make surrounding legacy routines public.

The [disclosure review](roads-u12-disclosure-review.md) identifies eight mixed
legacy-context files. Their exact bytes are retained privately in the native
repository, with hashes and paths in [the private-tool receipt](private-research-tools.json).
The patch is absent from this public research set. Seven existing Python paths
now contain original source-free entry points that require the private tool
explicitly. This preserves frozen scientific-document links and import contracts
without publishing legacy source anchors. Historical instrumenter hashes refer
to the retained private bytes, not to these later entry points.

To use these entry points in the research environment, set:

```bash
export WEPP_NATIVE_RESEARCH_TOOLS=/workdir/wepppy/out/roads-parameterization-program-20261031/private-research-tools
export PYTHONPATH=/workdir/wepppy/docs/work-packages/20261029_roads_parameterization_program/artifacts
```

Run the documented commands from the active ablation plan. Missing private
implementation fails explicitly; no substitute model or fallback is provided.
Instrumenters generally require a fresh output directory. Do not rerun them over
retained evidence. The private fraction observer keeps an identical copy of its
original public replay dependency. Observation-only runs require exact ordinary
output parity. Certificate/audit tools and numerical receipts remain directly
usable without native source access when their retained inputs are available.

The input capsule retains its documented FSWEPP2 management, WEPPcloud/SSURGO
soil and CLIGEN benchmark origins. Figures are original numerical illustrations,
not source screenshots or field-calibration predictions. No full native source,
source-bearing archive or private instrumenter is a public report attachment.

The execution path above is an exact private mirror under the existing ignored
research output tree. Both host and weppcloud container can read that existing
bind mount; the native checkout itself is not mounted in weppcloud. Its hashes
match the canonical native copies. No new mount or runtime permission is added.
The original host-only path failed an explicit container import check; the
selected mirror closes that portability issue without hiding missing dependencies.

For container execution, explicitly forward both selected variables:

```bash
wctl exec -T -e WEPP_NATIVE_RESEARCH_TOOLS="$WEPP_NATIVE_RESEARCH_TOOLS" -e PYTHONPATH="$PYTHONPATH" weppcloud python -c 'import param_sign_ablation; assert param_sign_ablation.P.is_dir()'
```

This read-only import check passes in the canonical container. Use the same
explicit environment forwarding for the documented seeds phase.

## Versioned particle audit correction

The frozen `audit_particle_closure.py` is historical v1 evidence. Its whitespace
ELEMENT parsing is unsuitable when adjacent fixed-width duration/enrichment
fields fill their widths. Use `audit_particle_closure_v2.py` for new current-R4
three-OFE EVENT audits, with the retained adjacent-field regression in
`check_particle_audit_v2.py`. Numeric printing bounds and strict fraction
predicates are unchanged. The v2 scope requires all 26 current ELEMENT columns;
it does not silently infer older formats. Never rewrite frozen records or
acceptance hashes to substitute the newer audit; append a versioned verification.
See [the independent disposition](review-legacy-particle-disposition.md).

The new factorial fraction observer remains private under the ignored
`fraction-arithmetic-r4-new-event-v2` output root. Its public certificate and
disposition contain numerical observations and hashes, not native source.
The initial insufficient-observation attempt is retained separately.
