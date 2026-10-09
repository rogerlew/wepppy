# Tenderfoot observed-flow calibration trials

Status: Blocked on fork-worker configuration, 2026-10-08 (UTC).

## Purpose and scope

Diagnose the large streamflow deficit in the public openwepp.org run `cultivated-ubiquity`, then run a bounded ET sensitivity experiment on isolated forks. Compare forest basal crop coefficients (`kcb`) 0.80 and 0.65 with the existing 0.95 baseline. This does not select a final calibration, change application defaults, or overwrite the baseline. Further forcing, snow, storage, historical-treatment, and independent-year validation remain necessary.

The user identified the run and provided a local PAT path for operations. Credentials stay outside the repository. Use rq-engine discovery/fork/run APIs, the existing disturbed lookup editor with CSRF and version checks, and read-only filesystem inspection on `hpc`. No new dependency, service, privilege, deployment, or parameter-control mechanism is permitted. Security impact: low; existing authorization boundaries are retained, with no security implementation change requiring a dedicated security review.

## Evidence and acceptance

Baseline diagnostics are under `papers/2026-weppcloud-scenarios-and-contrasts/data/tenderfoot-experimental/calibration/cultivated-ubiquity/`. Acceptance requires two completed isolated trials, exact prepared coefficient readback, unchanged climate/soil/management inputs where applicable, fresh outlet and water-balance outputs, matching observation dates, and a documented comparison. A failed or unchanged trial is evidence to retain, not success. Record any selected parameterization in an ADR before merging or promoting a calibration.

See [active plan](prompts/active/tenderfoot_calibration_execplan.md) and [tracker](tracker.md).

Both fork jobs failed while importing the optional Discord client because its `.bot_token` file is absent in the worker. Neither destination directory exists. Baseline scientific metadata, prepared PMET inputs, and observations remain byte-identical to the retained snapshot. The user clarified that Discord must not be a hard requirement. A bounded import conformance fix now mirrors core WEPP's existing missing/unreadable-credential handling in four RQ modules; see [repair record](artifacts/20261008_discord_import_conformance.md). Deploy and verify that fix through the established cluster workflow before retrying; no deployment change has been attempted here.
