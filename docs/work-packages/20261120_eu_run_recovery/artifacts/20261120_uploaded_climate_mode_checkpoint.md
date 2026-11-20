# Uploaded climate mode checkpoint

Starting revision `97cd07719`. The operator asked why a continuous user-defined upload still showed the single-storm error and directed continued recovery. The [upload contract](../../../schemas/upload-endpoint-contract.md#uploaded-climate-mode) repairs the content-to-mode association for the uploaded CLI. This checkpoint does not claim transactional artifact replacement or retention across failed builds. Those remain required before deploying the complete package.

Read the active CLI for saved upload modes only. Verify at least one parsed event/day record. Classify by the existing individual-event rule. Cache a read only against the current file identity, with a new result after replacement at the same name. No read of the Climate controls or summary persists a change. A genuine legacy mismatch encountered at an authorized WEPP preparation root is reconciled under the Climate lock before output mutation. An ordinary successful upload persists either uploaded mode as appropriate, clearing obsolete saved batch result references. No-preparation jobs do not reconcile against the upstream Climate source.

Missing, unreadable, malformed, and never-used climate inputs keep the existing input validity behavior. A readable individual event still receives the advisory. A valid continuous file uses the continuous pipeline and has no Climate single-event warning. Old independent generated and batch types keep their policy. This is a run-scoped calculation from existing controller-owned files with no new input or authorization surface. Test both upload directions, candidate modes against the archived `FLOOD4.cli` and `ESFANGAR.cli`, legacy read without persistence, write reconciliation, same-name cache refresh, and generated modes. The complete deployment and browser/RQ replay remain open.

## Independent review disposition

Both reviewers required a separate display calculation, leaving `climate_mode` and `is_single_storm` on their saved values for no-preparation and existing downstream consumers. The refreshed Climate summary renders the effective warning while the catalog keeps its mode-12 selection token. The controls no longer duplicate the warning. Require the active filename to match recorded upload provenance and user station metadata, keeping an unuploaded User-Defined selection over a previous generated file out of read-time inference. Reject absolute, traversing, symlinked, header-only, and malformed active paths on that lookup. Normal upload publication records the active CLI and its classification in the same NoDb mutation. At WEPP preparation, reload the controller and recheck identity under the existing climate root operation and the Climate lock before repairing a legacy mode or obsolete batch references. This verifies the current file at that point. Pending upload byte isolation remains a separate deployment gate.

## Candidate validation

In a private copy of the archived project, the server classified the existing
10,957-record `ESFANGAR.cli` as continuous while leaving the saved mode 15 and
`climate.nodb` bytes untouched. Normal WEPP preparation then saved mode 12
under the climate directory operation with isolated Redis. This used the
archived Climate controller and file; it did not run the full project.

The focused suite passed 442 cases. Two new report cases initially failed
because the template fixture lacked `monthlies`; after adding that field both
passed on the candidate. These cover the refreshed warning in both directions.
The real CLI tests cover malformed records and dates, non-upload database
paths, inactive inputs, path containment, same-name replacements, and a
recorded bad event rejected before deck preparation. The bounded legacy
provenance check can only infer ancestry from saved fields and the active
path. Publication isolation and artifact retention remain deployment gates.
