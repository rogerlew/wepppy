# Production vulnerability remediation tracker

| Milestone | Status and evidence to retain |
| --- | --- |
| Baseline | Serving source, image and scan manifest pinned in [package](package.md). wepp1 web and workers, both wepp2 workers and both wepp3 workers report the pinned image. JSON review copies verified against the manifest. The private ledger covers 3,002 primary and 516 suppressed rows, plus all 18 baseline npm package records. |
| Web and auth | `9afda6161` moves the common image to Starlette 1.3.1, Authlib 1.9.10, joserfc 1.8.0 and an updated OAuthlib. Commit `50de1db06` corrects OAuthlib to 4.0.1 after independent review. The focused trial passed 158 OAuth and query access tests. |
| Image processing and npm | `8d2ae32ad` passed 36 Pillow and PyCurl consumer cases. `f880db9c7` passed npm ci, lint, all tests and build. Local audit returned zero critical/high. |
| Additional Python consumers | `65084ea5a` updates Tornado, dnspython, SoupSieve, Mistune, fsspec and Jupyter Core. Signed login, notebook, transport and scientific file trials passed 90 tests with the final pins. |
| Debian, Go and cache | `5729db5e1` uses an ephemeral uv cache during production installation. All three embedded Go tool consumers have been identified. The candidate contains zero uv-cache files. All 432 Debian package versions and three Go executables match the serving image. See the [dated security review](artifacts/20261123_security_review.md) for the itemized ledger and applicability limits. |
| Candidate and decision | Source `65084ea5a` produced image `sha256:a116e2d21457a0e33a6070ab42518be0adead13ea9b53db5c55d9f7dfa8871d0`. Independent exact-image [correctness checks](artifacts/20261123_correctness_review.md) passed. The CI test image inherits all candidate layers. Its full pytest gate passed with 14,751 passed, 751 skipped and 99 deselected. Frontend lint and tests passed. The [release decision](artifacts/20261123_release_decision.md) records a security hold. The same-database comparison removed 327 primary rows and introduced zero normalized findings. Roger Lew owns production risk acceptance. |

Update each row with the commit, immutable artifact and evidence location as work lands. Track individual exceptions in the existing private evidence store.

Private execution records on forest are under `/workdir/weppcloud-deployments/.local/dependency-security/evidence/grype-remediation-20261123/`.
