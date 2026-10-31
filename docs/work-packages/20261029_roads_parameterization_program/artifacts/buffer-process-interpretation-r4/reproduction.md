# Reproduce the observation analysis

This packet contains original analysis code and numerical evidence. It does not
contain the private native observer patch or authorize a new native execution.
The observed binary and complete source/build/run provenance are retained in the
[observation archive](../revision4-buffer-process-observation-retention.json).
Restore that archive and the accepted event ledger at their declared paths before
replaying. The unchanged reference inputs/outputs and installed reader packages
must remain available; missing dependencies fail explicitly.

Use the repository `.venv` and execute from `/workdir/wepppy`. The scripts derive
their layout from their file location, so do not run the copies directly from
this documentation directory. The following fail-fast subshell creates fresh
siblings under the ignored research parent. Existing destinations abort the
entire block. Choose new suffixes for another attempt; never overwrite a retained
attempt.

```bash
(
set -e
cd /workdir/wepppy
packet="$PWD/docs/work-packages/20261029_roads_parameterization_program/artifacts/buffer-process-interpretation-r4"
research="$PWD/out/roads-parameterization-program-20261031"
replay="$research/buffer-process-observation-r4-replay-001"
summary_replay="$research/buffer-process-interpretation-r4-replay-001"
mkdir "$replay"
mkdir "$summary_replay"
mkdir "$replay/analysis-o3"
ln -s "$research/buffer-process-observation-r4/observer-o3" "$replay/observer-o3"
ln -s "$research/buffer-process-observation-r4/seeds.json" "$replay/seeds.json"
cp "$packet/analyze_observations.py" "$replay/analysis-o3/analyze_observations.py"
.venv/bin/python "$replay/analysis-o3/analyze_observations.py" declare
.venv/bin/python "$replay/analysis-o3/analyze_observations.py" analyze
.venv/bin/python - "$replay" "$research" <<'PY'
import json
import sys
from pathlib import Path
fresh, research = map(Path, sys.argv[1:])
old = research / 'buffer-process-observation-r4/analysis-o3/results.json'
assert json.loads((fresh/'analysis-o3/results.json').read_text()) == json.loads(old.read_text())
PY
cp "$packet/summarize_process.py" "$summary_replay/summarize_process.py"
cp "$packet/plot_process.py" "$summary_replay/plot_process.py"
.venv/bin/python "$summary_replay/summarize_process.py"
.venv/bin/python "$summary_replay/plot_process.py"
.venv/bin/python - "$summary_replay" "$packet" <<'PY'
import json
import sys
from pathlib import Path
fresh, packet = map(Path, sys.argv[1:])
for name in ('paired-target-table.json', 'hourly-return-reconciliation.json'):
    actual = json.loads((fresh/name).read_text())
    expected = json.loads((packet/name).read_text())
    if name == 'hourly-return-reconciliation.json':
        actual.pop('summary_declaration_sha256')
        expected.pop('summary_declaration_sha256')
    assert actual == expected, name
PY
)
```

The summary script intentionally reads the original retained analysis after the
fresh analysis has been checked for exact logical equality. Each replay creates
new declarations bound to its actual script paths; those declaration hashes
will differ. Figure metadata may differ on regeneration; the paired numerical
points and plotted fields are bound by `figure-receipt.json`.

`analysis-declaration.json` preserves the executed analysis contract;
`summary-declaration.json` preserves the later descriptive summary contract.
The [publication manifest](publication-manifest.json) binds the exact public
packet and raw receipts. Independent [runtime](../buffer-process-observation-r4-o3-independent-full-readback.json),
[scientific](../buffer-process-observation-r4-o3-independent-scientific-review.md)
and [implementation](../buffer-process-observation-r4-implementation-final-readback.json)
evidence remains separate. Interpretation accepts this bounded observation
dataset only; it does not accept parameter defaults or a proposed intervention.
