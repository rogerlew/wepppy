"""Routes for locations blueprint extracted from app.py."""

from datetime import datetime
from subprocess import PIPE, Popen

from ._common import *  # noqa: F401,F403


locations_bp = Blueprint('locations', __name__)

@locations_bp.route('/joh')
@locations_bp.route('/joh/')
def joh_index():
    return render_template('locations/joh/index.htm', user=current_user)


@locations_bp.route('/joh/joh-map.htm')
def joh_map():
    return render_template('locations/joh/joh-map.htm', user=current_user)


@locations_bp.route('/portland-municipal')
@locations_bp.route('/portland-municipal/')
@locations_bp.route('/locations/portland-municipal')
@locations_bp.route('/locations/portland-municipal/')
@roles_required('PortlandGroup')
def portland_index():
    return render_template('locations/portland/index.htm', user=current_user)


@locations_bp.route('/portland-municipal/results')
@locations_bp.route('/portland-municipal/results/')
@locations_bp.route('/locations/portland-municipal/results')
@locations_bp.route('/locations/portland-municipal/results/')
def portland_results_index():

    import io
    import wepppy
    fn = _join(wepppy.nodb.mods.locations.portland.portland._thisdir, 'results', 'index.htm')

    if _exists(fn):
        with io.open(fn, mode="r", encoding="utf-8") as fp:
            return fp.read()

@locations_bp.route('/portland-municipal/results/<file>')
@locations_bp.route('/portland-municipal/results/<file>/')
@locations_bp.route('/locations/portland-municipal/results/<file>')
@locations_bp.route('/locations/portland-municipal/results/<file>/')
@roles_required('PortlandGroup')
def portland_results(file):
    """
    recursive list the file structure of the working directory
    """
    import wepppy
    fn = _join(wepppy.nodb.mods.locations.portland.portland._thisdir, 'results', file)
    
    if _exists(fn):
        return send_file(fn, as_attachment=True)
    else:
        return error_factory('File does not exist')
    

@locations_bp.route('/lt')
@locations_bp.route('/lt/')
@locations_bp.route('/locations/lt')
@locations_bp.route('/locations/lt/')
def lt_index():
    return render_template('lt/index.htm', user=current_user)


@locations_bp.route('/ltf')
@locations_bp.route('/ltf/')
def ltf_index():
    return render_template('ltf/index.htm', user=current_user)


@locations_bp.route('/lt/SteepSlopes')
@locations_bp.route('/lt/SteepSlopes/')
@locations_bp.route('/locations/lt/SteepSlopes')
@locations_bp.route('/locations/lt/SteepSlopes/')
def lt_steep_slope_index():
    return render_template('lt/SteepSlopes.html', user=current_user)

@locations_bp.route('/locations/caldor')
@locations_bp.route('/locations/caldor/')
def calsor_index():
    return render_template('locations/caldor/Caldor.html', user=current_user)

@locations_bp.route('/locations/caldor/results/<file>')
@locations_bp.route('/locations//results/<file>/')
def caldor_results(file):
    """
    recursive list the file structure of the working directory
    """
    fn = _join('/workdir/wepppy/wepppy/weppcloud/templates/locations/caldor/results', file)
    
    if _exists(fn):
        return send_file(fn, as_attachment=True)
    else:
        return error_factory('File does not exist')
    
@locations_bp.route('/seattle-municipal')
@locations_bp.route('/seattle-municipal/')
@locations_bp.route('/locations/seattle-municipal')
@locations_bp.route('/locations/seattle-municipal/')
def seattle_index():
    return render_template('locations/spu/index.htm', user=current_user)

@locations_bp.route('/seattle-municipal/results')
@locations_bp.route('/seattle-municipal/results/')
@locations_bp.route('/locations/seattle-municipal/results')
@locations_bp.route('/locations/seattle-municipal/results/')
def seattle_results_index():

    import io
    import wepppy
    fn = _join(wepppy.nodb.mods.locations.seattle.seattle._thisdir, 'results', 'index.htm')

    if _exists(fn):
        with io.open(fn, mode="r", encoding="utf-8") as fp:
            return fp.read()


@locations_bp.route('/seattle-municipal/results/<file>')
@locations_bp.route('/seattle-municipal/results/<file>/')
@locations_bp.route('/locations/seattle-municipal/results/<file>')
@locations_bp.route('/locations/seattle-municipal/results/<file>/')
# roles_required('SeattleGroup')
def seattle_results(file):
    """
    recursive list the file structure of the working directory
    """
    import io
    import wepppy
    fn = _join(wepppy.nodb.mods.locations.seattle.seattle._thisdir, 'results', file)

    if _exists(fn):

        if '.htm' in fn:
            with io.open(fn, mode="r", encoding="utf-8") as fp:
                return fp.read()
        elif '.jpeg' in fn or '.jpg' in fn:
            return send_file(fn, mimetype='image/jpg')

        return send_file(fn, as_attachment=True)
    else:
        return error_factory('File does not exist')
    

@locations_bp.route('/seattle-municipal/results/<foo>/<bar>')
@locations_bp.route('/seattle-municipal/results/<foo>/<bar>/')
@locations_bp.route('/locations/seattle-municipal/results/<foo>/<bar>')
@locations_bp.route('/locations/seattle-municipal/results/<foo>/<bar>/')
# roles_required('SeattleGroup')
def seattle_results2(foo, bar):
    """
    recursive list the file structure of the working directory
    """
    import io
    import wepppy
    fn = _join(wepppy.nodb.mods.locations.seattle.seattle._thisdir, 'results', foo, bar)

    if _exists(fn):

        if '.htm' in fn:
            with io.open(fn, mode="r", encoding="utf-8") as fp:
                return fp.read()

        elif '.jpeg' in fn or '.jpg' in fn:
            return send_file(fn, mimetype='image/jpg')

        return send_file(fn, as_attachment=True)
    else:
        return error_factory('File does not exist')
    

@locations_bp.route('/seattle-municipal/static/<file>')
@locations_bp.route('/seattle-municipal/static/<file>/')
@locations_bp.route('/locations/seattle-municipal/static/<file>')
@locations_bp.route('/locations/seattle-municipal/static/<file>/')
# roles_required('SeattleGroup')
def seattle_static(file):
    """
    recursive list the file structure of the working directory
    """
    import wepppy
    fn = _join(wepppy.nodb.mods.locations.seattle.seattle._thisdir, 'static', file)

    if _exists(fn):
        
        with io.open(fn, "r", encoding="utf-8") as fp:
            return fp.read()
    else:
        return error_factory('File does not exist')
    