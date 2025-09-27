"""Routes for disturbed blueprint extracted from app.py."""

from ._common import *  # noqa: F401,F403

from wepppy.nodb import Baer, Disturbed, Ron
from wepppy.nodb.mods.disturbed import write_disturbed_land_soil_lookup


disturbed_bp = Blueprint('disturbed', __name__)


@disturbed_bp.route('/runs/<string:runid>/<config>/modify_disturbed')
def modify_disturbed(runid, config):
    authorize(runid, config)
    try:
        return render_template('controls/edit_csv.htm', 
            csv_url='download/disturbed/disturbed_land_soil_lookup.csv')
    except:
        return exception_factory('Error Clearing Locks', runid=runid)


@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/reset_disturbed')
def reset_disturbed(runid, config):
    authorize(runid, config)
    wd = get_wd(runid)
    try:
        disturbed = Disturbed.getInstance(wd)
        disturbed.reset_land_soil_lookup()

        return success_factory()
    except:
        return exception_factory('Error Resetting Disturbed Land Soil Lookup', runid=runid)


@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/load_extended_land_soil_lookup')
def load_extended_land_soil_lookup(runid, config):
    authorize(runid, config)
    wd = get_wd(runid)
    try:
        disturbed = Disturbed.getInstance(wd)
        disturbed.build_extended_land_soil_lookup()

        return success_factory()
    except:
        return exception_factory('Error Building Extended Land Soil Lookup', runid=runid)


@disturbed_bp.route('/runs/<string:runid>/<config>/api/disturbed/has_sbs')
@disturbed_bp.route('/runs/<string:runid>/<config>/api/disturbed/has_sbs/')
def has_sbs(runid, config):
    authorize(runid, config)
    try:
        wd = get_wd(runid)
        disturbed = Disturbed.getInstance(wd)
        return jsonify(dict(has_sbs=disturbed.has_sbs))
    except Exception:
        return exception_factory('Error Getting SBS Status', runid=runid)


@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/modify_disturbed', methods=['POST'])
def task_modify_disturbed(runid, config):
    authorize(runid, config)
    try:
        wd = get_wd(runid)
        data = json.loads(request.data.decode('utf-8'))
        lookup_fn = Disturbed.getInstance(wd).lookup_fn
        write_disturbed_land_soil_lookup(lookup_fn, data)
        return success_factory()
    except:
        return exception_factory('Error Modifying Disturbed', runid=runid)


@disturbed_bp.route('/runs/<string:runid>/<config>/query/baer_wgs_map')
@disturbed_bp.route('/runs/<string:runid>/<config>/query/baer_wgs_map/')
def query_baer_wgs_bounds(runid, config):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        if 'baer' in ron.mods:
            baer = Baer.getInstance(wd)
        else:
            baer = Disturbed.getInstance(wd)

        if not baer.has_map:
            return error_factory('No SBS map has been specified')

        return success_factory(dict(bounds=baer.bounds,
                                    classes=baer.classes,
                                    imgurl='resources/baer.png'))
    except Exception:
        return exception_factory(runid=runid)


@disturbed_bp.route('/runs/<string:runid>/<config>/view/modify_burn_class')
@disturbed_bp.route('/runs/<string:runid>/<config>/view/modify_burn_class/')
def query_baer_class_map(runid, config):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        if 'baer' in ron.mods:
            baer = Baer.getInstance(wd)
        else:
            baer = Disturbed.getInstance(wd)

        if not baer.has_map:
            return error_factory('No SBS map has been specified')

        return render_template('mods/baer/classify.htm', baer=baer)
    except Exception:
        return exception_factory(runid=runid)


@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/modify_burn_class', methods=['POST'])
@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/modify_burn_class/', methods=['POST'])
def task_baer_class_map(runid, config):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        if 'baer' in ron.mods:
            baer = Baer.getInstance(wd)
        else:
            baer = Disturbed.getInstance(wd)

        if not baer.has_map:
            return error_factory('No SBS map has been specified')

        classes = request.json.get('classes', None)
        nodata_vals = request.json.get('nodata_vals', None)

        baer.modify_burn_class(classes, nodata_vals)
        return success_factory()
    except Exception:
        return exception_factory(runid=runid)


