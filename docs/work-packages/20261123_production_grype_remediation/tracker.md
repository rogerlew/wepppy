# Production vulnerability remediation tracker

| Milestone | Status and evidence to retain |
| --- | --- |
| Baseline | Serving source, image and scan manifest pinned in [package](package.md). Next: reconcile current runtime exposure against prior itemized dispositions. |
| Web and auth | Pending. Record selected versions, route applicability, login and rejection results. |
| Image processing and npm | Pending. Record installed library identities, consumer output checks and lockfile evidence. |
| Debian, Go and cache | Pending. Record source-package decisions, tool consumers, cache-only matches and runtime delta. |
| Candidate and decision | Pending. Retain image digest, same-database scan delta, native coverage, independent correctness/security reviews and decision owner. |

Update each row with the commit, immutable artifact and evidence location as work lands. Track individual exceptions in the existing private evidence store.
