from __future__ import annotations

import pytest
import yaml

from wepppy.nodb.mods.features_export.catalog_loader import (
    LayerCatalogValidationError,
    load_layer_catalog,
)

pytestmark = pytest.mark.unit


def _minimal_catalog_payload(*, locator: dict[str, str]) -> dict[str, object]:
    return {
        "metadata": {
            "catalog_version": "test-1",
            "schema_version": 1,
            "updated_at_utc": "2026-03-26T00:00:00Z",
            "owner": "tests",
            "status": "draft",
            "resolver_contract": {
                "allowed_locator_kinds": ["nodb_ref", "relpath", "path_template"],
                "path_template_vars": {
                    "scope_root": {
                        "values": {"baseline": "output", "roads": "roads/output"},
                    }
                },
                "temporal_modes": ["annual_average", "yearly", "event"],
                "event_selectors": ["date", "return_period"],
            },
        },
        "layers": [
            {
                "layer_id": "test.layer",
                "family": "test_family",
                "scope_class": "scope_invariant",
                "geometry": {"type": "polygon", "locator": locator, "feature_id_keys": []},
                "join": {"primary_key": "id", "fallback_keys": []},
                "sources": [
                    {
                        "source_id": "src",
                        "kind": "parquet",
                        "locator": {"kind": "relpath", "value": "test.parquet"},
                        "required": True,
                        "role": "attributes",
                    }
                ],
                "dependencies": [],
                "temporal": {"supported_modes": [], "grain": "none", "time_columns": [], "mode_rules": {}},
                "measures": {"required": [], "optional": []},
            }
        ],
    }


def test_load_layer_catalog_default_file_contract_is_valid() -> None:
    catalog = load_layer_catalog()

    assert catalog.metadata.catalog_version
    assert catalog.metadata.schema_version == 2
    assert "watershed.subcatchments" in catalog.layer_index
    assert "wepp.summary.hillslopes" in catalog.layer_index
    assert catalog.layer_index["wepp.summary.hillslopes"].scope_class == "scope_aware"


def test_load_layer_catalog_requires_non_empty_labels_for_all_layers() -> None:
    catalog = load_layer_catalog()

    missing_labels = [
        layer.layer_id
        for layer in catalog.layers
        if not str(layer.raw.get("label") or "").strip()
    ]
    assert missing_labels == []


def test_load_layer_catalog_rejects_locator_alias_keys(tmp_path) -> None:
    payload = _minimal_catalog_payload(locator={"kind": "relpath", "path": "bad.alias"})
    catalog_path = tmp_path / "invalid_locator_catalog.yaml"
    catalog_path.write_text(yaml.safe_dump(payload), encoding="utf-8")

    with pytest.raises(LayerCatalogValidationError, match="exactly keys 'kind' and 'value'"):
        load_layer_catalog(catalog_path)
