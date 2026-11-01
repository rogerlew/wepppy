# Reproduce the compact localization readback

This packet contains original source-free analysis and bounded observations.
It does not contain the legacy native implementation, native patches, input decks
or full daily state traces. The retained private roots and archive receipts supply
those dependencies to authorized reviewers.

The numerical source is the independently accepted
[full readback](../buffer-roughness-coupling-localization-r4-independent-full-readback.json).
The summarizer first rehashes its bound evidence, then refuses an existing output
directory. It invokes no native model and changes no reference artifact.

From the WEPPpy checkout, use a fresh destination:

```bash
(
    set -e
    packet=docs/work-packages/20261029_roads_parameterization_program/artifacts/buffer-roughness-coupling-localization-r4
    review=docs/work-packages/20261029_roads_parameterization_program/artifacts/buffer-roughness-coupling-localization-r4-independent-full-readback.json
    replay=out/roads-parameterization-program-20261031/localization-summary-replay
    .venv/bin/python "$packet/summarize_localization.py" --review "$review" --output "$replay"
    cmp "$packet/paired-observations.md" "$replay/paired-observations.md"
)
```

The summary values and table reproduce exactly. The declaration includes the
actual script path, so its hash and the summary's `declaration_sha256` change
when the identical script is run from another location; compare summary fields
apart from that provenance field. Do not copy an old declaration into a new run.

The four-run native experiment remains governed by its immutable
[localization plan](../buffer-roughness-coupling-localization-r4-plan.md) and
private exact execution declaration. Public build/run reviews bind the private
source map, patch, objects, toolchain, inputs and outputs. Rebuilding or rerunning
the native observer requires those exact retained inputs and the declared gates;
this summary command is not a substitute for them.
