"""Routes for the Storm Event Analyzer report."""

from __future__ import annotations

from flask import Response
from wepppy.nodb.unitizer import Unitizer
from wepppy.nodb.unitizer import precisions as UNITIZER_PRECISIONS

from ._common import (
    Blueprint,
    authorize,
    current_user,
    load_run_context,
    render_template,
)
from wepppy.nodb.core import Ron
from wepppy.nodb.core.ron import RonViewModel
from wepppy.weppcloud.utils.cap_guard import requires_cap
from wepppy.weppcloud.utils.helpers import exception_factory, handle_with_exception_factory

from .gl_dashboard import _get_omni_scenarios

storm_event_analyzer_bp = Blueprint("storm_event_analyzer", __name__)


@storm_event_analyzer_bp.route(
    "/runs/<string:runid>/<config>/storm-event-analyzer", strict_slashes=False
)
@requires_cap(gate_reason="Complete verification to view storm event analysis.")
@handle_with_exception_factory
def storm_event_analyzer(runid: str, config: str) -> Response:
    authorize(runid, config)
    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    ron = Ron.getInstance(wd)
    unitizer = Unitizer.getInstance(wd)
    omni_scenarios = _get_omni_scenarios(wd)
    base_scenario_label = "Burned" if ron.has_sbs else "Undisturbed"

    return render_template(
        "reports/storm_event_analyzer.htm",
        runid=runid,
        config=config,
        ron=ron,
        current_ron=RonViewModel(ron),
        user=current_user,
        unitizer_nodb=unitizer,
        precisions=UNITIZER_PRECISIONS,
        omni_scenarios=omni_scenarios,
        base_scenario_label=base_scenario_label,
    )
