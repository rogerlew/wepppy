# Correctness and user-experience review - Dependency security gate

## Metadata

- **Reviewer**: independent `reviewer` agent, `/root/m0_correctness_review`
- **Date**: 2026-11-11 UTC
- **Source revision**: `2041fb8e267de3a1572d9fb4f4a62e725b75cc91`, dirty worktree
- **Scope**: M0 policy design; no evaluator/deploy-hook implementation exists
- **Canonical intent**: scope/policy artifact, especially Disposition Policy,
  Gate Behavior, and Ratified M0 policy; active ExecPlan M0-M4
- **Related reviews**: `20261110_operations_review.md`,
  `20261110_scanner_evaluation.md`, `20261110_security_review.md`
- **Gate status**: M0 checkpoint accepted after retained-evidence readback on
  2026-11-11; M1 and M4 final correctness review remain open.

## M0 Findings and Resolution

| ID | Severity | Finding | Resolution | Status |
| --- | --- | --- | --- | --- |
| COR-M0-01 | Medium | The disposition list included `Blocked follow-up`, while the original Critical/High rule prohibited merely undispositioned findings. A migration ticket could be mistaken for approval; advisory-only alias merging could apply one exception across different installations. | Concrete M0 proposal now explicitly keeps follow-up blocking without separate accepted risk, binds aliases to ecosystem/package/version/path, and rejects duplicate/conflicting exception records. | Resolved in proposed design; implementation tests pending |
| COR-M0-02 | Medium | The phrase *newly built common image* left retained rollback, batch-derived images, and worker-only presets ambiguous. Flag-based detection could skip a candidate or reject unrelated CAP repair. | Concrete M0 proposal now names full/web/worker/fork/archive/batch-derived activation, retained rollback evidence or accepted-risk requirements, CAP-only exclusion, and an immediate preactivation image-ID recheck. | Resolved in proposed design; implementation tests pending |

The reviewer reread the amended policy after reporting these findings. No open
High/Medium correctness ambiguity remained at that design review. That review
did not approve numeric freshness/retention limits, establish storage or runner
capacity, accept a vulnerability, or authorize production deployment. The later
M0 checkpoint below records completed baseline, tool and owner prerequisites;
deployed operation and retention qualification remain later gates.

The small Redis trial supports limited Debian-tool capability. Its findings are
not F6 common-image findings. This review reads the scanner evaluation's scoped
claims; it does not independently certify its raw trial files. No runtime
operation or production action was performed by this reviewer.

## Valid States and Operator Errors

These states are separate from command/input combinations; none is currently
claimed exhaustively tested.

| State | Valid state? | Required behavior | Direct evidence still required |
| --- | --- | --- | --- |
| Evidence absent on first candidate | Expected initial state | Generate evidence; fail before activation if generation fails | Real archive scan and missing-tool/database control-flow tests |
| Complete inventories, zero findings | Yes | Pass identity, coverage, freshness and policy checks | Positive fixture and reconciled candidate readback |
| Empty/truncated report or missing Python/Debian inventory | No approval evidence | Explicit schema/coverage failure; empty inventory is not a clean scan | Separate null/empty/missing-section fixtures |
| Findings with reviewed not-affected evidence or valid accepted risk | Conditional | Evaluate every occurrence and retain owner/expiry | Alias, multiple-version/path and approved-exception fixtures |
| Findings awaiting migration | Expected unresolved state | Block until an eligible separate accepted-risk record applies | Negative follow-up case and matching approved-risk control |
| Retained older image selected for rollback | Valid operator intent | Apply explicit rollback policy, with current evidence and exception checks | Retained image and fake activation ledger |
| CAP-only repair | Yes | Existing CAP workflow independent of common-image scanner availability | Scanner-absent excluded-mode test |
| Worker-only or batch-derived common image | Yes | Discover selected artifact without requiring `weppcloud` service | Rendered Compose variants and exact-ID fixtures |
| Malformed exception, conflicting duplicates, unknown severity/schema, changed image | No approval evidence | Bounded failure, retained receipt, running stack untouched | Negative policy cases and no-stop/down/up ledger |
| Exception/evidence at expiry boundary or future timestamp | Conditional | Deterministic UTC boundary; revalidate freshness before activation | Just-before/equal/just-after, skew and long-scan tests with fixed clock |

Input coverage must separately exercise full/web/worker/batch/CAP modes,
overlay/rollback selection, scanner/database availability, and tag mutation
during scanning. Operator errors should name the failed category, image, private
receipt location, and recovery action without displaying rendered environment.
Disk/permission/retention failures leave incomplete evidence and must not start
cutover. Retry produces fresh evidence without overwriting an accepted receipt.

## Generated Artifact Evidence Chain at Initial Design Review

