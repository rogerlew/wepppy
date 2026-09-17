"""Characterize actual D-Tale registration state after a bounded startup failure."""
import json

import pandas as pd
import pytest

from tests.microservices.test_dtale_freshness import dtale_service, _load


@pytest.mark.parametrize("kind", ["csv", "parquet"])
def test_registration_error_state(tmp_path, dtale_service, monkeypatch, kind):
    module = dtale_service
    source = tmp_path / f"data.{kind}"
    frame = pd.DataFrame({"a": [1, 2]})
    if kind == "csv":
        frame.to_csv(source, index=False)
    else:
        frame.to_parquet(source, index=False)
    data_id = module._make_dataset_id(tmp_path.name, "test", source.name)
    original = module.global_state.set_data

    def fail_after_registration(*args, **kwargs):
        original(*args, **kwargs)
        raise ValueError("review-injected failure after actual upstream data registration")

    with monkeypatch.context() as patch:
        patch.setattr(module.global_state, "set_data", fail_after_registration)
        response = _load(module, tmp_path, source.name)
    observed = {
        "kind": kind, "status": response.status_code,
        "frame_retained": module.global_state.get_data(data_id) is not None,
        "wrapper_meta_retained": data_id in module.DATASETS,
        "lazy_retained": data_id in module.LAZY_PARQUET_DATASETS,
    }
    print(json.dumps(observed, sort_keys=True))
    try:
        assert observed["status"] == 500
        assert observed["frame_retained"] is (kind == "csv")
        assert observed["wrapper_meta_retained"] is False
        assert observed["lazy_retained"] is False
    finally:
        module._discard_dataset(data_id)
