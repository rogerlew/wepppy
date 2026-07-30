"""Routes for the Storm Event Analyzer report."""

from __future__ import annotations

from flask import Response, request
from wepppy.nodb.unitizer import Unitizer
from wepppy.nodb.unitizer import precisions as UNITIZER_PRECISIONS
from wepppy.wepp.reports.output_scope import normalize_output_scope, scoped_dataset_path

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
from wepppy.weppcloud.utils.helpers import (
    error_factory,
    exception_factory,
    handle_with_exception_factory,
    is_omni_child_run,
)

from .gl_dashboard import _get_omni_scenarios

storm_event_analyzer_bp = Blueprint("storm_event_analyzer", __name__)


def _build_wepp_paths(output_scope: str) -> dict[str, str]:
    """Build scope-aware WEPP dataset relpaths for storm event analyzer queries."""
    return {
        "soil": scoped_dataset_path("wepp/output/interchange/H.soil.parquet", output_scope),
        "water": scoped_dataset_path("wepp/output/interchange/H.wat.parquet", output_scope),
        "outlet": scoped_dataset_path("wepp/output/interchange/ebe_pw0.parquet", output_scope),
        "hillEvents": scoped_dataset_path("wepp/output/interchange/H.ebe.parquet", output_scope),
        "tc": scoped_dataset_path("wepp/output/interchange/tc_out.parquet", output_scope),
    }


@storm_event_analyzer_bp.route(
    "/runs/<string:runid>/<config>/storm-event-analyzer", strict_slashes=False
)
@requires_cap(gate_reason="Complete verification to view storm event analysis.")
@handle_with_exception_factory
def storm_event_analyzer(runid: str, config: str) -> Response:
    authorize(runid, config)
    try:
        output_scope = normalize_output_scope(request.args.get("output_scope"))
    except ValueError as exc:
        response = error_factory(str(exc))
        response.status_code = 400
        return response

    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    ron = Ron.getInstance(wd)
    unitizer = Unitizer.getInstance(wd)
    is_omni_child = is_omni_child_run(runid, wd=wd, pup_relpath=ctx.pup_relpath)
    omni_scenarios = None if is_omni_child else _get_omni_scenarios(wd)
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
        output_scope=output_scope,
        wepp_paths=_build_wepp_paths(output_scope),
    )
