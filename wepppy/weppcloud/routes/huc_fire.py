
"""Routes for huc fire blueprint extracted from app.py."""

import uuid

from ._common import *  # noqa: F401,F403

from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.weppcloud.utils import auth_tokens

huc_fire_bp = Blueprint('huc_fire', __name__)


def _issue_rq_engine_token() -> str | None:
    if current_user.is_anonymous:
        return None

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


@huc_fire_bp.route('/huc-fire')
@huc_fire_bp.route('/huc-fire/')
def huc_fire():
    try:
        rq_engine_token = _issue_rq_engine_token()
        return render_template(
            'huc-fire/index.html',
            user=current_user,
            rq_engine_token=rq_engine_token,
        )
    except auth_tokens.JWTConfigurationError as exc:
        current_app.logger.exception("Failed to issue rq-engine token for huc-fire")
        return exception_factory(f"JWT configuration error: {exc}")
    except Exception:
        current_app.logger.exception("Failed to render huc-fire page")
        return exception_factory()


# noinspection PyBroadException
@huc_fire_bp.route('/runs/<string:runid>/<config>/resources/huc.json')
@authorize_and_handle_with_exception_factory
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
