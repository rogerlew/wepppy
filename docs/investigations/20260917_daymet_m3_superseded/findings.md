# Daymet M3 superseded during concurrent WEPP preparation

2026-09-17 UTC. Job `bb219a65-e71a-4c6c-bbaa-40814a8e2aac`, thespian-cleanness.
Attempt `932b890ecffa4f659d438bcf0dad68e5` ran 18:23:09–18:23:51 UTC.

## Confirmed failure

M3 generated predictor and result artifacts, then failed the pre-publication
`_current_authority` check at `production.execute_m3` line 790. All source
content-hash entries in the admission and current snapshots match. The only
snapshot difference is `files.active_cli` ctime. CLI size and mtime match.
The active CLI and `wepp/runs/pw0.cli` are hard links to the same inode.
WEPP logged watershed preparation at 18:23:38, coincident with the changed
ctime. Its later postprocessing completed at 18:24:22. Retained evidence:
[evidence.json](evidence.json). This was not a Daymet rainfall parser failure.

## Why the completed fixes did not cover this case

The accepted file-dependency freshness contract distinguishes accepted-result
currentness from active-worker admission/publication guards. The latter explicitly
retains strict snapshot equality and allows metadata churn to supersede an
in-flight attempt. The implementation follows that restriction; it still rejects
concurrent WEPP hard-link preparation, despite unchanged content.

This is a remaining valid-workflow limitation rather than evidence that Daymet
changed scientific inputs during the job. Relaxing the active guard requires a
reviewed contract amendment that preserves coherent reads, genuine content and
selection changes, publication races, and locking. Do not merely remove ctime or
reuse permissive accepted-result comparison in a publication finalizer.

## Recovery and follow-up

Retry M3 after WEPP preparation is finished; no climate rebuild is necessary
for this metadata-only failure. The retry is expected to avoid this race but
has not been submitted by this investigation. Existing accepted results and
failed-attempt diagnostics were preserved; no runtime code or run state changed.

The next fix needs a real overlapping M3/WEPP preparation regression, unchanged
content allowed through publication, and changed-content/selection adversarial
checks. Acceptance should exercise both job orderings and actual restarted
workers, not only WEPP execution after an already accepted post-fire result.
The completed package remains historical and was not edited.
