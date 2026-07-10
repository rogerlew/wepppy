from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from wepppy.nodb.mods.ag_fields import AgFieldsRunError, PlantFileProcessingError
from wepppy.rq import ag_fields_rq


pytestmark = pytest.mark.unit


@pytest.fixture
def rq_context(monkeypatch: pytest.MonkeyPatch):
    events: list[tuple[str, object]] = []
    published: list[tuple[str, str]] = []
    controller_box: dict[str, object] = {}

    monkeypatch.setattr(ag_fields_rq, "get_current_job", lambda: SimpleNamespace(id="job-17"))
    monkeypatch.setattr(ag_fields_rq, "get_wd", lambda runid: events.append(("get_wd", runid)) or "/runs/demo")
    monkeypatch.setattr(
        ag_fields_rq,
        "clear_nodb_file_cache",
        lambda runid, pup_relpath: events.append(("clear", (runid, pup_relpath))),
    )
    monkeypatch.setattr(
        ag_fields_rq.AgFields,
        "getInstance",
        lambda wd: events.append(("hydrate", wd)) or controller_box["controller"],
    )
    monkeypatch.setattr(
        ag_fields_rq.StatusMessenger,
        "publish",
        lambda channel, message: published.append((channel, message)),
    )
    return events, published, controller_box


def test_build_subfields_rq_orders_chain_and_guards_hydration(rq_context) -> None:
    events, published, controller_box = rq_context

    class DummyAgFields:
        field_n = 2
        sub_field_n = 5
        sub_field_fp_n = 1

        def rasterize_field_boundaries_geojson(self) -> None:
            events.append(("stage", "rasterize"))

        def periodot_abstract_sub_fields(self, minimum_area: float) -> None:
            events.append(("stage", ("abstract", minimum_area)))

        def polygonize_sub_fields(self) -> None:
            events.append(("stage", "polygonize"))

    controller_box["controller"] = DummyAgFields()

    result = ag_fields_rq.build_ag_fields_subfields_rq("demo", 25.0)

    assert events == [
        ("get_wd", "demo"),
        ("clear", ("demo", "ag_fields.nodb")),
        ("hydrate", "/runs/demo"),
        ("stage", "rasterize"),
        ("stage", ("abstract", 25.0)),
        ("stage", "polygonize"),
    ]
    assert result == {"field_n": 2, "sub_field_n": 5, "sub_field_fp_n": 1}
    assert any("AGFIELDS_BUILD_SUBFIELDS_TASK_COMPLETED" in message for _, message in published)


def test_plant_db_rq_returns_inventory_summary(rq_context) -> None:
    _events, published, controller_box = rq_context
    summary = {
        "valid_files": ["corn.man"],
        "invalid_files": [{"filename": "bad.man", "error": "bad format"}],
        "files": [],
        "replaced": [],
    }
    controller_box["controller"] = SimpleNamespace(
        handle_plant_file_db_upload=lambda filename: summary if filename == "plants.zip" else None
    )

    assert ag_fields_rq.process_ag_fields_plant_db_rq("demo", "plants.zip") == summary
    result_message = next(message for _, message in published if "RESULT_JSON" in message)
    assert json.loads(result_message.split("RESULT_JSON ", 1)[1]) == summary


def test_plant_db_rq_failure_names_aborting_file(rq_context) -> None:
    _events, published, controller_box = rq_context

    def _fail(_filename: str):
        raise PlantFileProcessingError("broken.man", "cannot parse")

    controller_box["controller"] = SimpleNamespace(handle_plant_file_db_upload=_fail)

    with pytest.raises(PlantFileProcessingError):
        ag_fields_rq.process_ag_fields_plant_db_rq("demo", "plants.zip")

    failure_message = next(message for _, message in published if "EXCEPTION_JSON" in message)
    payload = json.loads(failure_message.split("EXCEPTION_JSON ", 1)[1])
    assert payload["filename"] == "broken.man"


def test_run_wepp_rq_failure_names_subfield_and_parent_field(rq_context) -> None:
    _events, published, controller_box = rq_context

    def _fail(*, max_workers):
        assert max_workers == 3
        raise AgFieldsRunError(12, 34, "runner failed")

    controller_box["controller"] = SimpleNamespace(run_wepp_ag_fields=_fail)

    with pytest.raises(AgFieldsRunError):
        ag_fields_rq.run_ag_fields_wepp_rq("demo", max_workers=3)

    failure_message = next(message for _, message in published if "EXCEPTION_JSON" in message)
    payload = json.loads(failure_message.split("EXCEPTION_JSON ", 1)[1])
    assert payload["sub_field_id"] == 34
    assert payload["field_id"] == 12


def test_run_wepp_rq_applies_selected_binary_before_execution(rq_context) -> None:
    _events, _published, controller_box = rq_context

    class DummyAgFields:
        wepp_bin = "wepp_260430"

        def run_wepp_ag_fields(self, *, max_workers):
            assert max_workers is None
            assert self.wepp_bin == "wepp_dcc52a6"
            return {"run_count": 2}

    controller = DummyAgFields()
    controller_box["controller"] = controller

    result = ag_fields_rq.run_ag_fields_wepp_rq(
        "demo",
        wepp_bin="wepp_dcc52a6",
    )

    assert result == {"run_count": 2}
    assert controller.wepp_bin == "wepp_dcc52a6"
