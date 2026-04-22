from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict

import pytest

pytest.importorskip("flask")
from flask import Flask

import wepppy.weppcloud.routes.nodb_api.geneva_bp as geneva_module
from wepppy.nodb.mods.geneva import Geneva


pytestmark = pytest.mark.routes

RUN_ID = "geneva-run"
CONFIG = "0"


@pytest.fixture()
def geneva_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Any:
    Geneva.cleanup_all_instances()

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(geneva_module.geneva_bp)

    run_dir = tmp_path / RUN_ID
    run_dir.mkdir()
    context = SimpleNamespace(active_root=run_dir)

    monkeypatch.setattr(geneva_module, "load_run_context", lambda runid, config: context)

    helpers = __import__("wepppy.weppcloud.utils.helpers", fromlist=["authorize"])
    monkeypatch.setattr(helpers, "authorize", lambda runid, config, require_owner=False: None)

    captured: Dict[str, Any] = {}

    def fake_render_template(template: str, **context: Any) -> str:
        captured["template"] = template
        captured["template_context"] = context
        return "rendered"

    monkeypatch.setattr(geneva_module, "render_template", fake_render_template)

    with app.test_client() as client:
        yield client, captured, run_dir

    Geneva.cleanup_all_instances()


def test_modify_geneva_cn_table_route_renders_edit_csv_context(geneva_client: Any) -> None:
    client, captured, _ = geneva_client

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/modify_geneva_cn_table")

    assert response.status_code == 200
    assert captured["template"] == "controls/edit_csv.htm"
    template_context = captured["template_context"]
    assert template_context["runid"] == RUN_ID
    assert template_context["config"] == CONFIG
    assert template_context["page_title"] == "Edit Geneva CN Table"
    assert template_context["editor_title"] == "Geneva CN Table"
    assert template_context["csv_url"] == f"/runs/{RUN_ID}/{CONFIG}/download/geneva/data/cn_table.csv"
    assert template_context["save_url"] == f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_geneva_cn_table"
    assert template_context["lookup_meta_url"] == f"/runs/{RUN_ID}/{CONFIG}/api/geneva/cn_table_meta"
    assert template_context["lookup_snapshot_url"] == (
        f"/runs/{RUN_ID}/{CONFIG}/api/geneva/cn_table_snapshot"
    )


def test_cn_table_meta_and_snapshot_are_available(geneva_client: Any) -> None:
    client, _, _ = geneva_client

    meta_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/geneva/cn_table_meta")
    assert meta_response.status_code == 200
    meta = meta_response.get_json()["Content"]
    assert meta["path"] == "geneva/data/cn_table.csv"
    assert meta["schema_version"] == 1
    assert meta["exists"] is True
    assert meta["lookup_sha256"]

    snapshot_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/geneva/cn_table_snapshot")
    assert snapshot_response.status_code == 200
    snapshot = snapshot_response.get_json()["Content"]
    assert snapshot["meta"]["schema_version"] == 1
    assert snapshot["lookup_sha256"] == meta["lookup_sha256"]
    assert snapshot["rows"]
    assert "csv_text" in snapshot


def test_task_modify_geneva_cn_table_accepts_matching_if_match(geneva_client: Any) -> None:
    client, _, _ = geneva_client

    snapshot_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/geneva/cn_table_snapshot")
    baseline = snapshot_response.get_json()["Content"]

    rows = list(baseline["rows"])
    rows[0] = dict(rows[0])
    rows[0]["cn_arc_ii"] = "89"
    rows[0]["antecedent_condition_source"] = "user_override"

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_geneva_cn_table",
        json={
            "if_match_sha256": baseline["lookup_sha256"],
            "rows": rows,
        },
    )

    assert response.status_code == 200
    updated_sha = response.headers.get("X-Lookup-Sha256")
    assert updated_sha
    assert updated_sha != baseline["lookup_sha256"]

    refreshed_snapshot_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/geneva/cn_table_snapshot")
    refreshed = refreshed_snapshot_response.get_json()["Content"]
    assert refreshed["lookup_sha256"] == updated_sha
    assert refreshed["rows"][0]["cn_arc_ii"] == "89"


