"""Routes for omni blueprint extracted from app.py."""

import traceback

from .._common import *  # noqa: F401,F403

from wepppy.nodb.core import Ron
from wepppy.nodb.mods.omni import Omni
from wepppy.nodb.mods.treatments import Treatments
from wepppy.nodb.core import Watershed
from .project_bp import set_project_mod_state
from wepppy.weppcloud.utils.cap_guard import requires_cap


omni_bp = Blueprint('omni', __name__)

def _summarize_omni_outlet_metrics(df_report, scenario_names):
    scenarios = []
    if df_report is None or df_report.empty:
        return scenarios

    report_dict = df_report.to_dict()
    value_key = 'value' if 'value' in report_dict else ('v' if 'v' in report_dict else None)
    if value_key is None:
        return scenarios

    water_discharge_key = "Avg. Ann. water discharge from outlet"
    soil_loss_key = "Avg. Ann. total hillslope soil loss"

    scenario_index = {
        name: {'name': name, 'water_discharge': None, 'soil_loss': None}
        for name in scenario_names
    }

    for idx in report_dict.get('scenario', {}):
        scenario_name = report_dict['scenario'][idx]
        if scenario_name not in scenario_index:
            continue
        key_desc = report_dict.get('key', {}).get(idx)
        if key_desc == water_discharge_key:
            scenario_index[scenario_name]['water_discharge'] = {
                'value': report_dict[value_key][idx],
                'unit': report_dict.get('units', {}).get(idx)
            }
        elif key_desc == soil_loss_key:
            scenario_index[scenario_name]['soil_loss'] = {
                'value': report_dict[value_key][idx],
                'unit': report_dict.get('units', {}).get(idx)
            }

    for scenario_name in scenario_names:
        entry = scenario_index.get(scenario_name)
        if entry and entry['water_discharge'] and entry['soil_loss']:
            scenarios.append(entry)

    return scenarios


def _summarize_omni_contrast_outlet_metrics(df_report, selection_mode):
    contrasts = []
    if df_report is None or df_report.empty:
        return contrasts

    if selection_mode in {"stream_order_pruning", "stream-order-pruning"}:
        selection_mode = "stream_order"
    if selection_mode in {"user-defined-hillslope-groups", "user-defined-hillslope-group"}:
        selection_mode = "user_defined_hillslope_groups"

    report_dict = df_report.to_dict()
    value_key = 'value' if 'value' in report_dict else ('v' if 'v' in report_dict else None)
    if value_key is None:
        return contrasts

    label_key = None
    if selection_mode == 'cumulative' and 'contrast_topaz_id' in report_dict:
        label_key = 'contrast_topaz_id'
    elif selection_mode == 'user_defined_areas' and 'contrast_id' in report_dict:
        label_key = 'contrast_id'
    elif selection_mode == 'user_defined_hillslope_groups' and 'contrast_id' in report_dict:
        label_key = 'contrast_id'
    elif selection_mode == 'stream_order' and 'contrast_id' in report_dict:
        label_key = 'contrast_id'
    if label_key is None:
        if 'contrast' in report_dict:
            label_key = 'contrast'
        elif 'contrast_id' in report_dict:
            label_key = 'contrast_id'
        else:
            return contrasts

    water_discharge_key = "Avg. Ann. water discharge from outlet"
    soil_loss_key = "Avg. Ann. total hillslope soil loss"

    contrast_index = {}
    for idx in report_dict.get('key', {}):
        label_value = report_dict.get(label_key, {}).get(idx)
        if label_value is None:
            continue
        label = str(label_value)
        entry = contrast_index.setdefault(label, {
            'name': label,
            'contrast_id': report_dict.get('contrast_id', {}).get(idx),
            'water_discharge': None,
            'soil_loss': None
        })

        key_desc = report_dict.get('key', {}).get(idx)
        if key_desc == water_discharge_key:
            entry['water_discharge'] = {
                'value': report_dict[value_key][idx],
                'unit': report_dict.get('units', {}).get(idx)
            }
        elif key_desc == soil_loss_key:
            entry['soil_loss'] = {
                'value': report_dict[value_key][idx],
                'unit': report_dict.get('units', {}).get(idx)
            }

    for entry in contrast_index.values():
        if entry['water_discharge'] and entry['soil_loss']:
            contrasts.append(entry)

    def sort_key(item):
        contrast_id = item.get('contrast_id')
        if contrast_id is None:
            return item.get('name', '')
        try:
            return int(contrast_id)
        except (TypeError, ValueError):
            return str(contrast_id)

    contrasts.sort(key=sort_key)
    return contrasts


