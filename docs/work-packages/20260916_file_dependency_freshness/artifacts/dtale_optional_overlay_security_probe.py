"""Actual isolated D-Tale overlay behavior under read denial and disappearance."""
import importlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory


module = importlib.import_module("wepppy.webservices.dtale.dtale")
assert os.geteuid() != 0, "Probe requires ordinary unprivileged access checks"
observed = {"uid": os.getuid(), "gid": os.getgid()}
with TemporaryDirectory(prefix="dtale-overlay-security-") as temporary:
    root = Path(temporary)
    source = root / "map.geojson"
    source.write_text(json.dumps({
        "type": "FeatureCollection", "features": [{
            "type": "Feature", "properties": {"id": "1", "label": "old"},
            "geometry": {"type": "Point", "coordinates": [0, 0]},
        }],
    }))
    data_id = "security-overlay-fixture"
    runid = root.name
    key = f"{runid}-map"

    def register():
        return module._register_geojson_asset(
            runid, "map", source, data_id=data_id,
            preferred_keys=("id",), make_default=True,
        )

    def state():
        return {
            "registered": key in module.REGISTERED_GEOJSON,
            "upstream_record": any(item.get("key") == key for item in module.dtale_custom_geojson.CUSTOM_GEOJSON),
            "choices": module.MAP_CHOICES.get(data_id),
            "defaults": module.MAP_DEFAULTS.get(data_id),
        }

    observed["initial_result"] = register()
    before = source.stat()
    source.chmod(0)
    os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
    observed["denied_result"] = register()
    observed["after_denial"] = state()
    source.unlink()
    observed["missing_result"] = register()
    observed["after_removal"] = state()
    print(json.dumps(observed, indent=2))
    assert observed["denied_result"] == (None, None)
    assert observed["missing_result"] == (None, None)
    assert observed["after_denial"]["upstream_record"] is True
    assert observed["after_removal"]["registered"] is True
    assert observed["after_removal"]["choices"]
    assert observed["after_removal"]["defaults"]
