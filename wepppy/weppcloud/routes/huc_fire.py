
"""Routes for huc fire blueprint extracted from app.py."""

from datetime import datetime
from subprocess import PIPE, Popen

from ._common import *  # noqa: F401,F403

from wepppy.nodb import Ron
from wepppy.nodb.mods.disturbed import Disturbed

huc_fire_bp = Blueprint('huc_fire', __name__)

@huc_fire_bp.route('/huc-fire')
@huc_fire_bp.route('/huc-fire/')
def huc_fire():
    try:
        return render_template('huc-fire/index.html', user=current_user)
    except:
        return exception_factory()


@huc_fire_bp.route('/huc-fire/tasks/upload_sbs/', methods=['POST'])
def upload_sbs():
    from wepppy.weppcloud.app import create_run_dir, user_datastore
    try:
        file = request.files['input_upload_sbs']
    except Exception:
        return exception_factory('Could not find file')

    try:
        if file.filename == '':
            return error_factory('no filename specified')

        filename = secure_filename(file.filename)
    except Exception:
        return exception_factory('Could not obtain filename')

    runid, wd = create_run_dir(current_user)

    config = 'disturbed9002'
    cfg = f'{config}.cfg'

    try:
        Ron(wd, cfg)
    except Exception:
        return exception_factory('Could not create run')

    if not current_user.is_anonymous:
        try:
            user_datastore.create_run(runid, config, current_user)
        except Exception:
            return exception_factory('Could not add run to user database')


    disturbed = Disturbed.getInstance(wd)
    file_path = _join(disturbed.disturbed_dir, filename)
    try:
        file.save(file_path)
    except Exception:
        return exception_factory('Could not save file')

    try:
        res = disturbed.validate(filename)
    except Exception:
        os.remove(file_path)
        return exception_factory('Failed validating file')

    return jsonify(dict(runid=runid))


# noinspection PyBroadException
@huc_fire_bp.route('/runs/<string:runid>/<config>/resources/huc.json')
def huc(runid, config):

    ctx = load_run_context(runid, config)
    wd = str(ctx.active_root)
    disturbed = Disturbed.getInstance(wd)
    ((ymin, xmin), (ymax, xmax)) = disturbed.bounds

    # Construct the URL to query the hydro.nationalmap.gov server
    url = (f"https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer/6/query?"
           f"geometry=%7B%0D%0A++%22xmin%22%3A+{xmin}%2C%0D%0A++%22ymin%22%3A+{ymin}%2C%0D%0A++%22xmax%22%3A+{xmax}%2C%0D%0A++%22ymax%22%3A+{ymax}%2C%0D%0A++%22spatialReference%22%3A+%7B%0D%0A++++%22wkid%22%3A+4326%0D%0A++%7D%0D%0A%7D"
           f"&geometryType=esriGeometryEnvelope&spatialRel=esriSpatialRelIntersects&returnGeometry=true&f=geojson&inSR=4326&outSR=4326")

    # Fetch the GeoJSON from the hydro.nationalmap.gov server
    response = request.get(url)
    geojson_data = response.json()

    with open(_join(disturbed.disturbed_dir, 'huc.json'), 'w') as fp:
        json.dump(geojson_data, fp)

    return geojson_data
