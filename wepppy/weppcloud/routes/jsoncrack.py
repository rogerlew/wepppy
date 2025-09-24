import os
import json

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
from subprocess import check_output

import pandas as pd

from flask import abort, Blueprint, request, Response, jsonify, current_app

from utils.helpers import get_wd, htmltree, error_factory
_html = r"""
<!DOCTYPE html>
<html>
<head>
    <title>JSON Crack</title>
    <style>
body {
  margin: 0;
  padding: 0;
}

section {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

textarea {
  width: 100%;
  height: 100%;
}

div {
  display: flex;
  width: 100%;
  height: 150px;
}

#jsoncrackEmbed {
  flex: 1;
  order: 2;
  border: none;
  width: 100%;
  height: 100vh;
}
    </style>
</head>
<body>
    <iframe id="jsoncrackEmbed" src="https://jsoncrack.com/widget"></iframe>

    <script>
      const jsonCrackEmbed = document.querySelector("#jsoncrackEmbed");
      
      // Using a variable allows for easier debugging and readability
      const dataToPost = {
        json: JSON.stringify(__THE_JSON__)
      };
      
      // Wait for the iframe to load before posting the message
      jsonCrackEmbed.onload = () => {
        jsonCrackEmbed.contentWindow.postMessage(dataToPost, "*");
      };

      // An alternative or fallback listener
      window.addEventListener("message", (event) => {
        // You might want to add a check here to ensure the message is from a trusted source
        // or is a specific "ready" message from the iframe, but for this use case,
        // posting on load is generally sufficient and more reliable.
      }, false);
    </script>
</body>
</html>
"""

jsoncrack_bp = Blueprint('jsoncrack', __name__)  # fixed name


@jsoncrack_bp.route('/runs/<string:runid>/<config>/report/<string:wepp>/jsoncrack/<path:subpath>', strict_slashes=False)
def wp_jsoncrack_tree(runid, config, wepp, subpath):
    return jsoncrack_tree(runid, config, subpath)


@jsoncrack_bp.route('/runs/<string:runid>/<config>/jsoncrack/<path:subpath>', strict_slashes=False)
def jsoncrack_tree(runid, config, subpath):
    """
    Serve a pivot UI for a specific file under a run working directory.
    """
    wd = os.path.abspath(get_wd(runid))
    dir_path = os.path.abspath(os.path.join(wd, subpath))

    # jail within run wd
    if not dir_path.startswith(wd + os.sep) and dir_path != wd:
        abort(403)

    if not _exists(dir_path):
        abort(404)

    if os.path.isdir(dir_path):
        abort(404)

    return jsoncrack_response(dir_path, subpath)


def jsoncrack_response(path, subpath):
    if not _exists(path):
        return error_factory('path does not exist')

    lower = path.lower()
    try:
        if lower.endswith('.json') or lower.endswith('.geojson') or lower.endswith('.nodb'):
            with open(path, 'r', encoding='utf-8') as f:
                json_str = f.read()
        else:
            return error_factory('file is not a JSON, GEOJSON or NODB file')
    except Exception as e:
        return error_factory(f'failed to read data: {e}')

    page = _html.replace("__THE_JSON__", json_str)\
                .replace("__FILE__", subpath)\
                .replace("__SITE_PREFIX__", current_app.config.get('SITE_PREFIX', ''))
    return Response(page, mimetype='text/html; charset=utf-8')
