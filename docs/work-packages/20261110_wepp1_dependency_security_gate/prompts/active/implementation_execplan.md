# Bind dependency security decisions to the exact wepp1 common image

This ExecPlan is a living document governed by
`docs/prompt_templates/codex_exec_plans.md`. Keep `Progress`, `Surprises &
Discoveries`, `Decision Log`, and `Outcomes & Retrospective` current, and update
this plan and `tracker.md` at every stopping point.

## Purpose / Big Picture

After this work, a dependency-security decision for WEPPcloud is tied to the
actual common container image that would run on wepp1. An operator can identify
the image, reproduce its software inventory, see every advisory disposition,
and know that missing or blocking evidence stops activation before the running
known-good stack is disturbed. Users continue to authenticate, browse projects,
run models, and view reports under a dependency set proven compatible by
focused checks and complete Python/frontend regression gates.

Success is observable when one exact final image ID/digest has a reconciled
software bill of materials (SBOM), fresh Python/operating-system scan, exact npm
lock audit, reviewed disposition matrix, clean image build, and green full test
receipts. The required broad commands are `wctl run-pytest tests --maxfail=1`,
`wctl run-npm lint`, and `wctl run-npm test`. All must exit zero; a partial or
segmented substitute is not accepted.

## Progress

- [ ] (2026-11-12 UTC) Continue dependency remediation, beginning with the
  reviewed Mistune/nbconvert boundary and qualified native-library repairs.
  Deployment-resume implementation is explicitly deferred by Roger; do not
  treat that deferred choice as a blocker to dependency repair.

- [x] (2026-11-12 UTC) Complete OAuth collection: all 18 prior Authlib rows are
  removed, joserfc has no findings, inventory and artifact identities reconcile.
  Actual evaluation blocks on native coverage. Other rows remain retained;
  M1/M3/M4 are still open and no runtime activation is authorized by this result.

- [x] (2026-11-12 UTC) Verify clean OAuth candidate's exact two-package version
  delta and rerun all 50 callback tests successfully in 9.71s. Preserve the
  preceding PostgreSQL startup failure during heavy export and the unchanged
  quiet retry. See `artifacts/20261112_oauth_candidate_validation.md`.

- [x] (2026-11-12 UTC) Corrected parser collection 6 passes producer readback
  with zero analysis errors and unchanged finding counts. Actual policy
  evaluation rejects unresolved native coverage; no approvals were invented.

- [x] (2026-11-12 UTC) Independently partition all 2,105 native unknown paths
  into 1,201 hashes with ownership proposals. Bundled/static components and
  cache-only versions still require advisory coverage. No approvals fabricated;
  see `artifacts/20261112_native_coverage_review.md`.

- [x] (2026-11-12 UTC) Freeze independently reviewed OAuth implementation at
  detached revision `afe6e7264`; all 50 component tests pass. Clean build passes
  in 658.72s, image `sha256:e4e44d496fe0feead2b25e0b7833c86be2b321fcb5f8e9683fb9945c6db42e03`.
  The checkout is `/home/workdir/wepppy-security-oauth-candidate-20261112`. Keep
  the required new dependency isolated from forest's running older environment.
- [ ] Complete actual CI producer/import lifecycle; the reviewed bounded design
  is `artifacts/20261112_ci_producer_design.md`. A transport-only trial is not
  acceptance. Deployment-resume work is explicitly deferred separately.

- [x] (2026-11-12 UTC) Complete frozen real parser collection and independent
  inventory readback. Selected parser packages have no findings; native coverage
  and other dispositions remain open. Correct an overly broad diagnostic failure
  classification, retaining the original receipt. See
  `artifacts/20261112_parser_collector_acceptance.md`.

- [x] (2026-11-12 UTC) Commit three-package parser candidate `6c0c213a2` after
  disposable normal/boundary probes and independent correctness review. Clean
  no-cache Compose build passes in 584.36s; isolated test image also builds.
  Candidate `sha256:05f4d047b5460e0a867876aeff6af27b5515afab1a54b31b6b4a5df6d31931a9`
  remains under focused and scanner validation, not final M4 acceptance.

- [x] (2026-11-11 UTC) Commit reviewed M0 checkpoint `d4b175436`; preserve
      unrelated work. Prepare itemized M1 review packet with all 3,221 raw rows,
      330 narrow not-affected proposals and 2,891 unresolved rows; no clearance.
- [x] (2026-11-11 04:44 UTC) Confirm the F6 audit statement, wepp1 common-image
      path, and absence of retained raw scan evidence.
- [x] (2026-11-11 04:44 UTC) Discover dependency-upgrade, immutable-image,
      generated-workflow, and full-test precedent.
- [x] (2026-11-11 04:44 UTC) Scaffold the package, tracker, scope/policy,
      surface inventory, scanner evaluation, and review gates.
- [x] (2026-11-11 04:44 UTC) Record the operator's mandatory full pytest and npm
      validation decision.
- [x] (2026-11-11 07:18 UTC) M0: capture green pre-change baselines; select/evaluate scanner tooling; ratify
      policy, exceptions, retention, CI, and deploy-gate behavior.
- [x] (2026-11-11 05:05 UTC) Recapture revision/manifest identities on forest;
      confirm installed wctl resolves development Compose, not wepp1 Compose.
- [x] (2026-11-11 UTC) Initial full baseline completed: npm lint and 1,069 npm
      tests pass; pytest fails after 13,429 passes on a stale help-link assertion.
