import json, os, subprocess, threading
from pathlib import Path
from werkzeug.serving import make_server
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup
from tests.factories.fixtures import rq_environment, rq_recorder
from tests.weppcloud.routes.test_roads_bp import (
    roads_client,
    osm_access,
    roads_module,
    RUN_ID,
)


def test_browser_flow(roads_client, osm_access, monkeypatch, tmp_path):
    client, _, ron_cls, _, _, wd = roads_client
    cfg = "disturbed9002-wbt-mofe"
    ron = ron_cls.getInstance(wd)
    ron.config_stem = cfg
    ron.extent = [8.539, 47.376, 8.541, 47.378]
    osm_access("PowerUser")
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import time

    steps = [502, 200, 502, 502, "stall"]
    requests = []

    class Interpreter(BaseHTTPRequestHandler):
        def do_POST(self):
            step = steps[len(requests)]
            requests.append(time.monotonic())
            self.send_response(200 if step == "stall" else step)
            self.end_headers()
            if step == "stall":
                time.sleep(3)
            elif step == 200:
                self.wfile.write(
                    json.dumps(
                        {
                            "elements": [
                                {
                                    "id": 17,
                                    "type": "way",
                                    "tags": {"highway": "track"},
                                    "geometry": [
                                        {"lon": 8.5391, "lat": 47.3761},
                                        {"lon": 8.5401, "lat": 47.3771},
                                    ],
                                }
                            ]
                        }
                    ).encode()
                )

    upstream = ThreadingHTTPServer(("127.0.0.1", 0), Interpreter)
    worker = threading.Thread(target=upstream.serve_forever, daemon=True)
    worker.start()
    monkeypatch.setenv(
        "WEPPPY_OSM_ROADS_OVERPASS_BASE_URL", f"http://127.0.0.1:{upstream.server_port}"
    )
    monkeypatch.setenv("WEPPPY_OSM_ROADS_OVERPASS_TIMEOUT_SEC", "2")
    pyroot = Path.cwd() / "wepppy/weppcloud"
    env = Environment(
        loader=FileSystemLoader(
            [pyroot / "templates", pyroot / "routes/run_0/templates"]
        ),
        autoescape=True,
    )
    env.globals.update(
        url_for=lambda *a, **k: "#",
        url_for_run=lambda *a, **k: "#",
        usersum_doc_link=lambda *a: Markup('<a href="#">Roads user guide</a>'),
    )
    form = env.get_template("controls/roads_pure.htm").render(
        roads_download_access={"allowed": True},
        roads=None,
        roads_upload_cap_mb=10,
        runid=RUN_ID,
        config=cfg,
    )

    @client.application.get("/")
    def page():
        parts = ["<!DOCTYPE html><html><head><title>Roads</title></head><body>", form]
        for script in ["dom", "forms", "http", "events", "control_base", "roads"]:
            parts.extend(
                [
                    "<script>",
                    (pyroot / "controllers_js" / (script + ".js")).read_text(),
                    "</script>",
                ]
            )
        parts.append(
            '<script>window.url_for_run=path=>"/runs/test-run/'
            + cfg
            + '/".concat(path);Roads.getInstance().bootstrap({});</script></body></html>'
        )
        return "".join(parts)

    @client.application.post("/stalled-body")
    def stalled_body():
        from flask import Response

        def slow():
            yield "{"
            time.sleep(35)
            yield "}"

        return Response(slow(), mimetype="application/json")

    srv = make_server("127.0.0.1", 0, client.application, threaded=True)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        node_env = dict(
            os.environ,
            PLAYWRIGHT_BROWSERS_PATH=str(pyroot / "static-src/.playwright-browsers"),
            NODE_PATH=str(pyroot / "static-src/node_modules"),
        )
        subprocess.run(
            [
                "node",
                str(Path(__file__).with_name("browser-flow.cjs")),
                f"http://127.0.0.1:{srv.server_port}",
                str(tmp_path),
            ],
            env=node_env,
            check=True,
        )
    finally:
        srv.shutdown()
        thread.join()
        upstream.shutdown()
        upstream.server_close()
        worker.join()
    assert len(requests) == 5
    for i in (0, 2):
        assert 4 <= requests[i + 1] - requests[i] < 10
