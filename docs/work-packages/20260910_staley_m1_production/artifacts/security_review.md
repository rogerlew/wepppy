# Independent implementation security review

Reviewer: contract_security (security_reviewer), 2026-09-10. Final disposition:
**approved for the reviewed implementation**, with no unresolved medium/high
security findings. Reviewer made no edits. Closeout remains conditional on final
full-suite and required validation gates recorded in [validation](validation.md).

Closed findings:

- Safe run-relative paths, nonsymlink ancestry, strict detached raster/VRT decoder
  and hidden staging prevent uploads from reading arbitrary project/server data.
- Actual streamed multipart limits apply without Content-Length; duplicate parts,
  unknown keys and malformed finite numeric settings are rejected. Parser spools
  close on disconnect and cancellation; download handles close on disconnect.
- Config/readonly/authorized run scope are enforced at admission, with rechecks
  before staged writes. Retained candidates are bound to this run's accepted or
  latest unaccepted attempt with bounded expiry.
- Only fixed files from the latest accepted result can be downloaded; hashes and
  file identity are verified using the opened handle. Raw sources and arbitrary
  manifests/staging paths are not public browse artifacts.
- NoDb saves the exact planned RQ job before Redis receipt persistence. Missing
  or ambiguous submissions reconcile that job only, not a previous receipt.
- Publication verifies uploaded sources, source snapshots and attempt ownership;
  stale work cannot replace accepted output. Predictor reuse copies only verified
  inventory, never unrelated files or nested symlinks.
- Whole-state completion reconciliation, direct POLARIS/RUSLE enablement and the
  unchanged-checklist notification regression introduce no new security findings.

Noninterference evidence: real NoDb/raster/transport tests plus strict browser
[browser_smoke.log](browser_smoke.log) and [four finished RQ jobs](live_jobs.json).
Valid upload/run/download, reload, SI/English, ambiguous replacement preserving
accepted state, retained-file correction and live prerequisite changes all pass.
The receipt fault-injection script uses actual Redis and NoDb state.

This approval does not establish other-host deployment parity or the owner's
real-basin scientific acceptance. No production hosts were modified.
