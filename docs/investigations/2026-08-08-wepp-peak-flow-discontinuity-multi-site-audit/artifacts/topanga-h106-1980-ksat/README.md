# Topanga Hill 106 1980 Ksat Fixture

This compact fixture reconstructs the February 14, 1980 Ksat mutation used to
identify WEPP's daily surface-return timing defect. Both lanes use identical
Hill 106 inputs except for first-horizon Ksat: `20 mm/h` in the baseline and
`35 mm/h` in the mutant.

A third lane changes only the version-9002 `ksatfac` token from `1.3` to `9.3`.
WEPP produces byte-identical canonical outputs, making it the Phase 1 inactive-
parameter negative control.

The accepted event also requires restrictive-layer record
`1 10 0.0000108`. The currently synchronized Topanga project contains a later
no-restrictive-layer experiment and therefore is not the fixture authority.

## Run

From the WEPPpy repository root:

```bash
docs/investigations/2026-08-08-wepp-peak-flow-discontinuity-multi-site-audit/artifacts/topanga-h106-1980-ksat/run-and-check.sh
```

The checker verifies the executable hash, proves the two input trees differ by
only the intended Ksat token, runs both complete 45-year histories in a
temporary directory, and checks the February 14, 1980 outputs.

Run the negative control separately:

```bash
python tools/peakflow_phase1_negative_control.py \
  docs/investigations/2026-08-08-wepp-peak-flow-discontinuity-multi-site-audit/artifacts/topanga-h106-1980-ksat \
  --binary wepp_runner/bin/wepp_260803
```

## Provenance

- Source project: `/wc1/runs/ha/hand-to-mouth-drought`
- Binary: `wepp_260803`
- Binary SHA-256:
  `4a5158e224c175ac06c760f1006cc19f7691a9bd28911d94788af2622ba178a5`
- Binary source commit: `f24c957e3633898e0fd4cbbea5ae08c781f29dba`
- Reproducibility level: internal; the binary source repository is restricted.

`expected-event.json` separates published WEPP output from internal operands
reported by the prior forensic trace. Full-precision observational packets and
process-isolated replay reports are stored in the
[Phase 1 work-package artifacts](../../../../work-packages/20260808_peakflow_phase1/artifacts/).