| Stage | Required semantics | Current review result |
| --- | --- | --- |
| Intent/source | Resolved deployment set and exact build inputs, including dirty-source provenance | Proposed; revision alone cannot identify local modifications |
| Persisted candidate | Immutable image ID and resolved tag mapping | Common-image acceptance pending |
| Generated reports | Parse schemas, image identity, inventories, occurrence dispositions and DB identity | Limited Debian fixture described; Python/common-image coverage pending |
| Prepared input | Candidate requirement/lock readback, static-builder lock binding, emitted assets, test-image base identity | Pending M1/M4 |
| Execution | Same database bytes used by scan; exact required tests in declared candidate runtime | Pending; scanner exit zero does not mean policy approval |
| Activation/user outcome | Final selection still matches, containers consume that ID, changed user workflows remain valid | Pending M3-M5; separate rollout authority required |

At initial review the supported claim was **M0 design reviewed**, not implemented
or environment validated. Source/documentation checks cannot prove production
identities, mounts, filesystem permissions or availability. Retain direct tests
of each writer/consumer and the actual candidate; fake command ledgers supplement
that evidence rather than replace it.

Raw security inventories are operator artifacts under the protected
retention contract, not project-run artifacts for browse UI exposure. Preserve
private receipt discoverability and hash-linked review summaries. Actual
deployed retention/storage qualification remains pending; owner ratification and
local storage readback are recorded in the final M0 checkpoint below.

## User and Operator Goal

Users retain working authentication, project access, model execution, artifact
viewing, and reports after compatible security upgrades. Operators receive an
accurate, actionable candidate gate that leaves the known-good stack running
when evidence is missing or a finding blocks promotion.

## Required State Matrix

| State | Expected behavior | Required evidence |
| --- | --- | --- |
| No findings | Gate passes only with fresh image-bound reports | Direct candidate gate |
| Blocking finding | Gate fails before any service stop/recreate | Failure-path deploy test |
| Missing/stale report | Explicit failure names missing identity/freshness | Contract test |
| Approved unexpired exception | Gate passes and records owner/expiry | Policy fixture |
| Expired/malformed exception | Gate fails explicitly | Negative policy fixture |
| Ordinary login/session | Existing auth/session behavior remains valid | Focused route/browser smoke if auth deps change |
| OAuth success/failure | Provider flow and negative validation remain correct | Focused OAuth tests if changed |
| Hostile parser input | Existing rejection/output-safety behavior remains intact | Parser-specific tests if changed |
| Existing/legacy run | Browse, reports, RQ, and model preparation remain usable | Relevant focused tests plus full suite |
| Empty/optional feature | No new import/startup failure from absent optional state | Startup/import controls |
| Native/geospatial boundary | Python/system ABI and representative artifact semantics match | No-cache build and direct readback |
| Frontend lock | Clean build, lint, and all primary npm tests pass | Exact lock hash and command receipts |

## M4 Required Review Checks

- [x] Pre-change full pytest and npm baselines are retained and hash-verified.
- [ ] Each dependency batch has focused valid and failure-path evidence.
- [ ] The common image rebuilds without cache and exposes reviewed versions.
- [ ] The SBOM and scan reports describe that same image.
- [ ] The test image derives from the reviewed common-image candidate.
- [ ] `wctl run-pytest tests --maxfail=1` exits zero after final changes.
- [ ] `wctl run-npm lint` and `wctl run-npm test` exit zero after final changes.
- [ ] No segmented or diagnostic run is substituted for a required full gate.
- [ ] Gate failure leaves the currently running production stack untouched.
- [ ] Resolved M0 design findings have direct implementation regressions.
- [ ] Final image and freshness checks run before activation, including long
      scan and changed-tag cases.
- [ ] Status claims distinguish local validation, environment validation, and
      deployment.

## M0 Baseline Test Repair Review

Reviewed the bounded diff in
`tests/weppcloud/test_usersum_template_wiring.py` after the primary agent reported
that the full baseline failed on its obsolete `runsTtlDeletionHelpUrl` assertion.
The canonical
`docs/ui-docs/contracts/runs-catalog-ttl-deletion-contract.md#presentation-contract`
requires one panel-level **How to keep your project** link using the specified
Usersum document ID. `wepppy/weppcloud/templates/user/runs2.html` already places
that link above the table controls; no runtime/template change is needed.

The replacement assertions require that exact anchor once and the document ID
once. They preserve the endpoint/document wiring check and detect duplication,
while removing a requirement for a JavaScript global that the current contract
does not require. Existing
`tests/weppcloud/routes/test_runs_catalog_contract.py::test_runs_help_is_once_above_table`
separately checks rendered placement/count and absence of per-row help code.

**Verdict: pass for this test-only repair; no High/Medium findings.** The diff
does not change dependency, authentication, TTL, or application behavior. The
source-string assertion remains sensitive to harmless template whitespace, an
existing test-style limitation rather than a release blocker. This review did
not rerun tests; focused and exact full-baseline receipts remain the primary
agent's validation obligation. Correcting this stale assertion does not convert
the failed full command into a passing baseline or waive its rerun.

