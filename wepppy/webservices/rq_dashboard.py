# /workdir/wepppy/run_rq_dashboard.py

from flask import Flask
from rq_dashboard import blueprint
import os

app = Flask(__name__)
app.config["RQ_DASHBOARD_REDIS_URL"] = os.environ.get("RQ_DASHBOARD_REDIS_URL", "redis://129.101.202.237:6379/9")
app.register_blueprint(blueprint, url_prefix="/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8040, debug=True)