@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/modify_color_map', methods=['POST'])
@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/modify_color_map/', methods=['POST'])
def task_baer_modify_color_map(runid, config):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        if 'baer' in ron.mods:
            baer = Baer.getInstance(wd)
        else:
            baer = Disturbed.getInstance(wd)

        if not baer.has_map:
            return error_factory('No SBS map has been specified')

        color_map = request.json.get('color_map', None)
        color_map = {tuple(int(c) for c in color.split('_')) : sev for color, sev in color_map.items()}

        baer.modify_color_map(color_map)

        return success_factory()
    except Exception:
        return exception_factory(runid=runid)


@disturbed_bp.route('/runs/<string:runid>/<config>/resources/baer.png')
def resources_baer_sbs(runid, config):
    try:
        wd = get_wd(runid)
        ron = Ron.getInstance(wd)
        if 'baer' in ron.mods:
            baer = Baer.getInstance(wd)
        else:
            baer = Disturbed.getInstance(wd)

        if not baer.has_map:
            return error_factory('No SBS map has been specified')

        return send_file(baer.baer_rgb_png, mimetype='image/png')
    except Exception:
        return exception_factory(runid=runid)


@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/set_firedate/', methods=['POST'])
def set_firedate(runid, config):
    wd = get_wd(runid)
    disturbed = Disturbed.getInstance(wd)
    try:
        fire_date = request.json.get('fire_date', None)
        disturbed.fire_date = fire_date
        return success_factory()
    except Exception:
        return exception_factory("failed to set firedate", runid=runid)


@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/upload_sbs/', methods=['POST'])
def task_upload_sbs(runid, config):
    wd = get_wd(runid)

    ron = Ron.getInstance(wd)
    if 'baer' in ron.mods:
        baer = Baer.getInstance(wd)
    else:
        baer = Disturbed.getInstance(wd)

    try:
        file = request.files['input_upload_sbs']
    except Exception:
        return exception_factory('Could not find file', runid=runid)

    try:
        if file.filename == '':
            return error_factory('no filename specified')
        filename = secure_filename(file.filename)
    except Exception:
        return exception_factory('Could not obtain filename', runid=runid)

    try:
        file.save(_join(baer.baer_dir, filename))
    except Exception:
        return exception_factory('Could not save file', runid=runid)

    from wepppy.nodb.mods.baer.sbs_map import sbs_map_sanity_check

    try:
        ret, description = sbs_map_sanity_check(_join(baer.baer_dir, filename))
        if ret != 0:
            return exception_factory(description, runid=runid)
    except Exception:
        return exception_factory('Failed validating file', runid=runid)

    try:
        res = baer.validate(filename)
    except Exception:
        return exception_factory('Failed validating file', runid=runid)

    return success_factory(res)


@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/upload_cover_transform/', methods=['POST'])
def task_upload_cover_transform(runid, config):
    from wepppy.nodb.mods.revegetation import Revegetation

    wd = get_wd(runid)

    reveg = Revegetation.getInstance(wd)

    try:
        file = request.files['input_upload_cover_transform']
    except Exception:
        return exception_factory('Could not find file', runid=runid)

    try:
        if file.filename == '':
            return error_factory('no filename specified')

        filename = secure_filename(file.filename)
    except Exception:
        return exception_factory('Could not obtain filename', runid=runid)

    try:
        file.save(_join(reveg.revegetation_dir, filename))
    except Exception:
        return exception_factory('Could not save file', runid=runid)

    try:
        res = reveg.validate_user_defined_cover_transform(filename)
    except Exception:
        return exception_factory('Failed validating file', runid=runid)

    return success_factory(res)


@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/remove_sbs/', methods=['POST'])
def task_remove_sbs(runid, config):
   
    try:
        wd = get_wd(runid)

        ron = Ron.getInstance(wd)
        if 'baer' in ron.mods:
            baer = Baer.getInstance(wd)
            baer.remove_sbs()
        else:
            baer = Disturbed.getInstance(wd)
            baer.remove_sbs()
        
        return success_factory()

    except:
        return exception_factory(runid=runid)


@disturbed_bp.route('/runs/<string:runid>/<config>/tasks/build_uniform_sbs/<value>', methods=['POST'])
def task_build_uniform_sbs(runid, config, value):
    try:
        wd = get_wd(runid)

        disturbed = Disturbed.getInstance(wd)
        sbs_fn = disturbed.build_uniform_sbs(int(value))
    except:
        return exception_factory(runid=runid)

    try:
        res = disturbed.validate(sbs_fn)
    except Exception:
        return exception_factory('Failed validating file', runid=runid)

    return success_factory()
