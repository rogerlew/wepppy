"""Explicit operator repair for the named development Builder project only.

Run inside the development weppcloud service. No config or generated input edits.
Backups are local to the container and are not repository artifacts.
"""
from pathlib import Path
import hashlib
import json

from wepppy.nodb.core import Ron, Landuse, Soils, Watershed, Climate, Wepp
from wepppy.nodb.unitizer import Unitizer
from wepppy.nodb.mods.observed import Observed
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.project_config_reader import project_config_manifest_source_kind

wd = Path('/wc1/runs/fa/fair-division')
assert not (wd / 'READONLY').exists()
assert project_config_manifest_source_kind(wd, 'config.cfg', run_id='fair-division') == 'builder'
config_paths = [wd / 'config.cfg', wd / 'config-manifest.json']
digests = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in config_paths}
controllers = [cls.getInstance(str(wd)) for cls in (Ron, Landuse, Soils, Watershed, Climate, Wepp, Unitizer, Observed)]
ron, landuse = controllers[:2]
ron._configparser  # Validate the project-owned reader before any mutation.
assert ron.project_config_status.manifest_valid
assert not getattr(landuse, '_custom_mapping_relpath', None), 'Custom mapping requires separate repair scope'
assert landuse.mapping in (None, 'disturbed'), 'Populated mapping requires separate repair scope'
for controller in controllers:
    assert isinstance(controller.mods, list) and all(isinstance(x, str) for x in controller.mods)
disturbed = Disturbed.tryGetInstance(str(wd))
if disturbed is None:
    assert not (wd / 'disturbed').exists(), 'Orphan Disturbed directory; refusing to reset it'
    assert not (wd / 'disturbed.nodb.bak').exists(), 'Existing backup requires explicit restore'
backup = Path('/tmp/builder-sbs-fair-division-before')
backup.mkdir(exist_ok=True)
for path in wd.glob('*.nodb'):
    destination = backup / path.name
    if not destination.exists():
        destination.write_bytes(path.read_bytes())
if disturbed is None:
    disturbed = Disturbed(str(wd), 'config.cfg')
controllers.append(disturbed)
for controller in controllers:
    needs_mapping = isinstance(controller, Landuse) and controller.mapping is None
    if 'disturbed' not in controller.mods or needs_mapping:
        with controller.locked():
            # Scoped repair on a quiescent run; stale concurrent writes are rejected.
            if isinstance(controller, Landuse):
                assert not getattr(controller, '_custom_mapping_relpath', None)
                assert controller.mapping in (None, 'disturbed')
                controller._mapping = 'disturbed'
            if 'disturbed' not in controller.mods:
                controller._mods.append('disturbed')
assert all(hashlib.sha256(p.read_bytes()).hexdigest() == digests[p.name] for p in config_paths)
assert len(disturbed.get_disturbed_key_lookup()) >= 9
print(json.dumps({'runid': 'fair-division', 'controllers': [x.__class__.__name__ for x in controllers],
                  'mapping': landuse.mapping, 'has_sbs': disturbed.has_map,
                  'config_digests_unchanged': digests, 'backup': str(backup)}, indent=2))
