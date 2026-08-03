# Stevens Canyon Hillslope Synchronization Sensitivity

**Status:** Closed 2026-08-03
**Started:** 2026-08-03 16:48 UTC
**Security impact:** none

## Purpose

Test whether the year-34/day-203 undisturbed channel-flow inversion depends on
synchronized hillslope hydrographs. Produce reproducible scientific figures,
each with a Markdown sidecar, without changing production runs or the clean
`/workdir/wepp-forest_260430_baseline` source tree.

## Scope

The work uses unchanged undisturbed hillslope pass files, experimental
watershed-routing binaries, and selected reaches 169, 172, 173, and 193. It
tests contributor-indexed `htcs` and controlled timing dispersion. It does not
promote a production model change.

## Exit Criteria

The package closes when baseline parity, mutation-lane mass conservation,
figures and sidecars, cleanup verification, and investigation documentation
are complete.

## Outcome

Three full-period timing-dispersion lanes completed and produced three figures
with sidecars. The inversion persisted, while non-monotonic peak changes
confirmed event-specific synchronization sensitivity. The direct `htcs` lane
was rejected at a text-versus-binary pass compatibility boundary. Baseline
source cleanup was verified at the original clean commit.
