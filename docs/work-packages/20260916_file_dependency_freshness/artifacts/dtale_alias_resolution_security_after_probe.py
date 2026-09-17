"""Previously valid local alias becomes unavailable through a symlink loop."""
import json

import pandas as pd
import pytest

from tests.microservices.test_dtale_freshness import dtale_service, _load, _grid


def test_alias_resolution_failure_response(tmp_path, dtale_service):
    module = dtale_service
    target = tmp_path / "target.parquet"
    pd.DataFrame({"a": [1, 2]}).to_parquet(target, index=False)
    alias = tmp_path / "data.parquet"
    alias.symlink_to(target.name)
    loaded = _load(module, tmp_path)
    assert loaded.status_code == 200
    data_id = loaded.json["data_id"]
    lazy = module.LAZY_PARQUET_DATASETS[data_id]
    alias.unlink()
    alias.symlink_to(alias.name)
    with pytest.raises(module._SourceChangedError) as error:
        lazy.rows()
    observed = {
        "type": type(error.value).__name__,
        "translated_changed_source": isinstance(error.value, module._SourceChangedError),
        "grid_status": _grid(module, data_id).status_code,
        "cause_type": type(error.value.__cause__).__name__,
        "grid_error": _grid(module, data_id).json,
    }
    print(json.dumps(observed, sort_keys=True))
    assert observed["type"] == "_SourceChangedError"
    assert observed["translated_changed_source"] is True
    assert observed["grid_status"] == 200
    assert observed["cause_type"] == "RuntimeError"
    assert observed["grid_error"] == {"success": False, "error": module._SOURCE_CHANGED_MESSAGE, "code": "changed_source"}
