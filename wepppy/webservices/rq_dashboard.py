"""Standalone launcher for the rq-dashboard blueprint."""

from __future__ import annotations

import os
from flask import Flask, Response

try:  # pragma: no cover - optional dependency
    from rq_dashboard import blueprint as rq_dashboard_blueprint
except ImportError:  # pragma: no cover - optional dependency
    rq_dashboard_blueprint = None

app = Flask(__name__)
app.config["RQ_DASHBOARD_REDIS_URL"] = os.environ.get("RQ_DASHBOARD_REDIS_URL", "redis://129.101.202.237:6379/9")

if rq_dashboard_blueprint is not None:
    app.register_blueprint(rq_dashboard_blueprint, url_prefix="/")
else:
    @app.route("/", methods=["GET"])
    def dependency_missing() -> Response:
        """Inform callers that rq-dashboard is unavailable."""
        return (
            "rq-dashboard is not installed on this host. "
            "Install the dependency to enable the monitoring UI.",
            503,
        )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8040, debug=True)