- [x] (2026-11-11 UTC) Reproduce failure without dependency changes; repair the
      test to follow the existing Runs catalog contract; all 11 module tests pass.
- [x] (2026-11-11 07:17 UTC) Exact full pytest rerun passes: 13,502 passed,
      435 skipped. npm lint and all 1,069 tests pass; private baseline receipts
      retained with hashes. M0 reviewed checkpoint accompanies these documents.
- [x] (2026-11-11 05:11 UTC) Verify Trivy 0.76.2 release hash and exact GitHub
      signing identity; isolated archive trial reconciles all 89 Debian
      packages in a Redis fixture. This is tool qualification, not F6 evidence.
- [x] (2026-11-11 UTC) Independently approve the evaluated Syft/Grype image-only
      pipeline after reproducing Trivy's GDAL omission and auditing the
      alternative's parser, suppression, inventory, and error boundaries.
- [x] (2026-11-11 UTC) Roger ratifies policy and selects
      `/workdir/weppcloud-deployments/` for protected retention. Store raw M0
      evidence and the approved policy hash under its private ignored
      `.local/dependency-security/` directory.
- [x] (2026-11-11 06:31 UTC) Preparatory clean unchanged-source common-image
      build succeeds; inventory reconciles 308 Python/432 Debian versions.
- [x] (2026-11-11 UTC) Qualify exact-image scientific `.par` classification;
      rescan removes false Java parsing errors without changing package inventory.
      Retain 2,099 executable ownership gaps and all diagnostic findings.
- [ ] M1: build and inventory the exact baseline common image; reconcile the
      SBOM and disposition every Python/OS/npm finding.
- [ ] M2: implement compatible dependency batches with focused tests.
- [x] (2026-11-11 UTC) Clean Compose crypto/TLS candidate builds; exactly three
      installed-version upgrades, unchanged native versions, 51 focused tests
      and seven TLS checks pass. Fresh candidate scan removes 22 selected-package
      rows against the same-database baseline, with no package-level additions. Authlib
      remains held for the separate OAuth contract checkpoint.
- [ ] M3: wire candidate-image evidence into CI/test-image and the canonical
      pre-activation deployment path.
- [x] (2026-11-11 UTC) Test-image candidate argument builds the local image,
      preserves default digest, and passes layer/runtime/native readback plus
      51 focused tests. Add npm lint to its generated workflow and verify
      generation parity. Remote evidence handoff and activation wiring remain open.
- [x] (2026-11-11 UTC) Implement local manual importer; pass 31 focused tests,
      actual five-file private readback, and independent correctness/security
      component reviews. Full pytest passes with 13,533 passed/435 skipped;
      npm lint and 1,069 npm tests pass. Remote CI retrieval,
      policy evaluator and activation hook remain open.
- [ ] M4: build the final candidate; pass focused, full pytest, npm lint, full
      npm tests, artifact readback, and independent reviews.
- [ ] M5: perform a separately authorized wepp1 rollout and closeout.

## Surprises & Discoveries

- Observation (2026-11-12): Grype reorders complete location records for 135
  rows without changing their contents. Compare full-object multisets while
  preserving duplicates and approval-key identity; strict list order is not a
  semantic package identity requirement. Other artifact fields remain exact.

- Observation (2026-11-12): Grype's qualified no-Go-symbol warning preserves
  conservative module-level findings, but the initial producer rejected it as
  analysis loss. Recognize only the complete diagnostic under pinned effective
  scope, retain its raw text, and recollect; never enable symbol filtering to
  make advisory rows disappear.

- Observation (2026-11-12): independent review reproduced candidate Python
  startup emitting forged successful inventory JSON before the mounted verifier
  executes. Read-only root and dropped capabilities contain side effects but do
  not establish output authority. Replace that exploratory method with trusted
  streaming readback of a never-started container's exported filesystem; never
  extract or execute archive contents. Preserve the failed method's receipts
  with an explicit superseded status. This removes the inventory-only capability
  escalation considered during the earlier traversal investigation.


- Observation (2026-11-12): old Msgpack 1.2.1 retains 3,281,695 traced bytes
  after 100 invalid map-key operations; 1.2.3 retains 1,595 bytes under the same
  probe. nbconvert 7.17.1 preserves `../../outside.png` in an in-memory extracted
  output name; 7.17.2 contains it as `outside.png`. No outside file was written.
  Pyasn1 BER/DER compatibility probes pass on both versions; these probes do not
  demonstrate the reported performance defect. Clean candidate builds and actual
  dependent workflows remain required before disposition as fixed.
  Evidence: private `small-python-trial-20261112/security-boundary.log`.

- Observation (2026-11-12): Syft's output descriptor does not retain top-level
  scientific exclusion globs. The producer must bind the exact input config and
  qualify each matched image file against the approved path/hash manifest; a
  matching output descriptor alone cannot prove exclusion scope.


- Observation: a successful database refresh at 2026-11-11 06:26 UTC still
  returned Grype database build timestamp 2026-11-10 06:21:20 UTC, beyond the
  approved 24-hour window. Refresh exit zero cannot prove freshness. Preparatory
  scans may inform triage but cannot authorize activation with this database.
  Evidence: private `baseline-2041fb8e2-20261111/grype-db-update-receipt.json`,
  `grype-db/6/import.json`, and SQLite `db_metadata` readback.

- Observation: the full baseline fails on a stale test expecting a removed JS
  global. The template already provides the single static help anchor required
  by the Runs catalog TTL deletion contract. The focused reproduction fails
  identically; updating the test to the unchanged contract gives 11 module passes.
  Evidence: M0 validation receipt and private pytest logs.