## Final M0 Checkpoint Readback

On 2026-11-11, this reviewer independently parsed the private
`m0-20261111T0505/baseline-final/` receipts in the owner-selected store and
recomputed all ten manifest-member hashes and sizes. The manifest SHA-256 is
`321aa988535d4b05b2c3267b894adc28497ba1d41fbc641174992995323c2ba3`.
Its directory is 0700 and its files are 0600. Current requirements, frontend
lockfile and repaired test hashes match the retained `identity.json` values.

The complete `wctl run-pytest tests --maxfail=1` rerun exits zero, with 13,502
passed, 435 skipped and 6,029 warnings. Its command receipt spans
2026-11-11 06:14:22 to 07:17:46 UTC and records 3,803.88 seconds; the pytest
summary reports 3,784.78 seconds inside the wrapper. Both npm command receipts
exit zero; the test log confirms all 124 suites / 1,069 tests passed. The retained
stub-check log reports completeness. No full test was rerun by this reviewer.

The earlier failed full baseline remains retained; the successful rerun follows
the bounded, separately reviewed test repair above. Dependencies and production
behavior were unchanged. These are development-baseline results from recorded
image `sha256:b32d1c74915c7f7235c4f1bd02ff8e25808be7c8bac665e925a01785bc9f9afa`,
not acceptance of the preparatory common image or final dependency candidate.

External approval records bind Roger's policy decision and manual-transfer
clarification to current policy SHA-256
`2c381b5cf53b40278a1145d8bbf32e314647be8328010aaa9005ae414cd4e6be`;
this reviewer verified that current-file hash. ADR-0140 records the durable
decision. The independent security review approves confined Syft 1.57.1 to
Grype 0.121.3 evidence collection after the documented Trivy rejection; that
scoped specialist review supplies tool qualification, not production coverage.

**M0 checkpoint verdict: pass for proceeding with M1**, with no unresolved
High/Medium correctness findings at this boundary. Preserve the checkpoint
revision and these receipts. Fresh database evidence, common-image/native
coverage and advisory dispositions remain M1 work; candidate runtime testing,
manual CI evidence transfer, activation ordering and production-equivalent
validation remain M3/M4 gates. No stale database exception, risk acceptance,
production readiness or rollout approval is created by this verdict.

## M1 Disposition Review Packet v1

Reviewed at source checkpoint `d4b175436b69ad4ba1038f96f3289f14b15f0091`:
private baseline `build-disposition-review.py` and `disposition-review-v1.json`,
SHA-256 `70db4f87965fecb283445a9326c4f1314408a5c9dcef528c0e394faf48bf9279`.
The writer was inspected, not executed; neither packet nor private evidence was
modified by this review.

Independent readback verifies:

- The hash-bound classified report targets
  `sha256:1819856096bf838cdf32fe52b035d13971e6aaa3aad4652b63759926fae23d74`.
  Its `matches` and `ignoredMatches` arrays equal the original baseline arrays.
  All 3,221 source section/index pairs occur exactly once in the packet, with
  no omitted, duplicated or added source offset.
- Ecosystem, package, installed version, artifact ID, paths, layers, advisory,
  aliases, severity, fix data, description and scanner-ignore rules match the
  pointed-to raw record. Original draft fields outside the four intended
  disposition fields are preserved. Full scanner records remain available through
  the report hash and source offsets rather than being reduced to summary counts.
- An independently reconstructed alias graph yields 3,133 groups. Each group
  has one artifact/ecosystem/package/version/path/layer identity. The installed
  and cached Python Brotli records remain three distinct groups despite sharing
  advisory aliases. Group keys are local to this packet's image context; future
  cross-image consumers must retain that context rather than treating them as
  globally scoped exception keys.
- Exactly 327 proposals refer to Debian `linux-libc-dev` `6.12.116-1`, artifact
  `dfe74f96b0e44e69`, retaining all 327 distinct advisory IDs and ignore reasons.
  The hashed package-file receipt targets the exact image. These are proposals
  based on absent affected implementation in that header package, not a global
  kernel/CVE waiver. Per-advisory review still must reject an unsupported blanket
  inference about inline/header defects, userspace tools or the host kernel.
- Exactly three further proposals cover Python Brotli `1.2.0` artifacts
  `2a4ab130a1dfb474`, `bdda0670090a5bf7`, and `78a09e14b19c710f` for
  GHSA-9v8h-qqgm-4m35. Their installed/cache/source paths match the prior exact
  artifact review. All six packet evidence-file hashes verify. The prior
  security review's source-fix and binary-hash evidence supports these scoped
  proposals; it does not cover Pillow, PyCurl or other independent native copies.
