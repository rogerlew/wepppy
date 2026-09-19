# Forest failure disposition

Read-only triage on local `forest`, 2026-09-18 19:42 UTC. Parent job
`8c88742d-defd-4b3e-ac33-a3efd622dd42`; no retry, restart, output edits or
parameter changes during this investigation.

## Confirmed failures

| Scenario | Leaf job | Failed at UTC | Affected plot files | Asterisk rows |
| --- | --- | --- | --- | --- |
| uniform_low | `dc305ca7-64aa-4b9f-95b9-a61169ff52af` | 19:24:12 | 129 | 2822 |
| prescribed_fire | `e7fdd78b-b6ba-490e-aa1f-f243a4248519` | 19:37:59 | 3 | 56 |

Both canonical RQ tracebacks end in `Wepp.make_loss_grid`, called from
`wepp_run_service.py:325`, after the watershed execution stage:

    pyo3_runtime.PanicException: called `Result::unwrap()` on an `Err` value: ParseFloatError { kind: Invalid }

Artifacts under `/wc1/runs/ve/ventilated-gag/_pups/omni/scenarios/` confirm the
unparseable third column in `wepp/output/H*.plot.dat`. Examples:

    uniform_low/wepp/output/H10.plot.dat:205
        120.600     85.117 **********
    prescribed_fire/wepp/output/H195.plot.dat:405
        240.600     10.009 **********

Prescribed-fire affected files are H195, H341 and H343. Counts above were obtained
by scanning three-column data rows after the four-line header for asterisks in
column three. Moderate/high have zero such rows and their RQ leaves finished.
Both thinning leaves were still started; compilation/finalization remained
deferred at the status snapshot. Parent finished means dispatch completed,
not successful completion of the whole scenario batch.

## Cause and disposition

Confirmed application/model-output failure, not worker death or queue failure.
The Rust visualization reader at `/workdir/wepppyo3/wepp_viz/src/lib.rs`,
`read_plot_fn`, performs `values[2].parse().unwrap()` and panics on these tokens.
The local WEPP source `src/sedout.f90` writes plot values with `f10.3`; asterisk
fields are consistent with fixed-width numeric overflow. This is not merely
a map-reader concern: low-severity `H10.loss.dat` also has overflow fields in
average/max detachment and deposition and the slope profile. The plot jumps
from 0.644 kg/m2 at 120.0 m to overflow at 120.6 m, immediately beyond the
second 60 m OFE boundary. This is a diagnostic lead, not proof of its cause.

Disposition: **block full-model acceptance and numerical comparisons for these
two scenarios**. Retain existing artifacts. Do not replace asterisks with zero,
silently skip cells, disable required export, or blindly retry unchanged inputs.
The eligibility repair is not disproved by this traceback; neither is its
complete actual-project acceptance established. Low-severity construction does
not use the changed treatment candidate gate. Prescribed fire reached model
execution but its numerical output still requires investigation.

Next remediation should reproduce a representative affected hillslope in an
isolated workspace using the exact configured binary (`wepp_dcc52a6`, from
baseline state; verify executed provenance before reproduction). Inspect prepared
per-OFE management/soil transitions and profile calculations to distinguish
parameterization, model numerics and output formatting. Preserve full numerical
values with diagnostic output before deciding a remedy. Separately replace the
Rust panic with a contextual file/line/token error; that alone does not recover
lost values or make the scenario valid. Revalidate artifacts and then retry only
the affected workflow through supported orchestration after remediation.

This expands beyond the original candidate-selection repair into WEPP numerical
output and Rust visualization handling; implementation is not performed by this
disposition-only investigation.
