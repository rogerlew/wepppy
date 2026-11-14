# Security review - wepp1 common-image dependency security gate

## Metadata

- **Package**: `docs/work-packages/20261110_wepp1_dependency_security_gate/`
- **Reviewer**: independent `security_reviewer` (`scanner_review` agent)
- **Date**: 2026-11-11 UTC (M0/M1 design/source and evidence review; final review pending)
- **Scope reviewed**: scanner/tool supply chain, common image, Python/Debian
  packages, primary npm lock, CI policy, and pre-activation deploy gate
- **Commit context**: scaffold at `2041fb8e2`; implementation revision pending
- **Retained raw evidence**:
  `out/security-audit-20261110/f6/m0-20261111T0505/scanner-trial/`; original
  temporary command paths remain symlinked and receipt bytes are unchanged.
- **Related artifacts**:
  - Scope/policy: `artifacts/20261110_scope_and_policy_decision.md`
  - Surface inventory: `artifacts/20261110_surface_inventory.md`
  - Scanner evaluation: `artifacts/20261110_scanner_evaluation.md`
  - Correctness review: `artifacts/20261110_correctness_review.md`
  - QA review: `artifacts/20261110_qa_review.md`

## Security Triage Decision

- **Audit finding severity**: Medium; exact applicability remains unverified.
- **Change security impact**: high.
- **Dedicated security review required**: yes.
- **Mapping**: CWE-1104; OWASP Top 10 2021 A06.
- **Gate status**: fail until evidence, implementation, and reviews complete.

## Findings

| ID | Severity | Surface | Description | Required action | Status |
| --- | --- | --- | --- | --- | --- |
| F6-S1 | Medium | Evidence provenance | Preliminary Python count is not retained or bound to an image/scanner database | Reproduce with exact artifact and retained report | Open |
| F6-S2 | High | Candidate promotion | No fail-closed exact-image advisory gate precedes wepp1 activation | Ratify and implement CI/pre-activation gate | Open |
| F6-S3 | Medium | Test identity | Dependency changes can miss the full baseline trigger or run on an older test-image base | Bind workflow/test image to reviewed candidate | Open |
| F6-S4 | Medium | Build inputs | Tags, ranges, Git sources, vendored refs, and downloaded binaries complicate complete inventory | Record immutable/resolved identities and coverage | Open |
| F6-S5 | Medium | Scanner completeness | Trivy 0.76.2 logs a Python constraint error, omits GDAL CVE-2026-8212 from Python results, and exits zero | Reject matching errors and retain alternative detection regression | Trivy rejected; alternate qualified; M3 guards pending |
| F6-S6 | Medium | Scanner archive input | Syft/Grype link the vulnerable ar reader in GO-2026-6905; tested image mode excludes its cataloger | Enforce qualified image-to-SBOM scope and reject parser unknowns in M3/M4 | Scope-specific M1 exclusion evidenced; automation pending |
| F6-S7 | Medium | Common-image analysis | Syft treats 15,574 scientific `.par` files as Java archives and records parser failures despite exit zero | Validate exact-image scientific data, retain exact path/hash exclusions, and rescan with Java enabled | M1 classification/rescan pass; M3/M4 automation pending |
| F6-S8 | High | Bundled native components | Pillow and PyCurl carry independent Brotli decoder copies whose advisory applicability is not established by the Python Brotli Git fix | Retain each native path/hash and prove its patch provenance or remediate with representative consumer parity checks | Open; Pillow 13.0.0 wheel repair rejected; native repair/consumer parity pending |

These are package acceptance gaps, not claims of demonstrated live exploitation.
The preliminary count does not establish vulnerability reachability or severity.

## M0 independent assessment

The artifact boundary and fail-closed ordering are appropriate. Roger ratified
24-hour freshness, five-minute clock skew, 30-day maximum exceptions, 90-day CI
evidence and 365-day/rollback-lifetime activated evidence, then selected manual
transfer to the existing private deployment store. The review grants no
advisory-risk exception or production deployment authorization.

Trivy 0.76.2 was selected for confined qualification. That trial subsequently
exposed F6-S5, so it is not approved for adoption. The scanner
evaluation records independently verified release identities, current upstream
advisories, source-level capability checks, and the primary agent's measured
Redis-image trial. This reviewer read back its reports: exact image identity,
89/89 Debian package/version matches, verified release attestation, and network-
disabled scanning without a Docker socket. The 224 fixture advisories are not
common-image findings. Later development-image inventory reconciled 324/324
venv name/version pairs, but advisory matching is incomplete due to F6-S5.

The binary self-scan's UNKNOWN `GO-2026-5932` has an evidence-backed **not
affected** disposition for executable SHA-256
`6a972c69606c7b3ea4c6bdcc6fc9332ea9ad38381624310c1e85cc77345909f3` only:
the official advisory's OpenPGP packages are absent from 208,314 recovered linked
function names and the complete binary byte search; the linked OpenPGP code uses
the ProtonMail fork. The scanner evaluation retains exact method, hashes,
source references, limits and reevaluation trigger. UNKNOWN severity was not
silently treated as Low, and no accepted-risk exception was granted.

