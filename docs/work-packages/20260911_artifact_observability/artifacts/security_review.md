# Security review

Reviewer: independent `contract_security` agent. Final disposition: PASS; no
unresolved medium/high findings.

Review covered path containment, project access, legacy/new tree conflicts,
real admission/lifecycle and NoDb exclusion, recorded and prior RQ jobs, recovery
integrity, original metadata retention, accepted signature trust, and diagnostics.

All reported findings closed: external-source re-signing, directory traversal on
resume, editable hash-map/planned-state authority, and forged accepted inventory.
Recovery derives permitted transformations from original metadata and anchors
accepted files to original NoDb signatures. Raw backup validation uses JSON
inspection, not executable deserialization. Unknown science fingerprints remain
stale. Registry inspection is read-only and refuses active matching jobs.

Runtime evidence confirms worker uid 1000/gid 993, exact non-JSON payload retention,
unchanged accepted identity/freshness, ordinary authorized browser/download access,
and all 148 copied module records preserved by canonical archive/restore. Source
and disposable archive-check projects are both private. The final soil change
retains an existing raster under the same fresh-directory boundary and passes 35
tests. No credentials/session tokens were published and no access rule was weakened.
