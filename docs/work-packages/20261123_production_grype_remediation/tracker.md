# Production vulnerability remediation tracker

| Milestone | Status and evidence to retain |
| --- | --- |
| Baseline | Serving source, image and scan manifest pinned in [package](package.md). wepp1 web and workers, both wepp2 workers and both wepp3 workers report the pinned image. JSON review copies verified against the manifest. Itemized review in progress. |
| Web and auth | `9afda6161` moves the common image to Starlette 1.3.1, Authlib 1.9.10, joserfc 1.8.0 and OAuthlib 4.0.0. The focused trial passed 158 OAuth and query access tests. |
| Image processing and npm | `8d2ae32ad` passed 36 Pillow and PyCurl consumer cases. `f880db9c7` passed npm ci, lint, all tests and build. Local audit returned zero critical/high. |
| Debian, Go and cache | `5729db5e1` uses an ephemeral uv cache during production installation. All three embedded Go tool consumers have been identified. Awaiting installed-image readback and scan delta. |
| Candidate and decision | Clean candidate build from `5729db5e1` on forest. Hold pending exact-image evidence and independent reviews. Roger Lew owns production risk acceptance. |

Update each row with the commit, immutable artifact and evidence location as work lands. Track individual exceptions in the existing private evidence store.

Private execution records on forest are under `/workdir/weppcloud-deployments/.local/dependency-security/evidence/grype-remediation-20261123/`.
