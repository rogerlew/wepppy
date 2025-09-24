"""Routes for stats blueprint extracted from app.py."""

from datetime import datetime
from subprocess import PIPE, Popen
from collections import Counter

from ._common import *  # noqa: F401,F403


stats_bp = Blueprint('stats', __name__)

@stats_bp.route('/getloadavg')
@stats_bp.route('/getloadavg/')
def getloadavg():
    return jsonify(os.getloadavg())


@stats_bp.route('/access-by-year')
@stats_bp.route('/access-by-year/')
def access_by_year():
    try:
        project_loads = Counter()

        if _exists('/geodata/weppcloud_runs/access.csv'):
            with open('/geodata/weppcloud_runs/access.csv') as fp:
                rdr = csv.DictReader(fp)
                for d in rdr:
                    project_loads[int(d['year'])] += 1

    except Exception:
        return exception_factory()

    try:
        return jsonify(project_loads)

    except Exception:
        return exception_factory()


# stats blueprint
@stats_bp.route('/access-by-month')
@stats_bp.route('/access-by-month/')
def access_by_month():
    try:
        project_loads = Counter()

        if _exists('/geodata/weppcloud_runs/access.csv'):
            with open('/geodata/weppcloud_runs/access.csv') as fp:
                rdr = csv.DictReader(fp)
                for d in rdr:
                    year = int(d['year'])
                    month = int(d['date'].strip().split('-')[1])
                    project_loads[f'{year}-{month}'] += 1

    except Exception:
        return exception_factory()

    try:
        return jsonify(project_loads)

    except Exception:
        return exception_factory()


# stats blueprint
@stats_bp.route('/stats')
@stats_bp.route('/stats/')
def stats():
    try:
        if _exists('/geodata/weppcloud_runs/runs_counter.json'):
            with open('/geodata/weppcloud_runs/runs_counter.json') as fp:
                runs_counter = json.load(fp)
    except:
        runs_counter = {}

    try:
        return jsonify(runs_counter)

    except Exception:
        return exception_factory()


# stats blueprint
@stats_bp.route('/stats/<key>')
@stats_bp.route('/stats/<key>/')
def stats_key(key):
    try:
        if _exists('/geodata/weppcloud_runs/runs_counter.json'):
            with open('/geodata/weppcloud_runs/runs_counter.json') as fp:
                runs_counter = json.load(fp)
    except:
        runs_counter = {}

    try:
        return jsonify(runs_counter.get(key))

    except Exception:
        return exception_factory()

