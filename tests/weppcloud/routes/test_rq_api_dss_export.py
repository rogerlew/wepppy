from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Tuple

import pytest
from flask import Flask

from tests.factories.rq import RQRecorder, make_queue, make_redis_conn
from tests.factories.singleton import LockedMixin, singleton_factory

pytestmark = pytest.mark.unit


@pytest.fixture()
def dss_export_app(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Tuple[Flask, RQRecorder, Any, Any, Any, Any, Path]:
    import wepppy.weppcloud.routes.rq.api.api as api_module

    recorder = RQRecorder(job_ids=["job-001"])

    monkeypatch.setattr(api_module, "get_wd", lambda runid: str(tmp_path / runid))
    monkeypatch.setattr(api_module, "_redis_conn", lambda: make_redis_conn(recorder))
    monkeypatch.setattr(api_module, "Queue", make_queue(recorder))

    prep_cls = singleton_factory(
        "RedisPrepStub",
        attrs={"calls": []},
        methods={
            "remove_timestamp": lambda self, task: self.calls.append(("remove_timestamp", task)),
            "set_rq_job_id": lambda self, name, job_id: self.calls.append(("set_rq_job_id", name, job_id)),
        },
    )
    prep_cls.reset_instances()
    monkeypatch.setattr(api_module, "RedisPrep", prep_cls)

    def make_wepp_cls():
        def _get_mode(self):
            return getattr(self, "_dss_export_mode", None)

        def _set_mode(self, value):
            self._dss_export_mode = value
            self.mode_updates.append(value)

        def _get_orders(self):
            return getattr(self, "_dss_excluded_channel_orders", [])

        def _set_orders(self, value):
            self._dss_excluded_channel_orders = list(value)
            self.exclude_updates.append(list(value))

        def _get_channel_ids(self):
            return getattr(self, "_dss_export_channel_ids", [])

        def _set_channel_ids(self, value):
            self._dss_export_channel_ids = list(value)
            self.channel_updates.append(list(value))

        wepp_cls = singleton_factory(
            "WeppStub",
            attrs={
                "_dss_export_mode": None,
                "_dss_excluded_channel_orders": [],
                "_dss_export_channel_ids": [],
                "mode_updates": [],
                "exclude_updates": [],
                "channel_updates": [],
            },
            mixins=(LockedMixin,),
        )
        setattr(wepp_cls, "dss_export_mode", property(_get_mode, _set_mode))
        setattr(wepp_cls, "dss_excluded_channel_orders", property(_get_orders, _set_orders))
        setattr(wepp_cls, "dss_export_channel_ids", property(_get_channel_ids, _set_channel_ids))
        return wepp_cls

    wepp_cls = make_wepp_cls()
    wepp_cls.reset_instances()
    monkeypatch.setattr(api_module, "Wepp", wepp_cls)

    watershed_cls = singleton_factory(
        "WatershedStub",
        attrs={"chns_summary": {}},
    )
    watershed_cls.reset_instances()
    monkeypatch.setattr(api_module, "Watershed", watershed_cls)

    monkeypatch.setattr(api_module, "post_dss_export_rq", lambda *args, **kwargs: None)

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SITE_PREFIX"] = "/weppcloud"

    return app, recorder, prep_cls, wepp_cls, watershed_cls, api_module, tmp_path


def test_post_dss_export_rq_accepts_json_payload(dss_export_app):
    app, recorder, prep_cls, wepp_cls, watershed_cls, api_module, base_path = dss_export_app

    payload = {
        "dss_export_mode": 1,
        "dss_export_channel_ids": [24, 54, 24],
        "dss_export_exclude_orders": [3],
    }

    runid = "demo"
    with app.test_request_context(
        "/weppcloud/runs/demo/live/rq/api/post_dss_export_rq",
        method="POST",
        data=json.dumps(payload),
        content_type="application/json",
    ):
        response = api_module.api_post_dss_export_rq(runid, "live")

    assert response.status_code == 200
    assert response.get_json() == {"Success": True, "job_id": "job-001"}

    assert len(recorder.queue_calls) == 1
    queue_call = recorder.queue_calls[0]
    assert queue_call.func is api_module.post_dss_export_rq
    assert queue_call.args == (runid,)
    assert queue_call.timeout == api_module.TIMEOUT

    wepp_instance = wepp_cls.getInstance(str(base_path / runid))
    assert wepp_instance._lock_calls == 1
    assert wepp_instance.dss_export_mode == 1
    assert wepp_instance.dss_export_channel_ids == [24, 54]
    assert wepp_instance.dss_excluded_channel_orders == [3]

    prep_instance = prep_cls.getInstance(str(base_path / runid))
    assert ("remove_timestamp", api_module.TaskEnum.run_wepp_hillslopes) in prep_instance.calls
    assert ("remove_timestamp", api_module.TaskEnum.run_wepp_watershed) in prep_instance.calls
    assert ("set_rq_job_id", "post_dss_export_rq", "job-001") in prep_instance.calls


def test_post_dss_export_rq_mode2_builds_channels(dss_export_app):
    app, recorder, prep_cls, wepp_cls, watershed_cls, api_module, base_path = dss_export_app

    runid = "alpha"
    watershed = watershed_cls.getInstance(str(base_path / runid))
    watershed.chns_summary = {
        "101": {"order": 1},
        "102": {"order": 2},
        "103": {"order": "3"},
    }

    payload = {
        "dss_export_mode": 2,
        "dss_export_exclude_orders": [2],
    }

    with app.test_request_context(
        "/weppcloud/runs/alpha/live/rq/api/post_dss_export_rq",
        method="POST",
        data=json.dumps(payload),
        content_type="application/json",
    ):
        response = api_module.api_post_dss_export_rq(runid, "live")

    assert response.status_code == 200
    body = response.get_json()
    assert body == {"Success": True, "job_id": "job-001"}

    wepp_instance = wepp_cls.getInstance(str(base_path / runid))
    assert wepp_instance.dss_export_mode == 2
    assert wepp_instance.dss_excluded_channel_orders == [2]
    # Order 2 excluded; others retained.
    assert sorted(wepp_instance.dss_export_channel_ids) == [101, 103]


def test_post_dss_export_rq_handles_form_payload(dss_export_app):
    app, recorder, prep_cls, wepp_cls, watershed_cls, api_module, base_path = dss_export_app

    runid = "legacy"
    form_payload = {
        "dss_export_mode": "1",
        "dss_export_channel_ids": "12, 34 , 56",
        "dss_export_exclude_order_1": "on",
        "dss_export_exclude_order_3": "on",
    }

    with app.test_request_context(
        "/weppcloud/runs/legacy/live/rq/api/post_dss_export_rq",
        method="POST",
        data=form_payload,
        content_type="application/x-www-form-urlencoded",
    ):
        response = api_module.api_post_dss_export_rq(runid, "live")

    assert response.status_code == 200
    assert recorder.queue_calls[0].func is api_module.post_dss_export_rq

    wepp_instance = wepp_cls.getInstance(str(base_path / runid))
    assert wepp_instance.dss_export_mode == 1
    assert wepp_instance.dss_export_channel_ids == [12, 34, 56]
    assert sorted(wepp_instance.dss_excluded_channel_orders) == [1, 3]
