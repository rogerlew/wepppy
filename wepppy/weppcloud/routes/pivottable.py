import os
import json

from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists
from subprocess import check_output

import pandas as pd

from flask import abort, Blueprint, request, Response, jsonify, current_app

from wepppy.weppcloud.utils.helpers import authorize_and_handle_with_exception_factory, error_factory
from wepppy.weppcloud.utils.cap_guard import requires_cap

from ._run_context import load_run_context

_html = r"""
<!DOCTYPE html>
<html>
    <head>
        <meta charset="utf-8">
        <title>Pivot Table</title>
        <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/PapaParse/4.1.2/papaparse.min.js"></script>

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
            .controls {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 12px;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 6px;
                margin: 12px;
            }
            .control-group {
                display: grid;
                gap: 6px;
                font-size: 0.9rem;
            }
            select,
            textarea,
            input[type="text"],
            button {
                font: inherit;
            }
            #textarea {
                display: none;
                width: 100%;
                max-width: 420px;
                min-height: 120px;
            }
            #output {
                margin: 12px;
                overflow-x: auto;
            }
            .status {
                color: #666;
            }
            table.pivot-table {
                border-collapse: collapse;
                width: 100%;
            }
            table.pivot-table th,
            table.pivot-table td {
                border: 1px solid #ddd;
                padding: 6px 8px;
                text-align: right;
                white-space: nowrap;
            }
            table.pivot-table th:first-child,
            table.pivot-table td:first-child {
                text-align: left;
            }
            table.pivot-table thead th {
                background: #f5f5f5;
            }
            .totals {
                background: #fafafa;
                font-weight: 600;
            }
            #filechooser {
                color: #555;
                text-decoration: underline;
                cursor: pointer;
            }
        </style>
    </head>
    <body class="whiteborder">
        <p align="center" style="line-height: 1.5">
            __FILE__
        </p>

        <section class="controls">
            <div class="control-group">
                <label for="rows">Rows</label>
                <select id="rows" multiple size="6"></select>
            </div>
            <div class="control-group">
                <label for="cols">Columns</label>
                <select id="cols" multiple size="6"></select>
            </div>
            <div class="control-group">
                <label for="value">Value</label>
                <select id="value"></select>
            </div>
            <div class="control-group">
                <label for="aggregator">Aggregator</label>
                <select id="aggregator">
                    <option value="count">Count</option>
                    <option value="sum">Sum</option>
                    <option value="avg">Average</option>
                    <option value="min">Min</option>
                    <option value="max">Max</option>
                </select>
                <button id="render-btn" type="button">Render Pivot</button>
            </div>
            <div class="control-group">
                <label for="csv">Upload CSV/TSV</label>
                <input type="file" id="csv" accept=".csv,.tsv,.txt">
                <label for="textarea">Paste CSV</label>
                <textarea id="textarea" placeholder="Paste CSV content here"></textarea>
            </div>
        </section>

        <div id="output"></div>

        <script type="text/javascript">
            (function () {
                const output = document.getElementById('output');
                const rowsSelect = document.getElementById('rows');
                const colsSelect = document.getElementById('cols');
                const valueSelect = document.getElementById('value');
                const aggregatorSelect = document.getElementById('aggregator');
                const renderButton = document.getElementById('render-btn');
                const fileInput = document.getElementById('csv');
                const textarea = document.getElementById('textarea');

                let dataset = [];
                let fields = [];

                function setStatus(message) {
                    output.innerHTML = '<p class="status">' + message + '</p>';
                }

                function clearStatus() {
                    output.innerHTML = '';
                }

                function setOptions(select, items) {
                    select.innerHTML = '';
                    items.forEach((item) => {
                        const option = document.createElement('option');
                        option.value = item;
                        option.textContent = item;
                        select.appendChild(option);
                    });
                }

                function getSelectedValues(select) {
                    return Array.from(select.selectedOptions).map((opt) => opt.value);
                }

                function initState() {
                    return { sum: 0, count: 0, numCount: 0, min: null, max: null };
                }

                function updateState(state, rawValue) {
                    state.count += 1;
                    const num = parseFloat(rawValue);
                    if (!Number.isNaN(num)) {
                        state.sum += num;
                        state.numCount += 1;
                        state.min = state.min === null ? num : Math.min(state.min, num);
                        state.max = state.max === null ? num : Math.max(state.max, num);
                    }
                }

                function finalize(state, aggregator) {
                    if (!state) {
                        return '';
                    }
                    switch (aggregator) {
                        case 'count':
                            return state.count;
                        case 'sum':
                            return state.numCount ? state.sum : '';
                        case 'avg':
                            return state.numCount ? (state.sum / state.numCount) : '';
                        case 'min':
                            return state.min === null ? '' : state.min;
                        case 'max':
                            return state.max === null ? '' : state.max;
                        default:
                            return '';
                    }
                }

                function formatValue(value) {
                    if (value === '' || value === null || value === undefined) {
                        return '';
                    }
                    if (typeof value === 'number') {
                        if (!Number.isFinite(value)) {
                            return '';
                        }
                        if (Number.isInteger(value)) {
                            return String(value);
                        }
                        return value.toFixed(3).replace(/\.0+$/, '').replace(/(\.\d*?)0+$/, '$1');
                    }
                    return String(value);
                }

                function getKeyInfo(row, fieldsList) {
                    if (!fieldsList.length) {
                        return { key: '__ALL__', label: 'All' };
                    }
                    const parts = fieldsList.map((field) => {
                        const value = row[field];
                        return value === undefined || value === null ? '' : String(value);
                    });
                    return {
                        key: parts.join('||'),
                        label: parts.join(' / ') || 'All'
                    };
                }

                function renderPivot() {
                    if (!dataset.length) {
                        setStatus('No data loaded.');
                        return;
                    }

                    const rowFields = getSelectedValues(rowsSelect);
                    const colFields = getSelectedValues(colsSelect);
                    const aggregator = aggregatorSelect.value;
                    const valueField = valueSelect.value;

                    if (aggregator !== 'count' && !valueField) {
                        setStatus('Select a value field for this aggregator.');
                        return;
                    }

                    const rowKeys = [];
                    const colKeys = [];
                    const rowLabels = new Map();
                    const colLabels = new Map();
                    const matrix = new Map();
                    const rowTotals = new Map();
                    const colTotals = new Map();
                    const grandTotal = initState();

                    dataset.forEach((row) => {
                        const rowInfo = getKeyInfo(row, rowFields);
                        const colInfo = getKeyInfo(row, colFields);
                        if (!matrix.has(rowInfo.key)) {
                            matrix.set(rowInfo.key, new Map());
                            rowKeys.push(rowInfo.key);
                            rowLabels.set(rowInfo.key, rowInfo.label);
                        }
                        if (!colLabels.has(colInfo.key)) {
                            colKeys.push(colInfo.key);
                            colLabels.set(colInfo.key, colInfo.label);
                        }

                        const rowMap = matrix.get(rowInfo.key);
                        if (!rowMap.has(colInfo.key)) {
                            rowMap.set(colInfo.key, initState());
                        }
                        const cellState = rowMap.get(colInfo.key);
                        updateState(cellState, row[valueField]);

                        if (!rowTotals.has(rowInfo.key)) {
                            rowTotals.set(rowInfo.key, initState());
                        }
                        if (!colTotals.has(colInfo.key)) {
                            colTotals.set(colInfo.key, initState());
                        }

                        updateState(rowTotals.get(rowInfo.key), row[valueField]);
                        updateState(colTotals.get(colInfo.key), row[valueField]);
                        updateState(grandTotal, row[valueField]);
                    });

                    const table = document.createElement('table');
                    table.className = 'pivot-table';

                    const thead = document.createElement('thead');
                    const headerRow = document.createElement('tr');
                    const corner = document.createElement('th');
                    corner.textContent = rowFields.length ? rowFields.join(' / ') : 'All';
                    headerRow.appendChild(corner);

                    colKeys.forEach((key) => {
                        const th = document.createElement('th');
                        th.textContent = colLabels.get(key) || '';
                        headerRow.appendChild(th);
                    });

                    const totalHeader = document.createElement('th');
                    totalHeader.textContent = 'Total';
                    headerRow.appendChild(totalHeader);
                    thead.appendChild(headerRow);
                    table.appendChild(thead);

                    const tbody = document.createElement('tbody');
                    rowKeys.forEach((rowKey) => {
                        const tr = document.createElement('tr');
                        const th = document.createElement('th');
                        th.textContent = rowLabels.get(rowKey) || '';
                        tr.appendChild(th);

                        const rowMap = matrix.get(rowKey) || new Map();
                        colKeys.forEach((colKey) => {
                            const td = document.createElement('td');
                            const state = rowMap.get(colKey);
                            td.textContent = formatValue(finalize(state, aggregator));
                            tr.appendChild(td);
                        });

                        const totalCell = document.createElement('td');
                        totalCell.className = 'totals';
                        totalCell.textContent = formatValue(finalize(rowTotals.get(rowKey), aggregator));
                        tr.appendChild(totalCell);

                        tbody.appendChild(tr);
                    });

                    const totalRow = document.createElement('tr');
                    totalRow.className = 'totals';
                    const totalLabel = document.createElement('th');
                    totalLabel.textContent = 'Total';
                    totalRow.appendChild(totalLabel);

                    colKeys.forEach((colKey) => {
                        const td = document.createElement('td');
                        td.textContent = formatValue(finalize(colTotals.get(colKey), aggregator));
                        totalRow.appendChild(td);
                    });

                    const grandCell = document.createElement('td');
                    grandCell.textContent = formatValue(finalize(grandTotal, aggregator));
                    totalRow.appendChild(grandCell);

                    tbody.appendChild(totalRow);
                    table.appendChild(tbody);

                    clearStatus();
                    output.appendChild(table);
                }

                function normalizeParsedData(parsed) {
                    let data = parsed.data || [];
                    let headers = parsed.meta && parsed.meta.fields ? parsed.meta.fields.slice() : [];

                    if (!headers.length && data.length && Array.isArray(data[0])) {
                        headers = data[0].map((_, index) => `field_${index + 1}`);
                        data = data.map((row) => {
                            const obj = {};
                            headers.forEach((header, index) => {
                                obj[header] = row[index];
                            });
                            return obj;
                        });
                    }

                    if (!headers.length && data.length) {
                        headers = Object.keys(data[0]);
                    }

                    return { data, headers };
                }

                function loadData(parsed) {
                    const normalized = normalizeParsedData(parsed);
                    dataset = normalized.data;
                    fields = normalized.headers;

                    if (!fields.length) {
                        setStatus('No fields found in CSV data.');
                        return;
                    }

                    setOptions(rowsSelect, fields);
                    setOptions(colsSelect, fields);
                    setOptions(valueSelect, fields);

                    valueSelect.selectedIndex = 0;
                    renderPivot();
                }

                function parseInput(source, isFile) {
                    setStatus('Processing...');
                    Papa.parse(source, {
                        skipEmptyLines: true,
                        dynamicTyping: false,
                        header: true,
                        error: function (error) {
                            setStatus('Parse error: ' + error);
                        },
                        complete: function (parsed) {
                            loadData(parsed);
                        }
                    });
                }

                function handleFileChange(event) {
                    const file = event.target.files && event.target.files[0];
                    if (file) {
                        parseInput(file, true);
                    }
                }

                function handleTextareaInput() {
                    const value = textarea.value;
                    if (value && value.trim().length) {
                        parseInput(value, false);
                    }
                }

                function handleDragEvent(event) {
                    event.stopPropagation();
                    event.preventDefault();
                    document.body.classList.remove('whiteborder');
                    document.body.classList.add('greyborder');
                }

                function handleDragEnd(event) {
                    event.stopPropagation();
                    event.preventDefault();
                    document.body.classList.remove('greyborder');
                    document.body.classList.add('whiteborder');
                }

                function handleDrop(event) {
                    event.stopPropagation();
                    event.preventDefault();
                    document.body.classList.remove('greyborder');
                    document.body.classList.add('whiteborder');

                    const files = event.dataTransfer && event.dataTransfer.files;
                    if (files && files.length) {
                        parseInput(files[0], true);
                    }
                }

                renderButton.addEventListener('click', renderPivot);
                fileInput.addEventListener('change', handleFileChange);
                textarea.addEventListener('input', handleTextareaInput);

                document.documentElement.addEventListener('dragover', handleDragEvent);
                document.documentElement.addEventListener('dragend', handleDragEnd);
                document.documentElement.addEventListener('dragleave', handleDragEnd);
                document.documentElement.addEventListener('drop', handleDrop);

                if (typeof window.INIT_CSV === 'string' && window.INIT_CSV.length > 0) {
                    textarea.value = window.INIT_CSV;
                    parseInput(window.INIT_CSV, false);
                } else {
                    textarea.style.display = 'block';
                }
            })();
        </script>
    </body>
</html>
"""