The failed Trivy trial justifies qualifying the reserved Syft/Grype alternative.
Signed-checksum verification for the exact Syft 1.57.1 and Grype 0.121.3 archives
has been read back independently. The scanner evaluation section 6 records the
exact main-workflow identities, hashes, verifier bootstrap limitation and added
tooling cost. Grype source also has error-to-
no-match paths, some logged only at Debug: qualification must retain debug logs
and prove the GDAL case, not assume a second scanner repairs it.

Subsequent readback confirms the alternative detects the installed GDAL case,
reconciles 324/324 Python and 475/475 Debian pairs, and logs no matching errors
in the retained trial. F6-S5's concrete failure is avoided by this candidate;
retain it as the reason Trivy was rejected rather than claiming Trivy repaired.
The qualification's 3,006 matches and 330 default-ignored records remain
undispositioned development-image evidence. Enable Grype's
`include-matcher-suppressions` for accepted evidence and disposition both result
collections. `show-suppressed` affects tables only.

The alternative's self-audit exposes F6-S6 and verifier findings. Exact-binary
evidence supports not-affected `GO-2026-5932` dispositions for Syft/Grype, but
their ar-reader advisory remains a real vulnerable feature. Source and the trial
descriptor support a bounded image-to-SBOM exclusion. A 68-byte malformed ar
fixture proves that default image mode excludes the parser, while forcing the
cataloger triggers the exact panic recorded in native `files[].unknowns` despite
exit zero. The **M0 security tool-choice decision passes for the exact confined
image-to-SBOM M1 commands**, with native unknowns/log review and full suppression
capture. M3/M4 must automate mode enforcement and parser-error rejection; those
future guards are not a circular prerequisite to selecting the M0 tool.
Cosign's two High, two Medium and two UNKNOWN
records concern a temporary confined verifier; retain them and qualify the
supported verification path separately. No owner acceptance is inferred from
the trial. See scanner evaluation section 7 for IDs, hashes and limitations.

Resolve these concrete design conditions at the applicable policy/CI/deployment
milestones; they do not prevent confined M1 evidence collection after M0's
remaining full-baseline/evidence requirements pass. Owner policy and storage
selection are already ratified:

1. **Evidence authority:** SHA-256 proves byte identity, not who approved it.
   A PR must not authorize itself by editing policy, exceptions or expected
   hashes. Define the trusted reviewed policy revision and named human approval
   evidence; deployment must regenerate/check candidate evidence under that
   authority. Add fixtures proving unapproved policy/exception inputs fail.
2. **CI isolation:** `contents: read` alone does not isolate a self-hosted runner
   or its Docker daemon. Existing `remote-ci` labels in
   `.github/forest_workflows/stubtest.yml` are not proof of disposable-runner
   isolation. Name the runner/environment that actually meets the proposal;
   retain cleanup and separation evidence before enabling PR candidate builds.
3. **Retention:** confirm the actual protected storage and access policy. Public
   repository artifact upload is not automatically protected evidence storage.
   Retention must include database bytes or a reproducible immutable database
   artifact reference, not merely a timestamp/hash that cannot be retrieved.
4. **Coverage and errors:** require installed Python/Debian inventories and
   expected sentinels, not only nonempty JSON. Unknown severity/schema, omitted
   package results, malformed/duplicate exceptions and scanner errors must fail.
   A blocked-follow-up disposition cannot silently count as risk acceptance.
5. **Activation identity:** resolve the candidate before scanning and verify the
   image actually selected immediately before activation. A mutable tag replaced
   between those operations must fail, including targeted deployment paths that
   select a rebuilt common image. Fake-scanner tests must assert no stop/up on
   failure, and operational review must cover the real Compose selection.

Remaining scanner qualification closures are the M3 error guards, common-image coverage and
resource suitability, additional error-path trials, database immutability during
offline inspection, and final pinned scanner-runtime identity. Binary dependency
inventory, the sole detected self-advisory disposition, development-image Python
inventory and malformed-archive rejection now have retained evidence. The trial
supplied memory/CPU limits; it did not measure peak use or establish production
common-image suitability.

No dependency, workflow, deploy code or production system was modified by this
reviewer. Scope is M0 source/design plus trial-artifact readback. Correctness,
QA, operations and final implementation security reviews remain required.

## M1 scientific-data classification review

The unchanged common-image native SBOM has 17,673 file unknowns: 15,574 exact
`java-archive-cataloger: unable to read files from java archive: zip: not a valid zip file`
errors on `.par` files, plus 2,099 unidentified executables. The original report
remains failed analysis evidence. Complete installed-package reconciliation does
not erase these errors. Pinned Syft source selects `**/*.par` as a Java archive
extension; this overlaps CLIGEN station data used by the repository.

