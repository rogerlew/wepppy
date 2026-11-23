# Remediate the deployed common image

## Purpose

Reduce applicable runtime exposure while preserving login, upload, data acquisition, scientific output and report rendering. Use the [package baseline](../../package.md) and record milestone evidence in the [tracker](../../tracker.md).

## Progress

- [x] 2026-11-23 UTC. Bound scope to the serving artifact and existing release policy.
- [x] 2026-11-23 06:56 UTC. Confirmed the baseline worker image on all three hosts and verified the local review copies of the retained JSON against the pinned manifest.
- [x] 2026-11-23 07:10 UTC. Reconciled the serving inventory against source packages, prior evidence and all known-exploited flags. The private ledger identifies unresolved exposures.
- [x] Validate public-facing framework and authentication repairs.
- [x] Validate image processing, bundled libraries and frontend dependency repairs.
- [x] Disposition OS and embedded-tool findings and qualify cache cleanup. The [independent security review](../../artifacts/20261123_security_review.md) retains open applicability and fixes for operator follow-up.
- [x] Built, tested and independently reviewed the integrated candidate. Recorded a production hold.

- [x] 2026-11-23 07:03 UTC. Committed separate frontend, framework, native and build-cache batches. Focused tests passed. Started the integrated clean build from `5729db5e1` on forest.

- [x] 2026-11-23 07:19 UTC. Corrected OAuthlib to 4.0.1 and qualified six additional Python dependency repairs. Moved the clean build of `65084ea5a` to forest1 after forest Docker storage reached 5.2 GiB free. The source checkout uses serving-archive permissions inside a private staging directory.

- [x] 2026-11-23 07:54 UTC. Built the immutable image `a116e2d21457` and independently passed actual signed OAuth, PATH, DEVAL, compressed acquisition, scientific file and CLI checks. The exact CI extension passed frontend lint and all tests.

- [x] 2026-11-23 UTC. Imported the exact candidate bundle on wepp2 and rematched the serving SBOM against the same Grype database. Independent security review verified zero new normalized advisory groups. The same-database comparison removed 327 primary rows.

## Milestones and verification

1. Start from a clean current-master worktree. Confirm the serving image digest and load the retained SBOM, Grype, npm and native inventory from wepp2. Group rows by advisory alias and source component, retaining each installed path, executable owner, fix state and service exposure. Review all known-exploited flags across severity levels. Reconcile the OpenSSH client match against the affected daemon, libc and installed files. Record image and host scopes separately.
2. Reconcile prior candidate `63ae6f940` with current Starlette, FastAPI, Authlib and verifier dependencies. Identify which public routes and OAuth flows actually use the affected functionality. Test proxy and path handling, normal login, rejected tokens, account linking and the expected failure redirect. Commit the compatible repair and retain the scoped results.
3. Recheck the pinned Python Brotli patch against the installed extension. Identify separate libraries in Pillow and PyCurl and validate the selected fixes through real image decoding, rendering, and compressed data acquisition. Use a separate lockfile commit for applicable npm repairs, with frontend lint, tests and generated asset readback. Keep scientific outputs and authentication semantics under regression coverage.
4. Review Debian findings by source package and distribution revision. Record backports, missing affected features, fixes or remaining exposure with evidence. Trace Go matches to the Docker CLI, git-lfs and Quarto esbuild; establish actual consumers before upgrading or removing a tool. Verify an actual Quarto report and any affected CLI workflows. Evaluate excluding the uv cache from the final image, separately measuring installed-runtime findings and cache-only rows.
5. Combine accepted commits, build one immutable common image and run the existing candidate-image regression gates. Generate fresh SBOM, Grype, npm and native evidence. Rematch the baseline SBOM against the same advisory database. Report additions, removals, changed applicability, outstanding findings, native coverage gaps and exception expiration. Independently review the candidate and record release or hold under the existing policies. If activated, use the retained-candidate deployment workflow, verify serving identities and read back representative outputs. Retain the known-good image for rollback.

## Surprises & Discoveries

The 87 critical rows represent 31 distinct advisory IDs. Paths and advisory aliases account for repeated matches. Earlier reviews found patched Python Brotli with unchanged upstream version metadata. The evidence must be rebound to the current artifact, including separate examination of bundled libraries.

The serving image includes a separate PyCurl Brotli 1.1.0 decoder. The OpenSSH source match concerns sshd on musl, while the image contains the Debian client on glibc. See the security review for component-level reconciliation.

Forest1 built the image and CI extension but failed to create transient systemd scopes for standalone containers. Both images were transferred to forest with verified immutable identities. The first full run reached 2,802 passes, then retained-tree admission observed less than its 10 GiB free-space reserve in container scratch. A private scratch mount on forest provided sufficient capacity but hid the DuckDB spatial extension built into the image. The second run reached 7,159 passes before GeoJSON loading failed. Copying the exact image extension into that mount restored the GeoJSON test. Its SHA-256 is recorded in the private build evidence.

## Decision Log

2026-11-23 UTC. Use one package because all repair batches affect the same common image and share a release decision. A failing batch can be revised or reverted independently. Any residual exposure returns to the existing policy and approval process.

2026-11-23 UTC. Rejected the OAuthlib 4.0.0 intermediate after review identified an additional device-flow advisory. Chose 4.0.1. Retained the serving Node and Python base digests for the comparison.

## Outcomes & Retrospective

Six repair commits are available. Component trials on forest passed 158 framework/OAuth and 36 codec/transport cases. The targeted npm lock passed lint, 1,109 Jest tests, nine Node tests and the production asset build. The exact-image security and correctness reviews are complete. The [release decision](../../artifacts/20261123_release_decision.md) holds the image under the existing policy.

The full candidate suite passed with 14,751 passed, 751 skipped and 99 deselected. The isolated test stacks were removed after validation. The work package remains open for Roger Lew’s disposition of residual security findings.
