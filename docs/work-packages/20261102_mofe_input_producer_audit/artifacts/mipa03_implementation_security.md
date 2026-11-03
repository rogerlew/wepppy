# MIPA-03 implementation security review

Reviewer: `mipa03_contract_security`, 2026-11-03 UTC. Independent source and
direct-boundary review during implementation; **not final release approval**.

## Findings and disposition

| ID | Severity | Trigger, evidence and consequence | Required action | Current disposition |
| --- | --- | --- | --- | --- |
| SEC-MIPA03-I01 | Medium | Both RAP writers initially retained `open(p<ID>.cov, 'w')`. A symlink or hardlink destination overwrote the linked source. Direct ordinary/transformed writer probes reproduce all four combinations. This violates the ratified regular-file and hardlink-preservation boundary. | Publish cover through checked exclusive attempts and atomic replacement, preserving source bytes and failed evidence. | Fixed and independently verified by v2 writer probes: symlinks reject; hardlinked originals stay unchanged. |
| SEC-MIPA03-I02 | Medium | Initial flag/date helper replaced a mode-0600 existing file with mode-0644 under umask022. Actual helper reproduction confirms the widening. | Preserve existing destination mode before writing replacement payload; new files retain normal umask behavior. | Fixed and independently verified: replacement remains0600. |
| SEC-MIPA03-I03 | Medium | In combined native version2→3 execution, `main.for` initially left module `cc_run=1` after the final hillslope. `wshdrv.for:724` calls DECOMP, and channel SOIL reaches INFPAR, so specialized behavior could leak into routed channels. | Reset RAP mode at the actual watershed transition; retain a direct transition regression. | Source now calls `rap_mode(ivers,imodel)` on entry to the version3 block. Dynamic regression remains to be checked. |
| SEC-MIPA03-I04 | Medium | `numeric_row` allocates `n*129+1` characters and requires EOR on the first nonadvancing read. Three valid128-character tokens with the producer's two-character separator occupy exactly388 characters, equal to the buffer; the next EOR is not consumed. Thus a contract-valid boundary record can be rejected by an undocumented record-length constraint. | Exercise exact-buffer records and permitted token widths/separators; handle end-of-record without inventing a scientific clamp or silently accepting extra fields. | Reported to parent; fix/regression pending at this snapshot. |

These are bounded source/publication and valid-state findings. The operator's
reference numerical choices remain untouched. No new concurrency service or
transaction protocol is requested; the existing sole-writer preparation
assumption remains the reviewed scope.

## Scope and reviewed contract

The ratified final mirrored contract hash is
`c3b2f8b1bcdaec079e1a9574001dc9e562467cb2c004a4e54ef8c8b9bb4a164f`;
standalone ancestors are WEPPpy `c8f6ea854` and native `ee9e73f8b`, with
supplemental preimplementation confirmation in `mipa03_contract_security.md`.
Reviewed native `rap_state.f90`, activation/naming/reader integration in
MAIN/CONTIN/INFILE, specialized guards in INFPAR/DECOMP/growth callers, and
WEPPpy `revegetation_inputs.py`, both cover writers and full-preparation changes.

Security triage remains **high** because new native file parsing and changed
publication/retirement boundaries consume run-scoped data. No new auth, route,
secret, network, queue, subprocess command or privilege interface is introduced.
Final security sign-off follows correctness/QA and exact-artifact validation.

## Direct filesystem evidence

Executed real imported writers/helper through `wctl exec -T weppcloud python`.
Only unrelated NoDb/translator lookups were supplied as doubles; the failing
filesystem boundaries were real. Private evidence roots:

- `/wc1/holdouts/mipa-native-r7-20261103/security-implementation-v1`
- `/wc1/holdouts/mipa-native-r7-20261103/security-implementation-v2`