The smallest acceptable refinement is a **validated data-file exclusion**, not
an error-message waiver or disabling Java. Before each accepted scan, validate
the exact image's candidate files as regular scientific text, retain their
absolute paths and SHA-256 values bound to that image, and exclude only that
validated set. Check the entire text for unexpected binary/control content,
CLIGEN structure/numeric rows, and ZIP identity; a filename, first-line marker,
or absence of initial `PK` bytes is insufficient. Existing station parsing uses
fixed-width numeric fields and checks only selected early rows, so importing
`Station` alone does not validate the whole file. Retain the independent source
hash comparison as supporting provenance, not a substitute for image readback.

Syft image exclusions apply across catalogers and implicitly include descendants.
Use literal absolute file paths without glob metacharacters, verify they are
regular files, and retain the effective scanner configuration. If exact-list
matching proves too costly, a compact pattern is acceptable only when its entire
match set on this immutable image is proven equal to the validated file manifest;
do not widen it to unverified directory contents. Any new, changed, ZIP, binary,
symlink or unmatched `.par` must undergo fresh classification or remain visible
to the normal scanner/error gate. This is a candidate-specific data boundary,
not a permanent exemption for the extension or climate directory.

The baseline classification and revised match-set checks now pass. The original
parent-glob list failed because it also selected 12,703 symlinks; the retained
refinement matches exactly 15,574 regular files with no symlink ancestors.
Full text and all 79 numeric-row labels are verified. Eleven exact path/hash
entries have existing scientific numeric-format anomalies (17 rows/27 cells),
explicitly retained in private `par-independent-classification.json`; they
remain scientific text rather than archive/package content. This disposition
does not certify numerical correctness or exempt future malformed data.

The rescan uses the same immutable image/archive with Java enabled. Independent
comparison preserves all 2,260 package/type/version/PURL/cataloger/path/layer
identity tuples; the native report now has only the same 2,099 ownership
unknowns. Grype retains the original 2,894 matches and 327 ignored records.
Retain both reports and all classification evidence. Unexpected parser/analysis
errors still block; executable ownership gaps require separate coverage dispositions. M3/M4
must enforce and test this boundary, including binary/ZIP replacement at an
otherwise approved path and an unexpected `.par` path. Qualification may proceed
under these reviewed commands without waiting for the future wrapper. This
closes F6-S7's M1 classification gap; it does not grant final common-image
advisory or deployment acceptance.

Detailed source references, observed hashes and validation limits are in scanner
evaluation section 8. This review adds no advisory-risk exception or production
authorization.

## M1 Go-symbol and kernel-header applicability review

Capturing Go symbols with Syft's `capture-symbols: all` and
`use-packages-lib: false` is accepted as supplemental, network-disabled
inspection. **The no-symbol report remains the authoritative finding universe.**
Grype's symbol qualifier rejects records during vulnerability search, before
matches or ignored matches exist; `include-matcher-suppressions` does not retain
those rejected rows. Preserve and reconcile every original advisory/package/
version/path identity. A smaller supplemental report alone closes no finding.
The primary agent accepted this requirement for the M3 guard.

The supplemental result confirms the risk: 53 primary Go records disappear from
both its match collections, while ignored records remain 327. All 53 stay
pending in the original universe. This trial's database is stale and the receipt
explicitly marks it diagnostic-only.

Exact-advisory function-absence proposals require exact binary hashes, affected
import/function metadata and complete relevant symbol evidence, including
inlined names and normalization/vendor handling. Syft silently falls back when
its inlined-name header parser cannot decode a layout and drops some vendored
stdlib attribution; Grype documents a nested-generics normalization limitation.
These are concrete completeness checks, not reasons to discard useful symbol
evidence. Missing/partial symbols remain module-level matches. The supplemental
SBOM preserves all 2,260 artifact identities and ownership unknowns, but Docker's
`go1.21.11` stdlib still has no symbols/architecture; it receives no absence-based
disposition. No individual Go not-affected decision is granted here.

All 327 default-ignored kernel-source records are exact-indirect matches on
`linux-libc-dev` `6.12.116-1`. Exact-image package-file evidence identifies UAPI
headers and documentation, with no kernel or `perf` executable payload. This
supports an itemized not-affected proposal for implementation absent from this
specific header package. The rationale cannot be global: one retained advisory
concerns the userspace `perf` tool and another describes procps/PID enumeration.
Retain all IDs, including 150 Unknown records, and review any other image
component separately. No host-kernel applicability or safety conclusion follows.
Final row dispositions remain pending the ledger; scanner default-ignore status
is not approval. Source links, measurements, hashes and limitations are recorded
in scanner evaluation section 9. No accepted-risk exception is proposed.

## M1 Python Brotli patch review

