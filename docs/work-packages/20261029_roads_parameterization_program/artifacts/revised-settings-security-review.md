# Roads settings proposal security review

## Metadata and boundary

Reviewer: independent `settings_security` agent, 2026-11-03. Repository checkpoint
`6cf8dcad63aa75054a9bd8dcc75a539c405573df`. Reviewed the proposed canonical
`docs/schemas/roads-settings-contract.md`, ADR-0135, static layout, current Roads
route/controller boundaries, shared CSRF and NoDb contracts, and Roads lifecycle.
This review approves a concrete proposal's security design only. Human approval
is absent; no editor implementation, browser/RQ validation or deployment is approved.

Reviewed proposal hashes:

- Contract: `7bd11c84814707480656f7b26ab9abd5b63962bd7c2836424a069ffb07a291ca`.
- ADR: `1693bcac4ff41f8c75bcfb8a7761fe429dbe5e69bf39b040276a75e484511bc4`.
- Layout: `e6acb4990e7c79adae37560a8db3d8de11bd1f46cc1a423440a7887ea048b910`.

Scientific studies and their final citations are complete and independently reviewed. Changes to the
reviewed transport, persistence, authorization or artifact semantics require
review of that delta; adding bounded scientific outcome citations alone does not
constitute implementation validation.

## Triage and threat model

Security impact is **high** for the eventual implementation because it extends
public route behavior, saved project metadata and filesystem artifact production.
A dedicated review is therefore required even though no new endpoint, service,
queue, credential, path parameter or native executable is proposed. This
proposal-only checkpoint changes no deployed attack surface.

Threats are unauthorized mutation or disclosure, session CSRF, malformed numeric
or metadata payloads, unsafe rendering of uploaded/legacy labels, lost concurrent
updates, misleading provenance/currentness, and failure or restore exposing a
mixed state. Existing run access, request lifecycle fence, Roads operation guard,
NoDb serialization and ordinary browse/archive boundaries remain authoritative.
No new owner-only/login requirement or permission topology is inferred: existing
public/mutable projects must preserve their established authorized behavior.

## Design assessment

| Surface | Assessment and required implementation evidence |
| --- | --- |
| Authorization and readonly | Existing `roads_set_params` is decorated by `authorize_and_handle_with_exception_factory`; it authorizes before the mutation request fence. The Roads mutation decorator checks READONLY before controller mutation. Preserve these boundaries and enabled-state checks. Test private unauthorized denial, valid existing access and readonly denial through the real server. |
| CSRF | Reusing the session-authenticated POST with shared WCHttp/CSRF helpers conforms to the CSRF contract. Do not add an exemption or rely on same-origin headers alone. Test valid token success and absent/invalid token denial with middleware enabled. |
| Input and metadata | Five canonical keys, finite/range checks, enum validation and atomic known-field validation are explicit. Metadata is server-owned and has fixed schema/baseline values; clients cannot select policy or supply deserialization types. Test attempted metadata injection, nested/object/list values, null, booleans, nonfinite and invalid enums without mutation or current-receipt loss. Existing unrelated partial API behavior remains intact. |
| Rendering | Shared macros/status/Details are appropriate; no raw HTML rendering is required. Uploaded source labels and unsupported metadata must remain text/escaped data. Test hostile attribute strings in the actual presentation. Do not trust browser field bounds as server validation. |
| Persistence/concurrency | Settings and metadata share one NoDb transaction; no duplicate scientific-value store is proposed. Current durable state must be refreshed under canonical ownership before applying the field delta. Existing request/catalog/Roads/NoDb guard order and explicit busy errors remain. Verify unrelated fields survive contention and failure; a stale draft is not authority to replace whole controller state. |
| Invalidation/failure | Validation precedes artifact retention and NoDb changes. Rejected requests preserve a coherent current result; accepted invalidation followed by failure stays non-current with retained diagnostics. The proposal correctly declines a distributed-rollback guarantee. Exercise actual retain and persistence failure boundaries. |
| Artifact visibility | No new hidden artifact or download-only storage is introduced. Provenance resides in existing visible summary/manifest records and NoDb; history retains diagnostic context. Test normal authorized browse/download and canonical archive/restore bytes and permissions. Metadata must not confer current-result admission. |
| Fork/restore/legacy | Missing metadata means legacy provenance; reads/forks do not rewrite values. Unsupported metadata is reported rather than used to select a different policy. Save may establish supported metadata explicitly. Test legacy/new fork and coherent restore, including failure without current receipt and preservation of unrelated/baseline state. |
| Queue/subprocess/network | No enqueue edge, shell command construction, external fetch or new dependency is proposed. Existing run orchestration still needs post-approval end-to-end validation; there is no graph-change claim from this document. |

The proposed boolean rejection is an explicit prospective validation rule; current
numeric coercion can accept Python booleans. It must be recorded in the approved
normative delta and tested after approval, not described as already implemented
conformance. No change to scientific thresholds/defaults follows.

## Valid-state noninterference

The contract enumerates absent/never-used, empty/no-upload, populated, legacy,
unsupported metadata, invalid/hostile, readonly, concurrent, failed and restored
states. Optional metadata absence is not corruption and does not block reading or
saving an otherwise supported configuration. Unknown provenance cannot certify
old outputs, but neither may it discard existing values. Existing module activation
errors remain separate from absent optional metadata.

