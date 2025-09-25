from collections import Counter
import json
from flask_security import current_user
from ._common import *  # noqa: F401,F403
from wepppy.weppcloud.utils.helpers import exception_factory

weppcloud_site_bp = Blueprint('weppcloud_site', __name__)

@weppcloud_site_bp.route('/')
def index():
    runs_counter = Counter()
    try:
        if _exists('/geodata/weppcloud_runs/runs_counter.json'):
            with open('/geodata/weppcloud_runs/runs_counter.json') as fp:
                runs_counter = Counter(json.load(fp))
    except:
        pass

    try:
        return render_template('index.htm', user=current_user, runs_counter=runs_counter)
    except Exception:
        return exception_factory()
