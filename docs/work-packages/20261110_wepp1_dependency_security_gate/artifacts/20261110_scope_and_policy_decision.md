# Scope and policy decision - Production dependency evidence

**Status**: Owner-ratified for implementation; milestone evidence gates remain  
**Date**: 2026-11-11 UTC  
**Finding**: F6 / SEC-06

## Scope Decision

F6 covers dependencies installed in or used to build the shared WEPPcloud
Python image produced by `docker/Dockerfile`, plus the primary frontend lock used
by its static-builder stage. A finding is not present merely because it appears
in `docker/requirements-uv.txt`, and it is not absent merely because a manifest
scanner is clean. The authoritative subject is the exact candidate image and the
exact frontend lock/build inputs.

Distinct CAP, Caddy, Redis, PostgreSQL, Go status/preflight, WEPPcloudR, and
auxiliary images must remain visible in the inventory but are not covered by a
common-image all-clear. A scanner finding that requires a major native or
framework migration becomes an explicit follow-up package; it cannot be silently
ignored or forced through an incompatible bulk update.

## Evidence Policy

Every scan receipt must record:

- source revision and clean/dirty state;
- image repository/tag, local image ID, and manifest digest when available;
- Dockerfile, build arguments, base-image references, and vendored refs;
- requirements and lock SHA-256 values;
- SBOM/scanner tool name, version, immutable distribution identity, and command;
- advisory database source/version/timestamp and scan timestamp;
- raw report SHA-256 and protected retention location;
- policy revision and exit status.

The SBOM must be reconciled with direct Python and Debian inventories using
sentinel packages from auth/crypto, framework, parser, geospatial/native, RQ,
and report surfaces. Scanner omission is a coverage finding, not a clean result.

## Disposition Policy

Each advisory receives exactly one disposition:

1. **Fixed**: the final installed version is outside the affected range and
   focused/full regressions pass.
2. **Verified not present**: direct artifact readback proves the package/version
   is absent.
3. **Not affected**: retained evidence proves platform, feature, configuration,
   or reachability excludes the vulnerable path.
4. **Accepted risk**: the owner records rationale, compensating control, expiry,
   and review trigger after security-review recommendation.
5. **Blocked follow-up**: an applicable repair requires a separately scoped
   migration; the package remains explicit about the unresolved exposure and
   cannot claim SEC-06 fully verified without owner disposition.

No applicable Critical or High result may remain undispositioned. Applicable
Medium results must be fixed or time-bounded through explicit risk acceptance.
Low results are tracked and may be scheduled according to compatibility risk.
Scanner aliases and duplicate advisory IDs must be normalized without deleting
their source evidence.

## Gate Behavior

The candidate-image gate must fail closed when the scan is missing, stale,
targets a different image/lock, uses an unapproved policy, or reports a blocking
finding. There is no implicit `|| true`, severity-only suppression, or automatic
baseline acceptance. A future emergency override requires a separately approved
break-glass contract with an owner, reason, expiry, and retained audit record.

Production remains Docker Compose through the installed `wctl` preset and
`scripts/deploy-production.sh`, reaffirmed by Roger during execution. Manual
artifact transfer does not change the host-local build or activation workflow.

For wepp1, the gate belongs after the candidate image build and before any
running service is stopped or recreated. A scan failure therefore leaves the
known-good stack running. Deployment authorization remains separate from this
design decision.

## Test Policy

Focused boundary tests run after each compatible batch. Final acceptance also
requires these exact commands after the final clean rebuild:

    wctl run-pytest tests --maxfail=1
    wctl run-npm lint
    wctl run-npm test

All three must exit zero. Partial, segmented, or diagnostic aggregate results do
not substitute without a new explicit operator decision.

## Review Gate

### Ratified M0 policy (2026-11-11)

Roger approved the proposed policy during execution on 2026-11-11 and selected
`/workdir/weppcloud-deployments/` as the protected evidence store. Independent
correctness, security, and operations design reviews are retained in this
package. This ratifies implementation requirements; it does not authorize M5
rollout or waive baseline, coverage, or runtime acceptance evidence.

