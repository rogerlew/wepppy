# Fresh seven-material retention source cohort: acquisition protocol

Status: preparation for review only. No network acquisition, source build or
native invocation is authorized by this file alone. Parent review must bind the
final declaration before the acquisition action. This is the acquisition lane
proposed by [the feasibility review](resumption-r7-retention-feasibility-review.md).

## Scope and fixed identities

Fresh root:
`/wc1/runs/ro/roads-parameterization-program-20261103/retention-source-v1`.
Acquire exactly **1718465, 1718494, 1718510, 1856573, 2711184, 2711250, 53949**.
The six frozen withheld IDs in `design-v2.json` remain excluded. No retained
native outcomes determine source acquisition or row selection. Both future
default/optional arms must use this one cohort; source-vintage changes relative
to frozen U12 require separate accounting from any retention-policy effect.

Use the installed owned `SurgoSoilCollection`, with a new explicit
`collection.sqlite` and unchanged SQL construction, extraction, retry and missing
data behavior. Fetch the five owned table families in their normal dependency
order: component, chorizon, corestrictions, chfrags, chtexturegrp. Do not replace
SQL, add DISTINCT, sort returned source rows, change missing values to zero,
change component selection, or splice old table data into this cohort.

## Declaration and request evidence

`acquire_r7_retention_source.py declare` creates only a fresh declaration. It
records all seven requested IDs, exclusions, endpoint, exact owned query templates,
owned SQLite table schemas, helper/protocol/design and loaded dependency hashes,
service UID/GID, bounds and zero build/native scope. Query templates are captured
through the owned query functions with transport replaced by an in-memory capture;
this declaration performs no HTTP request. The final acquisition action requires
`execution-review.json` binding the declaration SHA256, both independent review
passes, and exact reviewed file hashes. An exclusive start receipt prevents reuse
of an already attempted root. Failed attempts require a new reviewed destination.

The request recorder wraps only the owned `requests.post` call. It checks each
exact query against the owned constructor and the allowed parent IDs obtained
from earlier cohort responses, then passes through the original request contract.
Owned 30-second timeouts and three-attempt timeout retry behavior remain unchanged.
A 600-second overall deadline bounds the acquisition. Each response has a
10,000,000-byte post-read retention cap; this is not a streaming memory limit.
The maximum raw row counts are 200 components, 2,000 horizons and 10,000 rows for
each auxiliary family. Exceeding any bound fails association and preserves the
available diagnostics; no partial response becomes a valid source.

For every actual attempt retain exact SQL, raw XML bytes, request/receipt UTC
timestamps, elapsed time, HTTP status, content length, SHA256 and completeness
state. **Only response `Date` and `Content-Type` headers are retained.** Never
serialize a response header dictionary, cookies or arbitrary exception text.
Failures record the exception class, status and raw-body binding; a truncated
oversize body is explicitly incomplete. Console output is limited to compact
status and receipt path/hash. Ordinary HTTP error behavior remains owned.

Raw XML must contain the expected SDA dataset/schema and exact projected child
order. Empty XML elements remain null; numeric-looking strings follow the owned
numeric conversion before SQLite affinity. Omitted or reordered columns cannot
satisfy the existing positional extractor and fail this association gate. Retain
original tokens alongside normalized values. Entity declarations, nonfinite
numeric tokens, unexpected parent IDs and unbounded tables fail explicitly.

## Independent cache association gate

After the owned collection finishes, commit, checkpoint/truncate WAL, switch to
DELETE journal mode and close the owned connection. Require no remaining WAL/SHM
and SQLite integrity `ok` before opening the finalized cache immutable/read-only.

Reparse every retained successful raw response independently of the owned
extractors and recorder's normalized rows. Preserve the owned first-row reduction:
component/chorizon use the first two keys, while auxiliary tables use the first
parent key. Build expected rows in an in-memory SQLite database using the pinned
owned schemas. This applies actual SQLite numeric/text affinity without assuming
that all REAL columns contain numbers or that all TEXT source tokens stay strings.
Compare complete ordered cached rows and scalar types, not just row counts.

Compare all `bad_*` parent records with the queried parent set minus returned
parents. The owned implementation returns early for an entirely empty response,
leaving its bad table empty; report both all missing parent IDs and that empty
cached record set explicitly. Do not manufacture missing-parent rows or retry
the empty family during later preparation. Require all seven map units to have
component and horizon support. Missing components/horizons and rejected columns
must never be hidden by a successful constructor or SQLite file alone.

Only after all five raw-to-cache comparisons pass may `source_association_valid`
be true. A successful fetch is not a successful soil build or scientific result.

## Frozen handoff artifacts

- `declaration.json`, `execution-review.json`, `acquisition-start.json` bind the
  reviewed action and its one-time invocation.
- `requests/*.sql`, `requests/*.xml`, `requests/*.json` retain each request,
  response and safe observation record. `normalized/<table>.json` retains ordered
  raw tokens, normalized rows, reduced rows and missing-parent identities.
- `collection.sqlite` is the finalized canonical cache. Its owned human-readable
  metadata remains separate provenance, with both artifacts hash-bound.
- `cache-association.json` contains `passed`, cache path/hash/integrity/journal
  mode, sorted represented material IDs and per-table raw/cached counts, ordered
  row digests and missing-parent records.
- `acquisition.json` is written last. It contains `passed`,
  `source_association_valid`, exact requested/represented IDs, declaration/cache/
  association hashes, request observations, and an `artifacts` map binding every
  prior file under the root. `source_builds` and `native_calls` remain zero.
  Failed receipts preserve partial artifacts with false validity flags.

The successful cohort is immutable after that final receipt. Later preparation
must verify its entire bound inventory and use `SHA256(acquisition.json)` as the
optional-retention source receipt. Use the installed read-only
`SurgoCollectionWorkerViewFactory` and ordinary worker path; calling a fetching
collection constructor could refetch an empty auxiliary family. No such build is
part of this acquisition helper. Seven exact source-build successes, admitted
U12 role/companion propagation and paired input-only verification remain separate
reviewed gates before any retention experiment or native observer action.
Keep command stdout/stderr logs outside the cohort directory, for example as
`retention-source-v1-acquisition.log` beside it. A log still receiving output after
the final inventory is written would correctly invalidate that inventory.

Offline verification must cover real retained P01 XML projection/null behavior,
synthetic duplicates and missing parents, SQLite affinity, header redaction,
partial failures and finalized-cache tampering. No live request is part of those
tests. Sequential SDA responses form one retained source cohort, not an atomic
database snapshot; retain each table's acquisition time rather than inventing
one simultaneous source date.
