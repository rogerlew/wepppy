"""Isolated actual D-Tale registration; no named run/service state mutation."""
import importlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

module = importlib.import_module("wepppy.webservices.dtale.dtale")
results = {}


def geojson(path, field):
    path.write_text(json.dumps({
        "type": "FeatureCollection", "features": [{
            "type": "Feature", "properties": {field: "1"},
            "geometry": {"type": "Point", "coordinates": [0, 0]},
        }],
    }))


with TemporaryDirectory(prefix="dtale-correctness-") as temporary:
    root = Path(temporary)
    runid = root.name
    channels = root / "channels.geojson"
    boundaries = root / "fields.geojson"
    missing = root / "missing.geojson"
    watershed = SimpleNamespace(subwta_shp=missing, channels_shp=channels)
    ag = SimpleNamespace(field_boundaries_geojson=boundaries.name,
                         ag_fields_dir=str(root), sub_fields_wgs_geojson=None)

    with patch.object(module.Watershed, "getInstance", return_value=watershed), \
            patch.object(module, "AgFields", SimpleNamespace(tryGetInstance=lambda *args, **kwargs: None)):
        data_id = "correctness-schema"
        geojson(channels, "channel_id")
        module._ensure_geojson_assets(runid, root, data_id)
        before = dict(module.MAP_DEFAULTS[data_id])
        geojson(channels, "reach_id")
        module._ensure_geojson_assets(runid, root, data_id)
        key = f"{runid}-channels"
        record = next(item for item in module.dtale_custom_geojson.CUSTOM_GEOJSON if item["key"] == key)
        results["overlay_identifier_change"] = {
            "before_default": before,
            "after_default": module.MAP_DEFAULTS.get(data_id),
            "record_featureidkey": record.get("featureidkey"),
            "record_properties": record.get("properties"),
            "choices": module.MAP_CHOICES.get(data_id),
        }

    module._remove_geojson_asset(f"{runid}-channels")
    channels.unlink()
    geojson(boundaries, "field_id")
    with patch.object(module.Watershed, "getInstance", return_value=watershed), \
            patch.object(module, "AgFields", SimpleNamespace(tryGetInstance=lambda *args, **kwargs: ag)):
        data_id = "correctness-remaining"
        module._ensure_geojson_assets(runid, root, data_id)
        before = dict(module.MAP_DEFAULTS[data_id])
        boundaries.unlink()
        geojson(channels, "channel_id")
        module._ensure_geojson_assets(runid, root, data_id)
        results["remaining_valid_overlay"] = {
            "before_default": before,
            "after_default": module.MAP_DEFAULTS.get(data_id),
            "choices": module.MAP_CHOICES.get(data_id),
        }

    source = root / "data.csv"
    source.write_text("a\n1\n2\n")
    data_id = module._make_dataset_id(runid, "test", source.name)
    native_startup = module.startup

    def interrupted_startup(*args, **kwargs):
        native_startup(*args, **kwargs)
        raise ValueError("injected failure after actual upstream state publication")

    with patch.object(module, "get_wd", return_value=str(root)), \
            patch.object(module, "DTALE_INTERNAL_TOKEN", "correctness-token"), \
            patch.object(module, "_ensure_geojson_assets", return_value=None), \
            patch.object(module, "startup", side_effect=interrupted_startup):
        response = module.app.test_client().post("/internal/load", json={
            "runid": runid, "config": "test", "path": source.name,
        }, headers={"X-DTALE-TOKEN": "correctness-token"})
        results["eager_startup_failure"] = {
            "response_status": response.status_code,
            "global_state_contains": module.global_state.contains(data_id),
            "metadata_published": data_id in module.DATASETS,
            "rows_retained": module.global_state.get_data(data_id)["a"].tolist()
                if module.global_state.contains(data_id) else None,
        }
    module._discard_dataset(data_id)

print(json.dumps(results, indent=2))
output = Path(__file__).with_name(sys.argv[1] + ".json") if len(sys.argv) > 1 else Path(__file__).with_suffix(".json")
output.write_text(json.dumps(results, indent=2) + "\n")
