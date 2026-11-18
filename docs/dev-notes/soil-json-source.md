# Selecting a JSON soil-data server

The default remains USDA XML. An operator can select the unofficial JSON service
for a project using its published immutable active release ID:

```python
from wepppy.nodb.core.soils import Soils

soils = Soils.getInstance('/path/to/project')
soils.configure_soil_data_source(
    endpoint='https://soil.example.org/Tabular/post.rest',
    profile='wepppy-json-v1',
    release='published-release-id',
)
```

The method validates and persists the three settings under the NoDb lock. Equivalent
configuration keys in the soils section are soil_data_endpoint, soil_data_profile,
and soil_data_release. This is operator configuration; there is no browser control
or automatic failover. The example hostname is illustrative, not a deployed service.
Rebuild soils through the project's usual workflow after selection. Selecting a
source does not change existing model inputs or certify their origin.

JSON cache filenames include a hash of endpoint/profile/release. Original XML caches
remain available, and cache clearing affects the selected identity only. A server
release change fails explicitly until the operator selects the new release. Do not
copy old rows into a new identity or edit provenance tables to suppress an error.
Calling soils.configure_soil_data_source() restores XML selection and its original
cache paths; it does not guarantee USDA is reachable during an outage.

## Inspecting provenance

The cache's .meta.md companion summarizes the selected endpoint, profile, release,
retrieval count, and whether historical rows have unknown origin. The SQLite tables
soil_data_source and soil_data_fetch retain the binding and successful fetch events,
including observed server revision/release manifest and response hashes for JSON.
Warm-cache reuse preserves those retrieval timestamps without contacting the server.
An observed server revision applies to the metadata request, not proof of the binary
serving every subsequent query. Legacy cached rows retain unknown historical origin.

Each generated base soil has a .sol.provenance.json companion with MUKEY, selected
component, cache name, source evidence, and a hash of the soil bytes. Verify it with:

```python
from wepppy.soils.ssurgo.source import read_artifact_provenance

provenance = read_artifact_provenance('/path/to/project/soils/123.sol')
print(provenance['source']['binding']['identity'])
```

A hash mismatch raises SoilDataSourceError. Keep companions with their base soils.
Treated and prepared model files retain the existing Source File lineage; they do
not gain independent per-request sidecars. Scientific .sol content is unchanged.

## Developer boundaries

The [canonical contract](../schemas/soil-data-source-provenance-contract.md) defines
identity validation, 1000-key batches, strict string/null decoding, bounded HTTP,
atomic cache events, and failure semantics. SoilDataSourceError deliberately does
not inherit from RuntimeError or ValueError: source failures must escape numerical
fallback handlers. Empty successful queries are recorded as negative cache entries.
Tests exercise real HTTP/SQLite, selected-cache clearing, and NoDb lock/reload with
a disposable Redis socket selected through SOIL_PROVENANCE_TEST_REDIS_SOCKET.
