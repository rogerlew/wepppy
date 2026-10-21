# Observation design and validity

The baseline is the captured native source; the candidate adds observations in
`src/wshpas.f90`, `src/wshred.for`, and precision for new tags only in
`src/wepp_observe.for`. No model arithmetic, state assignments, thresholds,
solver order or scientific formats change. Existing `wepp_observe.on` enables
the observations. `wepp_observe_frost.on` must be absent because it filters them.

| Tag | Phase | v1 | v2 | Identity |
| --- | --- | --- | --- | --- |
| WCL_RAW_Q | Before PASS filtering | terminal runoff, m | terminal runoff volume, m3 | e=hill, c=terminal OFE |
| WCL_RAW_L | Before PASS filtering | lateral depth, m | tile depth, m | e=hill, c=terminal OFE |
| WCL_AREA | Before PASS filtering | terminal length, m | terminal width, m | e=hill, c=terminal OFE |
| WCL_GW | Before PASS filtering | baseflow, m3 | deep seepage, m3 | e=hill, c=terminal OFE |
| WCL_SELECTED | Before binary capture | lateral argument, m3 | tile argument, m3 | e=hill, c=terminal OFE, s=event enum |
| WCL_READ_Q | After successful actual reader | runoff, m | runoff volume, m3 | e=reader hillslope index |
| WCL_READ_L | After successful actual reader | lateral depth, m | lateral volume, m3 | e=reader hillslope index |
| WCL_READ_T | After successful actual reader | tile depth, m | tile volume, m3 | e=reader hillslope index |
| WCL_READ_G | After successful actual reader | baseflow, m3 | seepage, m3 | e=reader hillslope index |

All observations include calendar year and Julian day. Hillslope standalone
processes can use hill index 1; the run card/PASS filename supplies project hill
identity. Real-project logs are separated by process/card. `WCL_SELECTED` is
explicitly **not** retained payload: event enum 0 can discard nonzero lateral
arguments. Read the actual `.hbp` with the existing native interchange reader,
join the event enum, then compare loaded values. `WCL_READ_L` precedes tile
addition; `WCL_READ_T` remains a separate transfer at this boundary.

Existing `WB33_M1A_BAL_DIAG` and `WB33_M7_PUBLISH_TRACE` expose channel snapshots
and publication terms, with paths set inside each attempt. They have independent
environment switches; all are off in baseline/candidate-off and on in candidate-on.
They cover configured monitored channels, not necessarily every channel.

New WCL formatting uses 16 decimal places in scientific notation to expose
stored default-real values; other tags retain their existing format. Diagnostic
output precision does not change simulation precision. PASS volume quantization
is 1e-9 m3 (`hillslope_binary_pass_writer.f90`); reader arrays are default real.
Writer/payload/readback comparisons therefore allow half a quantization unit
plus one single-precision epsilon times magnitude. Area-product checks use
the producer's single-precision multiplication order, with four epsilon bound.

## Validation and retention

Baseline and candidate-off completed five 44-year cases with identical hashes
for every file in their scientific output directories. Observation-on comparison,
day cardinality, event joins, controls, and runtime/log-size evidence are separate
gates. Channel outputs in `runs/` must also be compared; output-directory parity
alone does not cover those files.

The first NFS observation attempt was interrupted because per-record open/close
latency dominated runtime. It remains under the original holdout with
`interruption.json`. Complete observation attempts use
`/workdir/watershed-channel-routing-closure-20261021/`; baseline sources and the
supported full-project fork remain under the `/wc1/holdouts/` provenance root.
Both roots are retained, visible investigation artifacts.

Native primary correctness and secondary QA reviews found no source blockers.
Fortitude and scoped whitespace checks passed. Both reviews explicitly withheld
runtime acceptance pending generated evidence. Native source-header spec links
were already dangling (`docs/specs/source` absent); this document supplies the
new observation contract without asserting that the old routine specs exist.
