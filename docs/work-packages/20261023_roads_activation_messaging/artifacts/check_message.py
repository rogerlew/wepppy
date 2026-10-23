"""One-off actual guard and standard response readback; no project mutation."""
from types import SimpleNamespace
from unittest.mock import patch
from flask import Flask
from wepppy.weppcloud.routes.nodb_api import roads_bp as roads
from wepppy.weppcloud.utils.helpers import exception_factory

expected = (
    "Roads is unavailable because of a server configuration problem. "
    "This request could not be processed. "
    "Contact support and include this project's URL."
)
app = Flask(__name__)
for membership, enabled in ((True, False), (False, True), (True, True), (False, False)):
    controller = SimpleNamespace(enabled=enabled)
    ron = SimpleNamespace(mods=["roads"] if membership else [])
    with patch.object(roads.Ron, "getInstance", return_value=ron), patch.object(
        roads.Roads, "tryGetInstance", return_value=controller
    ), app.test_request_context():
        if membership == enabled:
            assert roads._sync_roads_enabled_state("/unused", "unused.cfg") is controller
        else:
            try:
                roads._sync_roads_enabled_state("/unused", "unused.cfg")
            except RuntimeError as exc:
                assert str(exc) == expected
                response = exception_factory(exc)
                assert response.status_code == 500
                assert response.get_json()["error"]["message"] == "RuntimeError: " + expected
            else:
                raise AssertionError("Mismatch was accepted")
        assert controller.enabled == enabled
        assert ron.mods == (["roads"] if membership else [])
with patch.object(roads.Ron, "getInstance", return_value=SimpleNamespace(mods=[])), patch.object(
    roads.Roads, "tryGetInstance", return_value=None
):
    try:
        roads._sync_roads_enabled_state("/unused", "unused.cfg")
    except FileNotFoundError as exc:
        assert str(exc) == "Roads controller has not been initialized"
    else:
        raise AssertionError("Absent controller behavior changed")
print("PASS: two mismatches return actionable HTTP 500 messages; agreeing and absent states unchanged")