@omni_bp.route('/runs/<string:runid>/<config>/api/omni/get_scenarios')
def get_scenarios(runid, config):
    authorize(runid, config)
    try:
        wd = get_wd(runid)
        return jsonify(Omni.getInstance(wd).scenarios)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/omni_bp.py:142", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory('Error Getting Scenarios', runid=runid)


@omni_bp.route('/runs/<string:runid>/<config>/api/omni/get_scenario_run_state')
def get_scenario_run_state(runid, config):
    authorize(runid, config)
    try:
        wd = get_wd(runid)
        omni = Omni.getInstance(wd)
        return jsonify({
            'run_state': omni.scenario_run_state,
            'dependency_tree': omni.scenario_dependency_tree,
            'run_markers': omni.scenario_run_markers(),
        })
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/omni_bp.py:157", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory('Error Getting Scenario Run State', runid=runid)


@omni_bp.route('/runs/<string:runid>/<config>/api/omni/delete_scenarios', methods=['POST'])
def delete_scenarios(runid, config):
    authorize(runid, config)
    try:
        wd = get_wd(runid)
        payload = parse_request_payload(request)
        scenario_names = payload.get('scenario_names') or payload.get('scenarios') or []
        if isinstance(scenario_names, str):
            scenario_names = [scenario_names]
        if not isinstance(scenario_names, (list, tuple)):
            scenario_names = []

        omni = Omni.getInstance(wd)
        result = omni.delete_scenarios(scenario_names)
        return success_factory(result)
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/omni_bp.py:176", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory('Error deleting scenarios', runid=runid)


@omni_bp.route('/runs/<string:runid>/<config>/tasks/omni_migration')
def omni_migration(runid, config):
    authorize(runid, config)
    try:
        set_project_mod_state(runid, config, 'omni', True)
        return success_factory("Reload project to continue")
    except ValueError as exc:
        return error_factory(str(exc))
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/nodb_api/omni_bp.py:188", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory('Error Resetting Disturbed Land Soil Lookup', runid=runid)


@omni_bp.route('/runs/<string:runid>/<config>/report/omni_scenarios')
@omni_bp.route('/runs/<string:runid>/<config>/report/omni_scenarios/')
@requires_cap(gate_reason="Complete verification to view Omni reports.")
def query_omni_scenarios_report(runid, config):
    try:
        wd = get_wd(runid)
        omni = Omni.getInstance(wd)
        df_report = omni.scenarios_report()

        # Get unique scenarios
        unique_scenarios = sorted(set(df_report['scenario'].values.tolist())) if 'scenario' in df_report else []
        scenarios = _summarize_omni_outlet_metrics(df_report, unique_scenarios)

        # Sort scenarios for consistent display
        scenarios.sort(key=lambda x: x['name'])

        return render_template('reports/omni/omni_scenarios_summary.htm', runid=runid, config=config,
                               user=current_user,
                               watershed=Watershed.getInstance(wd),
                               scenarios=scenarios)

    except Exception as exc:
        return exception_factory(msg=exc, runid=runid, details=traceback.format_exc())


