# Runs Catalog TTL Deletion Contract

**Owner**: REM-02 bounded remediation of SURF-06  
**Status**: Ratified by GOV-00A-M1B at `d3380287ca706360879240c3d203c5e7cc2be9ef`; implementation evidence pending
**Security tier**: high (inherited authenticated run-metadata surface)

## Purpose and Scope

The Runs catalog gives an authenticated caller lifecycle information only for
runs they are already allowed to enumerate. This contract governs a single
lifecycle column and its bulk protection action; it does not govern TTL
calculation, physical deletion, permissions or catalog ownership/filtering.
The 2026-11-05 sorting/bulk amendment is implemented locally after checkpoint
`6cbd4404b`; deployment remains separate.

## Presentation Contract

The 2026-11-04 wording amendment is implemented and locally validated after
checkpoint `c62567f1c`; deployment remains separate.
An active valid expiration renders **Automatic deletion is enabled for [readable
date]**, using readable UTC and an ISO `datetime` attribute. Confirmed disabled
or excluded policy renders **Automatic deletion is disabled**. Missing, empty,
malformed, unreadable, stale or unsupported state renders **Automatic deletion
status is unavailable**, followed by the existing Last Modified date if known.
Unknown state never implies protection. The top of the Table card links
**How to keep your project** once, not per row, using `url_for('usersum.view_doc', doc_id='usersum.weppcloud.run_ttl_deletion')`.
Text is rendered with DOM text nodes; no raw paths or payloads appear.

The column is **Automatic deletion** and sorts by `ttl_deletion_at`, never
Last Modified. The first header activation selects ascending chronological
order (earliest dates, including overdue dates, first); subsequent activations
toggle direction and expose `aria-sort`. When sorting by expiration, dated active
rows come first, unknown dates next, and confirmed-disabled rows last in both
directions. Switching from Creation date or any other sort must leave every
sort link operable; repeated activation continues to reverse direction. Other
columns retain their own sort order. Existing sort defaults, scope and paging remain.

For a fixed viewport, column widths stay consistent across sorting, filtering
and pagination. Wrap header and cell content, including long unbroken labels,
within their columns; retain horizontal table scrolling on narrow viewports.

The 2026-11-06 presentation refinement is specified; implementation pending.
Rationale: stable wrapping columns prevent moving click targets, a single panel
help link removes repeated clutter, and disabled-last ordering keeps expiration
review predictable in either direction.

Place **Disable Automated Deletion for Selected** beside **Delete selected**.
Reuse the visible checked-row selection and its readonly restrictions. Disable
the new button when nothing is selected or while its batch is in progress.
Snapshot the selection and issue sequential requests through the existing
[TTL setter](project-ttl-control-contract.md), with same-origin credentials
and CSRF protection. Report progress and final success/failure counts, identifying
failed runs with text-safe messages. Only confirmed successful responses may
update a row to disabled; failures remain unchanged and retryable. Re-sort the
current catalog after successful dates become null and preserve failed selections
that remain visible, so retry does not accidentally include successful rows. Responses
from an earlier catalog scope must not overwrite the newly selected scope.
This is a sequence of independent mutations, not an atomic bulk operation.
Protection confirmation follows the setter contract: null metadata or a
queued/trash/purged lifecycle is not successful protection. Explain that
already-started deletion cannot be stopped by this control.

Rationale (operator request, 2026-11-05): genuine expiration sorting helps users
find runs needing protection; reusing the setter preserves authorization/audit
and avoids a second bulk mutation API. The former no-sort rule prevented a
misleading Last Modified sort, not this explicitly requested expiration sort.

## Payload and Compatibility

Keep `ttl_deletion_at` and all existing fields. Add nullable boolean
`ttl_disabled`: true for known disabled/excluded policy, false for active policy
with a valid timezone-aware expiration, null for all other states. Read the TTL
file once per selected row. No persistence schema, default, formula, or physical
deletion change. Old clients may ignore the additive field; new clients must
treat its absence as unknown unless an active date is supplied.

## Authorization and Safety

Catalog authentication and owner/admin alias filtering run before any TTL
metadata lookup; an unselected run must never invoke the TTL reader. TTL reads
use the non-mutating reader after selection. `read_ttl_state` converts expected
`OSError` and `json.JSONDecodeError` file failures to `None`; the catalog helper
must not catch broadly and may handle only `TypeError` and `ValueError` from its
own timestamp parsing. Rendering must not touch access
timestamps, alter deletion policy/state, enqueue work, or disclose data for
unselected runs. Timestamp values are rendered with DOM text nodes, never HTML.

## User Documentation

The `usersum.weppcloud.run_ttl_deletion` document has `min_role: user`, appears
in the generated Usersum catalog/navigation tree, and is resolvable by the
least-privileged authenticated Runs-catalog user. It explains rolling deletion,
access refresh, disabled TTL, and the control available to all signed-in users
under the [project TTL control contract](project-ttl-control-contract.md). It does not
guarantee an exact retention duration beyond the displayed per-run timestamp.

## PostgreSQL projection amendment (specified; implementation pending)

The [catalog projection specification](../../schemas/run-catalog-projection-contract.md)
defines an opt-in database-only read path after its contract checkpoint and
staged cutover. The original "no database column" statement describes the
implemented REM-02 change; the new additive projection is a separately reviewed
change, not a claim that REM-02 implemented SQL storage.

After cutover, authorization still precedes scope selection and no request
opens TTL/project files or triggers repair. A background non-mutating extractor
preserves the existing normalization and expiration validation. Known-dirty,
unreadable, or older-than-24-hour TTL observations emit null `ttl_deletion_at`
and use unknown status with Last Modified; current observations use the
plain-language presentation above and the immutable same-origin help link. Additive scoped freshness
metadata and accessible stale/updating presentation are specified in that
contract. Policy calculations, TTL touch, readonly/ownership authorization,
and physical deletion authority remain unchanged.

This detailed freshness policy is pending independent review/ratification and
implementation. Verify source→SQL→JSON→browser propagation, no request project
I/O, scoped counts, dirty/error/recovery states, and current/legacy parity before
activation. Legacy mode retains the existing behavior during rollout/rollback.

## Verification

Evidence must include focused metadata (including every fallback listed above),
catalog scope/no-read ordering, client/template prefix/link safety, and normal-
user/privileged Usersum route tests; frontend and documentation checks; and two
independent reviews with no unresolved high/medium finding. The accepted
GOV-00A-M1B contract ancestor is recorded in the REM-02 tracker before
implementation.

## RUNS-TTL-BULK-01 local implementation evidence (2026-11-05)

Implemented after standalone contract ancestor `6cbd4404b`: chronological
expiration sorting and the selected-run protection action. Focused Python,
frontend and rendered-template Chromium checks pass; the Chromium HTTP
responses are mocked. Independent correctness/security reviews passed after
stale scope-state fixes. See [validation and limits](../../work-packages/20261105_runs_bulk_ttl_control/artifacts/validation.md).
Production deployment and catalog projection activation remain separate.