For GHSA-9v8h-qqgm-4m35 / CVE-2026-111497, evidence supports **not affected for
the exact installed Python Brotli artifact**, despite its displayed `1.2.0`
version. The advisory fix is an ancestor of its recorded VCS commit; exact-image
decoder source retains the fix, the image build log names that commit, and the
actual imported extension hash matches the installed `RECORD`. The bounded
round trip proves ordinary runtime integration, not exploit rejection. Cached
source is also patched, and exact-image readback confirms both cached compiled
extensions have the same SHA-256 as the installed extension. This closes the
three Python package records at the installed distribution, cached wheel and
cached source paths for this advisory only. Scanner evaluation section 10 retains
paths, hashes, primary sources and limits.

Pinning that existing Git source is an appropriately small M2 candidate, subject
to the required candidate validation. F6-S8 separately covers confirmed native
decoder copies in Pillow and PyCurl, including their cache copies. Neither the
Python package's fix nor its import test closes those consumers. Their versions
alone do not prove affectedness; require each component's patch evidence or a
compatible repair. No global CVE suppression or accepted-risk exception is
granted.

### Pillow 13.0.0 bundled decoder qualification

**F6-S8 remains open:** the reviewed upstream Pillow 13.0.0 wheel does not
incorporate the reviewed Brotli fix and cannot close this finding by version
upgrade alone. The CPython 3.12/x86_64 wheel hash matches retained PyPI metadata;
runtime/API compatibility has not been tested.

