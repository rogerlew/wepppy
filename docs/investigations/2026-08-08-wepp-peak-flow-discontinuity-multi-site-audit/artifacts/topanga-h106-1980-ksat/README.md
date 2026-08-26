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
WEPP_GATE21_OBSERVER_BINARY=/path/to/wepp_hill \
WEPP_GATE21_REPLAY_BINARY=/path/to/peak_replay \
docs/investigations/2026-08-08-wepp-peak-flow-discontinuity-multi-site-audit/artifacts/topanga-h106-1980-ksat/run-and-check.sh
```

The checker verifies both executable hashes, proves the two input trees differ
only by the intended Ksat token, compares active and inactive tracing for both
45-year histories, validates immutable packets, runs both replay families in a
separate process, checks full-precision expected values, reproduces the 1986
anomalies, and runs the inactive control.

## Provenance

- Source project: `/wc1/runs/ha/hand-to-mouth-drought`
- Observer source: pushed WEPP-Forest branch
  `feature/peakflow-phase1-observer` at `ea25ad79`
- Binary SHA-256:
  `2ec15778df957f909da383df9e3e0c9b516688d367c11f0109c6012387c0731f`
- Binary source commit: `ea25ad79ef7dab20206bca095b2958786f5ae317`
- Reproducibility level: internal; the binary source repository is restricted.

`expected-event.json` pins the full-precision packet hashes and both replay
families. Full observational packets and process-isolated replay reports are stored in the
[Phase 1 work-package artifacts](../../../../work-packages/20260808_peakflow_phase1/artifacts/).
