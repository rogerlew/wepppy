# Runs Catalog TTL Deletion Contract

**Owner**: REM-02 bounded remediation of SURF-06  
**Status**: Ratified by GOV-00A-M1B at `d3380287ca706360879240c3d203c5e7cc2be9ef`; implementation evidence pending
**Security tier**: high (inherited authenticated run-metadata surface)

## Purpose and Scope

The Runs catalog gives an authenticated caller lifecycle information only for
runs they are already allowed to enumerate. This contract governs a single
read-only lifecycle column; it does not govern TTL calculation, deletion,
permissions or catalog ownership/filtering. The 2026-11-04 amendment removes
the misleading deletion-column sort link without changing sort semantics.

## Presentation Contract

Implementation of the 2026-11-04 wording amendment is pending its checkpoint.
An active valid expiration renders **Automatic deletion is enabled for [readable
date]**, using readable UTC and an ISO `datetime` attribute. Confirmed disabled
or excluded policy renders **Automatic deletion is disabled**. Missing, empty,
malformed, unreadable, stale or unsupported state renders **Automatic deletion
status is unavailable**, followed by the existing Last Modified date if known.
Unknown state never implies protection. All rows link **How to keep your project**
using `url_for('usersum.view_doc', doc_id='usersum.weppcloud.run_ttl_deletion')`.
Text is rendered with DOM text nodes; no raw paths or payloads appear.

The column is **Automatic deletion** and is not presented as sortable: the old
header incorrectly sorted by last-modified while describing deletion. Other
sorts are unchanged.

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