pivottable_bp = Blueprint('pivottable', __name__)  # fixed name


@pivottable_bp.route('/runs/<string:runid>/<config>/report/<string:wepp>/pivottable/<path:subpath>', strict_slashes=False)
@requires_cap(gate_reason="Complete verification to view report tables.")
def wp_pivottable_tree(runid, config, wepp, subpath):
    return pivottable_tree(runid, config, subpath)


@pivottable_bp.route('/runs/<string:runid>/<config>/pivottable/<path:subpath>', strict_slashes=False)
@authorize_and_handle_with_exception_factory
def pivottable_tree(runid, config, subpath):
    """
    Serve a pivot UI for a specific file under a run working directory.
    """
    ctx = load_run_context(runid, config)
    wd_root = os.path.abspath(str(ctx.active_root))
    dir_path = os.path.abspath(os.path.join(wd_root, subpath))

    # Do not resolve symlinks here: critical functionality for browsing batch,
    # culverts, omni scenarios, and omni-contrast projects.
    if not dir_path.startswith(wd_root + os.sep) and dir_path != wd_root:
        abort(403)

    if not os.path.exists(dir_path):
        abort(404)

    if os.path.isdir(dir_path):
        abort(404)

    safe_subpath = os.path.relpath(dir_path, wd_root).replace(os.sep, "/")
    return pivottable_response(dir_path, safe_subpath)


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
        # Boundary catch: preserve contract behavior while logging unexpected failures.
        __import__("logging").getLogger(__name__).exception("Boundary exception at wepppy/weppcloud/routes/pivottable.py:536", extra={"runid": locals().get("runid"), "config": locals().get("config"), "job_id": locals().get("job_id")})
        return error_factory(f'failed to read data: {e}')

    # Safely embed as a JSON string in JS; also neutralize </script> to avoid early script termination
    csv_json = json.dumps(csv).replace("</", "<\\/")

    page = _html.replace("__CSV_JSON__", csv_json)\
                .replace("__FILE__", subpath)\
                .replace("__SITE_PREFIX__", current_app.config.get('SITE_PREFIX', ''))
    return Response(page, mimetype='text/html; charset=utf-8')
