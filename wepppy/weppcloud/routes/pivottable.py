import os
import json

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
from subprocess import check_output

import pandas as pd

from flask import abort, Blueprint, request, Response, jsonify

from utils.helpers import get_wd, htmltree, error_factory

_html = r"""
<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8">
        <title>Pivot Table</title>
        <!-- external libs from cdnjs -->
        <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/jquery/1.11.2/jquery.min.js"></script>
        <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/jqueryui/1.11.4/jquery-ui.min.js"></script>
        <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/d3/3.5.5/d3.min.js"></script>
        <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/jqueryui-touch-punch/0.2.3/jquery.ui.touch-punch.min.js"></script>
        <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/PapaParse/4.1.2/papaparse.min.js"></script>
        <script src="https://cdn.plot.ly/plotly-basic-latest.min.js"></script>

        <!-- PivotTable.js libs from /static/pivottable/ -->
        <link rel="stylesheet" type="text/css" href="/static/pivottable/pivot.css">
        <script type="text/javascript" src="/static/pivottable/pivot.js"></script>
        <script type="text/javascript" src="/static/pivottable/d3_renderers.js"></script>
        <script type="text/javascript" src="/static/pivottable/plotly_renderers.js"></script>
        <script type="text/javascript" src="/static/pivottable/export_renderers.js"></script>

        <!-- CSV payload injected server-side -->
        <script type="text/javascript">
          // Will be replaced with a JSON string by the server:
          window.INIT_CSV = __CSV_JSON__;
        </script>

        <style>
            html { height:100%; }
            body {
                font-family: Verdana, Arial, sans-serif;
                min-height: 95%;
                border: 5px dotted;
            }
            .whiteborder {border-color: white;}
            .greyborder {border-color: lightgrey;}
            #filechooser {
                color: #555;
                text-decoration: underline;
                cursor: pointer;
            }
            .node {
              border: solid 1px white;
              font: 10px sans-serif;
              line-height: 12px;
              overflow: hidden;
              position: absolute;
              text-indent: 2px;
            }
            /* Hide textarea by default; we show it only if no INIT_CSV provided */
            #textarea { display: none; width: 300px; }
        </style>
    </head>
    <body class="whiteborder">
        <script type="text/javascript">
            $(function(){
                var renderers = $.extend(
                    $.pivotUtilities.renderers,
                    $.pivotUtilities.plotly_renderers,
                    $.pivotUtilities.d3_renderers,
                    $.pivotUtilities.export_renderers
                );

                var parseAndPivot = function(f) {
                    $("#output").html("<p align='center' style='color:grey;'>(processing...)</p>");
                    Papa.parse(f, {
                        skipEmptyLines: true,
                        dynamicTyping: false,
                        error: function(e){ alert(e); },
                        complete: function(parsed){
                            try {
                                $("#output").pivotUI(parsed.data, { renderers: renderers }, true);
                            } catch (err) {
                                $("#output").html("<pre style='color:red'></pre>");
                                $("#output pre").text("Pivot render error:\\n" + (err && err.stack ? err.stack : err));
                            }
                        }
                    });
                };

                // File chooser
                $("#csv").on("change", function(event){
                    if (event.target.files && event.target.files[0]) {
                        parseAndPivot(event.target.files[0]);
                    }
                });

                // Manual paste (only if visible)
                $("#textarea").on("input change", function(){
                    parseAndPivot($("#textarea").val());
                });

                // Drag/drop
                var dragging = function(evt) {
                    evt.stopPropagation();
                    evt.preventDefault();
                    if (evt.originalEvent && evt.originalEvent.dataTransfer) {
                        evt.originalEvent.dataTransfer.dropEffect = 'copy';
                    }
                    $("body").removeClass("whiteborder").addClass("greyborder");
                };

                var endDrag = function(evt) {
                    evt.stopPropagation();
                    evt.preventDefault();
                    if (evt.originalEvent && evt.originalEvent.dataTransfer) {
                        evt.originalEvent.dataTransfer.dropEffect = 'copy';
                    }
                    $("body").removeClass("greyborder").addClass("whiteborder");
                };

                var dropped = function(evt) {
                    evt.stopPropagation();
                    evt.preventDefault();
                    $("body").removeClass("greyborder").addClass("whiteborder");
                    if (evt.originalEvent && evt.originalEvent.dataTransfer && evt.originalEvent.dataTransfer.files.length) {
                        parseAndPivot(evt.originalEvent.dataTransfer.files[0]);
                    }
                };

                $("html")
                    .on("dragover", dragging)
                    .on("dragend", endDrag)
                    .on("dragexit", endDrag)
                    .on("dragleave", endDrag)
                    .on("drop", dropped);

                // Auto-run if CSV injected server-side; otherwise reveal textarea for paste.
                if (typeof window.INIT_CSV === "string" && window.INIT_CSV.length > 0) {
                    // set the hidden textarea (for debugging if user unhides)
                    $("#textarea").val(window.INIT_CSV);
                    parseAndPivot(window.INIT_CSV);
                } else {
                    // allow manual paste if no preloaded CSV
                    $("#textarea").show();
                }
             });
        </script>

        <p align="center" style="line-height: 1.5">
            __FILE__
        </p>

        <div id="output" style="margin: 10px;"></div>
    </body>
</html>
"""

pivottable_bp = Blueprint('pivottable', __name__)  # fixed name


@pivottable_bp.route('/runs/<string:runid>/<config>/report/<string:wepp>/pivottable/<path:subpath>', strict_slashes=False)
def wp_pivottable_tree(runid, config, wepp, subpath):
    return pivottable_tree(runid, config, subpath)


@pivottable_bp.route('/runs/<string:runid>/<config>/pivottable/<path:subpath>', strict_slashes=False)
def pivottable_tree(runid, config, subpath):
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

    return pivottable_response(dir_path, subpath)


def pivottable_response(path, subpath):
    if not _exists(path):
        return error_factory('path does not exist')

    lower = path.lower()
    try:
        if lower.endswith('.parquet'):
            df = pd.read_parquet(path)
            # Write CSV with RFC4180 quoting to keep PapaParse happy
            csv = df.to_csv(index=False)
        elif lower.endswith('.tsv'):
            # Preserve TSV delimiter if user expects tabs
            df = pd.read_table(path, sep='\t')
            csv = df.to_csv(index=False, sep='\t')
        elif lower.endswith('.csv'):
            with open(path, 'r', encoding='utf-8') as f:
                csv = f.read()
        else:
            return error_factory('file is not a CSV, TSV or Parquet file')
    except Exception as e:
        return error_factory(f'failed to read data: {e}')

    # Safely embed as a JSON string in JS; also neutralize </script> to avoid early script termination
    csv_json = json.dumps(csv).replace("</", "<\\/")

    page = _html.replace("__CSV_JSON__", csv_json).replace("__FILE__", subpath)
    return Response(page, mimetype='text/html; charset=utf-8')