- Observation: the local `out/` tree occupies approximately 852 GiB and is not
  excluded by `.dockerignore`, while Docker's root filesystem has much less
  free capacity. A working-tree common-image build would include unrelated
  generated data. Gitignored does not mean excluded from Docker context.
  Evidence: `.dockerignore`, `du -sh out`, and Docker root-directory readback.

- Observation: Trivy 0.76.2 returns zero while omitting the Python GDAL advisory
  GHSA-r5m4-5vww-w9f5/CVE-2026-8212 after failing to parse `<3.13.0RC1`.
  Evidence: scanner evaluation section 5 and private `gdal-matcher-gap.json`.
  The verified distribution is not sufficient proof of scanner completeness.

- Observation: Syft 1.57.1 reconciles all 324 Python and 475 Debian versions in
  the development image; Grype 0.121.3 detects the omitted installed GDAL case.
  Both default and suppression-enabled trials retain 3,006 matches plus 330
  ignored kernel-header matches. These are qualification findings, not M1's
  production-common-image baseline, and all categories require disposition.
  Evidence: scanner evaluation section 7 and private trial reports.

- Observation: Grype can create a zero-byte report before exiting nonzero for
  malformed input or an absent database. Report existence cannot release a gate.
  Evidence: private `malformed-sbom-receipt.json` and `missing-db-receipt.json`.

- Observation: forcing Syft's excluded Debian-archive cataloger on the inert
  negative-size fixture triggers a recovered parser panic recorded only in
  native SBOM `files[].unknowns`; exit remains zero. The default image catalogers
  do not select this parser. The development SBOM separately records 1,969
  unidentified executables, requiring M1 ownership/coverage reconciliation.
  Evidence: scanner evaluation section 7 and private fixture/native SBOMs.

- Observation: the installed wctl on forest resolves `wepppy-dev` from
  `docker/Dockerfile.dev`. The pre-change wrapper run is development evidence;
  final acceptance must explicitly select the candidate test runtime.
  Evidence: sanitized `wctl docker compose config --format json` readback.

- Observation: existing deploy retry helpers can return zero after a failed
  command because they capture status after an `if` without an `else`.
  Evidence: `artifacts/20261110_operations_review.md`. The new security gate
  must propagate its own failure directly; integration is not yet implemented.

- Observation: the audit retained a summary of 168 advisory records across 22
  package names but no raw report, scanner version, database identity, manifest
  hash, or image identity. The number is not a reproducible baseline.
  Evidence: gitignored audit board Phase 6 and its validation notes.

- Observation: no repository-integrated image scanner and no local `syft`,
  `trivy`, `grype`, `osv-scanner`, or `pip-audit` executable was found during
  scaffold discovery. Docker is available.
  Evidence: command discovery at 2026-11-11 04:44 UTC.

- Observation: the common image contains more than ordinary pinned Python
  packages. `docker/requirements-uv.txt` has one Git source and five
  range-constrained lines, while the Dockerfile also downloads or vendors
  repositories, Quarto, Docker CLI, and a DuckDB extension.
  Evidence: `docker/Dockerfile` and the 259-line requirements manifest.

- Observation: the full-baseline workflow source does not list
  `docker/requirements-uv.txt` as a trigger, and `docker/Dockerfile.test` starts
  from a previously published common-image digest. A green baseline could
  therefore test a different Python dependency image from a pull request.
  Evidence: `.github/forest_workflows/stubtest.yml` and
  `docker/Dockerfile.test`.

- Observation: the primary npm workflow runs tests but not lint. The package
  must retain the operator-required npm tests and add the repository-required
  lint gate for frontend lock changes.
  Evidence: `.github/forest_workflows/npm-tests.yml`.

## Decision Log

- Decision (Roger, 2026-11-12): continue dependency remediation and defer the
  resume workflow. Never wait for hours for stale NFS handles; report failure
  and require manual recovery. Prioritize concrete package repairs and their
  consumer regressions over further deployment workflow design. Existing
  dependency acceptance requirements remain in force; no risk waiver is implied.

- Direction (Roger, 2026-11-12): prioritize dependency remediation; NFS retained
  handles require manual intervention and are a separate concern. Hold the
  deployment-resume proposal while package remediation remains unfinished.
  Six package upgrades are committed on master (cryptography, certifi, urllib3,
  pyasn1, msgpack, nbconvert); Authlib/joserfc remain in the validated isolated
  candidate. None of these statements implies production rollout or M4 closure.

- Decision (2026-11-12, Codex): preserve frozen collection 5 and correct the
  producer's exact qualified warning classification for a new collection.
  Rationale: a conservative module-level advisory warning is not parser loss;
  changing the existing receipt would invalidate its retained manifest identity.

- Decision (Roger, 2026-11-12): complete F6 through M4 as part of the F7
  continuation. Preserve the ratified evidence policy and required final-image
  gates. Production rollout (M5) and advisory-risk exceptions are not inferred
  from this instruction.

- Decision: reaffirm production Docker Compose after the operator's explicit
  reminder. The candidate-base argument belongs only to the isolated test image;
  it neither requires a registry nor changes installed wctl/deploy-production.
  Rationale: prove tests use the locally built candidate while preserving the
  established production deployment boundary.
  Date/Author: 2026-11-11, Roger; recorded by Codex.