- There are 330 proposed not-affected rows and 2,891 rows without a disposition.
  **All 3,221 rows remain `blocking-unreviewed`.** Proposed rows explicitly
  require independent itemized review; no row contains an approval/owner field,
  and the packet declares no approval or gate clearance.

**Verdict: pass for review-packet integrity and proposal scoping; no M1
acceptance or activation clearance.** No High/Medium correctness defect was
found in the emitted packet's stated review-only behavior. The incomplete
reachability/call-site fields, pending rows, stale database and native coverage
remain acceptance gaps rather than implicit not-affected findings.

Before this packet can serve as standalone approval evidence, hash-bind the
Brotli installed/cache command receipts and build log as well as their output
JSON. They exist in the retained root and prior security review but are not in
v1's `evidence_files`: the output JSON alone does not record its producing image
command, and cached source alone cannot establish compiled provenance. This
review verified both extra command receipts target the packet image and exit
zero; the build-log hash matches the earlier security review. Preserve v1 bytes
and add a versioned packet/manifest when extending evidence. Reusing the private
writer as production validation would also require explicit source-offset and
all-field validation like this review, rather than its partial assertions alone.

## M1 Disposition Review Packet v2

Independently verified `disposition-review-v2.json` SHA-256
`1a5d5707812050c666b16466f7f2052cf095b42b6875571e8332bd067efc944a`.
Its `supersedes_sha256` matches the preserved v1 packet. All 11 evidence-file
hashes verify. The additions include both Brotli command receipts, the build
receipt/log and resolved build inputs, closing the v1 provenance-link gap above.
Only the three Python Brotli rows' evidence lists changed; all other row fields,
source references, grouping, counts and blocking status equal v1. The packet
still has 330 proposals and 2,891 pending rows, with no approval or clearance.

## M3 Manual Import Component Review

Reviewed `tools/security/import_dependency_evidence.py`, its focused tests and
`docs/infrastructure/dependency-security-evidence.md`. Final reviewed code
SHA-256: `c5bcbb8d6fdefeae138f2af1b4ccf8cac8c98e9912f67e6cecd45ae009bb6ebe`.
This is a local retention-integrity component review; M1 acceptance and M4
release review remain separate and open.

Two Medium correctness findings identified during review are resolved:

- **Failure after rename could leave a completed-looking bundle.** The earlier
  implementation marked publication before syncing the reservation and store
  directories. A sync failure returned an error but retained `bundle/`, making
  its status ambiguous and preventing retry. Lines 171-181 now mark publication
  only after both syncs and remove the renamed bundle and own reservation on
  failure. Focused tests inject each post-rename sync failure. The operator
  contract additionally requires successful exit plus readback; directory
  existence alone never proves completion, including after process termination.
- **A changed caller alias could produce an incorrect receipt path.** Writes
  used held directory descriptors, but the earlier result used the caller's
  unresolved alias. Lines 125-130 and 182 now resolve roots once and return the
  canonical destination. The regression test changes the alias during copying,
  verifies bytes at the reported original destination, and checks that the
  alternate destination remains empty.

The final implementation rejects duplicate JSON keys, unsupported schema fields,
incorrect expected hashes/image identity, path traversal, non-regular artifacts,
unlisted members and byte/hash/size mismatches. Exclusive reservation prevents
overwrite; failed copying removes the new import while preserving unrelated
retained evidence. Source mutation detection supplements exact byte hashing.
The raw manifest is retained without serialization changes. Root aliases are
supported explicitly while contained artifact reads use `O_NOFOLLOW`.

The implementation agent reports all 31 focused tests passed in 8.97 seconds.
This reviewer inspected their success and failure assertions, including real
temporary files, FIFOs, symlinks, retained-byte readback, private modes, alias
replacement, source mutation and injected durability errors. No full pytest run
was repeated by this reviewer; the post-implementation broad gate remains due.

Independently read back the five-file local import and its manifest using
`import-trial-20261111/receipt-v2.json`, SHA-256
`8705c565a4a077b03e2db99e556ec3140a3c583b933e1e05ee73eb773e72a7e1`.
The receipt exits zero, reports `retained-not-approved` and binds the reviewed
code hash. All retained file bytes equal collected bytes, all sizes and hashes
match the manifest and receipt, image identity matches the explicit command,
the manifest bytes/hash are preserved, directory membership is exact, files are
0600 and store/reservation/bundle directories are 0700. This includes the actual
SBOM, classified scanner report, Python/Debian inventories and v2 disposition
packet; no artifact content was interpreted as policy clearance.

**Component verdict: pass, unresolved High 0 / Medium 0.** Remaining coverage
limits are real power-loss recovery, independently authenticated remote runner
collection, producer/evaluator integration and Compose activation ordering.
Cleanup cannot promise removal when the filesystem itself prevents cleanup;
such a failed or interrupted import requires operator review and is unaccepted.
The exact imported scanner database remains stale and the advisory dispositions
remain unresolved. Neither this component nor its successful trial closes M1,
the complete M3 milestone, or M4.