- Require reports and the advisory database build timestamp to be no more than
  24 hours old at evaluation. Reject future timestamps beyond five minutes of
  clock skew. Require successful database refresh before a new scan; a cached
  report alone does not authorize activation.
- Block unresolved Critical/High findings and applicable Medium findings without
  an approved exception. Unknown severity and unrecognized scanner schema require
  review rather than being treated as Low. Preserve Low findings in the matrix.
  `Blocked follow-up` remains blocking unless a separate accepted-risk record
  passes review. A disposition label alone cannot authorize activation.
- Bind each exception to advisory aliases, ecosystem, package, installed version,
  image or lock identity, disposition, named owner and approver, rationale,
  evidence, compensating control, creation/expiry timestamps, and review trigger.
  Limit accepted-risk entries to 30 days; renewals require a fresh review.
  No exception exists merely because this proposal permits the schema.
  Normalize aliases within ecosystem/package/version/path identity; do not let
  one installation's exception cover another installation. Reject conflicting
  or duplicate exception records.
- Retain ordinary CI evidence for 90 days and activated-image evidence for at
  least 365 days and throughout that image's rollback eligibility, whichever is
  longer. Keep local raw files private (directories 0700, files 0600); only
  sanitized identity/hash summaries enter the public repository. Use the existing
  private deployment repository's ignored `.local/dependency-security/` area for
  raw evidence and approval records. Roger selected **manual** evidence transfer during execution. Verify manual
  collection/import and retention behavior at M3/M4; local filesystem availability
  or CI job success alone does not prove protected retention. Required raw reports
  must reach the private store and pass hash/identity readback before acceptance.
  No automated transfer service or new runner storage topology is authorized.
- Use isolated disposable PR runners with read-only repository permissions and
  no production mounts, credentials, registry write permissions, or production
  Docker socket. A scanner consumes an exported image archive through a read-only
  mount; it does not receive a Docker socket. Trusted image publication retains
  its existing separate authorization.
- Evaluate a newly built common image before any service stop/recreate command.
  Tool, database, schema, identity, freshness, or policy failures leave the
  running stack untouched and exit nonzero. Targeted operations that do not
  build/select a common image retain their existing scope.
  Full, targeted-web, worker, fork/archive, and batch-derived common images are
  subject to the gate when selected for activation. Retained common-image
  rollback also needs fresh evidence under current policy or explicit temporary
  accepted risk; the rollback flag itself grants no bypass. Targeted CAP alone
  is excluded. Resolve and recheck each selected image ID immediately before
  activation so a changed tag cannot consume another image.
- Policy and exception approval must come from the named maintainer/operator,
  with reviewed file hashes recorded outside candidate-controlled inputs.
  A PR may propose policy changes but cannot approve its own revision. The
  trusted invocation supplies expected approved hashes; absent or mismatched
  authority fails closed. Store approval records beneath the protected store's
  `.local/dependency-security/approvals/`, outside candidate-controlled inputs.
- Require Python/Debian inventory and sentinel reconciliation. Empty reports,
  missing package coverage, absent npm lock identity, and unexpected ecosystems
  cannot be interpreted as clean scans. Preserve database bytes or a retrievable
  immutable database artifact with the reports, and check database identity
  before and after offline scanning.
  Inspect native SBOM analysis fields as well as JSON syntax and stderr: parser
  failures, recovered panics, and version-matching failures block. Unidentified
  executable files require explicit ownership/coverage dispositions; they are
  distinct from parser errors and cannot disappear during format conversion.
  Include scanner-ignored and matcher-suppressed findings with their reasons in
  the reviewed matrix; scanner defaults are not policy-approved exceptions.

Rationale: daily freshness bounds advisory staleness; short owned exceptions
avoid permanent suppression; archive scanning removes scanner access to the
Docker control socket. Retention must preserve deployment and rollback evidence
without placing raw inventories in public source. The proposed numeric limits
are owner-ratified; operational fit must still be demonstrated.

The package owner, correctness reviewer, security reviewer, and wepp1 operator
must approve the scope, thresholds, evidence retention, and deployment failure
behavior before implementation changes production dependency or deploy paths.