- Decision: develop and validate the local manual evidence importer while M1
  applicability review remains open. This is an M3 component, not milestone
  acceptance or permission to activate an image. The external CI prerequisite
  is a confirmed operator retrieval route before isolated-runner cleanup.
  Rationale: manual collection is owner-selected, and import integrity can be
  tested independently without approving findings or changing deployment.
  Date/Author: 2026-11-11, Codex.

- Decision (Roger, 2026-11-11): transfer evidence **manually** to the selected
  private store; production remains Docker Compose through canonical wctl/deploy
  entry points. Verify imported report hashes/identities before acceptance.
  Rationale: use the operator-selected bounded handoff without adding a transfer
  service or changing production topology. M3/M4 must validate this handoff.

- Decision: prepare a clean detached build of unchanged revision `2041fb8e2`
  while the corrected full baseline runs. This is preparatory evidence, not M0
  or M1 acceptance; no dependency, workflow, or deployment code changes precede
  the green baseline and reviewed checkpoint. Verify build-context differences
  against that checkpoint before reusing any preparatory image evidence.
  Rationale: the unmodified production build is independent of a test-only repair
  and can expose build blockers without extending the hour-long baseline wait.
  This refines the earlier strictly sequential build decision; the original
  working tree and all running services remain intact.
  Date/Author: 2026-11-11, Codex.

- Decision: correct only the obsolete help-link test expectation and repeat the
  exact full baseline before dependency changes.
  Rationale: existing normative UI behavior already works; restoring an unused
  JS global would alter production code solely to satisfy an outdated assertion.
  Date/Author: 2026-11-11, Codex.

- Decision: after the green M0 checkpoint, build candidates from a clean
  detached checkout of its reviewed revision using the canonical Dockerfile
  and Compose overlays. Materialize and verify LFS through canonical tooling.
  Rationale: avoid embedding unrelated local outputs or ignored state, preserve
  the operator's current branch/worktree, and bind source context to a revision.
  This does not change wepp1's deployment workflow or its host-local build.
  Date/Author: 2026-11-11, Codex.

- Decision: adopt the owner-ratified M0 policy and use the existing private
  deployment repository's `.local/dependency-security/` for evidence and approved
  policy hashes, with 0700 directories and 0600 records.
  Rationale: Roger selected this store and approved the concrete policy. The
  local filesystem has sufficient observed capacity; remote CI ingestion still
  requires M3/M4 validation. No production rollout or advisory-risk exception
  was authorized by this decision.
  Date/Author: 2026-11-11, Roger; recorded by Codex.

- Decision: reject the tested Trivy release for adoption and qualify the pinned
  Syft/Grype pair as the smallest justified alternative.
  Rationale: the retained real GDAL omission falsifies the simpler scanner's
  acceptance condition. The pair adds a second distribution/schema and a larger
  database; qualification remains conditional on scoped parser use, trusted
  policy authority, protected retention, and the full baseline.
  Date/Author: 2026-11-11, Codex with independent security review.

- Decision: confine M0 scanner trials to temporary, private image archives with
  an unprivileged read-only container, no Docker socket, and no runtime mounts.
  Rationale: measure tool capability before adoption without granting scanner
  access to host workloads. A fixture scan is not a production disposition.
  Date/Author: 2026-11-11, Codex.

- Decision: treat the exact common image and exact frontend lock as the evidence
  boundary rather than the requirements text alone.
  Rationale: installed OS/Python state, vendored inputs, build resolution, and
  emitted browser assets can differ from a manifest-only scan.
  Date/Author: 2026-11-11, Codex; subsequently owner-ratified at M0.

- Decision: evaluate and pin a non-runtime scanner before adoption.
  Rationale: the repository has no existing scanner precedent, and adding an
  unreviewed supply-chain tool to CI/deployment would recreate the same trust
  problem this package addresses.
  Date/Author: 2026-11-11, Codex.

- Decision: fix compatible applicable advisories in bounded batches and defer
  incompatible native/framework migrations explicitly.
  Rationale: the July Dependabot package demonstrated that forcing an
  incompatible Python/native pair can make the image invalid; a large batch also
  obscures the causal dependency when tests fail.
  Date/Author: 2026-11-11, Codex.

- Decision: place a future wepp1 gate after image build and before service
  disruption, with no silent fallback.
  Rationale: a missing/stale/blocking report must leave the known-good stack
  running and make the operator failure explicit.
  Date/Author: 2026-11-11, Codex; design subsequently owner-ratified at M0, rollout separate.

- Decision: require exact full pytest, npm lint, and full npm tests before
  handoff.
  Rationale: the operator explicitly requested full pytest and npm validation;
  dependency changes can have cross-cutting compatibility effects.
  Date/Author: 2026-11-11, operator.

## Outcomes & Retrospective

The parser candidate now has actual artifact and complete direct-inventory
readback evidence. Its three upgraded packages have no remaining scanner rows.
The first frozen producer bundle remains rejected on the known diagnostic
classification defect. Corrected collection 6 passes that boundary and rejects
unresolved native coverage; remaining findings independently block readiness.
No M1/M3/M4 completion or deployment is implied.

The isolated OAuth candidate also builds cleanly and passes its real-library
callback suite against that exact image. The required dependency import remains
isolated from forest until final integration/activation is authorized and ready.
Its fresh scan removes all 18 Authlib rows, but the actual gate rejects unresolved
native coverage. The deployment workflow choice is still pending. CI producer
integration, image-bound dispositions and the final exact full test commands
remain required; this continuation does not complete M4.

