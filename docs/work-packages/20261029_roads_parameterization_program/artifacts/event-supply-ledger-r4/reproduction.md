# Reproducing the revision-4 paired ledger

The Python files in this directory are exact copies of the executed analysis
scripts. They derive their output root from their own location and the source
panel root from its parent. **Do not execute them directly in this artifact
directory.** Stage them into a new, empty sibling of the original ignored run
root; never reuse or overwrite an existing attempt.

The retained source is
`/workdir/wepppy/out/roads-parameterization-program-20261031/`, including all
116 `legacy-soil-anchors-r4` records, their matching U12 generated records,
original input/output files, exact dependency versions and the frozen native
writer provenance referenced by `declaration.json`. The source panel and
dependencies must be available. These scripts do not build or execute WEPP.
Missing or changed required inputs fail explicitly.

From `/workdir/wepppy`, choose a fresh destination name:

```bash
(
set -e
packet=docs/work-packages/20261029_roads_parameterization_program/artifacts/event-supply-ledger-r4
replay=out/roads-parameterization-program-20261031/event-supply-retention-r4-replay
mkdir "$replay"
cp "$packet/ledger.py" "$packet/summarize.py" "$packet/explore_hydrology.py" "$packet/plot_boundaries.py" "$replay/"
.venv/bin/python "$replay/ledger.py" declare
.venv/bin/python "$replay/ledger.py" preflight
.venv/bin/python "$packet/prepare_analysis.py" --root "$replay"
.venv/bin/python "$replay/ledger.py" run
.venv/bin/python "$replay/summarize.py"
.venv/bin/python "$replay/explore_hydrology.py"
.venv/bin/python "$replay/plot_boundaries.py"
.venv/bin/python "$packet/../review_event_supply_ledger_r4.py" --root "$replay" --output "$replay/independent-readback.json"
)
```

`prepare_analysis.py` creates a fresh pre-execution analysis declaration,
binding the newly staged script, declaration and preflight receipt. It retains
the comparison scope and explicitly corrects the original ranking wording to
three largest **signed daily** reported differences, including zeros. The
historical declaration remains immutable in this packet. Do not copy it
unchanged into a new run: its hashes bind the original execution.

The two actual preflights cover both ordinary and outsloped/unrutted emitted
width representations; declaration checks geometry for all 116 pairs. The run
converts the remaining 114 pairs with four workers. New Parquet metadata binds
the fresh declaration, so byte hashes can differ across staged roots even when
the accounting values match. Use numerical readback in addition to hashes.

The last command performs independent verification without importing the ledger
helpers. The subshell exits on a failed command; in particular, an existing
destination makes `mkdir` fail before any copying or analysis can overwrite it.

The original `verify_final.py` is a readback of the original frozen root and its
preserved figure-layout draft; it is included as evidence tooling, not required
for fresh-root generation. Original verification binds 541 dependencies, 116
case receipts, 232 source records, 928 parsed Parquets, 696 derived Parquets and
232 particle-audit receipts. Independent numerical evidence is linked from
[findings.md](findings.md).

The final figure is a layout-only publication derivative. All 43 case points
and the case-summary hash match the retained first-layout draft. Its PNG, SVG,
PDF and `figure-data.json` are bound in `manifest.json`. Exploration and
interpretation clarifications are separate from the frozen execution and
summary scripts; no changed model or audit threshold is hidden in reproduction.