Each contains the replay script and a receipt binding source hashes. The v1
receipt SHA256 is
`37369d2783e5b2cf6510fe7637d725e14bd56004bd78ed3e3a95cae13cb9df32`;
v2 is
`3c6d83cc8d41b41c3a055854824fc84f1cf048f8e3ba3a2396534b859396d2a7`.

| Direct check | Initial result | Revised result |
| --- | --- | --- |
| Ordinary cover at symlink | Linked source overwritten | Explicit ValueError; source unchanged |
| Transformed cover at symlink | Linked source overwritten | Explicit ValueError; source unchanged |
| Ordinary/transformed cover at hardlink | Both source inodes overwritten | Both original source payloads unchanged |
| Mode0600 date replacement under umask022 |0644 |0600 |
| Date at symlink | Explicit error | Explicit error |
| Date at hardlink | Source preserved | Source preserved |
| Injected second rename failure after retirement | Explicit OSError; original and attempted date retained | Same explicit failure and retention |

v2 loaded `rap_ts.py` SHA256
`6c24deae69b7a8b4e1ac64c32245e79d8f73b92ee97fbdad01afab7d21cf88fc`
and `revegetation_inputs.py` SHA256
`388b36dfa584f63143632e5a8d8b26b4e1ef16fb62d2a812902aacb8cd60e59f`.
The revised MAIN source SHA256 at inspection is
`b40d40fefd2dd9302aeb53dc5dc1ed0809718f9c0e7db99440bd97c5c57e9446`.
The inspected parser source SHA256 is
`50b6527f1fe8cc5ccf2544769829c1e0a02fb163fe2b3bdd839fc708f6b6fab5`.

## Parser and valid-state assessment

The current reader rejects null/slash/repeat syntax lexically, enforces numeric
count within each physical row, checks finite REAL64 parsing and REAL conversion,
checks calendar labels, validates Gregorian dates before month indexing, and
rejects extra physical records. Current-hill allocation avoids the historical
global cover cube. Dimension product checks use widened arithmetic; allocation
failure is explicit. Cover basename extraction drops parent paths rather than
combining their digits into another hill identity. No cover contents become a
shell command or output pathname.

These are source observations; required compiled malformed-reader tests are
being developed by the parent. Nonfinite summed vegetation can still fail under
the retained numerical domain behavior; this review does not authorize a new
normalization or clamp. Optional absent fire state retains reference zero date,
and ordinary mode does not request the specialized reader. Observer writes must
remain observational and be bound to their actual final source and outputs.

## Remaining validation and verdict

At this interim snapshot, **FAIL pending I04 closure and validation**. I01/I02
have direct closure evidence; I03's source correction still needs its compiled
transition assertion. Required broader evidence remains: committed native parser
regressions, real canonical archive/restore of retired and failed records,
normal project browse/download, service-identity full preparation and final
matched artifacts. No production files were edited and no shared native build
was launched by this reviewer. Ordinary mode controls, scientific parity and
full histories belong to the separate correctness/QA gates.
## Supplemental closure review

Rechecked the final streaming parser, MAIN routing transition and both ordinary
and transformed cover publication paths. This supplement supersedes the interim
FAIL above for the bounded implementation security gate. **PASS: no unresolved
medium/high implementation security findings in the reviewed source.** Final
release approval remains conditional on the separate gates below.

- **I01/I02 closed:** the publisher and both actual cover writers still match the
  independent v2 receipt hashes above. Exclusive attempts, regular-file checks,
  visible retirement, atomic replacement and prior permission retention remain
  in place. Direct ordinary/transformed probes reject symlinks and preserve
  hardlinked source bytes; private replacements remain mode0600. Failed writes
  and failed replacement retain useful bytes. Under the existing sole-writer
  preparation assumption, no additional blocking race was identified. Concurrent
  hostile mutation of the run directory is outside this reviewed assumption.
- **I03 closed at the source and component boundary:** MAIN calls `rap_mode` before
  watershed initialization on the actual version3 path. The compiled native
  reader fixture activates RAP, reads cover, invokes `rap_mode(3,1)`, and fails
  unless `cc_run` becomes zero. Full combined routing remains an end-to-end
  correctness gate; this component assertion alone does not prove it.
