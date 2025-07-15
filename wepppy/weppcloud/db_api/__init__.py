from datetime import datetime
from math import ceil
from flask import Flask
from sqlalchemy import create_engine, desc, nullslast
from sqlalchemy.orm import sessionmaker
from wepppy.weppcloud.app import Run

# load app configuration based on deployment
import socket
_hostname = socket.gethostname()
config_app = None
if 'wepp1' in _hostname or 'forest' in _hostname:
    try:
        from wepppy.weppcloud.wepp1_config import config_app
    except:
        pass
elif 'wepp2' in _hostname:
    from wepppy.weppcloud.wepp2_config import config_app
elif 'wepp3' in _hostname:
    from wepppy.weppcloud.wepp3_config import config_app


if config_app is None:
    from wepppy.weppcloud.standalone_config import config_app

app = Flask(__name__)

current_app = config_app(app)


def _get_session():
    """
    Create a new SQLAlchemy session bound to the Flask app's database.
    """
    engine = create_engine(current_app.config['SQLALCHEMY_DATABASE_URI'])
    Session = sessionmaker(bind=engine)
    return Session()


def update_last_modified(runid, timestamp=None):
    """
    Update the last_modified field for a run.
    """
    session = _get_session()
    try:
        if timestamp is None:
            timestamp = datetime.now()
        session.query(Run).filter_by(runid=runid).update({'last_modified': timestamp})
        session.commit()
    finally:
        session.close()


def update_last_accessed(runid, timestamp=None):
    """
    Update the last_accessed field for a run.
    """
    session = _get_session()
    try:
        if timestamp is None:
            timestamp = datetime.now()
        session.query(Run).filter_by(runid=runid).update({'last_accessed': timestamp})
        session.commit()
    finally:
        session.close()


def get_run_by_id(runid):
    """
    Fetch a single Run by its runid.

    Returns:
        Run or None
    """
    session = _get_session()
    try:
        run = session.query(Run).filter_by(runid=runid).first()
    finally:
        session.close()
    return run