@omni_bp.route('/runs/<string:runid>/<config>/report/omni_contrasts')
@omni_bp.route('/runs/<string:runid>/<config>/report/omni_contrasts/')
@requires_cap(gate_reason="Complete verification to view Omni reports.")
def query_omni_contrasts_report(runid, config):
    try:
        wd = get_wd(runid)
        omni = Omni.getInstance(wd)
        selection_mode = (omni.contrast_selection_mode or "cumulative").strip().lower()
        if selection_mode in {"stream_order_pruning", "stream-order-pruning"}:
            selection_mode = "stream_order"
        if selection_mode in {"user-defined-hillslope-groups", "user-defined-hillslope-group"}:
            selection_mode = "user_defined_hillslope_groups"
        df_report = omni.contrasts_report()
        contrasts = _summarize_omni_contrast_outlet_metrics(df_report, selection_mode)

        metrics_index = {}
        for entry in contrasts:
            contrast_id = entry.get("contrast_id")
            if contrast_id is None:
                continue
            try:
                key = int(contrast_id)
            except (TypeError, ValueError):
                key = str(contrast_id)
            metrics_index[key] = entry

        status_report = omni.contrast_status_report()
        items = []
        if selection_mode == "user_defined_areas":
            for entry in status_report.get("items", []):
                contrast_id = entry.get("contrast_id")
                metrics = metrics_index.get(contrast_id) or metrics_index.get(str(contrast_id))
                items.append(
                    {
                        "contrast_id": contrast_id,
                        "control_scenario": entry.get("control_scenario"),
                        "contrast_scenario": entry.get("contrast_scenario"),
                        "area_label": entry.get("area_label"),
                        "n_hillslopes": entry.get("n_hillslopes"),
                        "water_discharge": metrics.get("water_discharge") if metrics else None,
                        "soil_loss": metrics.get("soil_loss") if metrics else None,
                    }
                )
        elif selection_mode == "user_defined_hillslope_groups":
            for entry in status_report.get("items", []):
                contrast_id = entry.get("contrast_id")
                metrics = metrics_index.get(contrast_id) or metrics_index.get(str(contrast_id))
                items.append(
                    {
                        "contrast_id": contrast_id,
                        "control_scenario": entry.get("control_scenario"),
                        "contrast_scenario": entry.get("contrast_scenario"),
                        "group_index": entry.get("group_index"),
                        "n_hillslopes": entry.get("n_hillslopes"),
                        "water_discharge": metrics.get("water_discharge") if metrics else None,
                        "soil_loss": metrics.get("soil_loss") if metrics else None,
                    }
                )
        elif selection_mode == "stream_order":
            for entry in status_report.get("items", []):
                contrast_id = entry.get("contrast_id")
                metrics = metrics_index.get(contrast_id) or metrics_index.get(str(contrast_id))
                items.append(
                    {
                        "contrast_id": contrast_id,
                        "control_scenario": entry.get("control_scenario"),
                        "contrast_scenario": entry.get("contrast_scenario"),
                        "subcatchments_group": entry.get("subcatchments_group"),
                        "n_hillslopes": entry.get("n_hillslopes"),
                        "water_discharge": metrics.get("water_discharge") if metrics else None,
                        "soil_loss": metrics.get("soil_loss") if metrics else None,
                    }
                )
        else:
            for entry in status_report.get("items", []):
                contrast_id = entry.get("contrast_id")
                metrics = metrics_index.get(contrast_id) or metrics_index.get(str(contrast_id))
                topaz_id = entry.get("topaz_id")
                if topaz_id is None and metrics:
                    topaz_id = metrics.get("name")
                items.append(
                    {
                        "contrast_id": contrast_id,
                        "topaz_id": topaz_id,
                        "water_discharge": metrics.get("water_discharge") if metrics else None,
                        "soil_loss": metrics.get("soil_loss") if metrics else None,
                    }
                )

        report = {"selection_mode": selection_mode, "items": items}

        return render_template('reports/omni/omni_contrasts_summary.htm', runid=runid, config=config,
                               user=current_user,
                               watershed=Watershed.getInstance(wd),
                               report=report)

    except Exception as exc:
        return exception_factory(msg=exc, runid=runid, details=traceback.format_exc())