- **I04 closed:** the reader streams 256-character chunks while retaining only a
  128-character numeric token. It counts exactly the required tokens at physical
  EOR, including EOR arriving on a later read, without bounding legal whitespace
  length. Regression inputs include three maximum-width tokens separated by
  space/tab and a second row with 257 leading/trailing spaces. Extra, missing,
  null, slash, repeated, partial, nonfinite and overlong values still fail.
  Nonadvancing EOF checking also rejects extra blank physical records.

Wide parsing validates each token, while a separate direct REAL read preserves
reference storage rounding. The discriminating double-rounding regression also
checks that the observer emits the actual stored value. No scientific clamp,
normalization or parameter change is authorized by this closure; the user's
preserve-reference decision remains controlling.

The parent confirmed the v4 run includes reader/growth and the v5 run includes
reader/growth/hydraulics. Retained `native-focused-v5.log` reports **320 passed**;
its SHA256 is
`b30fcef7e4d9b6cd939b539e01b5a24a315be001338131416dff85762ad094e3`.
This reviewer inspected source/tests and the retained result, without launching a
concurrent native build. The actual-reader regression source SHA256 is
`3ab576d271cfa2b4b2a00f7800391f9a37dacf79c99ba947e0a343ad60e7c27f`;
the final reviewed `rap_state.f90` SHA256 is
`d95df340f1588fc9b218bd654cf5367709693e9d3d21f93ee1fb38dab5968272`.
MAIN, `rap_ts.py` and the publisher retain the revised hashes recorded above.

`python-focused-v2.log` explicitly runs RAP transforms, publication and canonical
project archive tests: **75 passed**. Log SHA256 is
`d67c8a09420a737cdaff7274506a106b622229ca63b1d193b57ccf48c2dd4a20`.
The new canonical archive test invokes `archive_rq`/`restore_archive_rq`, compares
actual ZIP members with retired date/current date/failed-cover bytes, and verifies
the restored bytes. Publication tests also cover unchanged no-op, hardlink/private
mode preservation, symlink rejection and failed-final-replace retention. This
closes the focused archive regression requirement, with service-identity workflow
validation still pending. Publication test SHA256 is
`7a30ff90cf0854e03527636309d74db15ae09c269746d507dbf4e1e9cbd7b200`;
archive test SHA256 is
`0560eb57f55bb95de274d0eb7e9705846cba5a51274f7b9ee2adc6acdd8fc8fc`.

The mirrored contract's implementation clarification explicitly covers flags,
dates and cover files and preserves existing modes while honoring umask for new
files. Its SHA256 is
`d92feee506c5fdb8a5eb1e6902e6f9cf6dae5db297c4b9f375de4ff3736fff04`.
It documents the reviewed closure without changing reference scientific behavior.

Remaining release gates: final matched native/source artifacts, complete normal
preparation under service identity on the configured fork, normal project
browse/download, ordinary-mode and combined-routing controls, and final
correctness/QA findings closure. This is an implementation security PASS, not
production deployment or package-closeout approval. Reference sources remain
untouched; this reviewer edited only the review artifact.

## Final local workflow security review

Rechecked after independent source correctness and native QA closures. The
reviewed parser, publisher, cover writers and MAIN transition retain the hashes
bound above. The local vendored pair matches both sidecars and the executed
service context:

| Role | SHA-256 |
| --- | --- |
| Watershed | `4a9da3980d1a9249e566626c01de920de7dba5088ec25324dc1c6dd6eff8c825` |
| Hillslope | `210d48da09ff60707ba2404dd32af1f0a74e95437d2cb900c5408121141a1936` |