def test_task_modify_geneva_cn_table_rejects_missing_if_match(geneva_client: Any) -> None:
    client, _, _ = geneva_client

    snapshot_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/geneva/cn_table_snapshot")
    rows = snapshot_response.get_json()["Content"]["rows"]

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_geneva_cn_table",
        json={"rows": rows},
    )

    assert response.status_code == 428
    payload = response.get_json()
    assert payload["error"]["code"] == "PRECONDITION_REQUIRED"


def test_task_modify_geneva_cn_table_rejects_stale_if_match(geneva_client: Any) -> None:
    client, _, _ = geneva_client

    snapshot_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/geneva/cn_table_snapshot")
    rows = snapshot_response.get_json()["Content"]["rows"]

    response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/modify_geneva_cn_table",
        json={
            "if_match_sha256": "stale-token",
            "rows": rows,
        },
    )

    assert response.status_code == 409
    payload = response.get_json()
    assert payload["error"]["code"] == "STALE_LOOKUP"


def test_task_reset_geneva_cn_table_requires_confirm_and_resets(
    geneva_client: Any,
) -> None:
    client, _, run_dir = geneva_client

    meta_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/geneva/cn_table_meta")
    assert meta_response.status_code == 200

    table_path = run_dir / "geneva" / "data" / "cn_table.csv"
    assert table_path.exists()
    table_path.unlink()

    recreated_meta_response = client.get(f"/runs/{RUN_ID}/{CONFIG}/api/geneva/cn_table_meta")
    recreated_meta = recreated_meta_response.get_json()["Content"]
    assert recreated_meta["exists"] is True

    missing_confirm = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/reset_geneva_cn_table",
        json={"confirm": False},
    )
    assert missing_confirm.status_code == 400

    reset_response = client.post(
        f"/runs/{RUN_ID}/{CONFIG}/tasks/reset_geneva_cn_table",
        json={
            "schema_version": 1,
            "confirm": True,
        },
    )
    assert reset_response.status_code == 200
    content = reset_response.get_json()["Content"]
    assert content["schema_version"] == 1
    assert content["lookup_sha256"]


