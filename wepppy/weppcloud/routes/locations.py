"""Routes for locations blueprint extracted from app.py."""

from datetime import datetime
import uuid
from subprocess import PIPE, Popen

from ._common import *  # noqa: F401,F403
from wepppy.weppcloud.utils import auth_tokens


locations_bp = Blueprint('locations', __name__)


def _issue_rq_engine_token() -> str:
    subject = None
    if hasattr(current_user, "get_id"):
        subject = current_user.get_id()
    if not subject:
        subject = getattr(current_user, "id", None)
    if not subject:
        subject = getattr(current_user, "email", None)
    if not subject:
        raise RuntimeError("Unable to resolve user subject for rq-engine token")

    roles = [
        str(getattr(role, "name", role)).strip()
        for role in (getattr(current_user, "roles", None) or [])
        if str(getattr(role, "name", role)).strip()
    ]

    token_payload = auth_tokens.issue_token(
        str(subject),
        scopes=["rq:enqueue"],
        audience="rq-engine",
        extra_claims={
            "roles": roles,
            "token_class": "user",
            "email": getattr(current_user, "email", None),
            "jti": uuid.uuid4().hex,
        },
    )
    token = token_payload.get("token")
    if not token:
        raise RuntimeError("Failed to issue rq-engine token")
    return token

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
    try:
        rq_engine_token = _issue_rq_engine_token()
        cap_base_url = (current_app.config.get("CAP_BASE_URL") or os.getenv("CAP_BASE_URL", "/cap")).rstrip("/")
        cap_asset_base_url = (
            current_app.config.get("CAP_ASSET_BASE_URL")
            or os.getenv("CAP_ASSET_BASE_URL", f"{cap_base_url}/assets")
        ).rstrip("/")
        cap_site_key = current_app.config.get("CAP_SITE_KEY") or os.getenv("CAP_SITE_KEY", "")
        return render_template(
            'locations/portland/index.htm',
            user=current_user,
            rq_engine_token=rq_engine_token,
            cap_base_url=cap_base_url,
            cap_asset_base_url=cap_asset_base_url,
            cap_site_key=cap_site_key,
        )
    except auth_tokens.JWTConfigurationError as exc:
        current_app.logger.exception("Failed to issue rq-engine token for portland interface")
        return exception_factory(f"JWT configuration error: {exc}")
    except Exception:
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/locations.py:83", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return exception_factory()


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
    return redirect('https://doc.wepp.cloud/lake-tahoe-2020/', code=301)


@locations_bp.route('/lt/SteepSlopes')
@locations_bp.route('/lt/SteepSlopes/')
@locations_bp.route('/locations/lt/SteepSlopes')
@locations_bp.route('/locations/lt/SteepSlopes/')
def lt_steep_slope_index():
    return redirect('https://doc.wepp.cloud/lake-tahoe-2020/SteepSlopes.html', code=301)


@locations_bp.route('/locations/caldor')
@locations_bp.route('/locations/caldor/')
def caldor_index():
    return redirect('https://doc.wepp.cloud/caldor-fire-2025/', code=301)


@locations_bp.route('/locations/caldor/results/<file>')
@locations_bp.route('/locations//results/<file>/')
def caldor_results(file):
    """
    recursive list the file structure of the working directory
    """
    return redirect('https://github.com/ui-weppcloud/caldor-fire-2025/tree/storage', code=301)
 

@locations_bp.route('/seattle-municipal')
@locations_bp.route('/seattle-municipal/')
@locations_bp.route('/locations/seattle-municipal')
@locations_bp.route('/locations/seattle-municipal/')
def seattle_index():
    return redirect('https://doc.wepp.cloud/seattle-municipal/', code=301)


@locations_bp.route('/seattle-municipal/results')
@locations_bp.route('/seattle-municipal/results/')
@locations_bp.route('/locations/seattle-municipal/results')
@locations_bp.route('/locations/seattle-municipal/results/')
def seattle_results_index():
    return redirect('https://github.com/ui-weppcloud/seattle-municipal/tree/storage', code=301)


@locations_bp.route('/seattle-municipal/results/<path:subpath>')
@locations_bp.route('/seattle-municipal/results/<path:subpath>/')
@locations_bp.route('/locations/seattle-municipal/results/<path:subpath>')
@locations_bp.route('/locations/seattle-municipal/results/<path:subpath>/')
# roles_required('SeattleGroup')
def seattle_results(subpath):
    """
    recursive list the file structure of the working directory
    """
    
    return redirect('https://github.com/ui-weppcloud/seattle-municipal/tree/storage', code=301)