The M3 manual importer is implemented and passes focused/local evidence checks
and scoped independent review. Full pytest passes with 13,533 passed and 435
skipped at 2026-11-11 08:52 UTC; npm lint and all 1,069 npm tests pass.
The operator's CI
retrieval method remains an external prerequisite; this does not replace or
alter host-local Compose deployment. See `artifacts/20261111_importer_validation.md`.

M0 is accepted with a green full baseline, reviewed tooling/policy and this checkpoint. M1 is in progress. Source/manifest identity was recaptured, full pre-change gates
found one stale test assertion (corrected, full rerun passes), and confined scanner trials produced actual inventory, matching,
and failure evidence. Independent correctness, security, and operations reviews
refined the policy proposal. Trivy's GDAL omission blocks its adoption; the
Syft/Grype alternative is approved for scoped evidence collection. Roger ratified
the policy and selected protected storage. Qualification evidence is retained in
`/workdir/weppcloud-deployments/.local/dependency-security/evidence/m0-20261111T0505/`,
with the gitignored local `out/` path and original temporary scanner path as
symlinks. Full baseline logs are retained under private `baseline-initial/` and
`baseline-final/`, with final manifest hash in the M0 receipt. Manual CI handoff
and deployed retention behavior remain unvalidated.

A preparatory unchanged-source image now exists at
`sha256:1819856096bf838cdf32fe52b035d13971e6aaa3aad4652b63759926fae23d74`;
see `artifacts/20261111_baseline_image.md`. The required full baseline rerun passes with 13,502 tests. Classified native inventory preserves all package artifacts, but
freshness, executable coverage and advisory dispositions remain blocking.

Primary application dependencies and production systems remain unchanged.
A detached checkout holds the bounded crypto/TLS candidate; a separate isolated
Compose test project passes focused checks. The test Dockerfile/Compose now
accept an explicit candidate base while retaining their existing digest default;
actual extension build, layer ancestry, runtime identity, native/Python version
readback and 51 focused tests pass. The npm workflow now runs lint before tests;
generation check passes using the existing repository virtualenv. No M1-M5
acceptance is claimed.

## Context and Orientation

Work from `/home/workdir/wepppy`. Before editing, read the root `AGENTS.md`,
`docker/AGENTS.md`, `.github/workflows/AGENTS.md`, `tests/AGENTS.md`,
`docs/standards/dependency-evaluation-standard.md`, and
`docs/standards/generated-artifact-validation-standard.md`.

The common production image is built by `docker/Dockerfile`. The base image
creates `/opt/venv` and installs `docker/requirements-uv.txt`, installs Debian
libraries and tools, loads DuckDB's spatial extension, and vendors Rosetta,
WEPPcloud2, WBT, and WEPPpyo3. Its static-builder stage uses
`wepppy/weppcloud/static-src/package-lock.json` and copies only built assets into
the runtime image. The production Compose definition names this shared image
`${WEPPCLOUD_IMAGE:-wepppy:latest}`; the wepp1 overlay changes runtime UID/GID
and mounts but continues to use the common Dockerfile.

An SBOM is a machine-readable list of components in an artifact. It is useful
only when bound to a specific image and checked for coverage. A vulnerability
scanner compares identified components with an advisory database. A scanner hit
is evidence that a package/version may be affected; reachability and deployment
configuration still require review. Conversely, a clean report is incomplete if
the scanner missed a vendored repository or downloaded binary.

Raw SBOM and scan output can be large and changes whenever advisory databases
change. Store it beneath gitignored
`out/security-audit-20261110/f6/<image-id>/` during local work or as a protected
CI artifact. Track its SHA-256, tool/database identities, image/lock identities,
summary, and every disposition in this package. Never include runtime secrets,
registry credentials, private run identifiers, or project data.

The isolated full Python runtime uses `docker/Dockerfile.test` and
`docker/docker-compose.test.yml`. The Dockerfile now exposes
`WEPPCLOUD_TEST_BASE_IMAGE` with the previous digest as its default. To validate
dependency changes, have
the dependency-security workflow pass the locally built candidate tag or exact
published digest. This keeps unrelated baseline workflows stable while proving
the candidate under review.

Generated workflows under `.github/workflows/` must be changed through their
source specs in `.github/forest_workflows/` and rebuilt with
`scripts/build_forest_workflows.py`. The manually maintained common-image
publication workflow is a separate file and must remain a non-deploying
openwepp.org/compatibility mechanism; it does not replace wepp1's host-local
build and `scripts/deploy-production.sh`.

## Plan of Work

### Milestone 0 - Freeze baseline, select tools, and ratify policy

Start by recording the source revision, worktree state, manifest/lock hashes,
current Compose-resolved common image name, and exact commands. Run the required
pre-change regression baseline through canonical wrappers:

    wctl run-pytest tests --maxfail=1
    wctl run-npm lint
    wctl run-npm test

All three must exit zero before dependency changes. If one fails, retain the
complete output and reproduce it without changing dependencies. Repair or
separately disposition the baseline blocker before continuing; do not redefine a
partial/segmented run as the required baseline.

Complete `artifacts/20261110_scanner_evaluation.md`. Apply every relevant gate
from the dependency evaluation standard: precedent, capability overlap,
dependency tax, operational fit, and explicit decision. The selected scanner
must be distributed by immutable version/digest, run outside the application
runtime, emit standard machine-readable output, reveal its advisory-database
identity/freshness, and inspect a local image without reading secrets or project
mounts. Record rejected candidates. If no candidate meets the contract, stop and
report the blocker rather than introducing a manifest-only fallback.

