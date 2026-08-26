# Hill 106 WEPPcloud Fixture

This fixture is an unchanged, read-only snapshot of the Hill 106 inputs,
run-scoped sidecars, run log, and generated outputs from the two WEPPcloud
working copies used in W. Elliot's report.

## Provenance

- Retrieved: `2026-08-07` from production host `wepp1`.
- Undisturbed source:
  `/geodata/wc1/runs/po/positional-mink/wepp/{runs,output}`.
- Burned source:
  `/geodata/wc1/runs/ha/hand-to-mouth-drought/wepp/{runs,output}`.
- Production access was read only; no run state or source artifact was changed.

Each `runs/` directory contains the complete `p106` input set plus every
sidecar present that can alter this executable's hydrology:

- `wepp_ui.txt` selects the 24-step hourly seepage update;
- `pmetpara.txt` selects Penman-Monteith ET and supplies crop coefficients;
- `gwcoeff.txt` supplies WEPPcloud groundwater/baseflow coefficients;
- `snow.txt` supplies WEPPcloud snow calibration parameters.

The archived `p106.err` logs independently confirm both `wepp_ui.txt` and PMET
were active in the source runs: they contain `WEPP hourly water seepage update
set (UI code)` and `FAO Penman-Monteith ET Method Implemented`. They also end
with the successful hillslope-simulation marker.

`output/` contains every `H106.*.dat` target named by `p106.run`. These are
baseline evidence for replay comparisons, not expected Windows-WEPP outputs.
The fixture does not establish which sidecars were present in Elliot's Windows
working directory; that remains an experimental question.

`windows-reconstruction/burned-man-ballpark/` is derived evidence rather than
part of the production snapshot. It preserves the management sweep and closest
Windows replay used to reconstruct Elliot's burned Hill 106 water balance.

## Integrity

Run `sha256sum -c SHA256SUMS` from this directory to verify the snapshot.
