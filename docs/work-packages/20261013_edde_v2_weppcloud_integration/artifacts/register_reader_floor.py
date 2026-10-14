"""Append EDDE graph identities before live catalogs expose the new choice."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from wepppy.nodb.config_builder.resolver import resolve_builder_capability_graph
from wepppy.nodb.locales.capability_graph import capability_structure_payload
from wepppy.nodb.single_input_policy import single_input_capability_graph

root = Path(__file__).resolve().parents[4]
path = root / 'wepppy/nodb/locales/capability_structures/catalog.json'
catalog = json.loads(path.read_text())
previous = deepcopy(catalog['structures'])
receipts = []
for locale in ('continental-us', 'canada'):
    ordinary = resolve_builder_capability_graph(locale)
    for single in (False, True):
        graph = single_input_capability_graph(ordinary, selected_binary='wepp_260803') if single else ordinary
        payload = capability_structure_payload(graph)
        assert 'future_edde_v2' not in payload['axes']['climate_datasets'], 'Run only before live writer changes'
        payload['axes']['climate_datasets'].append('future_edde_v2')
        payload['relations']['climate_station_methods']['future_edde_v2'] = ['auto', 'distance', 'multi_factor']
        payload['relations']['climate_spatial_methods']['future_edde_v2'] = ['single', 'multiple']
        payload['method_defaults']['climate_station']['future_edde_v2'] = 'auto'
        payload['method_defaults']['climate_spatial']['future_edde_v2'] = 'single'
        identity = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        if not any(entry['structure_sha256'] == identity for entry in catalog['structures']):
            catalog['structures'].append({'first_reader_revision': 'pending-standalone-edde-reader-floor', 'structure_sha256': identity, 'payload': payload})
        receipts.append({'locale': locale, 'single_inputs': single, 'structure_sha256': identity})
assert catalog['structures'][:len(previous)] == previous
path.write_text(json.dumps(catalog, indent=2) + '\n')
Path(__file__).with_name('reader-floor-identities.json').write_text(json.dumps(receipts, indent=2) + '\n')
print(json.dumps(receipts))