A supported empty Roads controller must accept an authorized settings Save without
an upload; preparation still requires its existing inputs. Baseline-only projects
must remain usable without creating Roads state during reads. Security tests must
prove both valid-state success and hostile denial; UI-disabled controls or mocked
boundary calls are insufficient. Security approval cannot substitute for the
separate correctness/UX/scientific reviews.

## Findings and verdict

**PASS for the proposed security design.** No unresolved high, medium or low
security-design finding was identified in these reviewed artifacts. This is not
risk acceptance for missing runtime evidence. The explicit human gate and required
contract ancestor remain open; release recommendation is **hold implementation
until those gates, then hold release until actual boundary validation passes**.

Review was read-only against production files. Source inspection verified the
existing route authorization/request fence, mutation READONLY check, stale-controller
check and accepted-save invalidation order. No live mutation or test is claimed
for the unimplemented editor. Documentation lint and spelling preview validate
this review artifact only.

## Revised proposal delta review

Re-reviewed the expanded contract after correctness review, including checkpoint
`20261103_revised_settings_contract_decision.md` SHA256
`07798d9a7c9f7d9b9f1e8739fce9a10e81a76ff8d9ab210dcd2ba8a4e2c8faf5`.
The hashes above now bind this revision rather than the initial draft.

The execution manifest remains a list and provenance is additive per row. Source
segment entries and prepared-file paths/hashes are explicit; generated identities
are not accepted as authorization or current-result eligibility. Existing path,
browse and archive boundaries still govern those records. Failure records retain
unresolved/partial status rather than fabricated source values. Usage counts are
not another persisted model-input authority.

Malformed **present** saved fields now have an explicit repair path: safe text
and field diagnostics, finite JSON output, no default/custom certification, and
no Prepare/Run until an authorized complete five-field Save repairs the state.
Absent legacy fields continue existing defaulting, and missing optional metadata
continues to allow supported operations. This preserves valid-state noninterference
while preventing malformed values from silently selecting physical inputs. A
partial Save cannot evade remaining malformed fields; the full repair uses normal
authorization, CSRF, readonly, lifecycle and atomic NoDb checks. Required runtime
coverage must exercise both absent-key success and present-invalid rejection plus
successful repair, including raw-value validation before normalizers run.

The explicit traffic-null/boolean rejection and saved-corruption policy are
prospective behavior changes requiring human approval; the checkpoint now says so.
Concurrency wording correctly permits a later explicitly accepted Save under the
existing serialization policy without claiming automatic stale-draft conflict
detection. No hidden access restriction, permission change or new lock is added.

**Delta verdict: PASS for proposal security design, no unresolved findings.**
This re-review does not waive any post-approval evidence or grant implementation
permission. Scientific outcome evidence remains separate from security validation.

## Adjacent action and draft-ownership re-review

Reviewed the added client action contract after the existing mapping action was
found to read surface/traffic fallback fields. Separating the panel payloads
(mapping-only versus five settings keys) prevents an adjacent action from silently
committing an unsaved settings draft. Existing broader API compatibility remains;
there is no authorization expansion or server policy bypass.

Dirty-draft and pending-request restrictions are local workflow safeguards, not
security admission. The contract explicitly keeps readonly/busy restrictions,
requires action-handler checks as well as disabled controls, binds hydration to
the current Save request, and prevents passive/late responses from overwriting a
draft. Cancel re-reads without mutation and a failed reload does not guess settings
or unlock Prepare/Run. Clean-state actions retain existing behavior. These are
bounded UI state changes requiring the same human approval; they add no lock,
credential or persistence topology.

**Security delta verdict: PASS, no unresolved design findings.** Required later
browser/controller tests must prove both clean-state success and dirty/pending/
readonly denial, payload separation, late-response handling and reload failure.
They do not replace real server authorization, CSRF or atomic mutation tests.
The proposal hashes above bind this latest reviewed action contract and layout.

## Final evidence and proposal identity confirmation

The final contract/ADR/layout replace pending-study text with the completed
47-profile and four-project evidence and independent scientific review. The added
scope qualifications distinguish studied values, validity limits and calibration;
retain context-dependent traffic response and non-EVENT/PASS accounting limits;
and grant no generated-soil adoption or browser/RQ security certification.
No transport, saved schema, authorization, artifact-retention or server concurrency
behavior changed from the reviewed design. The explicit pending-Save wording also
correctly disables Cancel/Reset until that request settles; cancellation is not a
rollback of a server mutation.

**Final proposal security verdict: PASS, no unresolved findings.** The three
proposal hashes in Metadata bind the final evidence-bearing artifacts. The human
specification/layout gate and post-implementation runtime security acceptance
remain open; completed controller studies cannot substitute for those boundaries.

## Post-approval security acceptance

Retain direct, unmocked evidence for valid and denied authorization/CSRF/readonly
requests, atomic malformed-input rejection, same-transaction values/metadata,
contention/stale writes, failed retention/persistence, historical artifact visibility,
archive/restore and baseline preservation under actual service identities/mounts.
Verify the browser uses the normal request helper and that current-result reads
reject stale resources after Save. Do not mark any of these completed from the
present proposal review or controller-only sensitivity studies.

No secrets or operational credentials appear in the proposal. No new secret,
network, CI/CD or supply-chain policy is needed. Existing archival permissions and
runtime ownership remain unchanged. There are no accepted-risk exceptions.

Security reviewer sign-off: `settings_security`, 2026-11-03. Package-owner
acknowledgment and final proposal disposition belong in the parent checkpoint;
human specification/layout approval remains a separate decision.
