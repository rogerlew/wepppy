from __future__ import annotations

from typing import Any, Dict, List

from ._common import Blueprint, Response, jsonify, request, current_app, current_user
from wepppy.profile_recorder import get_profile_recorder

recorder_bp = Blueprint("recorder", __name__, url_prefix="/weppcloud")


def _normalise_events(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    events = payload.get("events")
    if isinstance(events, list):
        return [event for event in events if isinstance(event, dict)]
    return []


@recorder_bp.route("/runs/<runid>/<config>/recorder/events", methods=["POST"])
def recorder_events(runid: str, config: str) -> Response:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Expected JSON object payload"}), 400

    events = _normalise_events(payload)
    if not events:
        return jsonify({"error": "events must be a non-empty array"}), 400

    recorder = get_profile_recorder(current_app)
    for event in events:
        event.setdefault("runId", runid)
        event.setdefault("config", config)
        recorder.append_event(event, user=current_user)

    return Response(status=204)