The [tagged dependency manifest](https://github.com/python-pillow/Pillow/blob/13.0.0/.github/dependencies.json)
selects Brotli 1.2.0. Its [wheel build script](https://github.com/python-pillow/Pillow/blob/13.0.0/.github/workflows/wheels-dependencies.sh)
reads that value through `_get_ver`, downloads the corresponding upstream tag,
and builds it without applying the decoder fix. The tagged decoder retains the
old boolean/error handling. The [upstream fix](https://github.com/google/brotli/commit/0ed4268a4401abcb4472096340477cf4af7d1a2b)
adds `FORMAT_BLOCK_SWITCH` and error-status propagation. Static inspection finds
the existing exported error function and older error strings in the wheel's
actual decoder, but not the new error string. Exact-baseline Pillow and PyCurl
decoders show the same absence; the independently proven patched Python Brotli
extension contains it. This conclusion combines recipe, source and binary
evidence; it does not rely on the shared-library filename.

Private `upstream-metadata/pillow-13-brotli-review.json` beneath the baseline
evidence directory retains full paths, hashes, source links and limits; SHA-256
`cfb7376bc0889670fdfee54d28c663e8cf1cb5da9342d70b19fed2d406b4ca0c`.
No wheel was installed and no exploit or font-decoding test was run. Absence of
the marker alone cannot exclude a separately implemented fix; none is evidenced
here.

The bounded M2 candidate is an owned build of pinned upstream Pillow with fixed
Brotli, or verified patched distribution libraries if they preserve the current
features. Record build provenance and actual linked-library/cache hashes,
compare codec/font features, and exercise representative image/font/report
workflows plus required full gates. A source build is not yet qualified:
optional features and major-version API changes need parity checks. Updating
the standalone Python Brotli package cannot repair these native copies.

## M1 frontend npm applicability review

The 19 primary-lock audit rows contain ten directly advised packages and nine
propagated rows, with 22 distinct GHSA aliases. Exact-image readback and verified
consumer sources support **not affected for these rows in the recorded common
image runtime and bounded Docker static build**. The frontend dependency tree
is absent at runtime. The build copies fixed assets using `fs-extra`; its package
closure and the separately reviewed Linux install-hook closure do not invoke
these 19 package instances. This decision is bound to exact image/lock/source
and command identities, not the development-dependency flag or production-only
audit count.

Scanner evaluation section 11 retains every row/path/alias, actual parser-input
sources, narrow feature exclusions, candidate fixes and limits. In particular,
glob's no-signal argument does not close its inherited minimatch finding;
jsdom's string conversion excludes one ws condition but not network-fragment
exhaustion. Existing Jest configuration avoids the preset/globals deepmerge
branch; new configs require reevaluation. `braces` and `brace-expansion` are
different packages.

Same-major candidate repairs are separated from glob/minimatch major changes.
Do not apply npm audit's Jest 25.1.0 downgrade. Source/metadata inspection proves
Node 20 and `glob.sync` support for the researched glob candidate, but not full
consumer compatibility. No dependency update or risk exception is approved by
this review.

**PR/CI admission remains open.** Tests and lint consume repository-controlled
code/configuration and can have parser or network inputs beyond the static
build. Runtime exclusion cannot prove runner isolation or a private retrieval
route. Those obligations remain M3/M4 gates, including for this exact lock.

## M3 manual handoff design review

**Design status:** acceptable within the ratified manual-transfer and existing
Docker Compose boundaries; implementation and actual transfer validation remain
M3/M4 work. This adds no recurring human approval beyond the already selected
manual collection/import, existing code review, and policy-required acceptance
of any actual advisory risk.

Independent readback confirms scope-policy SHA-256
`2c381b5cf53b40278a1145d8bbf32e314647be8328010aaa9005ae414cd4e6be`.
The separate 0600 private record
`/workdir/weppcloud-deployments/.local/dependency-security/approvals/policy-20261111-manual-transfer.json`
names that hash and the prior approved policy hash. The original approval is
preserved. [ADR-0140](../../../adrs/ADR-0140-dependency-security-gate-policy.md)
records manual transfer and the unchanged production Compose entry point.

### Minimal handoff

1. An isolated PR job builds, inventories, scans and tests its candidate in a
   job-local workspace. It emits a fixed-format evidence manifest and raw files
   beneath a private directory. The manifest names the source/workflow run,
   image ID, lock hash, scanner/database identities, file hashes and command
   outcomes. Public output contains sanitized identities/status only. The job
   receives neither the private store nor approval records/production credentials,
   and does not upload raw reports as public repository artifacts.
2. The operator manually collects that directory using an existing authenticated
   access channel and transfers it into the selected private store. A small
   repository-owned import command copies only expected regular files into a new
   0700 staging directory, recomputes hashes after copying, and performs the same
   schema/identity/freshness/coverage checks as the gate. It then publishes a
   private import receipt and accepted evidence directory atomically. It does
   not run scripts, hooks or executables supplied inside the incoming bundle.
3. The trusted invocation supplies approved policy/exception identities from
   the separate private approval area. Incoming content cannot choose those
   expected values, replace approval files, or introduce a self-approved
   exception. The importer/evaluator itself comes from the reviewed tooling
   revision, not an executable in the incoming bundle. Ordinary imports need
   no new policy approval when those ratified inputs are unchanged.
4. Manual import proves retention, not deployment approval or equivalence to a
   different image. Production still builds through installed `wctl` and
   `scripts/deploy-production.sh`. After build, the gate resolves the actual
   selected common-image IDs from rendered Compose and generates/checks fresh
   evidence for those IDs before Step 3 can stop/recreate services. An imported
   CI receipt for another image cannot satisfy that boundary, even when source,
   tag or requirements match. Evidence required to identify the final test
   runtime must likewise name the exact candidate under review.

The bundle need not introduce an archive protocol, transfer service, storage
daemon, registry publication or alternate deployment command. A directory with
a strict manifest and existing manual copy mechanism is sufficient. Private
approval records are not bundled with candidate evidence; the importer reads
them through its trusted local configuration.

### Conditions that must fail closed

- Missing/incomplete collection, failed copy, hash mismatch, malformed or
  duplicate manifest keys, unexpected files, absolute/parent-relative paths,
  symlinks, or attempts to overwrite accepted evidence/approval records. Repeat
  import may reuse an identical accepted receipt; differing bytes cannot replace
  it silently. Verify private ownership/modes at the destination.
- Missing/mismatched external policy authority, an unapproved exception revision,
  duplicate/conflicting exception scope, or expired risk acceptance. Hashes in an
  untrusted manifest do not authenticate that manifest's authority.
- Missing/zero-byte/unsupported reports, nonzero producer exit, wrong image or
  lock, missing inventories/sentinels, native parser unknowns/recovered panics,
  matcher errors, or unmanaged coverage without a reviewed disposition. Include
  both ordinary and suppressed findings; an empty result is not a coverage test.
- Failed database refresh, missing database identity/retrievable bytes, changed
  database during offline inspection, stale/future evidence, or blocking findings.
  Transfer/import time does not reset scan or database age. Delayed manual
  collection can require a new scan under the existing 24-hour policy.
- An unresolved selected image or a tag changing after validation. Recheck before
  the first disruptive operation and activation, including batch-derived and
  rollback paths. Targeted CAP alone retains its exclusion. Preserve the known-
  good stack on pre-activation gate failure; no fallback or rollback flag bypass
  is introduced.

### M3/M4 evidence needed

Prove one real manual collection/import from the intended disposable PR runtime
before its workspace is removed. Existing `remote-ci` labels and isolated Compose
containers alone do not prove runner disposability or an accessible collection
channel. If the selected runtime has no existing way to retrieve raw files
privately before teardown, report that boundary as unavailable and leave
retention/acceptance pending; do not enable public uploads, add credentials or
invent new storage infrastructure. The remaining choice concerns actual channel
availability, not another approval of manual transfer.

Exercise importer rejection of altered/missing files, traversal/symlinks,
self-supplied approval, expired evidence, zero-byte output, and the retained
Syft parser-panic fixture. Confirm interrupted import cannot publish acceptance.
Use fake deployment/scanner commands to prove every failing gate precedes
stop/up and that selected image IDs are checked on every covered mode. Also
exercise success with exact post-copy readback and current approved hashes.
CI scan/test success may be recorded separately while manual retention is
pending; it must not be presented as accepted retained evidence.

Operations review must account for the existing long worker-drain interval
between Step 3 and activation when checking image identity and freshness. Do not
claim a later post-drain failure left already-stopped services untouched, or
silently extend freshness to accommodate the interval. This is validation of
the canonical deployment path, not authorization for a different workflow.

## M3 local importer security review

**Scoped status: pass for local byte retention only.** Reviewed
`tools/security/import_dependency_evidence.py`, its focused tests, and
`docs/infrastructure/dependency-security-evidence.md`. This decision does not
complete M3 or approve any advisory disposition, image, CI transfer or deployment.

Findings closed during review:

- **Low, receipt path:** changing a caller-selected store alias during copying
  originally left correct bytes under the held directory while the returned
  alias path pointed elsewhere. The importer now resolves roots once and returns
  the canonical store path. An independent `wctl exec` probe reproduces the
  original defect and confirms the corrected result; the alias-swap regression
  checks retained bytes and leaves the alternate store empty.
- **Medium, completion evidence:** correctness review identified that a directory
  synchronization failure after rename left a completed-looking `bundle/`.
  Publication is now marked successful only after synchronization; failure
  removes the newly renamed bundle. Both post-rename synchronization failures
  have regression coverage. The contract requires successful exit/receipt and
  readback, so directory existence after a crash cannot confer completion.

No unresolved Medium/High finding was identified in this component's stated
boundary. The manifest is strict, hash-bound, and duplicate-key rejecting;
filenames cannot contain traversal or nested paths. Nonblocking, no-follow file
opens followed by regular-file checks reject symlinks, directories and FIFOs.
Held directory descriptors, exclusive reservation and exclusive file creation
prevent bundle content from redirecting writes or replacing earlier imports.
The invoking user must own the 0700 destination; retained directories/files are
0700/0600. Payloads remain opaque bytes and are never executed. Expected hash
and image ID must come from the trusted collection record; the declared image ID
does not independently prove the contents of a scanner report.

An independent filesystem probe modifies an already-read source byte while the
remaining stream still has the expected hash. The metadata guard rejects it
and removes the reservation; this case is now a focused regression. The primary
agent's final focused `wctl run-pytest tests/tools/test_import_dependency_evidence.py`
run reports **31 passed in 8.97 seconds**, including source mutation, alias swap,
special files, malformed identities, duplicate keys, no-overwrite and durability
failures. Caller-controlled root selection and same-user/root modification of
the trusted store remain outside the untrusted-bundle boundary.

Independent readback of the real local import verifies all five files totaling
72,245,902 bytes, the manifest hash, and private modes. Its private
`evidence/import-trial-20261111/receipt-v2.json` SHA-256 is
`8705c565a4a077b03e2db99e556ec3140a3c583b933e1e05ee73eb773e72a7e1`;
status is `retained-not-approved`. Reviewed implementation SHA-256 is
`c5bcbb8d6fdefeae138f2af1b4ccf8cac8c98e9912f67e6cecd45ae009bb6ebe`.
Independent probe evidence is retained through
`out/security-audit-20261110/f6/m3-import-review-20261111/`; review JSON SHA-256
`acc24020ac371ba595491f8d9b5e7b65e16f61e96eafa1a48d22e52e8d4963f0`.

The authenticated CI retrieval route is still missing. Report schema/coverage,
freshness, policy authority, advisory evaluation, final test identity, retention
lifecycle and the Compose pre-activation boundary remain separate gates. This
local trial supplies no exception or implied approval for those obligations.

## OAuth verification-failure contract review (pre-implementation)

**Frozen proposal assessment: security pass for owner ratification.**
Reviewed `artifacts/20261111_oauth_contract_decision.md` at SHA-256
`09b2790f274c5891732680f1fa518c6bbd17ef17a81dd58d802b79417821059b`,
the current callback at `d4b175436`, session/CSRF authorities and the retained
candidate probes. This review grants no route edit, dependency adoption or owner
ratification.

Final frozen-text readback confirms the exact redirect/flash, unconditional
value-free diagnostics and callback-only CSRF classification remain as reviewed.
Added new-account, authenticated-identity rejection, optional next destination
and remember/session cases improve valid-state coverage. Consuming flow state
while preserving existing identity is consistent; no-side-effects assertions
apply to rejected callbacks, while valid callbacks exercise existing creation
and login. OAUTH-C1/C2 remain closed. Owner ratification and canonical checkpoint
ancestry are still pending; this is approval of the proposed contract only.

| Finding | Severity | Evidence / required disposition |
| --- | --- | --- |
| OAUTH-C1: conditional reuse of exception text | Medium | Closed in the revised proposal: separate JOSE handling mandates static/provider/class diagnostics and prohibits raw exception text/traceback or token/header/claim values. Implementation must prove this with a sentinel-bearing error/log capture regression. |
| OAUTH-C2: implicit response details | Low | Closed in the revised proposal: HTTP 302, configured `SECURITY_LOGIN_ERROR_VIEW` with fallback `security_ui.login`, and the exact generic error flash are normative. |

The proposed `JoseError` catch is appropriately bounded to
`authorize_access_token`: it returns before userinfo, datastore/linking and
`login_user`, without weakening verification or catching unrelated programming
errors. [Official joserfc error documentation](https://jose.authlib.org/en/guide/errors/)
shows descriptions can interpolate token-header input; a few value-free sample
messages cannot establish a safe raw-error logging contract. Existing provider
cancellation/transport branches are separate and receive no new behavior waiver.

The revised state matrix includes absent optional OpenID claims that remain
valid for the configured provider, successful non-OpenID providers, supported
linking/legacy alias states, and mismatched/replayed Authlib OAuth state. Missing PKCE verifier
and OAuth state validation are distinct boundaries. Preserve already-authenticated
session identity when a callback is rejected; do not introduce logout, cookie
clearing, weaker claim rules or retry. Existing/new account and valid identity
linking outcomes plus `remember=True` remain noninterference checks. Include a
real verification success through the callback, not only a mocked success token.

The additional CSRF clarification is appropriately limited to the two named GET
callback paths. It reconciles the existing safe-GET rule with the generic
cookie-backed session same-origin rule while retaining session-bound OAuth
state, the existing PKCE exchange, and configured OpenID checks. Rejected
verification cannot restore consumed state. No exception applies to disconnect,
token minting or other session mutations. Validate cross-site/no-origin valid
returns and missing/mismatched/replayed state separately on both callback paths;
do not require previously optional provider capabilities or claims. This is a
protocol-specific contract clarification, not permission to weaken CSRF middleware.

The retained actual-library probe confirms one valid RS256 token and 15 expected
JOSE rejections. The Flask invalid-nonce probe confirms that real verification
escapes the current route through `LoggedBlueprint`; it substitutes the client
exchange and therefore does not prove OAuth state/transport or complete login
parity. Its receipt SHA-256 is
`243f2b396a131c268e9269771c8adbcef99f751cbb126bbf0ffaaa065a534e83`.
No crafted-provider network request was needed to establish this discrepancy.

The finite-authority conclusion is correct: the current session contract governs
identity/remember behavior and credential-free logging, but does not specify this
OpenID failure response. Ratify the precise delta, promote it to the session and
CSRF contracts with implementation pending, and obtain independent readback of
both final amended texts. The checkpoint, canonical amendments and resolved reviews
must be a standalone ancestor before route/Authlib edits. Existing plan/M0
authorization is not recorded as that specific ratification.

## M2 crypto/TLS candidate review (2026-11-11)

**Scoped assessment: pass to continue candidate validation; no release clearance.**
No new batch-specific Medium/High finding was identified. M1 applicability and
coverage work, M4 final gates, and the existing package findings remain open.
Private evidence is retained under
`/workdir/weppcloud-deployments/.local/dependency-security/evidence/crypto-batch-20261111/`;
independent `security-batch-review.json` SHA-256 is
`4fe798058cb332b5de857d5abfa153a97dfe25e3a6f2bf37c6d1f55c388b36ab`.

The reviewed common image is
`sha256:f0f3fbb48f4afe636eb8bfcc491d7fa28514543cc1fe4bc628bce8fda373da48`.
Its only installed Python version changes are cryptography 46.0.7 → 50.0.2,
certifi 2024.8.30 → 2026.10.18, and urllib3 2.7.0 → 2.8.0; the existing Brotli
Git source is pinned to its already evaluated commit. Authlib remains 1.6.12.
Independent JSON duplicate-key checks, declared Syft schema 16.1.13, tool/image
identities, unique artifact IDs and all Grype artifact references pass readback.
This is structural/identity validation, not a claim of formal JSON Schema
validation. Direct inventories reconcile 308/308 Python and 432/432 Debian
name/version pairs. All 15,574 classified scientific data path/hash pairs are
unchanged; exact exclusion-set and symlink checks pass again.

The same fresh Grype database (schema v6.1.10, built 2026-11-11 06:21:32 UTC)
produces 3,056 → 3,034 ordinary matches and 330 → 330 ignored matches.
Matcher suppressions remain included. The package/version/advisory multiset
removes exactly 22 records: cryptography 14, urllib3 six, certifi two, including
installed and cached copies; it adds none. These are records, including advisory
aliases, not 22 distinct vulnerabilities. Candidate report SHA-256 is
`ba07f596350334e0242e830da11cdfb31b81333887029b7eb9fd0ba7f35f0b51`.
The qualified repeat closes the initial missing before/after input-hash receipt
gap: actual DB/SBOM hashes agree with its before/after states, and both match
arrays are identical. Its report SHA-256 is
`6c545912cdabb69223c598ab3a504902cec72ed663deebeb2bce245c688193d8`;
independent `security-qualified-readback.json` SHA-256 is
`402b803eb6d7b5029657f6bdb560d92adbef308f523796c8b98f3c2a258d3b4d`.
Changed cache paths do not transfer prior applicability dispositions automatically.

The scan still contains 2,099 unidentified executable files and 46 artifacts
without PURLs. No new parser-unknown class or matcher constraint error appears.
Debug logs also retain 73 missing NVD metadata lookups for 12 CVE IDs, identical
in baseline and candidate. Exact Grype source and report readback show these
remain **UNKNOWN primary findings**, also present in related-vulnerability
metadata; none disappeared. They require explicit review. A metadata fallback,
unknown severity, or unchanged count does not waive their disposition.

Candidate Brotli evidence independently renews the narrow NOT AFFECTED proposal
for its three Python records. The imported extension and both cached extensions
all hash to `ddd8f72be33cfbd7a459625555610cdf31b97fbfca8e4cd799085f708a3f4ceb`;
the installed RECORD agrees and a real round trip passes. Installed `direct_url`
records requested and resolved commit `d89c4b1c52e25ddafe047bc78bbee5c1e24b1809`.
Candidate `decode.c` hashes to
`c74c2d668314fefe645d3ab9bbafe6b6db8a95769ca06dc54d875610c803fc56`, matching the
previously verified upstream fixed source and retaining the checked error guard.
These hashes were measured from this candidate, although they equal baseline.
The initial failed cache probe is retained: cached `direct_url.json` is absent;
the corrected readback uses actual source and binaries. This proposal does not
cover Pillow/PyCurl native copies or claim exploit-proof testing. F6-S8 stays open.

Real RS256, Fernet and Paramiko outcomes and native-library readback match
baseline. Seven local TLS checks cover trusted/untrusted CA behavior, redirects,
Authorization stripping, timeout and HTTP-error handling; the actual certifi
bundle independently loads 117 CAs. Live provider trust compatibility is not
proven. Both compared images still accept the wrong nonce when the token sets
`nonce_supported: false`; preserved Authlib behavior is not security closure.
Focused tests pass 51 cases on the common image and 51 on its test extension.
The extension's layer ancestry, all 308 Python versions and native/crypto outputs
match the common image; its 90 additional browser OS packages are separate test
inputs. Production-identity probes use UID 1002/GID 130; Compose tests use their
existing UID 1000/GID 993. These observations do not replace final end-to-end
workflow evidence, authorize production changes, or infer owner risk acceptance.

## Required Review Checks

- [ ] Scanner adoption passes the dependency-evaluation standard and is pinned.
- [ ] Scan execution cannot read runtime secrets or project data.
- [ ] SBOM/report identities match the exact candidate image and lock.
- [ ] Advisory database identity/freshness and failure behavior are explicit.
- [ ] Duplicate aliases do not inflate risk or erase source evidence.
- [ ] Reachability dispositions cite actual imports/routes/configuration.
- [ ] No applicable Critical/High remains unresolved.
- [ ] Medium accepted risks name owner, expiry, and compensating control.
- [ ] Upgrade batches preserve auth, parser, network, native, RQ, and report
      security boundaries relevant to changed components.
- [ ] CI uses least privilege and untrusted PRs cannot access publishing or
      production credentials.
- [ ] Deployment gate runs before service disruption and fails closed safely.
- [ ] Full pytest, npm lint, and full npm tests pass on the final candidate.
- [ ] Distinct excluded images are not represented as covered.

## Verdict

- **M0 security tool-choice status**: pass for the evaluated confined
  image-to-SBOM commands and explicit coverage/error obligations.
- **M3 manual handoff design status**: pass for bounded manual collection/import
  and exact host-local Compose image checks; real transfer/retention evidence pending.
- **M3 local importer security status**: pass for the reviewed byte-retention
  component and local readback; remote collection and policy acceptance remain open.
- **Final gate status**: hold; full baseline, common-image evidence,
  implementation, transfer/retention validation and final reviews remain open.
- **Release recommendation**: hold until all applicable High/Medium package
  findings are closed or explicitly accepted by the owner.

## 2026-11-14 operator decision and bounded tooling review

The historical hold above is superseded for this release by Roger's explicit
[residual-risk exception](20261113_gdal_residual_risk_exception.md) and controlling
[deployment policy](../../../infrastructure/production-deployment-policy.md).
The executing agent reviewed version-2 release bindings at `04165dfe7`: protected
operator-owned records bind exact image IDs, receipt hash, current tooling and
expiry; application/build-input changes and configuration drift still reject.
The change intentionally reuses accepted evidence without invoking scanners or
rehashing raw bundles. Focused tests cover wrong images, expiry, tampering,
missing risk fields, changed tooling, changed application inputs and config drift.
83 deployment tests passed, followed by 26 final receipt tests. Actual gates
passed on all three production hosts without rebuilds. This is an executing-agent
review, not an additional independent review or a claim that accepted dependency
findings were remediated. See the [rollout record](20261114_production_rollout.md).
