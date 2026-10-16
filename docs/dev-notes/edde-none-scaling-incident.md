# EDDE unset precipitation scaling failure

## Evidence and scope

On 2026-10-16 at 17:50 UTC, read-only inspection on `wepp1` confirmed job
`aa788e34-a9ed-49e1-a45a-00bc54b9850e` failed for `forty-seven-medic`.
`wctl run-python` fetched the canonical RQ traceback and loaded the run's
Climate state: scaling mode and scalar factor were both `None`, with EDDE
WRF-MPI/SSP3-7.0 selected for 2025–2099. The host run directory exists.

This is a conformance fix under the unchanged
[EDDE contract](../schemas/edde-v2-weppcloud-contract.md#acquisition-eligibility-and-execution):
existing unscaled behavior must remain supported. The input snapshot called
`int(None)`; after that boundary, the scaling dispatcher would incorrectly
attempt scalar scaling with an unset factor. Both corrections are limited to
the EDDE builder. Saved settings, schemas, scaling formulas and defaults stay
unchanged. No production deployment or job retry has been performed.

## Regression plan and state coverage

Exercise stored `None` and explicit `NoScaling` through real CLI generation,
publication and NoDb reload, with remote acquisition fixtures. Verify full-year
dates, final file hash, unscaled filename and unchanged saved scaling mode.
Absent mode uses the existing Climate getter's `NoScaling`; present unset state
is `None`. Populated Scalar/Monthlies/Spatial handling remains unchanged;
unsupported AnnualMonthlies and malformed selections retain existing validation.
The map signature is needed only for Spatial mode. Preserve raw captured inputs
for the existing finalization comparison, rather than normalizing saved state.

Production recovery requires rollout of the reviewed patch, a targeted climate
retry, and generated CLI/provenance readback. The fixture test does not establish
successful acquisition or completion of the production run's 75-year request.

## Validation and review

The new `None` regression reproduced the exact `int(None)` failure before the
patch. After the two-line correction, `wctl run-pytest
tests/nodb/test_climate_edde_build.py --maxfail=1` passed all 20 tests, including
native generation, publication and file readback. Documentation lint and
changed-file broad-exception enforcement passed. Independent correctness review
found no blocking issues; production acquisition remains outside fixture proof.
All four inspected production services (`rq-worker`, `rq-worker-batch`,
`rq-engine`, `weppcloud`) were running. The broad command
`wctl run-pytest tests --maxfail=1` collected 11,019 tests; that run was interrupted
to restart against the subsequently requested new-project default change. Its
log is `/tmp/edde-none-scaling-pytest.log`; the replacement run's log is
`/tmp/climate-default-full.log`. Neither is a claimed passing gate. The combined
focused validation now passes 287 tests, including explicit None/NoScaling
precipitation equality.