Review and ratify `artifacts/20261110_scope_and_policy_decision.md`. Decide the
freshness window, blocking thresholds, exception schema, raw artifact retention,
CI event/runner permissions, and wepp1 failure behavior. The default proposed
policy blocks undispositioned applicable Critical/High and requires explicit,
expiring treatment of applicable Medium findings. Retain a reviewed checkpoint
before changing dependencies, workflows, or deployment code.

Milestone acceptance is a green pre-change full baseline, reviewed scanner
choice, approved policy, and a checkpoint revision. No production behavior has
changed.

### Milestone 1 - Build and reconcile the exact baseline image

Resolve the production common-image name and wepp1 build arguments from the
canonical Compose configuration. Build the common image without cache from the
reviewed source and record the local image ID. Use immutable base and vendored
references where already supported by Dockerfile build arguments; if the
ordinary wepp1 defaults remain floating, record their resolved identities and
open a policy finding rather than silently claiming reproducibility.

Run the selected toolchain against that image ID and retain:

- SBOM in a standard JSON format;
- vulnerability result for Debian and Python components;
- direct `/opt/venv` inventory and `dpkg-query` inventory;
- resolved Git/vendor and downloaded-binary provenance;
- `npm audit --json` for the complete static-builder lock and
  `npm audit --omit=dev --json` for production browser dependencies;
- hashes of all raw reports and the exact requirements/lock files.

Reconcile the SBOM against direct inventory. Select sentinel packages across
authentication/OAuth, crypto/TLS, ASGI/Flask, parser/rendering, HTTP/network,
geospatial/native, RQ, and report/notebook surfaces. Explain every missing or
duplicated component. Update `artifacts/20261110_surface_inventory.md` with
coverage and exclusions.

Create `artifacts/20261110_advisory_dispositions.md`. Normalize aliases while
retaining source IDs. For every result record installed version, affected range,
fixed version, image layer/path, import/call sites, production reachability,
exploit preconditions, existing controls, and one policy disposition. Search
actual application imports and routes; do not infer reachability solely from the
requirements file.

Milestone acceptance is a reproducible baseline tied to one exact image, a
coverage reconciliation, and a complete reviewed disposition matrix. The old
168-record summary is superseded only if the new evidence is retained and its
differences are explained.

### Milestone 2 - Apply compatible upgrades in bounded batches

Order changes by risk and coupling. Start with applicable authentication/OAuth,
cryptography/TLS, and HTTP-client fixes. Continue with hostile-input
parser/rendering packages. Handle general frameworks and build tools only after
their direct security findings and compatibility constraints are understood.
Keep geospatial/native pairs together and defer a version whose Python binding
cannot match the system library or owned native component.

For each batch:

1. Freeze exact old/new versions, advisory IDs, upstream source/changelog, and
   transitive changes.
2. Update only the relevant manifest/lock entries; use clean package-manager
   resolution and inspect all transitive diffs.
3. Rebuild the common image without cache and inspect installed versions and
   native imports.
4. Re-run the exact image scan and policy evaluation.
5. Run focused tests for every changed boundary, including valid and hostile or
   failure states.
6. Record outcome before starting the next batch.

OAuth/auth packages require login/session/JWT/OAuth success and negative tests.
Parser/rendering packages require their hostile-input corpus and normal controls.
Network/TLS packages require certificate, redirect, timeout, and error-contract
tests relevant to their current call sites. RQ packages require worker/enqueue
compatibility and canonical graph checks if wiring changes. Geospatial/native
packages require actual import, ABI/version readback, and representative artifact
semantics. Do not change application policy or scientific outputs merely to make
an upgrade pass.

If an upgrade needs a major migration, record the exact blocker, current
compensating control, owner, and follow-up package. Do not leave a hidden pin or
force an incompatible combination.

Milestone acceptance is that every compatible applicable fix is in the
candidate, each batch has focused evidence, and remaining items are explicit
policy dispositions or separately scoped blockers.

### Milestone 3 - Wire artifact-bound gates into CI and deployment

Create stable repository-owned interfaces under `tools/security/`, for example
`audit_wepppy_image.sh` and `evaluate_dependency_findings.py`. The shell entry
point invokes the pinned external scanner and direct inventories; the Python
policy evaluator uses the standard library where practical and checks image ID,
lock/report hashes, freshness, thresholds, exceptions, and report schema. Add
fixtures/tests for clean, blocking, duplicate, missing, stale, image-mismatch,
approved exception, expired exception, and malformed exception cases. Never
accept a schema/tool error as a clean result.

Make `docker/Dockerfile.test` accept an explicit common base image build argument
while retaining the current digest default. Pass that argument through
`docker/docker-compose.test.yml`. Add or update a source workflow in
`.github/forest_workflows/` so changes to the production Dockerfile,
requirements, primary package lock, scanner policy/scripts, or relevant workflow
source build and scan the candidate, build the test image from that candidate,
and run the full baseline. Update the npm source workflow to run both lint and
full tests for the primary frontend. Regenerate `.github/workflows/` and verify
`scripts/build_forest_workflows.py --check`.

Keep pull-request scanning on an isolated runner with `contents: read`, no
registry write token, no production secrets, no `/wc1` or `/geodata` mount, and
job-local image/report cleanup. Publishing remains restricted to the existing
trusted workflow. Do not run untrusted PR code with a production Docker socket
or credentials; the selected scanner execution design must pass security review.

