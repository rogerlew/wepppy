from __future__ import annotations

from typing import Any, Dict, List

from flask import abort
from ._common import (
    Blueprint,
    Response,
    jsonify,
    request,
    current_app,
    current_user,
    login_required,
)
from wepppy.profile_recorder import get_profile_recorder
from wepppy.nodb.core.ron import Ron

recorder_bp = Blueprint("recorder", __name__)


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
    assembler_override = None
    try:
        ron = Ron.getInstanceFromRunID(runid, ignore_lock=True)
        if ron is not None:
            assembler_override = ron.profile_recorder_assembler_enabled
    except Exception:
        assembler_override = None

    for event in events:
        event.setdefault("runId", runid)
        event.setdefault("config", config)
        recorder.append_event(event, user=current_user, assembler_override=assembler_override)

    return Response(status=204)


@recorder_bp.route("/runs/<runid>/<config>/recorder/promote", methods=["POST"])
@login_required
def recorder_promote(runid: str, config: str) -> Response:
    if not current_user.has_role("PowerUser"):
        abort(403)

    payload = request.get_json(silent=True) or {}
    slug = payload.get("slug")
    capture_id = payload.get("captureId") or "stream"

    recorder = get_profile_recorder(current_app)

    try:
        result = recorder.assembler.promote_draft(
            run_id=runid,
            capture_id=capture_id,
            slug=slug,
        )
    except FileNotFoundError as exc:
        return jsonify({"success": False, "message": str(exc)}), 404
    except Exception as exc:
        current_app.logger.exception("Failed to promote recorder draft for %s", runid)
        return jsonify({"success": False, "message": str(exc)}), 500

    return jsonify({"success": True, "profile": result})