def test_query_geneva_summary_returns_interactive_payload_contract(
    geneva_client: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, _ = geneva_client
    query_calls: list[dict[str, Any]] = []

    class _SummaryStub:
        def query_summary_payload(
            self,
            *,
            datasource_id: str = "all",
            ari_years: list[int] | tuple[int, ...] | None = None,
            measure: str = "peak_discharge",
            selected_storm_id: str | None = None,
        ) -> dict[str, Any]:
            query_calls.append(
                {
                    "datasource_id": datasource_id,
                    "ari_years": list(ari_years or []),
                    "measure": measure,
                    "selected_storm_id": selected_storm_id,
                }
            )
            return {
                "schema_version": 1,
                "filters": {
                    "datasource_id": datasource_id,
                    "ari_years": list(ari_years or [10]),
                    "measure": measure,
                },
                "filter_options": {
                    "datasource_ids": ["all", "cligen_freq", "noaa14_pds"],
                    "datasource_availability": {"cligen_freq": True, "noaa14_pds": False},
                    "ari_years": [10],
                    "measures": ["peak_discharge", "runoff_depth", "runoff_volume"],
                    "duration_minutes": [30],
                },
                "assumptions": {
                    "arc_condition": "arc_ii",
                    "storm_distribution_assumption": "neh4_type_b",
                    "uniform_rainfall_assumed": True,
                },
                "chart": {
                    "x_axis": "intensity_mm_per_hr",
                    "y_axis": "selected_measure",
                    "series_grouping": "ari_years",
                    "marker_grouping": "duration_minutes",
                    "series": [
                        {
                            "series_id": "ari_10",
                            "series_label": "ARI 10-year",
                            "ari_years": 10,
                            "points": [
                                {
                                    "storm_id": "cligen_30m_10y",
                                    "datasource_id": "cligen_freq",
                                    "duration_minutes": 30,
                                    "intensity_mm_per_hr": 40.0,
                                    "measure_value": 1.2,
                                    "marker_label": "30m",
                                }
                            ],
                        }
                    ],
                },
                "selected_storm_id": selected_storm_id or "cligen_30m_10y",
                "event_table": [
                    {
                        "storm_id": "cligen_30m_10y",
                        "status": "completed",
                        "datasource_id": "cligen_freq",
                        "duration_minutes": 30,
                        "ari_years": 10,
                        "depth_mm": 20.0,
                        "intensity_mm_per_hr": 40.0,
                        "distribution_type": "neh4_type_b",
                        "peak_discharge": {"value": 1.2, "unit": "m3_s"},
                        "time_to_peak_minutes": 5.0,
                        "runoff_volume": {"value": 100.0, "unit": "m3"},
                        "runoff_depth": {"value": 4.0, "unit": "mm"},
                        "warning_count": 0,
                        "error_count": 0,
                    }
                ],
                "warnings": [],
                "errors": [],
            }

    monkeypatch.setattr(geneva_module, "_ensure_geneva_controller", lambda _wd, _cfg: _SummaryStub())

    response = client.get(
        f"/runs/{RUN_ID}/{CONFIG}/query/geneva/summary"
        "?datasource_id=cligen_freq&ari_years=10&measure=runoff_depth&selected_storm_id=cligen_30m_10y"
    )

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate, max-age=0"
    assert response.headers["Pragma"] == "no-cache"
    assert response.headers["Expires"] == "0"
    payload = response.get_json()
    assert payload["schema_version"] == 1
    assert payload["filters"]["datasource_id"] == "cligen_freq"
    assert payload["filters"]["measure"] == "runoff_depth"
    assert payload["filter_options"]["datasource_ids"] == ["all", "cligen_freq", "noaa14_pds"]
    assert payload["chart"]["series"]
    assert payload["selected_storm_id"] == "cligen_30m_10y"
    assert payload["event_table"]
    assert query_calls == [
        {
            "datasource_id": "cligen_freq",
            "ari_years": [10],
            "measure": "runoff_depth",
            "selected_storm_id": "cligen_30m_10y",
        }
    ]


def test_report_geneva_summary_passes_contract_payload_to_template(
    geneva_client: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, captured, _ = geneva_client
    query_calls: list[dict[str, Any]] = []

    class _SummaryStub:
        def query_summary_payload(
            self,
            *,
            datasource_id: str = "all",
            ari_years: list[int] | tuple[int, ...] | None = None,
            measure: str = "peak_discharge",
            selected_storm_id: str | None = None,
        ) -> dict[str, Any]:
            query_calls.append(
                {
                    "datasource_id": datasource_id,
                    "ari_years": list(ari_years or []),
                    "measure": measure,
                    "selected_storm_id": selected_storm_id,
                }
            )
            return {
                "schema_version": 1,
                "filters": {
                    "datasource_id": datasource_id,
                    "ari_years": list(ari_years or [10]),
                    "measure": measure,
                },
                "filter_options": {
                    "datasource_ids": ["all", "cligen_freq", "noaa14_pds"],
                    "datasource_availability": {"cligen_freq": True, "noaa14_pds": False},
                    "ari_years": [10],
                    "measures": ["peak_discharge", "runoff_depth", "runoff_volume"],
                    "duration_minutes": [30],
                },
                "assumptions": {
                    "arc_condition": "arc_ii",
                    "storm_distribution_assumption": "neh4_type_b",
                    "uniform_rainfall_assumed": True,
                },
                "chart": {
                    "x_axis": "intensity_mm_per_hr",
                    "y_axis": "selected_measure",
                    "series_grouping": "ari_years",
                    "marker_grouping": "duration_minutes",
                    "series": [],
                },
                "selected_storm_id": selected_storm_id,
                "event_table": [],
                "warnings": [],
                "errors": [],
            }

    monkeypatch.setattr(geneva_module, "_ensure_geneva_controller", lambda _wd, _cfg: _SummaryStub())

    response = client.get(
        f"/runs/{RUN_ID}/{CONFIG}/report/geneva/summary"
        "?datasource_id=all&ari_years=10&measure=peak_discharge&selected_storm_id=cligen_30m_10y"
    )

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate, max-age=0"
    assert response.headers["Pragma"] == "no-cache"
    assert response.headers["Expires"] == "0"
    assert captured["template"] == "reports/geneva/summary.htm"
    payload = captured["template_context"]["summary_payload"]
    assert payload["schema_version"] == 1
    assert payload["filter_options"]["measures"] == ["peak_discharge", "runoff_depth", "runoff_volume"]
    assert payload["chart"]["series_grouping"] == "ari_years"
    assert payload["selected_storm_id"] == "cligen_30m_10y"
    assert captured["template_context"]["ron"] is not None
    assert captured["template_context"]["current_ron"] is not None
    assert captured["template_context"]["unitizer_nodb"] is not None
    assert "temperature" in captured["template_context"]["precisions"]
    assert captured["template_context"]["ron"].runid == RUN_ID
    assert captured["template_context"]["ron"].config_stem == CONFIG
    assert query_calls == [
        {
            "datasource_id": "all",
            "ari_years": [10],
            "measure": "peak_discharge",
            "selected_storm_id": "cligen_30m_10y",
        }
    ]


def test_query_geneva_summary_rejects_non_integer_ari_filter(
    geneva_client: Any,
) -> None:
    client, _, _ = geneva_client

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/query/geneva/summary?ari_years=bad")

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"]["code"] == "invalid_input"
    assert payload["error"]["details"] == "ari_years filter values must be integers"


def test_report_geneva_summary_rejects_non_integer_ari_filter(
    geneva_client: Any,
) -> None:
    client, _, _ = geneva_client

    response = client.get(f"/runs/{RUN_ID}/{CONFIG}/report/geneva/summary?ari_years=bad")

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"]["code"] == "invalid_input"
    assert payload["error"]["details"] == "ari_years filter values must be integers"


def test_query_geneva_summary_normalizes_comma_separated_ari_filter(
    geneva_client: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, _ = geneva_client
    query_calls: list[dict[str, Any]] = []

    class _SummaryStub:
        def query_summary_payload(
            self,
            *,
            datasource_id: str = "all",
            ari_years: list[int] | tuple[int, ...] | None = None,
            measure: str = "peak_discharge",
            selected_storm_id: str | None = None,
        ) -> dict[str, Any]:
            query_calls.append(
                {
                    "datasource_id": datasource_id,
                    "ari_years": list(ari_years or []),
                    "measure": measure,
                    "selected_storm_id": selected_storm_id,
                }
            )
            return {
                "schema_version": 1,
                "filters": {
                    "datasource_id": datasource_id,
                    "ari_years": list(ari_years or []),
                    "measure": measure,
                },
                "filter_options": {
                    "datasource_ids": ["all", "cligen_freq", "noaa14_pds"],
                    "datasource_availability": {"cligen_freq": True, "noaa14_pds": False},
                    "ari_years": [10, 25],
                    "measures": ["peak_discharge", "runoff_depth", "runoff_volume"],
                    "duration_minutes": [30],
                },
                "assumptions": {
                    "arc_condition": "arc_ii",
                    "storm_distribution_assumption": "neh4_type_b",
                    "uniform_rainfall_assumed": True,
                },
                "chart": {
                    "x_axis": "intensity_mm_per_hr",
                    "y_axis": "selected_measure",
                    "series_grouping": "ari_years",
                    "marker_grouping": "duration_minutes",
                    "series": [],
                },
                "selected_storm_id": selected_storm_id,
                "event_table": [],
                "warnings": [],
                "errors": [],
            }

    monkeypatch.setattr(geneva_module, "_ensure_geneva_controller", lambda _wd, _cfg: _SummaryStub())

    response = client.get(
        f"/runs/{RUN_ID}/{CONFIG}/query/geneva/summary"
        "?ari_years=25,10&ari_years=10&datasource_id=all&measure=peak_discharge"
    )

    assert response.status_code == 200
    assert query_calls == [
        {
            "datasource_id": "all",
            "ari_years": [10, 25],
            "measure": "peak_discharge",
            "selected_storm_id": None,
        }
    ]