Both identify committed native source
`e0abe0581f77c6f66917e90daf8f8f429e9315c8`. The last Makefile-only correction
retains model/compiler behavior and rebuilt identical bytes. Retained final gates
show 1,750 native passes, 31 watchlist passes, artifact-policy/provenance passes,
eight post-vendor runner tests and both role smoke passes. The installed
9005/RAP application pair completes hillslope and watershed execution. Independent
mode/history QA closes the actual MAIN combined routing transition and final
history integrity checks; these are no longer outstanding security prerequisites.

The complete configured fork uses UID1000, GID993, supplementary group993 and
umask022 in the ordinary WEPPcloud container with the recorded `/wc1` NFS mount,
repository mounts and saved configuration. Canonical preparation covers 72
hillslopes, 235 OFEs and 35 calendar years. Execution and installed interchange /
HillslopeWatbalReport readback complete on the same NFS fork. This is actual
service-identity workflow evidence, beyond the earlier component tests.

This reviewer independently checked that all 576 output filenames equal the
prepared run-card declarations and retained receipt, all 72 execution-log hashes
match, and H1/H72 water/loss samples match their retained hashes. All 75 current
specialized files (72 covers plus three activation/date files) are regular files
owned by UID1000:GID993 with mode0644. The normalized fire date and all 235 cover
OFE blocks are present. The independent checks and evidence hashes are retained
in `/wc1/holdouts/mipa-native-r7-20261103/security-workflow-v1/receipt.json`,
SHA-256 `e8b4f5ae76fd59df7d22b7206426537c5ab167b5efc873faedcfce868cb4efd5`.

The new browse route regression uses real publication helpers, lists the visible
retired directory and failed temporary file, and downloads their exact bytes as
attachments. `browse-evidence-v1.log` reports one pass. Existing fixture auth and
run resolution are supplied as doubles: this verifies artifact reachability
through the existing route, not a live authentication flow. No production auth,
route or run-access change is introduced. Together with the earlier canonical
archive/restore regression this closes the visible retained-evidence boundary.

The initial execution log's 504-versus-576 assertion remains retained failed
validation evidence. Readback v2 instead checks the actual run-card declarations:
revegetation preparation requests an eighth graphics output per hill. All 576
files remain in the inventory. Correctness review confirms the inherited F10.5
formatter cannot represent disturbance ages at or above 10,000 days; the all-file
audit confines 734,107 star cells to “Days since last disturbance.” This is a
recorded serialization limitation, not an authorization to normalize, suppress or
change the reference field. Water/interchange validation is a separate claim.

One additional **Low evidence-quality finding (I05)** arose during this review:
`finite_water_columns` in the initial audit receipt was accidentally populated
with final graphics-row tokens because a local variable was reused. The water
finite checks themselves had executed before the reassignment. The parent fixed
the variable binding and reran the all-file audit, retaining the original receipt.
**Closed:** `configured-execution-v1/artifact-audit-v3.json`, SHA-256
`d817c9a7247698a3c77c675c0c523537d9bd994df1df844a4d733574e63598e3`,
now lists the 22 checked water fields. It confirms 3,004,240 unique daily rows
across all 235 OFEs, finite/non-null values in those fields, and explicitly
all-null optional `InterceptionStorage`, which this native writer does not emit.
The rerun checks every non-star graphics token with numeric finite conversion,
retains the inherited star-field limit, and confirms the source project files
remain unchanged. No audit exclusion silently turns a missing field into a value.

**PASS for the bounded local workflow security gate.** No unresolved medium/high
security finding remains, and I01–I05 are closed. The sole-writer preparation
assumption and recorded inherited numerical/serialization limitations remain
explicit. Configured-project observer neutrality and final publication/disclosure
review are still separate pending gates at this snapshot. A local `/tmp`
observer replay does not replace the already completed ordinary NFS service
workflow; retain its earlier NFS timeout and partial trace as failed diagnostic
evidence. This approval does not authorize deployment, a default-executable
switch, expanded upload support, altered runtime identity or changed reference
science. This reviewer changed no production code or binary.