In `scripts/deploy-production.sh`, integrate the same policy interface after a
candidate common image exists and before Step 3 stops/recreates services. Resolve
the actual image name/ID from rendered Compose. Write evidence under a 0700/0600
deployment-state directory and avoid environment/secret output. A missing tool,
database refresh failure, report mismatch, expired exception, or blocking
finding exits nonzero while leaving the current stack running. Do not apply the
common-image gate to unrelated targeted CAP/batch operations unless their
resolved deployment set actually selects a newly built common image.

Test the deploy hook with a fake scanner/policy fixture and a disposable image;
do not stop local or production services merely to test control flow. Verify the
gate's location by asserting no stop/up command occurs on failure.

Milestone acceptance is deterministic local/CI behavior, generated workflow
parity, least-privilege review, and a pre-activation failure that preserves the
running stack.

### Milestone 4 - Build and validate the final candidate

After the last dependency, lock, policy, workflow, or test-image change, build
the common image without cache from the exact final revision. Generate fresh
SBOM/scan/npm reports and direct inventories, and prove every report matches the
final image ID or lock hash. Run the candidate gate and expect success. Build the
isolated test image from that same common-image candidate and inspect its base
identity and installed sentinel versions.

Run all focused tests identified in M2 and M3. Then run the operator-required
complete gates exactly:

    wctl run-pytest tests --maxfail=1
    wctl run-npm lint
    wctl run-npm test

All commands must exit zero. If the full pytest command stops at a baseline or
environment failure, retain it and keep M4 open until the actual command passes
or the operator explicitly changes the requirement. Do not substitute shards,
selected modules, pre-import workarounds, or aggregate accounting for a green
required command.

Also run workflow generation/check, scanner policy tests, stub/test hygiene when
affected, Docker/Compose configuration validation, scoped documentation lint,
and `git diff --check`. Retain concise validation evidence with revision, image
IDs/digests, tool/database identities, report hashes, commands, counts,
durations, exit statuses, and limitations.

Obtain independent correctness/UX, QA/code-quality, security/supply-chain, and
wepp1 operations reviews. Close every High/Medium review finding or obtain the
explicit, time-bounded risk acceptance required by policy. Update the package,
tracker, advisory matrix, and audit board.

Milestone acceptance is a reviewed artifact-bound final candidate with every
required focused and broad gate green. This establishes local/environment
readiness, not deployment.

### Milestone 5 - Separately authorized wepp1 rollout

This scaffold does not authorize deployment. If the operator later authorizes
rollout, use the installed `wctl` preset and `scripts/deploy-production.sh`; do
not invent a registry or ad hoc Compose path. Record the exact source revision,
candidate image ID, gate evidence, running container image IDs, and deployment
receipt. Verify the dependency gate runs before activation and the services
consume the scanned image.

Run production-equivalent health and a bounded set of ordinary authentication,
browse, query/RQ, parser/report, and worker checks selected from changed
dependencies. Inspect user-visible outputs and relevant generated artifacts, not
only container health. Do not use hostile live payloads. Preserve a known-good
rollback image and ensure rollback does not bypass the dependency policy without
an explicit accepted-risk record.

Milestone acceptance is the exact reviewed image running on wepp1 with retained
post-deploy evidence. Distinct excluded images and accepted risks remain named;
do not claim all of wepp1's supply chain is verified by the common-image gate.

## Concrete Steps

All commands run from `/home/workdir/wepppy` unless stated otherwise.

1. Establish the baseline and preserve unrelated work:

       git status --short
       git rev-parse HEAD
       sha256sum docker/requirements-uv.txt \
         wepppy/weppcloud/static-src/package-lock.json
       wctl docker compose config --format json > /tmp/wepppy-compose-config.json

   Do not print or retain secrets from rendered configuration. Extract only the
   image/build fields needed for the evidence receipt, then remove the temporary
   config.

2. Run the pre-change broad gates and retain exit status/count/duration:

       wctl run-pytest tests --maxfail=1
       wctl run-npm lint
       wctl run-npm test

3. Complete the scanner evaluation and policy review. Create the gitignored raw
   evidence root with mode 0700 only after the tool is approved.

4. Build the baseline image through the canonical Compose configuration without
   cache, inspect its ID, generate evidence, and complete the disposition matrix.
   Record the exact tool-specific commands in this plan once M0 selects them.

5. Implement one dependency batch at a time with `apply_patch`, focused tests,
   clean rebuild, scan, and disposition updates.

6. Implement repository-owned policy interfaces, candidate test-image wiring,
   generated workflow source/output, and the pre-activation deploy hook. Run:

       python3 scripts/build_forest_workflows.py
       python3 scripts/build_forest_workflows.py --check

7. Build the final candidate and run M4 exactly. Store raw reports outside Git;
   store tracked hashes and summaries under this work package.

8. Stop before M5 unless production rollout is explicitly authorized.

## Validation and Acceptance

Acceptance is based on the following observable behaviors:

- The SBOM and scanner identify the same exact final image used by direct
  inventory and the isolated test runtime.
- Known sentinel Python and Debian packages appear with their direct-readback
  versions; missing unmanaged components are explicitly supplemented.
- Every scanner result has one reviewed disposition; no applicable Critical/High
  result is undispositioned.
- A stale report, changed image, missing database identity, malformed/expired
  exception, or synthetic blocking finding causes a nonzero gate result.
- The deploy-path failure occurs before any service stop/recreate command.
- Compatible upgrade batches preserve their actual application boundaries and
  clean no-cache image construction.
- `wctl run-pytest tests --maxfail=1`, `wctl run-npm lint`, and
  `wctl run-npm test` all exit zero after final changes.
