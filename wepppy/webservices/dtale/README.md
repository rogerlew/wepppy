# D-Tale Run Data Viewer

> Browse run tables with an eager reader for CSV/TSV/Feather/Arrow and bounded
> Parquet pages backed by DuckDB/PyArrow.

Open a file through the run's browse page. If the grid says the source changed
or is unavailable, reopen that file from browse after its upstream operation
finishes. Reopening refreshes the table and recompiles its filter. A filter that
references a removed column must be corrected; it is never silently discarded.
Tabs viewing the same dataset share server state and may also need reopening.

Pickle files (`.pkl` and `.pickle`, in any letter case) cannot be opened in
D-Tale. Existing files remain visible and downloadable as original bytes in
browse. Direct D-Tale bridge and internal loader requests return HTTP 415;
there is no pickle reader or fallback. This prevents server-side execution of
project-controlled pickle content. The approved
[pickle restriction](../../../docs/schemas/browse-filesystem-contract.md#pickle-artifacts)
is implemented and locally validated; deployment pending.

Changing file timestamps alone does not reload identical data. Changed bytes
refresh on the next launch even if timestamps were restored. An already loaded
baseline or explicitly historical CSV remains a point-in-time view until reopened. Lazy Parquet pages verify the
accepted source generation so a changed schema cannot be combined with old grid
columns or counts. Missing optional maps do not prevent viewing the table.

The service runs one Gunicorn worker at `wepppy.webservices.dtale:app` in the
canonical development Compose stack. Existing browse authorization, internal
loader token, file/row limits and NoDir materialization remain authoritative.
Grid failures use upstream D-Tale's visible error envelope; loader acquisition
conflicts return409 `changed_source`. No additional service or persistent cache
is required.

Fingerprints use the shared verified file digest cache. Cold loads and recently
changed or evicted sources may require full streaming hash reads; settled page
checks reuse verified hashes without rereading content. Parquet data itself
remains lazily paged and is never loaded wholesale into pandas as a fallback.
See the [freshness contract](../../../docs/schemas/file-dependency-freshness-contract.md#d-tale-dataset-generations-implemented)
and [local implementation guide](AGENTS.md).

Validate with `wctl run-pytest tests/microservices/test_dtale_freshness.py` and the
browse/D-Tale integration tests. Deployment acceptance also requires a normal
browse launch and actual browser refresh/error behavior after service restart.

Physical file viewers follow the [browse filesystem contract](../../../docs/schemas/browse-filesystem-contract.md).
Roads receipts, model freshness and lifecycle locks do not gate file viewing.
Private dataset scopes, viewer reauthorization, containment and sensitive-path
protections remain mandatory. Eager datasets remain acquired snapshots; lazy
readers retain their ordinary byte-generation checks and report `changed_source`
when the source changes or disappears. Reopen to read the actual current file.
