"""Routes for combined_watershed_viewer blueprint extracted from app.py."""

from ._common import *  # noqa: F401,F403


combined_watershed_viewer_bp = Blueprint('combined_watershed_viewer', __name__)


@combined_watershed_viewer_bp.route('/combined_ws_viewer')
@combined_watershed_viewer_bp.route('/combined_ws_viewer/')
def combined_ws_viewer():
    return render_template('combined_ws_viewer.htm')


@combined_watershed_viewer_bp.route('/combined_ws_viewer2')
@combined_watershed_viewer_bp.route('/combined_ws_viewer2/')
def combined_ws_viewer2():
    return render_template('combined_ws_viewer2.htm')


@combined_watershed_viewer_bp.route('/bounds_ws_viewer')
@combined_watershed_viewer_bp.route('/bounds_ws_viewer/')
def bounds_ws_viewer():
    return render_template('bounds_ws_viewer.htm')


@combined_watershed_viewer_bp.route('/combined_ws_viewer/url_generator', methods=['GET', 'POST'])
@combined_watershed_viewer_bp.route('/combined_ws_viewer/url_generator/', methods=['GET', 'POST'])
def combined_ws_viewer_url_gen():
    if current_user.is_authenticated:
        if not current_user.roles:
            from wepppy.weppcloud.app import user_datastore  # lazy import to avoid circular

            user_datastore.add_role_to_user(current_user.email, 'User')

    try:
        title = request.form.get('title', '')
        runids = request.form.get('runids', '')
        runids = runids.replace(',', ' ').split()

        from wepppy.weppcloud.combined_watershed_viewer_generator import combined_watershed_viewer_generator
        url = combined_watershed_viewer_generator(runids, title)

        return render_template('combined_ws_viewer_url_gen.htm',
            url=url, user=current_user, title=title, runids=', '.join(runids))
    except:
        return exception_factory('Error processing request')