## M1 MariaDB Artifact Review

**Blocking finding: a reported Connector/C version of 3.4.9 does not prove the
client escaping fix is present.** Exact-image shared and static libraries both
fail the upstream CVE-2026-44172 / CONC-819 Big5 escaping regression. Keep raw
`matches[51]`, `[52]`, and `[53]` blocking for `libmariadb-dev`,
`libmariadb-dev-compat`, and `libmariadb3`. Clearing these rows from the version
string would be a High correctness defect; the scanner's original Critical
severity is preserved. No application non-reachability waiver is established.

The [upstream advisory](https://github.com/MariaDB/server/security/advisories/GHSA-pv9p-5w55-55jm)
and [release notes](https://mariadb.com/docs/release-notes/connectors/c/3.4/3.4.9)
identify 3.4.9 as fixed, while the [Debian source tracker](https://security-tracker.debian.org/tracker/CVE-2026-44172)
still flags `1:11.8.6-0+deb13u1`. The retained probe applies the input and expected
output from [upstream fix 1f168de4](https://github.com/mariadb-corporation/mariadb-connector-c/commit/1f168de4e09838ffe14da061142ed387541aa25d)
to `mysql_real_escape_string()` on a locally initialized Big5 handle, with no
server or network. Both libraries produce `a15c27202b203130202d2d20`; expected
output is `5ca15c27202b203130202d2d20`. Both child probes return 1. The collecting
Python process returns 0 because collection itself succeeds, not because the
regressions pass.

The diagnostic positive control preserves each installed library and changes
only the temporary handle's copied charset callback to the upstream unsigned-
byte length rule. Both then produce the expected bytes. The original callback
returns length 1 for sign-extended `0xa1` and length 2 for unsigned `0xa1`,
matching the source defect addressed by the fix. This establishes failed local
escaping behavior, not an end-to-end SQL injection against WEPPcloud.

The confined readback uses exact image
`sha256:1819856096bf838cdf32fe52b035d13971e6aaa3aad4652b63759926fae23d74`,
UID/GID `1002:130`, no network, read-only root, dropped capabilities and
`no-new-privileges`. Only a disposable tmpfs holds the small compiled probe.
The initial execution-denied tmpfs trial is retained alongside the corrected
execution setup, failed regression results and successful diagnostic controls.
No installed library, application, dependency or production state was changed.

`/proc/self/maps` identifies the loaded Debian-owned
`/usr/lib/x86_64-linux-gnu/libmariadb.so.3`, SHA-256
`d283268434adf3cc3ffcb0580b384f3e13c91bd24b58114022073694dbcc2928`.
The explicitly linked `libmariadb.a` hashes to
`3225aa4836e6bc6b47f3b511a3004aa4bb64fe25c3ca61ea79f43f9c723e92cc`;
`nm` shows defined escaping/version functions and `readelf` shows no dynamic
MariaDB dependency in that static probe. All compatibility-library aliases
resolve to these binaries. The separate `libmysqlservices.a` contains service
data symbols, not the server implementations implicated below.

All **112 raw rows / 28 advisories** were reviewed, including 16 Critical,
44 High, 48 Medium and 4 Low rows. Each advisory occurs once for each exact
artifact: `libmariadb-dev` `71daf1efd9d81e66`, `libmariadb-dev-compat`
`498ea45976563a97`, `libmariadb3` `fe7e6e1ad0b2ec14`, and `mariadb-common`
`bc670f2a58abb257`, all Debian version `1:11.8.6-0+deb13u1`. Package contents,
archive members, upstream source changes and advisory component boundaries
support **109 narrow not-affected proposals; three client rows remain blocking**.
The list below uses zero-based offsets in the hash-bound raw report's `matches`
array. Every four-row range follows the package order just listed.

| CVE | Raw offsets | Affected implementation / proposed treatment |
| --- | --- | --- |
| CVE-2026-49261 | 13-16 | Server Galera notification command; absent. |
| CVE-2026-92262 | 20-23 | Server table-name/DDL encoding; absent. |
| CVE-2026-48165 | 29-32 | Galera SST joiner command construction; absent. |
| CVE-2026-107815 | 33-36 | CONNECT DOS table stack buffer; plugin absent. |
| CVE-2026-97380 | 37-40 | Server GRANT PROXY authorization; absent. |
| CVE-2026-44172 | 51-54 | 51-53 blocking; 54 configuration/docs only, no escaping code or library alias. |
| CVE-2026-107821 | 55-58 | Server binary FRM parser; absent. |
| CVE-2026-85746 | 61-64 | Server ST_AsText in `sql/spatial.cc`; absent. |
| CVE-2026-48163 | 102-105 | Galera rsync SST donor script; absent. |
| CVE-2026-86047 | 109-112 | Server SHOW serialization and `mariadb-dump`; both absent. |
| CVE-2026-107823 | 169-172 | Server view FRM parser; absent. |
| CVE-2026-44168 | 303-306 | Galera mariabackup SST donor script; absent. |
| CVE-2026-102523 | 333-336 | Server partition filename handling; absent. |
| CVE-2026-44173 | 533-536 | Server OUTFILE/DUMPFILE privilege enforcement; absent. |
| CVE-2026-107818 | 537-540 | Server service unit/Galera bootstrap; absent. |
| CVE-2026-107822 | 615-618 | Server role/user ACL cache; absent. |
| CVE-2026-85745 | 732-735 | Server ST_Area in `sql/spatial.cc`; absent. |
| CVE-2026-85985 | 752-755 | CONNECT file-access UDFs; plugin absent. |
| CVE-2026-60585 | 841-844 | Oracle Server: Replication implementation; absent. |
| CVE-2026-107816 | 904-907 | Server `qc_info` plugin; absent. |
| CVE-2026-60184 | 1000-1003 | Oracle Server: Replication implementation; absent. |
| CVE-2026-47023 | 1025-1028 | Oracle Server: Replication implementation; absent. |
| CVE-2026-44171 | 1079-1082 | `mbstream` archive extraction tool; absent. |
| CVE-2026-60331 | 1206-1209 | Oracle Server: Replication implementation; absent. |
| CVE-2026-44169 | 1217-1220 | Server stored-routine role privilege check; absent. |
| CVE-2026-60747 | 1229-1232 | Oracle Server: Replication implementation; absent. |
| CVE-2026-61081 | 1410-1413 | Oracle Server: Performance Schema; absent, including this Low finding. |
| CVE-2026-107817 | 1423-1426 | Server `type_mysql_json` plugin; absent. |

The six Oracle component assignments were checked against its
[July 2026 advisory](https://www.oracle.com/security-alerts/cpujul2026.html).
MariaDB server findings were checked against their individual upstream
advisories and, where linked, source commits: SQL/parser/privilege/spatial code,
CONNECT/query-cache/JSON plugins, Galera scripts, server service files, and dump
tool code. The private row review retains each primary advisory URL and exact
artifact/path/layer/group identity; the source review retains inspected commit
IDs and source paths. The four package lists contain none of those affected
implementations. The stronger readback retains `dpkg-query` exit 1, empty stdout
and explicit missing-package stderr for server/core/client/client-core/backup/
CONNECT/Galera packages.

Evidence is under the private baseline's `mariadb-correctness-review/`.
`manifest.json`, SHA-256
`82fe6f93abc9e07e70ddb6aafb3b20752603808f370e36ff8eaec533daf0ed59`,
binds 17 local evidence files and the original package readback, scanner report
and v2 disposition packet. `row-review.json`, SHA-256
`e976eefbbbfcec9d4ce143b0be08aa53abd5c8a4c64b7c93ef69caf6faa86a8b`,
itemizes all 112 rows and the 109/3 decision split. The original disposition
packets remain untouched.

These are artifact-specific proposals, not a blanket MariaDB source-package
waiver. They do not cover separate bundled copies, external database servers,
future builds, or native caller reachability. `mariadb-common`'s config-only
proposal does not exempt its client-library dependencies. Fresh scanner data,
independent security disposition and the three failed client findings still
block acceptance.

## OAuth Verification-Failure Contract Review

Independent read-only review of `20261111_oauth_contract_decision.md`, initial
SHA-256 `7e0ed541f42041e5dec6bb6a5db7d13f98aeeb4c587cad2a58b344ac7b9f1a91`.
This is the second pre-implementation contract review, not owner ratification,
implementation approval or M4 closure.

The normative addition is appropriate in principle: an expected provider-token
verification rejection should return a generic login failure before profile,
account or login side effects. It must preserve actual verification and valid
login, linking, redirects, `remember=True`, SID rotation and cookie behavior.
The failure escapes the current `authorize_access_token` catch at
`wepppy/weppcloud/routes/_security/oauth.py:473`; the retained actual-library
trial proves the exception mismatch, and the Flask probe proves it reaches
`LoggedBlueprint`'s propagation boundary. Existing mocked route tests alone do
not demonstrate the library boundary. The [documented JoseError family](https://jose.authlib.org/en/api/errors/)
is a bounded catch at this specific verification operation.

Initial findings requiring disposition before accepting the checkpoint:

1. **Medium — reconcile the CSRF contract explicitly.** The proposal refers to
   an existing OAuth callback classification, but the current CSRF contract
   names only provider disconnect explicitly. Its safe-GET matrix removes the
   CSRF-token requirement, while `Flask Route Requirements` line 39 separately
   requires same-origin checks for cookie-auth session mutations. A reference
   to the GET row alone does not resolve that broader language for normal
   cross-site provider callbacks. Record the bounded OAuth initiation/callback
   classification and Authlib state/nonce/PKCE safeguards without changing
   ordinary browser mutation or disconnect protections. Amend/cross-link both
   current contracts if this clarification creates an explicit exception.
2. **Medium — make the response and valid-state matrix concrete.** Freeze the
   intended HTTP 302 destination (`SECURITY_LOGIN_ERROR_VIEW`, default
   `security_ui.login`), generic error flash and state-consumption semantics.
   Distinguish a missing/empty application PKCE verifier from missing, expired,
   mismatched or replayed Authlib OAuth state; one cannot substitute for the
   other. Include valid anonymous/new-account, existing-linked-account and
   authenticated-linking states; absent/empty/populated optional `next` and
   remember/session state; legacy callback aliases; and supported non-OpenID
   providers. Verify rejection preserves a preexisting identity without new
   account/link/login calls. A real signed-token success through the actual
   Flask callback and real state validation must accompany the negative paths.
3. **Medium — forbid reuse of arbitrary exception text.** Adding `JoseError`
   to the existing catch and its `%s` exception logging can disclose supplied
   token-header data. The retained joserfc 1.8.0 wheel concretely interpolates
   `kid` in `_keys.py:153` and `alg` in `_rfc7515/registry.py:83-90`;
   `JoseError` also accepts arbitrary descriptions. Require fixed event text
   plus trusted provider and an error class or fixed code, never `str(exc)`,
   description, token/header/claim values or traceback text on this rejection
   path. Assert redaction using a sentinel in a real rejected header as well
   as claims; the fifteen existing rejection fixtures do not establish it.

Authority assessment: the current session contract governs successful OAuth
remember behavior and authentication diagnostics but does not prescribe this
verification-failure response. Classify this as a new normative clarification
for expected rejection, not an already-authorized conformance repair. The
dependency plan/M0 approval supplies task scope but does not replace explicit
owner ratification of the checkpoint required by the contract-first standard.
Canonical amendments marked implementation-pending, both independent reviews,
their dispositions and explicit owner approval must become a standalone
ancestor before the OAuth route or dependency batch is changed. A separate
crypto/TLS-only trial does not confer OAuth checkpoint acceptance.

Existing session, cookie, CSRF, authentication logging and OAuth suites remain
regression gates. The canonical session contract's listed conformance suites
need reviewed N/A rationales where behavior is unchanged, then regression runs;
they must not be silently omitted. No new test or implementation was authored
or executed in this review. Initial verdict: **changes required; three Medium
contract findings, no proposed relaxation of authentication checks accepted**.
### OAuth Proposal Finding Disposition

Rereviewed revised proposal SHA-256
`1299af67e22297774a9d8495d6efc0cffcfe3b8914fea7b60759b55fe7f9ca52`.
All three initial Medium findings are resolved at the proposal boundary:

- **CSRF scope:** the two named GET callback routes have a protocol-specific,
  cross-linked classification preserving cross-site returns and mandatory
  session-bound OAuth state, the existing PKCE exchange and configured OpenID
  verification. Disconnect, token minting and other mutations gain no exemption.
  The original canonical wording conflict is explicitly recorded for owner
  ratification and promotion into both current contracts.
- **Observable behavior and valid states:** the response now specifies HTTP 302,
  the configured/default endpoint, exact generic flash and `error` category.
  State consumption remains irreversible for that attempt. The matrix separates
  PKCE from absent/mismatched/replayed OAuth state and includes anonymous/new
  accounts, existing login/linking, preexisting identity on rejection, optional
  next/session/remember state, optional OpenID claims, non-OpenID providers and
  the legacy alias. A valid signed token must traverse the actual Flask callback
  alongside rejection cases; library-only success does not meet that obligation.
- **Diagnostic redaction:** the proposed separate `JoseError` branch permits
  only fixed text, configured provider and exception class/category. It forbids
  string/repr/traceback rendering and token/header/claim values irrespective of
  the library's current error-message examples. Final conformance evidence must
  exercise a sentinel-bearing rejected header, as requested in the initial review.

Two wording clarifications accompany this disposition: preservation of a
preexisting session means its authenticated identity/authentication state;
temporary OAuth/PKCE state is consumed and flash state can change. Assertions
of a generic error and no profile/account/login work apply to rejected callbacks;
valid callbacks must reach the existing successful outcome. These clarify the
matrix rather than authorizing any further behavior change.

**Revised proposal verdict: pass for explicit owner ratification; unresolved
High 0 / Medium 0 at this contract-design boundary.** No route or canonical
contract edit was present during this rereview. The final promoted session and
CSRF amendments still require independent readback, recorded owner ratification,
review disposition and a standalone checkpoint ancestor before implementation.
Implementation-specific correctness, real state/verification and cookie-boundary
evidence, the canonical regression gates and M4 remain pending.

Final frozen-proposal readback verifies SHA-256
`09b2790f274c5891732680f1fa518c6bbd17ef17a81dd58d802b79417821059b`.
Reversing exactly the two wording corrections above reproduces the previously
reviewed `1299af67...` hash; no other proposal content changed. **Correctness
approval for owner ratification applies to this final frozen hash**, with no
unresolved High/Medium contract-design findings. Owner ratification, canonical
amendments/readback and checkpoint ancestry remain pending; no implementation
or canonical edits are implied by this approval.
## Test-Base Selection and npm Lint Wiring Review

Reviewed `docker/Dockerfile.test`, `docker/docker-compose.test.yml`,
`docker/README.md`, `.github/forest_workflows/npm-tests.yml` and its generated
`.github/workflows/npm-tests.yml`. This scope changes isolated test-image base
selection and adds the existing npm lint command; it changes no primary
dependency, application or production deployment code.

**One Medium finding resolved:** the first Compose patch repeated the default
image digest as a build-argument fallback. That would silently override a later
Dockerfile pin update performed according to the existing README. Compose now
passes through the optional `WEPPCLOUD_TEST_BASE_IMAGE` without its own default;
the Dockerfile remains the single default-pin authority. Final Dockerfile
SHA-256 is `b04a7ec643bd35a7eb1b1fd6048dfbde9c65321ba1d4515880b1f885717f6188`;
Compose SHA-256 is
`15679549f10d20a4f9f869fc6ec2a1bfc4ccc2e6c9eb38d036853f05cad66fb2`.

The retained actual Compose build plan distinguishes unset arguments (`{}`),
an explicitly empty argument, and the explicit local candidate tag. The empty
build exits 1 with an empty-base error, matching the documented invalid state.
The final explicit rebuild exits 0 and produces the same reviewed test image,
`sha256:c52f34545097d7a46c88b381eeaefcd1852192474646b320cd6c94036f643d38`.
The private `crypto-batch-20261111/explicit-base-rebuild-receipt.json` hashes to
`9a53c47669a8121dd7ce014ae9c0a369ea5460ae44df05c301b3a6ff51a63ecb`.

Independent Docker inspection confirms the retained ancestry arrays and exact
base-layer prefix from candidate
`sha256:f0f3fbb48f4afe636eb8bfcc491d7fa28514543cc1fe4bc628bce8fda373da48`.
Both image configurations retain user `roger`. The actual isolated Compose
container matches the recorded image and user `1000:993`, with only the candidate
checkout bind, no published ports, all capabilities dropped and
`no-new-privileges`. This test identity is distinct from the separately retained
direct-image checks under production UID/GID `1002:130`.

Independent inventory reconciliation confirms 90 added browser-system packages,
zero changed packages and zero removed packages (432 to 522). The candidate and
test-extension Python/native/crypto probe files are byte-identical, SHA-256
`2f00d61ae04c3566f2aeac67c00afc0ecab79999597b64f4b72cb9078bc90026`.
The focused log confirms 51 passed and 13 warnings in 9.17 seconds; the wrapper
receipt records 17.9 seconds. These show the extension preserves the candidate
surface checked, not that its additional packages are production-approved.
The inherited old Authlib `nonce_supported` acceptance remains visible in that
probe and gains no OAuth/security clearance from equality.

The npm source spec adds lint between dependency installation and tests, with
normal fail-on-error behavior, and includes its own source file in both trigger
path lists. The generated workflow matches. Independent
`.venv/bin/python scripts/build_forest_workflows.py --check` exits zero; the
existing missing nightly-profile README section is reported as skipped, with
no generator or dependency change. Runner labels/bootstrap, permissions and
publication behavior are unchanged. This existing homelab npm job does not
establish isolated PR scanner collection or protected evidence transfer.

**Scoped verdict: pass; unresolved High 0 / Medium 0.** Future overrides still
require the documented tag-to-image readback, ancestry and installed-version
checks; an arbitrary different base is not covered by this trial. The earlier
importer component approval is unchanged. Its full-suite run, final candidate
validation and all remaining M1/M3/M4 gates are separate; none was rerun or
declared complete by this review.

## Verdict

M0 checkpoint: **pass**, unresolved correctness findings High 0 / Medium 0.
The owner, full baseline and scoped scanner prerequisites are retained as
described above; later artifact and operational evidence remains open.

M4 final correctness: **pending**. Closure requires implementation-specific
independent review, every changed user/operation boundary to remain valid, all
three broad test commands to pass, and no unresolved High/Medium correctness
finding. This design checkpoint grants no release or deployment recommendation.
