# Integrate the explicit JSON soil source with durable provenance

## Purpose


Allow operators to select the unofficial soil service for WEPPpy while retaining
which endpoint/profile/release supplied the cached data. Preserve XML by default
and scientific soil outputs. Execute against the canonical soil-data-source-provenance
contract; this is faithful integration, not a mocked transport demonstration.

## Next phase: mirror-first rollout

The operator's 2026-11-18 amendment to the canonical provenance contract directs
mirror-first defaults and bounded, observable USDA SDA fallback. The original
explicit-source integration is complete; the amendment is a new implementation
phase. Execute the service plan at /workdir/soil-data-access/docs/mirror-first-rollout.md
with the existing client/cache identity rules as the baseline. Comprehensive
geographic/live parity is deferred until SDA recovery, not a prerequisite.

## Progress

- [x] (2026-11-18 06:24 UTC) All three host activations and eight consumer reachability checks passed. Four queued canary jobs produced 152 reference-matching prepared soils and verified base provenance. See artifacts/production-activation.json.

- [x] (2026-11-18) Integrate approved deployment tooling as PR #679, merge 0f2ec047d9f323877e84e489d3f5006bf0b559d5. Load identical common image on all hosts and renderer on wepp2; preserve source-image receipt.
- [x] (2026-11-18) Fresh production database backup and live upgrade f6b8d27a901c → a7c1106e42b9; 5,482 users retain legacy account defaults. CILogon remains inactive.

