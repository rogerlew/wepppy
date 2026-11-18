# Selecting a soil-data server

Without deployment configuration, the default remains USDA XML. An operator can select the unofficial JSON service
for a project using its published immutable active release ID:

```python
from wepppy.nodb.core.soils import Soils

soils = Soils.getInstance('/path/to/project')
soils.configure_soil_data_source(
    endpoint='https://soil.example.org/Tabular/post.rest',
    profile='wepppy-json-v1',
    release='published-release-id',
    fallback_to_sda=True,
)
```

The method validates and persists the identity and selection policy under the NoDb lock. Equivalent
configuration keys in the soils section are soil_data_endpoint, soil_data_profile,
and soil_data_release. This is operator configuration; there is no browser control. With fallback_to_sda=True,
availability failures or missing mirror component coverage retry the entire
collection through SDA in a separate cache. Omitting the option selects explicit
JSON with no automatic fallback. The example hostname is illustrative, not a deployed service.
Rebuild soils through the project's usual workflow after selection. Selecting a
source does not change existing model inputs or certify their origin.

JSON cache filenames include a hash of endpoint/profile/release. Original XML caches
remain available, and cache clearing affects the selected identity only. A server
release change fails explicitly until the operator selects the new release. Do not
copy old rows into a new identity or edit provenance tables to suppress an error.
Calling soils.configure_soil_data_source() restores XML selection and its original
cache paths; it does not guarantee USDA is reachable during an outage.

## Deployment defaults

SOIL_DATA_MODE=mirror-first, SOIL_DATA_ENDPOINT and SOIL_DATA_RELEASE initialize
new/unconfigured projects. Saved identities and explicit project configuration win;
older saved XML settings remain explicit. Invalid deployment settings fail visibly.
Defaults do not rewrite saved projects when changed. See the
[forest Compose runbook](../infrastructure/soil-data-forest.md).

Fallback has a 30-second acquisition budget per source and 60 seconds overall.
Malformed responses, wrong releases, corrupt cache evidence and numerical soil
rejection do not trigger fallback. Both-source failure records both attempts and
fails the build. A regional release relies on SDA for keys outside its coverage.

## Inspecting provenance

The cache's .meta.md companion summarizes the selected endpoint, profile, release,
retrieval count, and whether historical rows have unknown origin. The SQLite tables
soil_data_source and soil_data_fetch retain the binding and successful fetch events,
including observed server revision/release manifest and response hashes for JSON.
Warm-cache reuse preserves those retrieval timestamps without contacting the server.
Mirror-first selection adds soil_data_selection history and a latest
<primary-cache>.selection.json file. The event records configured primary, attempts,
reasons, actual supplier and whether historical row origin remains unknown. The
same event appears under selection in each base-soil sidecar. A missing latest
selection file is not successful selection evidence.
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