- Workflow generation is current, CI permissions are least-privilege, and raw
  evidence contains no secrets or project data.
- Status language accurately distinguishes scaffolded, locally validated,
  environment validated, and deployed.

A large green test count cannot replace an image/report identity mismatch, and a
clean scanner result cannot replace the required full tests.

## Idempotence and Recovery

Image builds, scans, direct inventories, policy evaluation, and tests are
read-only with respect to project/run data and can be repeated. Raw evidence is
written to a new image-ID-specific directory rather than overwriting a prior
receipt. Advisory database refreshes create new evidence with a new timestamp
and hash; they do not rewrite an accepted report.

Never scan by mounting production secret directories or project data. Never
delete the current known-good image as part of candidate validation. Use explicit
candidate tags and validate resolved image IDs before cleanup. Clean only
job-local images/reports whose exact names and directories were created by this
package.

If a dependency batch fails, retain the failing manifest diff and evidence,
revert only that uncommitted batch with `apply_patch`, and rebuild from the last
reviewed candidate. Do not weaken tests or the scanner policy to make the batch
pass. If the deploy gate fails, it exits before activation; correct evidence or
disposition and rerun. A scanner outage is an explicit failure, not a clean
fallback.

For a deployed compatibility regression, restore the exact retained known-good
image through the canonical deployment recovery path. Record whether the
rollback image satisfies current policy; if not, require an explicit temporary
risk decision rather than silently bypassing the gate.

## Artifacts and Notes

The starting source revision is `2041fb8e267de3a1572d9fb4f4a62e725b75cc91`.
The worktree contains unrelated user documentation and generated-file changes;
preserve them. Always ignore
`wepppy/weppcloud/routes/usersum/generated/docs_index.json` unless explicitly
asked to modify it.

Initial manifest identities at scaffold time were:

    docker/requirements-uv.txt
      d15ff4fd344453b1d10f528178c90127c78e3748790a36768d38136ac7aacb80
    wepppy/weppcloud/static-src/package-lock.json
      2ddc0117c0bf2c559d2509bded8964801092fe68e4046ec3c8fa3df9c6877a92

These hashes are discovery evidence, not accepted baselines; M0 must recapture
them at its reviewed starting revision.

Required closeout artifacts are the completed policy decision, surface
inventory, scanner evaluation, advisory disposition matrix, validation receipt,
correctness review, QA review, security review, operations review, and optional
rollout receipt. Raw JSON/SBOM/log files remain gitignored or protected CI
artifacts with tracked hashes.

## Interfaces and Dependencies

The final implementation must expose stable, non-runtime interfaces under
`tools/security/`:

- an image-evidence command accepting an explicit image reference/ID and output
  directory, invoking only the approved pinned scanner distribution;
- a policy evaluator accepting explicit SBOM/scan/npm report paths, image ID,
  lock hash, policy, and exception file, and returning nonzero on schema,
  identity, freshness, or finding failure;
- machine-readable policy/exception fixtures whose accepted-risk entries require
  advisory/package identity, owner, rationale, compensating control, expiry, and
  review trigger.

Exact filenames may be finalized at M0, but CI and deployment must call the same
repository-owned policy interface. The scanner is a build/security tool, not an
application dependency. Do not import it into WEPPcloud, add it to
`docker/requirements-uv.txt`, expose a service endpoint, or grant it access to
runtime secrets and mounts.

`docker/Dockerfile.test` must support an explicit candidate common-image base
while retaining a safe immutable default. Generated workflows must be edited
through `.github/forest_workflows/`. wepp1 deployment remains host-local Docker
Compose through `scripts/deploy-production.sh`; the GHCR publication workflow
continues to serve its existing non-deploying/Kubernetes compatibility purpose.

## Revision Note

2026-11-12: Record real parser collection, independent inventory reconciliation,
the exact conservative-warning correction and retained unresolved findings.

2026-11-11: Record accepted M0 checkpoint and itemized M1 review packet. The
preparatory image remains bound to its original source revision; documentation
and test additions do not permit relabeling the copied image context.

2026-11-11 M0 execution: record development-runtime identity, independent policy
review, Trivy's reproduced GDAL matching gap, justified alternative-tool trials,
and retained failure semantics. Record owner policy/storage ratification and
scoped alternative-tool approval. Full regression remains open; no dependency
or deploy implementation was started.

2026-11-11: Initial ExecPlan created for F6. It rejects the preliminary advisory
count as artifact proof, requires evaluated/pinned scanner tooling, binds CI and
deployment decisions to the exact common image, and makes full pytest, npm lint,
and full npm tests mandatory per operator direction.

2026-11-12 continuation: implemented standalone policy evaluator after the
ratified M0 policy, with 35 local tests and independent security review; component
receipt records corrected coverage failures and remaining integration. Promoted
the previously qualified crypto/TLS patch. No M1/M3/M4 milestone acceptance is
claimed. Authenticated SSH/SCP via the existing trusted `runner-02` alias has
passed a disposable synthetic bundle transfer and private import. Actual CI
producer collection and its bounded cleanup window remain unvalidated.

2026-11-12 deployment integration decision: independent review found that fresh
no-cache rebuilds conflict with exact-image manual approval on a later invocation.
The concrete retained-candidate resume versus same-invocation review proposal is
in `artifacts/20261112_deploy_approval_boundary.md`. Operator selection is pending;
no generic skip-build bypass or deployment workflow change has been implemented.
Producer qualification and advisory review continue independently.