- [x] (2026-11-18) Implement and validate operator-directed deployment-script repair (118 tests; integrated as PR #679): retain absence for first-install services, preserve existing rollback images, remove only newly created containers on failure, and preserve volumes. Reuse already built application images.

- [x] (2026-11-18) Assemble combined committed release in isolated task worktree; preserve shared WIP. Back up production application database and successfully rehearse account migration on explicitly asserted disposable PostgreSQL database; all existing data hashes unchanged.
- [x] Finish production service preparation, exact-candidate integration gate, retained builds, live migration and full host rollout.

- [x] (2026-11-18) Recover nationwide SSURGO and STATSGO2 coverage, transition forest release pins, and verify cavernous-oxygen: 21 base provenance hashes, all 32 prepared inputs, and 152 reference-matching canary files. See service nationwide-recovery-plan.md.


- [x] Inspect six collection consumers, legacy transport/cache and frozen service contracts.
- [x] Author operator-authorized canonical contract and data compatibility plan.
- [x] Complete independent reviews; contract ancestors 090e9f2b6 and 2f9aff0a7.
- [x] Implement transport, cache identity/events, base-sidecar and NoDb selection (39f24ce92).
- [x] Run 75 focused tests, two-module stubtest, stub hygiene and broad-exception gate; broad suite attempted with unrelated environment blockers retained.
- [x] Real PostgreSQL/API fresh-cache replay: 24,049 records, 499 valid soils, six unchanged non-valid outcomes, 501 canonical files and 499 verified sidecars.
- [x] Retain review/evidence and update tracker; publish task branches task/ssurgo-json-provenance and task/wepppy-json-parity.

- [x] Record the operator's mirror-first/SDA-fallback direction and revised parity scope.
- [x] Freeze selection-event schema, total timeout, default/migration behavior and transport ADR; complete contract reviews.
- [x] Implement collection-level source selection across all six consumers, retaining source-separated caches and failure evidence.
- [x] Integrate forest dev Compose, import official regional data, and pass bounded queued soil/fallback acceptance.
- [x] Integrate the protected Compose change after exact-SHA/digest owner approval, then activate the shared forest client default.
- [x] Deploy the full wepp.cloud release in host order wepp1, wepp2, wepp3, including required application database migrations and national soil service activation. Forest1 is explicitly deferred; comprehensive live SDA validation remains deferred.

## Context and plan


Worktree: /workdir/wepppy-ssurgo-json, branch task/ssurgo-json-provenance. The shared
/workdir/wepppy checkout has unrelated edits and must remain untouched. Service
repo: /workdir/soil-data-access, branch task/wepppy-json-parity. Its runtime is
committed at 9dc2264 and local validation at ad38881; frozen legacy reference uses
WEPPpy 917708c. The current WEPPpy base only adds explicit HTTP 5xx diagnostics to
the soil module, with no changed numerical path.

Add wepppy/soils/ssurgo/source.py to validate explicit settings, perform bounded
JSON requests and persist cache identity/retrieval events. Extend collection
construction and the existing five query builders without changing default XML
helper signatures at call sites. Use the existing cache schema and numerical
builder. Create provenance sidecars alongside generated base soils. Wire the six
Soils call sites through persisted settings and namespace selected JSON cache paths.
Clear only the selected identity; leave source caches and other releases intact.

Run focused tests through wctl after verifying which checkout the container consumes.
Do not remount/recreate the shared development stack. If its mount rejects this
worktree, retain the rejection and use an isolated, already-authorized test setup
against the exact candidate checkout, recording identities explicitly. Check stubs
and run the broad suite when feasible; retain unrelated blockers honestly.

Extend the service parity runner to query the real API into empty separate caches
with candidate WEPPpy and external networking blocked. Import complete fixtures
separately with their replay release IDs. Compare records and emitted soil bytes
using only the existing Build Date/Source File exclusions; retain failures and
known legacy negatives. Verify sidecar soil hashes and cache retrieval identities.
Do not claim full NoDb/RQ/raster workflow or national source coverage from these runs.

## Validation and recovery


Use disposable scratch directories and isolated Compose project names. Never clear
production caches or delete retained volumes. Rollback selection returns to XML
and the retained original cache. Provenance mismatch fails; it is not fixed by
rewriting identity. Preserve raw diagnostics outside public artifacts. Tests must
cover real filesystem/SQLite and local HTTP boundaries, plus real generated output.

## Surprises & Discoveries

Production follow-up: image-ID Docker archives leave existing Compose tags unchanged; align verified imported IDs with those tags before resume. Wepp2 caught the mismatch before queue drain. Wepp1 UFW INPUT dropped local bridge connections to the shared Tailscale endpoint. A Compose-local endpoint candidate was prepared but never activated because saved projects move between hosts. Restore the original config and permit only the backend bridge/subnet to the existing Tailscale port. All eight consumers then passed; application privileges and public exposure are unchanged.

Wepp1 retained activation uses raw Docker Compose, which did not inherit the soil-data profile from wctl’s temporary env file. The complete service check caught absent soil services; the operator-owned attempt was interrupted through its recovery trap, existing workloads restored, and queue dequeue resumed. The retry exports COMPOSE_PROFILES=soil-data explicitly; raw service-list readback includes both soil services. An earlier receipt-path typo was rejected before queue drain. Retain both failed logs with the successful attempt.

The canonical script rejects first installation: capture_known_good_state requires a running container for every candidate service. National soil services have never existed on wepp1. The operator chose a script repair over a one-time manual bootstrap. Absence must be captured and checked, not treated as an existing known-good image.

Production discovery: all three hosts are clean at 917708c90dce46bbab920ecf9ce5f315e8611290; wepp1 application database reports f6b8d27a901c. The account migration a7c1106e42b9 exists on committed local master, not remote master b301ff64c. Its precondition rejects duplicate normalized login emails. Release assembly must account for local-master changes rather than assume remote master contains the requested migrations. No production mutation has occurred.

The regional default failed all 22 Colorado keys in cavernous-oxygen while SDA returned HTTP 5xx. National imports contain those keys and both SSURGO/STATSGO2 domains; source/import parity and real queued recovery passed. Treat national loading separately from deferred live geographic parity.


The current sidecar hardcodes USDA attribution; old rows do not have verified source
lineage. Existing _sync does not persist all-empty negative responses. JSON will
record those attempts atomically; XML behavior remains unchanged apart from additive
honest provenance. Local candidate fallback catches SsurgoRequestError/ValueError;
a distinct source-contract exception must propagate instead of silently falling back.

The existing development image differs from the frozen reference in Python, libc,
and Rosetta source. Its first ssurgo-004 run failed two diagnostic-comment bytes
(5.917715041673642 versus 5.917715041673644). Preserve that failure and the fixed
comparison rules. Matching the reference libraries/interpreter through read-only
mounts in the isolated client container restores all five exact artifacts; this is
a matched-environment transport result, not proof of deployment-image equivalence.

## Decision Log

2026-11-18 production routing: retain one cross-host source endpoint; do not persist a wepp1-only DNS name in projects. The smallest fix for confirmed UFW INPUT drops is a persistent bridge/subnet/destination/port-specific allow rule. Document exact rollback and bridge-recreation caveat in docs/infrastructure/soil-data-production.md, Local firewall and shared source identity. Image import requires explicit Compose-tag alignment before activation; it neither rebuilds nor changes running containers.

2026-11-18: Repair the existing canonical entry point for first-install services. A missing running container is accepted only if no stopped container exists and inventory succeeds. Record zero-count rows; verify absence until cutover; on failure remove newly introduced containers without deleting volumes, restore existing images, and retain the RQ fence if either operation fails. Use build-once direct transfer as the stated default: export/load exact image IDs, verify a checksum-pinned source receipt, and create separate host-local candidates without rebuilding. No registry is introduced. Keep application builds reusable across deployment-tool-only changes.

2026-11-18: Operator prioritizes wepp.cloud over forest1 and explicitly requires a full deployment to include other changes and database migrations. Prepare a combined release in an isolated task worktree, preserve shared checkout WIP, and use scripts/deploy-production.sh with installed wctl in wepp1 → wepp2 → wepp3 order. Preserve the independent CILogon registration/credential activation hold. Back up and rehearse application migration against an explicitly asserted disposable database before live migration. Reuse national soil import/parity evidence; activate national SSURGO and STATSGO2 together, then verify generated soil artifacts from production workers.

2026-11-18: Nationwide SSURGO and STATSGO2 are required for the shared default. The regional rollout was insufficient during the SDA outage; loading national data is mandatory while full live parity remains deferred. Canonical scope is now in soil-data-source-provenance-contract.md, Shared default geographic coverage.

2026-11-18 follow-up: accept retained SSURGO/STATSGO fixture evidence for broader
query/builder behavior and move comprehensive geographic/live testing to recovery.
The operator now prefers the mirror as default with SDA fallback. Keep actual data
loading distinct from evidence generalization; preserve the real supplier in every
cache/artifact record. These are prospective changes, not current runtime behavior.



2026-11-18: the operator explicitly requested endpoint provenance with JSON integration.
Use persisted per-project selection, SHA-256 cache namespaces, embedded identity,
and additive base-soil sidecars. Do not place server comments into scientific .sol
files or silently relabel historical rows. Require an explicit expected release so
warm-cache reuse needs no metadata request and cannot mix releases.

## Outcomes & Retrospective

2026-11-18 production activation completed: canonical deployments succeeded on wepp1, wepp2, and wepp3 using the same built images. National SSURGO and STATSGO2 contain 22,073,263 rows; live account migration preserves 5,482 legacy defaults. Authenticated HTTPS home/profile return 200. Four real queued jobs verify both source sidecars and 152 exact reference inputs. Eight web/RQ consumers reach the shared pinned endpoint. Evidence: artifacts/production-activation.json. Forest1, CILogon activation, public API hosting, and comprehensive live SDA parity remain deferred. Earlier preparation statements below are historical checkpoints.

2026-11-18 production preparation: PR #678 integrated, full wepp1 images built and retained, national SQL verified, and database rehearsal passed. The canonical first-install limitation required a bounded operator-directed script repair. Image reuse and first-install tests pass; actual-image read-only checks pass. Script integration, local release bindings, live migration, host activation, and generated-output checks remain pending.

National recovery completed on forest: 22,073,263 imported rows, source-family projection parity, successful real-project build/preparation, 152 reference-matching canary inputs, and authenticated HTTPS checks. Retained evidence is artifacts/national-activation.json. Regional qualification alone was insufficient for the outage-resilience deployment objective.


Implementation and independent review complete. Paired ssurgo-004 real-service run
passes all five canonical artifacts in the matched reference numerical environment.
All six corpus cases have been accounted for: five complete (one empty) and one
incomplete explicitly excluded. Full matched-environment parity passes; evidence
is retained in soil-data-access/artifacts/wepppy-parity/json-client. Public deployment
and broader service release gates remain deferred.

Integration follow-up, 2026-11-18 UTC: PR #673 revealed inherited unmerged local
master changes. Preserve that history and integrate only the four soil commits via
task/ssurgo-json-merge from remote master. No protected policy paths change; all
soil source files remain identical and 75 focused tests pass on the new checkout.

Next-phase outcome: acceptance direction and pending contract recorded. No default,
cache, project, or deployed service changed in this documentation checkpoint.

## Authorized forest execution, 2026-11-18

Implement the canonical Forest contract and ADR-0145 from task/mirror-first-contract.
Use a bounded source-selection factory shared by six NoDb consumers. Extend HTTP
acquisition for an absolute selection budget and bounded XML fallback, add typed
availability errors and durable selection events, and preserve explicit-source code.
Keep old saved identities explicit; environment defaults initialize only absent state.

The service branch task/mirror-first-rollout owns an official-source importer and
portable Compose integration. Import Idaho SSURGO and retained STATSGO2 Virgin
Islands downloads as a scoped combined release, independently compare raw projections,
and build keys outside the replay corpus. Do not claim nationwide data from this
regional release. Use forest (verified local hostname) with isolated qualification
worker/queue and the actual runtime image first; preserve shared dirty checkout and
unrelated running services. Activate only the narrowly changed dev services after
bounded tests. Production/test-production activation remains outside this phase.

Progress: contract ancestor 43c78bf95, ADR-0145 and independent reviews complete.
Mirror-first implementation, regional import and forest Compose qualification pass.
New services run on forest; shared clients remain unchanged pending protected-policy
integration approval. Evidence: artifacts/forest-validation.md and the service's
artifacts/forest directory.

Surprises & Discoveries: PostgreSQL COPY requires ANALYZE before relationship joins
to avoid a poor initial join plan; the canceled candidate import left the prior
release intact. Review caught XML error envelopes treated as empty data, legacy
config precedence, and a connection leak after evidence-read failure; all fixed
and covered. An initial qualification comparator missed whitespace in Build Date
comments; use the existing exact two-comment-value canonicalizer and retain the
diagnostic failure. No numerical tolerance or extra exclusion was added.

Decision Log: keep only the regional source scope in the manifest; missing keys
use bounded SDA fallback. New project defaults persist, existing identity-absent
projects resolve configuration/defaults, and saved identities remain explicit.
Forest qualification uses the actual worker image and UID/GID with a separate Redis
and queue. The shared dirty checkout and existing services are preserved.

Outcomes & Retrospective: SSURGO MUKEY 78905 and STATSGO2 MUKEY 1390208 are outside
all replay caches. Each produces 76 prepared soils with exact same-image reference
parity through primary cold/warm and warm fallback. Base sidecar hashes and final
inputs are independently read back; dual failure generates no soils. Shared forest
default activation and public/test-production/production rollout remain distinct.


## Approved forest cutover, 2026-11-18 UTC

The operator approved candidate 09f6633e660c73570cc3f181bef75c6b49853ef3 and policy
digest af780106f077abb9cd1ace333aeec80cd04f2295ac94b0f96f354f9d15a08d12. PR #675
merged as 0ae17ad8a393a4fbe250241b2253b77cc475d06b with an identical tree. Required
candidate and merge governance checks passed after recording approval externally.

Progress: shared forest consumers are refreshed and source/default/readiness checks
pass. The source overlay preserves local master history, unrelated dirty files and
existing vector-upload settings. Canonical fence programs guarded the empty default,
batch and fork/archive registries, then released dequeue after readiness. Runtime
source/configuration backups remain in the ignored activation directory.

Decision Log: apply the seven approved runtime paths to the existing dev mounts;
do not rebase/reset the divergent shared checkout or replace unrelated local work.
Every Python runtime file matches the approved candidate. The Compose file retains
both its existing local vector settings and the approved soil additions. Public,
forest1 and production activation remain separate scope.

Evidence: artifacts/forest-activation contains exact approval/integration, source
hashes, consumer defaults and normal-queue canary receipts. This completes the
approved forest implementation/activation phase; comprehensive live SDA comparison
remains deferred until recovery.
