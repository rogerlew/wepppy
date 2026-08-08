# Phase 1 Peak-Flow Audit Artifacts

> Evidence for Topanga Gates 0–2: versioned data contracts, observational
> tracing, process-isolated legacy solver replay, compact fixtures, and controls.

## Overview

These artifacts support an internal reproducibility claim for the pinned
WEPP-Forest source. No diagnostic executable is committed. The manifests record
the exact source, compiler, flags, and executable hashes; authorized developers
can rebuild them from the restricted source. The event packets and replay
reports are public, machine-readable evidence in this repository.

The observational executable invokes the production-selected peak method only
once. A marker file enables writes of immutable scalar and forcing data. Both
peak methods are then called by a standalone executable in a separate process,
so `HDRIVE` cannot overwrite COMMON-block state in the observational run.

## Evidence Map

| Artifact | Claim supported |
| --- | --- |
| `schemas/*.schema.json` | Gate 0 grains and field contracts are versioned |
| `observer-build-manifest.json` | Observational build provenance |
| `observer-parity-report.json` | All seven canonical outputs are byte-identical with tracing disabled |
| `event-packets/*.json` | Full-precision 1980 event operands and pre-/post-surplus forcing |
| `replay-build-manifest.json` | Standalone driver and linked legacy routines |
| `replay-reports/*.json` | Exact selected-method replay and separately labeled counterfactuals |
| `topanga-h106-1986-fixture-result.json` | Frozen canopy and ground-cover anomalies; mechanism unresolved |
| `negative-control-*.json` | A realized version-9002 Ksat-factor mutation has no output effect |

## Observational Build

The source transformation is hash-guarded and refuses any `irs.for` other than
the pinned acceptance version:

```bash
python tools/peakflow_phase1_instrument.py \
  /path/to/pinned/src/irs.for \
  /path/to/isolated-build/src/irs.for
make -C /path/to/isolated-build/src COMPILER=gfortran wepp_hill
```

Place an empty `peak_diag.on` beside the run file to enable `peak_diag.csv`.
Without that marker, the seven files under the fixture's `output/` directory
must match the reference hashes in `observer-parity-report.json` byte for byte.

## Standalone Replay

Compile `peak_replay_driver.for` with the exact pinned routines listed in
`replay-build-manifest.json`. Then create and replay a packet:

```bash
python tools/peakflow_phase1_replay.py packetize peak_diag.csv packet.json \
  --year 1980 --day 45 \
  --build-id wepp-f24c957e-phase1-observer \
  --event-id topanga-h106-1980-02-14-ksat20

python tools/peakflow_phase1_replay.py replay packet.json \
  --binary /path/to/peak_replay \
  --output replay.json
```

`legacy_input_replay` preserves WEPP's pre-surplus `remax` operand.
`harmonized_forcing_diagnostic` recomputes that summary from the same
post-surplus series supplied to `HDRIVE`. The latter is diagnostic and is not a
claim about legacy WEPP behavior.

## Acceptance Fixtures

Run the compact 1980 fixture, 1986 fixtures, and inactive control from the
repository root:

```bash
docs/investigations/2026-08-08-wepp-peak-flow-discontinuity-multi-site-audit/artifacts/topanga-h106-1980-ksat/run-and-check.sh

python tools/peakflow_phase1_1986_fixture.py \
  docs/investigations/2026-08-07-topanga-2025-fire-peak-flow-analysis/artifacts/openwepp-hill106-effective-duration-reproducer \
  --binary wepp_runner/bin/wepp_260803

python tools/peakflow_phase1_negative_control.py \
  docs/investigations/2026-08-08-wepp-peak-flow-discontinuity-multi-site-audit/artifacts/topanga-h106-1980-ksat \
  --binary wepp_runner/bin/wepp_260803
```

## Limits

- This package establishes internal, not public, source rebuildability.
- The 1980 surface-return timing mechanism is confirmed for the fixture event.
- The 1986 canopy and ground-cover jumps are reproduced, but their immediate
  internal transition remains unresolved.
- These artifacts do not authorize or estimate a Topanga-wide or cross-site
  anomaly frequency.

## Further Reading

- [Work-package overview](../package.md)
- [Completed execution record](../prompts/completed/phase1_execplan.md)
- [Multi-site audit protocol](../../../investigations/2026-08-08-wepp-peak-flow-discontinuity-multi-site-audit/README.md)
- [Stakeholder solver report](../../../investigations/2026-08-07-topanga-2025-fire-peak-flow-analysis/artifacts/wepp-peak-flow-solver-documentation-and-topanga-evidence.md)
