# Runs Catalog TTL Deletion Contract

**Owner**: REM-02 bounded remediation of SURF-06  
**Status**: Ratified by GOV-00A-M1B at `d3380287ca706360879240c3d203c5e7cc2be9ef`; implementation evidence pending
**Security tier**: high (inherited authenticated run-metadata surface)

## Purpose and Scope

The Runs catalog gives an authenticated caller lifecycle information only for
runs they are already allowed to enumerate. This contract governs a single
read-only lifecycle column; it does not govern TTL calculation, deletion,
permissions, catalog ownership/filtering, or catalog sorting.

## Presentation Contract

For an active TTL state, the lifecycle cell renders the text `TTL Deletion:`,
the expiration timestamp, and a `Learn More` link. An active state is exactly a
TTL payload whose `policy` equals `rolling_90d` and whose `expires_at` is a
timezone-aware ISO-8601 timestamp. The Jinja template must create the link with
`url_for('usersum.view_doc', doc_id='usersum.weppcloud.run_ttl_deletion')`; it
must not read the href from catalog JSON or a timestamp value. This preserves
the deployment prefix and makes the route an immutable same-origin template
value.

For every other state, including the existing Disable TTL Deletion setting,
readonly/batch exclusions, missing TTL file, malformed JSON, non-mapping TTL
file, non-string/unknown policy, or missing/null/invalid timestamp, the lifecycle
cell renders `Last Modified:` and the existing catalog
timestamp. It does not render a deletion time or Learn More link. A missing
last-modified value uses the existing `—` empty-date convention. Per-row TTL
failure is silent to the user, does not include filesystem paths or raw metadata
in a response, and must not cause a catalog failure, TTL touch, or mutation.

The table's existing `last_modified` sort remains unchanged. The column is not
sortable by TTL expiration in this bounded remediation.

## Payload and Compatibility

`/runs/catalog` retains all existing fields, especially `last_modified`, and
adds `ttl_deletion_at` to every returned row. It is either `null` or a UTC
ISO-8601 string ending in `Z`. It is non-null only for the active state above;
the server normalizes an accepted expiry to that representation before JSON
serialization. The browser displays this existing serialized string rather than
attempting locale conversion. Older/incomplete runs receive `null`. No database
column, persisted run state, request shape, sort key, or time calculation changes.

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
access refresh, disabled TTL, and the existing role-gated control. It does not
guarantee an exact retention duration beyond the displayed per-run timestamp.

## Verification

Evidence must include focused metadata (including every fallback listed above),
catalog scope/no-read ordering, client/template prefix/link safety, and normal-
user/privileged Usersum route tests; frontend and documentation checks; and two
independent reviews with no unresolved high/medium finding. The accepted
GOV-00A-M1B contract ancestor is recorded in the REM-02 tracker before
implementation.
