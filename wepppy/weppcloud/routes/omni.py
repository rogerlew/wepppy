"""Routes for omni blueprint extracted from app.py."""

from ._common import *  # noqa: F401,F403

from wepppy.nodb import Ron
from wepppy.nodb.mods.omni import Omni
from wepppy.nodb.mods.treatments import Treatments
from wepppy.nodb.watershed import Watershed


omni_bp = Blueprint('omni', __name__)


@omni_bp.route('/runs/<string:runid>/<config>/api/omni/get_scenarios')
def get_scenarios(runid, config):
    authorize(runid, config)
    try:
        wd = get_wd(runid)
        return jsonify(Omni.getInstance(wd).scenarios)
    except Exception:
        return exception_factory('Error Getting Scenarios', runid=runid)


@omni_bp.route('/runs/<string:runid>/<config>/tasks/omni_migration')
def omni_migration(runid, config):
    authorize(runid, config)
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        if 'omni' in ron._mods:
            return error_factory('omni already in mods')
        
        with ron.locked():
            ron._mods.append('omni')

            if 'treatments' not in ron._mods:
                ron._mods.append('treatments')
                
        cfg_fn = f'{config}.cfg'
        Omni(wd, cfg_fn)

        if not _exists(_join(wd, 'treatments.nodb')):
            Treatments(wd, cfg_fn)

        return success_factory("Reload project to continue")
    except:
        return exception_factory('Error Resetting Disturbed Land Soil Lookup', runid=runid)


@omni_bp.route('/runs/<string:runid>/<config>/report/omni_scenarios')
@omni_bp.route('/runs/<string:runid>/<config>/report/omni_scenarios/')
def query_omni_scenarios_report(runid, config):
    try:
        wd = get_wd(runid)
        omni = Omni.getInstance(wd)
        df_report = omni.scenarios_report()

        # Convert DataFrame to dictionary if needed (assuming df_report is a DataFrame-like object)
        report_dict = df_report.to_dict()

        # Initialize result list for scenarios
        scenarios = []

        # Get unique scenarios
        unique_scenarios = set(report_dict['scenario'].values())

        # Define target metrics
        water_discharge_key = "Avg. Ann. water discharge from outlet"
        soil_loss_key = "Avg. Ann. total hillslope soil loss"

        # Process each scenario
        for scenario in unique_scenarios:
            scenario_data = {'name': scenario, 'water_discharge': None, 'soil_loss': None}

            # Iterate through report entries
            for idx in report_dict['scenario']:
                if report_dict['scenario'][idx] == scenario:
                    key_desc = report_dict['key'][idx]
                    if key_desc == water_discharge_key:
                        scenario_data['water_discharge'] = {
                            'value': report_dict['v'][idx],
                            'unit': report_dict['units'][idx]
                        }
                    elif key_desc == soil_loss_key:
                        scenario_data['soil_loss'] = {
                            'value': report_dict['v'][idx],
                            'unit': report_dict['units'][idx]
                        }

            # Only add scenario if both metrics are found
            if scenario_data['water_discharge'] and scenario_data['soil_loss']:
                scenarios.append(scenario_data)

        # Sort scenarios for consistent display
        scenarios.sort(key=lambda x: x['name'])

        return render_template('reports/omni/omni_scenarios_summary.htm', runid=runid, config=config,
                               user=current_user,
                               watershed=Watershed.getInstance(wd),
                               scenarios=scenarios)

    except:
        return exception_factory(runid=runid)
