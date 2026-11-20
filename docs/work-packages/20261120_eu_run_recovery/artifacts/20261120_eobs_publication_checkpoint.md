# E-OBS generated climate publication draft

Starting implementation `51cea3b24`. The operator asked to fix the E-OBS
failure and the competing applied-climate and failed-job state. The
[Climate Parquet lineage contract](../../../schemas/climate-parquet-lineage-contract.md)
is the canonical base. This draft has unresolved review findings and does
not change implementation authority. The legacy generic build router
clears saved artifact references and removes active files before calling
CLIGEN. An E-OBS failure therefore destroys usable files from the prior
operation. Existing observed builders have a compatible staged finalization
and archive visibility model.

Isolate E-OBS acquisition and CLIGEN work prior to publication. Use
the existing Climate controller transaction and derived-file publication.
Retain working or failed status evidence under the run's climate artifacts.
Publish E-OBS files and output metadata together. Preserve established
settings, scaling, history and HTTP/RQ contracts. Validate an actual CLI and
its parameter file before publication. Check Single and Multiple, where
every required hillslope has its own pair and failure must keep the previous
generation. A selected E-OBS operation leaving a previous upload applied
cannot prepare a new deck as E-OBS, even when the previous upload is valid.
Do not add a source-file gate to no-preparation execution. The existing
rerun pipeline still classifies its report mode from the mutable controller, so
old event decks selected under a different mode require a separate fix. Test
real E-OBS admission, including a conflict, without removing the previous
completed timestamp. Verify that an
archived prior upload remains readable without mutation after a failure.
Later scaling, export and generalized provider rollback are separate
publication questions.

## Unresolved read-only review findings

- Separate last-applied availability and timestamps from current E-OBS
  readiness. Pipeline status currently gives a previously completed timestamp
  priority over an independently failed job. Verify admission conflicts and
  failure through controller readiness, the Climate report and schema defaults.
- Define provenance and compatibility for an earlier generated climate as well
  as an earlier upload. Fingerprint the selected settings and actual accepted
  file generation without treating an expired RQ result as execution authority.
  Enforce the new generation check while copying inputs in
  `wepp_prep_service.prep_climates`, including direct and asynchronous routes.
  Read the selected generation under the same publication serialization.
- Keep the report's applied CLI, station and advisory together even when
  selection fields or a desired spatial mode move ahead. Cover an old Single
  upload and a failed requested Multiple E-OBS job.
- Reject a symlink or unmanaged attempt root before writes. Preserve valid
  contained mount behavior. Retain diagnostic inputs using a private attempt
  and a separate publication child inside the destination. Retire stale flat
  derivatives when the new base inputs publish and use the existing commit
  outcome handling for after-replace failures.
- Preserve the configured override and actual CLIGEN default seed of 12345
  when the override is unset. Keep sufficient failing-hillslope evidence for
  Multiple independently of its shared native log pathname.

## Proposed direction

Implementation conformance is pending. The E-OBS provider and CLIGEN write
their centroid and any configured hillslope CLI and PAR outputs to a visible
attempt under `climate_artifacts/eobs/attempts/`. The existing Climate write
lock holds through acquisition, generation and publication. Provider, CLIGEN
or required-output validation failure leaves the previous active files,
their output references and completed Climate timestamp intact. The E-OBS
HTTP submission leaves the completion timestamp in place while a job is
pending or rejected. Keep the
failed attempt and status available for authorized browse and archive.
An absent previous artifact is a normal first-build state.

Publish the complete generated inputs through the normal derived-artifact
publication boundary. Persist the new filenames, output metadata and seed
in the same Climate commit. Keep the established scaling and export stages
after generation. The contract bar for this checkpoint is provider and
CLIGEN generation failure, including an individual hillslope failure in
Multiple. General rollback after a later scaling or export stage remains
outstanding. Clear obsolete upload and storm-batch references when the
generated climate is published. If a user-uploaded climate is still the
applied file after the user selects E-OBS, show its advisory if applicable
and require the selected E-OBS build to finish before preparing a new deck.
This checkpoint leaves the prepared-input path untouched. It does not
claim stable native and postprocessing mode classification for an old
event deck if the controller selection changed independently.
