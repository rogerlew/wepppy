/* ----------------------------------------------------------------------------
 * Geneva Summary Report
 * ----------------------------------------------------------------------------
 */
var GenevaSummaryReport = (function () {
    "use strict";

    var instance;
    var SVG_NS = "http://www.w3.org/2000/svg";
    var CHART_WIDTH = 960;
    var CHART_HEIGHT = 420;
    var SERIES_CLASS_NAMES = [
        "geneva-summary__series-line--0",
        "geneva-summary__series-line--1",
        "geneva-summary__series-line--2",
        "geneva-summary__series-line--3",
        "geneva-summary__series-line--4"
    ];

    function byId(id) {
        return document.getElementById(id);
    }

    function parseJsonNode(node) {
        if (!node) {
            return null;
        }
        try {
            return JSON.parse(node.textContent || "{}");
        } catch (error) {
            console.warn("[GenevaSummaryReport] Failed to parse JSON payload.", error);
            return null;
        }
    }

    function asString(value) {
        if (value === undefined || value === null) {
            return "";
        }
        return String(value);
    }

    function asNumber(value) {
        if (value === undefined || value === null || value === "") {
            return null;
        }
        var parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : null;
    }

    function formatNumber(value, decimals) {
        var parsed = asNumber(value);
        if (parsed === null) {
            return "\u2014";
        }
        return parsed.toFixed(decimals);
    }

    function escapeHtml(value) {
        return asString(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function measureLabel(measure) {
        var labels = {
            peak_discharge: "Peak Discharge",
            runoff_depth: "Runoff Depth",
            runoff_volume: "Runoff Volume"
        };
        return labels[measure] || asString(measure);
    }

    function datasourceLabel(datasourceId) {
        var labels = {
            all: "All Datasources",
            cligen_freq: "CLIGEN Frequency",
            noaa14_pds: "NOAA Atlas 14 PDS"
        };
        return labels[datasourceId] || asString(datasourceId);
    }

    function stormShapeLabel(stormShape) {
        var labels = {
            uniform: "Uniform",
            neh4_type_b: "NEH-4 B",
            type_i: "Type I",
            type_ia: "Type IA",
            type_ii: "Type II",
            type_iii: "Type III"
        };
        var key = asString(stormShape).trim();
        return labels[key] || key || "\u2014";
    }

    function unitHydrographLabel(methodId) {
        var labels = {
            scs_triangular: "SCS Triangular",
            scs_curvilinear: "SCS Curvilinear"
        };
        var key = asString(methodId).trim();
        return labels[key] || key || "\u2014";
    }

    function timingMethodLabel(methodId) {
        var labels = {
            kirpich: "Kirpich",
            kent: "Kent",
            simas: "Simas"
        };
        var key = asString(methodId).trim().toLowerCase();
        return labels[key] || (key ? key : "\u2014");
    }

    function durationLabel(durationMinutes) {
        var value = Number(durationMinutes);
        if (!Number.isFinite(value) || value <= 0) {
            return asString(durationMinutes);
        }
        if (value === 60) {
            return "1h";
        }
        if (value % 60 === 0 && value > 60) {
            return String(value / 60) + "h";
        }
        return String(value) + "m";
    }

    function metricCellDisplay(metric) {
        if (!metric || typeof metric !== "object") {
            return "\u2014";
        }
        var value = asNumber(metric.value);
        if (value === null) {
            return "\u2014";
        }
        return value.toFixed(2);
    }

    function canonicalUnitKey(unitKey) {
        var raw = asString(unitKey).trim();
        if (!raw) {
            return "";
        }
        var aliases = {
            m3_s: "m^3/s",
            m3: "m^3",
            mm_hr: "mm/hour",
            mm_per_hr: "mm/hour",
            mm_hour: "mm/hour",
            mm_h: "mm/hour",
            mm: "mm"
        };
        return aliases[raw] || raw;
    }

    function getUnitizerClientSync() {
        var unitizer = (typeof window !== "undefined" && window.UnitizerClient)
            ? window.UnitizerClient
            : null;
        return unitizer && typeof unitizer.getClientSync === "function"
            ? unitizer.getClientSync()
            : null;
    }

    function unitizedValueHtml(value, unitKey, decimals) {
        var parsed = asNumber(value);
        var canonicalUnit = canonicalUnitKey(unitKey);
        if (parsed === null) {
            return "\u2014";
        }
        if (!canonicalUnit) {
            return escapeHtml(formatNumber(parsed, decimals));
        }

        var client = getUnitizerClientSync();
        if (client && typeof client.renderValue === "function") {
            return client.renderValue(parsed, canonicalUnit, { includeUnits: false });
        }
        return escapeHtml(formatNumber(parsed, decimals));
    }

    function unitizedUnitHtml(unitKey, fallbackLabel) {
        var canonicalUnit = canonicalUnitKey(unitKey);
        if (!canonicalUnit) {
            return escapeHtml(asString(fallbackLabel || ""));
        }

        var client = getUnitizerClientSync();
        if (client && typeof client.renderUnits === "function") {
            return client.renderUnits(canonicalUnit, { parentheses: false });
        }
        return escapeHtml(asString(fallbackLabel || canonicalUnit));
    }

    function metricCellValue(metric) {
        if (!metric || typeof metric !== "object") {
            return null;
        }
        return asNumber(metric.value);
    }

    function isAvailableEventRow(row) {
        return asString(row && row.status).toLowerCase() !== "unavailable";
    }

    function displayEventRows(payload) {
        var rows = Array.isArray(payload && payload.event_table) ? payload.event_table : [];
        return rows.filter(isAvailableEventRow);
    }

    function appendSvg(parent, tagName, attrs) {
        var node = document.createElementNS(SVG_NS, tagName);
        var key;
        if (attrs) {
            for (key in attrs) {
                if (Object.prototype.hasOwnProperty.call(attrs, key) && attrs[key] !== undefined && attrs[key] !== null) {
                    node.setAttribute(key, String(attrs[key]));
                }
            }
        }
        parent.appendChild(node);
        return node;
    }

    function GenevaSummaryReportController() {
        this.root = document.querySelector("[data-geneva-summary-root]");
        this.payloadNode = byId("geneva-summary-payload");
        this.datasourceSelect = byId("geneva-summary-datasource");
        this.ariSelect = byId("geneva-summary-ari");
        this.measureSelect = byId("geneva-summary-measure");
        this.noaaNote = document.querySelector("[data-geneva-summary-noaa-note]");
        this.chartNode = document.querySelector("[data-geneva-summary-chart]");
        this.chartEmpty = document.querySelector("[data-geneva-summary-chart-empty]");
        this.paramsBody = document.querySelector("[data-geneva-summary-params-body]");
        this.tableBody = document.querySelector("[data-geneva-summary-event-body]");
        this.eventsEmpty = document.querySelector("[data-geneva-summary-events-empty]");
        this.messages = document.querySelector("[data-geneva-summary-messages]");
        this.warningBox = document.querySelector("[data-geneva-summary-warnings]");
        this.warningBody = document.querySelector("[data-geneva-summary-warnings-body]");
        this.errorBox = document.querySelector("[data-geneva-summary-errors]");
        this.errorBody = document.querySelector("[data-geneva-summary-errors-body]");
        this.payload = null;
        this.selectedStormId = null;
        this.requestOrdinal = 0;
    }

    GenevaSummaryReportController.prototype.init = function init() {
        if (!this.root || !this.payloadNode) {
            return;
        }
        this.bindEvents();
        this.applyPayload(parseJsonNode(this.payloadNode), { focusSelection: false });
        this.ensureUnitizerHydration();
    };

    GenevaSummaryReportController.prototype.ensureUnitizerHydration = function ensureUnitizerHydration() {
        var unitizer = (typeof window !== "undefined" && window.UnitizerClient)
            ? window.UnitizerClient
            : null;
        if (!unitizer || typeof unitizer.ready !== "function") {
            return;
        }
        unitizer.ready()
            .then(function () {
                if (!this.payload) {
                    return;
                }
                this.renderTable(this.payload);
                this.syncSelection(this.payload.selected_storm_id, { focusSelection: false });
            }.bind(this))
            .catch(function (error) {
                console.warn("[GenevaSummaryReport] Unitizer hydration failed.", error);
            });
    };

    GenevaSummaryReportController.prototype.bindEvents = function bindEvents() {
        var controller = this;
        if (this.datasourceSelect) {
            this.datasourceSelect.addEventListener("change", function () {
                controller.refreshFromQuery();
            });
        }
        if (this.ariSelect) {
            this.ariSelect.addEventListener("change", function () {
                controller.refreshFromQuery();
            });
        }
        if (this.measureSelect) {
            this.measureSelect.addEventListener("change", function () {
                controller.refreshFromQuery();
            });
        }
    };

    GenevaSummaryReportController.prototype.refreshFromQuery = function refreshFromQuery() {
        var queryUrl = this.root ? asString(this.root.getAttribute("data-query-url")) : "";
        if (!queryUrl) {
            return;
        }
        var params = this.buildQueryParams();
        var url = queryUrl + (params ? "?" + params : "");
        var currentRequest = this.requestOrdinal + 1;
        this.requestOrdinal = currentRequest;
        this.setMessageState({
            warning: null,
            error: "Loading summary data..."
        });

        fetch(url, {
            method: "GET",
            headers: {
                Accept: "application/json"
            }
        })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("Unable to load Geneva summary payload (" + response.status + ").");
                }
                return response.json();
            })
            .then(function (payload) {
                if (currentRequest !== this.requestOrdinal) {
                    return;
                }
                this.applyPayload(payload, { focusSelection: false });
            }.bind(this))
            .catch(function (error) {
                if (currentRequest !== this.requestOrdinal) {
                    return;
                }
                console.error("[GenevaSummaryReport] Query refresh failed.", error);
                this.setMessageState({
                    warning: null,
                    error: "Failed to refresh Geneva summary data. Check query endpoint availability."
                });
            }.bind(this));
    };

    GenevaSummaryReportController.prototype.buildQueryParams = function buildQueryParams() {
        var search = new URLSearchParams();
        var datasourceValue = this.datasourceSelect ? asString(this.datasourceSelect.value).trim() : "all";
        var ariValue = this.ariSelect ? asString(this.ariSelect.value).trim() : "all";
        var measureValue = this.measureSelect ? asString(this.measureSelect.value).trim() : "peak_discharge";

        if (datasourceValue) {
            search.set("datasource_id", datasourceValue);
        }
        if (ariValue && ariValue !== "all") {
            search.set("ari_years", ariValue);
        }
        if (measureValue) {
            search.set("measure", measureValue);
        }
        if (this.selectedStormId) {
            search.set("selected_storm_id", this.selectedStormId);
        }
        return search.toString();
    };

    GenevaSummaryReportController.prototype.applyPayload = function applyPayload(payload, options) {
        if (!payload || typeof payload !== "object") {
            return;
        }
        if (this.payloadNode) {
            this.payloadNode.textContent = JSON.stringify(payload);
        }

        this.payload = payload;
        this.renderControls(payload);
        this.renderStormParameters(payload);
        this.renderTable(payload);
        this.renderChart(payload);
        this.renderMessages(payload);
        this.syncSelection(payload.selected_storm_id, options || {});
    };

    GenevaSummaryReportController.prototype.renderControls = function renderControls(payload) {
        var filterOptions = payload.filter_options || {};
        var filters = payload.filters || {};
        var datasourceIds = Array.isArray(filterOptions.datasource_ids) ? filterOptions.datasource_ids : ["all"];
        var ariYears = Array.isArray(filterOptions.ari_years) ? filterOptions.ari_years : [];
        var measures = Array.isArray(filterOptions.measures) ? filterOptions.measures : [];
        var datasourceAvailability = filterOptions.datasource_availability || {};
        var selectedAri = "all";

        if (Array.isArray(filters.ari_years) && filters.ari_years.length === 1) {
            selectedAri = asString(filters.ari_years[0]);
        }

        this.replaceSelectOptions(this.datasourceSelect, datasourceIds, filters.datasource_id, datasourceLabel);
        this.replaceSelectOptionsWithAll(this.ariSelect, ariYears, selectedAri, function (value) {
            return "ARI " + String(value) + "-year";
        });
        this.replaceSelectOptions(this.measureSelect, measures, filters.measure, measureLabel);

        if (this.datasourceSelect) {
            var noaaOption = this.datasourceSelect.querySelector('option[value="noaa14_pds"]');
            var noaaAvailable = Boolean(datasourceAvailability.noaa14_pds);
            if (noaaOption) {
                noaaOption.disabled = !noaaAvailable;
            }
            if (this.noaaNote) {
                this.noaaNote.hidden = noaaAvailable;
            }
        }
    };

    GenevaSummaryReportController.prototype.replaceSelectOptions = function replaceSelectOptions(
        select,
        values,
        selected,
        labelFn
    ) {
        if (!select) {
            return;
        }
        var list = Array.isArray(values) ? values : [];
        select.innerHTML = "";
        list.forEach(function (value) {
            var text = asString(value);
            if (!text) {
                return;
            }
            var option = document.createElement("option");
            option.value = text;
            option.textContent = labelFn(text);
            if (asString(selected) === text) {
                option.selected = true;
            }
            select.appendChild(option);
        });
        if (!select.value && select.options.length > 0) {
            select.options[0].selected = true;
        }
    };

    GenevaSummaryReportController.prototype.replaceSelectOptionsWithAll = function replaceSelectOptionsWithAll(
        select,
        values,
        selected,
        labelFn
    ) {
        if (!select) {
            return;
        }
        select.innerHTML = "";
        var allOption = document.createElement("option");
        allOption.value = "all";
        allOption.textContent = "All ARI Years";
        if (asString(selected) === "all" || !asString(selected)) {
            allOption.selected = true;
        }
        select.appendChild(allOption);

        (Array.isArray(values) ? values : []).forEach(function (value) {
            var option = document.createElement("option");
            option.value = asString(value);
            option.textContent = labelFn(value);
            if (asString(selected) === asString(value)) {
                option.selected = true;
            }
            select.appendChild(option);
        });
    };

    GenevaSummaryReportController.prototype.renderStormParameters = function renderStormParameters(payload) {
        if (!this.paramsBody) {
            return;
        }
        this.paramsBody.innerHTML = "";

        var parameters = payload && typeof payload === "object" ? (payload.storm_parameters || {}) : {};
        var rows = [
            {
                label: "Hyetograph time step",
                value: this.formatStormParameterValue("hyetograph_time_step_minutes", parameters.hyetograph_time_step_minutes)
            },
            {
                label: "Storm Shape",
                value: this.formatStormParameterValue("storm_shape", parameters.storm_shape)
            },
            {
                label: "Lambda mode override",
                value: this.formatStormParameterValue("lambda_mode_override", parameters.lambda_mode_override)
            },
            {
                label: "Unit hydrograph override",
                value: this.formatStormParameterValue(
                    "unit_hydrograph_override",
                    parameters.unit_hydrograph_override
                )
            },
            {
                label: "Timing method",
                value: this.formatStormParameterValue("timing_method", parameters.timing_method)
            },
            {
                label: "tc override",
                value: this.formatStormParameterValue("tc_override_hours", parameters.tc_override_hours)
            }
        ];

        rows.forEach(function (entry) {
            var tr = document.createElement("tr");
            var labelCell = document.createElement("th");
            var valueCell = document.createElement("td");
            labelCell.scope = "row";
            labelCell.textContent = entry.label;
            valueCell.textContent = entry.value;
            tr.appendChild(labelCell);
            tr.appendChild(valueCell);
            this.paramsBody.appendChild(tr);
        }.bind(this));
    };

    GenevaSummaryReportController.prototype.formatStormParameterValue = function formatStormParameterValue(
        parameterId,
        rawValue
    ) {
        if (parameterId === "storm_shape") {
            return stormShapeLabel(rawValue);
        }
        if (parameterId === "unit_hydrograph_override") {
            return unitHydrographLabel(rawValue);
        }
        if (parameterId === "timing_method") {
            return timingMethodLabel(rawValue);
        }
        if (parameterId === "hyetograph_time_step_minutes") {
            var timeStep = asNumber(rawValue);
            return timeStep === null ? "\u2014" : formatNumber(timeStep, 2) + " min";
        }
        if (parameterId === "tc_override_hours") {
            var tcHours = asNumber(rawValue);
            return tcHours === null ? "\u2014" : formatNumber(tcHours, 3) + " hr";
        }
        var text = asString(rawValue).trim();
        return text || "\u2014";
    };

    GenevaSummaryReportController.prototype.renderTable = function renderTable(payload) {
        if (!this.tableBody) {
            return;
        }
        this.tableBody.innerHTML = "";
        var rows = displayEventRows(payload);
        if (this.eventsEmpty) {
            this.eventsEmpty.hidden = rows.length > 0;
        }
        if (rows.length > 0) {
            this.appendUnitsRow();
        }

        rows.forEach(function (row) {
            var tr = document.createElement("tr");
            tr.className = "geneva-summary__event-row";
            tr.dataset.stormId = asString(row.storm_id);
            tr.tabIndex = -1;

            this.appendSelectCell(tr, row);
            this.appendTextCell(tr, row.storm_id);
            this.appendTextCell(tr, datasourceLabel(row.datasource_id));
            this.appendNumberCell(tr, row.duration_minutes, 0);
            this.appendNumberCell(tr, row.ari_years, 0);
            this.appendNumberCell(tr, row.depth_mm, 2, "mm");
            this.appendNumberCell(tr, row.intensity_mm_per_hr, 2, "mm/hour");
            this.appendTextCell(tr, row.distribution_type);
            this.appendMetricCell(tr, row.peak_discharge);
            this.appendNumberCell(tr, row.time_to_peak_minutes, 2);
            this.appendMetricCell(tr, row.runoff_volume);
            this.appendMetricCell(tr, row.runoff_depth);
            this.appendNumberCell(tr, row.warning_count, 0);
            this.appendNumberCell(tr, row.error_count, 0);

            tr.addEventListener("click", function (event) {
                var target = event.target;
                if (target && target.closest && target.closest("button, a, input, select, textarea, label")) {
                    return;
                }
                this.syncSelection(row.storm_id, { focusSelection: true });
            }.bind(this));

            tr.addEventListener("keydown", function (event) {
                if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    this.syncSelection(row.storm_id, { focusSelection: true });
                }
            }.bind(this));

            this.tableBody.appendChild(tr);
        }.bind(this));
    };

    GenevaSummaryReportController.prototype.appendUnitsRow = function appendUnitsRow() {
        var tr = document.createElement("tr");
        tr.className = "geneva-summary__units-row";
        tr.setAttribute("data-sort-position", "top");

        this.appendTextCell(tr, "", "wc-text-muted");
        this.appendTextCell(tr, "", "wc-text-muted");
        this.appendTextCell(tr, "", "wc-text-muted");
        this.appendTextCell(tr, "min", "wc-text-right wc-text-muted");
        this.appendTextCell(tr, "years", "wc-text-right wc-text-muted");
        this.appendTextCell(tr, unitizedUnitHtml("mm", "mm"), "wc-text-right wc-text-muted", null, true);
        this.appendTextCell(
            tr,
            unitizedUnitHtml("mm/hour", "mm/hour"),
            "wc-text-right wc-text-muted",
            null,
            true
        );
        this.appendTextCell(tr, "", "wc-text-muted");
        this.appendTextCell(
            tr,
            unitizedUnitHtml("m^3/s", "m^3/s"),
            "wc-text-right wc-text-muted",
            null,
            true
        );
        this.appendTextCell(tr, "min", "wc-text-right wc-text-muted");
        this.appendTextCell(
            tr,
            unitizedUnitHtml("m^3", "m^3"),
            "wc-text-right wc-text-muted",
            null,
            true
        );
        this.appendTextCell(tr, unitizedUnitHtml("mm", "mm"), "wc-text-right wc-text-muted", null, true);
        this.appendTextCell(tr, "", "wc-text-right wc-text-muted");
        this.appendTextCell(tr, "", "wc-text-right wc-text-muted");

        this.tableBody.appendChild(tr);
    };

    GenevaSummaryReportController.prototype.appendSelectCell = function appendSelectCell(tr, row) {
        var td = document.createElement("td");
        var button = document.createElement("button");
        button.type = "button";
        button.className = "pure-button pure-button-link geneva-summary__event-select";
        button.textContent = "Select";
        button.setAttribute("aria-label", "Select storm " + asString(row.storm_id));
        button.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            this.syncSelection(row.storm_id, { focusSelection: true });
        }.bind(this));
        td.appendChild(button);
        tr.appendChild(td);
    };

    GenevaSummaryReportController.prototype.appendTextCell = function appendTextCell(
        tr,
        value,
        className,
        sortKey,
        allowHtml
    ) {
        var td = document.createElement("td");
        if (className) {
            td.className = className;
        }
        if (sortKey !== undefined && sortKey !== null && sortKey !== "") {
            td.setAttribute("sorttable_customkey", asString(sortKey));
        }
        if (allowHtml) {
            td.innerHTML = value === undefined || value === null ? "\u2014" : asString(value);
        } else {
            td.innerHTML = escapeHtml(value === undefined || value === null ? "\u2014" : value);
        }
        tr.appendChild(td);
        return td;
    };

    GenevaSummaryReportController.prototype.appendNumberCell = function appendNumberCell(tr, value, decimals, unitKey) {
        var parsed = asNumber(value);
        var display = unitKey
            ? unitizedValueHtml(value, unitKey, decimals)
            : formatNumber(value, decimals);
        this.appendTextCell(
            tr,
            display,
            "wc-text-right",
            parsed === null ? null : parsed,
            Boolean(unitKey)
        );
    };

    GenevaSummaryReportController.prototype.appendMetricCell = function appendMetricCell(tr, metric) {
        var parsed = metricCellValue(metric);
        var display;
        if (metric && typeof metric === "object") {
            display = unitizedValueHtml(metric.value, metric.unit, 2);
        } else {
            display = metricCellDisplay(metric);
        }
        this.appendTextCell(
            tr,
            display,
            "wc-text-right",
            parsed === null ? null : parsed,
            true
        );
    };

    GenevaSummaryReportController.prototype.renderChart = function renderChart(payload) {
        if (!this.chartNode) {
            return;
        }
        this.chartNode.innerHTML = "";

        var chart = payload.chart || {};
        var series = Array.isArray(chart.series) ? chart.series : [];
        var points = [];

        series.forEach(function (entry, seriesIndex) {
            var rowPoints = Array.isArray(entry.points) ? entry.points : [];
            rowPoints.forEach(function (point) {
                var x = asNumber(point.intensity_mm_per_hr);
                var y = asNumber(point.measure_value);
                if (x === null || y === null) {
                    return;
                }
                points.push({
                    x: x,
                    y: y,
                    storm_id: asString(point.storm_id),
                    marker_label: asString(point.marker_label || durationLabel(point.duration_minutes)),
                    duration_minutes: asNumber(point.duration_minutes),
                    datasource_id: asString(point.datasource_id),
                    ari_years: asNumber(entry.ari_years),
                    seriesIndex: seriesIndex
                });
            });
        });

        if (this.chartEmpty) {
            this.chartEmpty.hidden = points.length > 0;
        }
        if (!points.length) {
            return;
        }

        var margin = { top: 20, right: 24, bottom: 62, left: 76 };
        var plotWidth = CHART_WIDTH - margin.left - margin.right;
        var plotHeight = CHART_HEIGHT - margin.top - margin.bottom;
        var xDomain = this.expandDomain(points.map(function (point) { return point.x; }));
        var yDomain = this.expandDomain(points.map(function (point) { return point.y; }));
        var xScale = function (value) {
            return margin.left + ((value - xDomain.min) / (xDomain.max - xDomain.min)) * plotWidth;
        };
        var yScale = function (value) {
            return margin.top + plotHeight - ((value - yDomain.min) / (yDomain.max - yDomain.min)) * plotHeight;
        };

        var svg = appendSvg(this.chartNode, "svg", {
            class: "geneva-summary__chart-svg",
            viewBox: "0 0 " + CHART_WIDTH + " " + CHART_HEIGHT
        });
        var layer = appendSvg(svg, "g", { class: "geneva-summary__plot-layer" });

        this.renderAxes(layer, margin, plotWidth, plotHeight, xDomain, yDomain, xScale, yScale, payload);
        this.renderSeriesLines(layer, series, xScale, yScale);
        this.renderMarkers(layer, series, xScale, yScale);
    };

    GenevaSummaryReportController.prototype.expandDomain = function expandDomain(values) {
        var min = Math.min.apply(null, values);
        var max = Math.max.apply(null, values);
        if (!Number.isFinite(min) || !Number.isFinite(max)) {
            return { min: 0, max: 1 };
        }
        if (min === max) {
            return { min: min - 1, max: max + 1 };
        }
        var span = max - min;
        var pad = span * 0.05;
        return { min: min - pad, max: max + pad };
    };

    GenevaSummaryReportController.prototype.renderAxes = function renderAxes(
        layer,
        margin,
        plotWidth,
        plotHeight,
        xDomain,
        yDomain,
        xScale,
        yScale,
        payload
    ) {
        var chart = payload.chart || {};
        var measure = payload.filters ? payload.filters.measure : "";
        var xTicks = 5;
        var yTicks = 5;
        var index;
        var xValue;
        var yValue;
        var xPosition;
        var yPosition;

        appendSvg(layer, "line", {
            class: "geneva-summary__axis",
            x1: margin.left,
            y1: margin.top + plotHeight,
            x2: margin.left + plotWidth,
            y2: margin.top + plotHeight
        });
        appendSvg(layer, "line", {
            class: "geneva-summary__axis",
            x1: margin.left,
            y1: margin.top,
            x2: margin.left,
            y2: margin.top + plotHeight
        });

        for (index = 0; index <= xTicks; index += 1) {
            xValue = xDomain.min + (index / xTicks) * (xDomain.max - xDomain.min);
            xPosition = xScale(xValue);
            appendSvg(layer, "line", {
                class: "geneva-summary__grid-line",
                x1: xPosition,
                y1: margin.top,
                x2: xPosition,
                y2: margin.top + plotHeight
            });
            appendSvg(layer, "text", {
                class: "geneva-summary__tick-label",
                x: xPosition,
                y: margin.top + plotHeight + 22,
                "text-anchor": "middle"
            }).textContent = formatNumber(xValue, 1);
        }

        for (index = 0; index <= yTicks; index += 1) {
            yValue = yDomain.min + (index / yTicks) * (yDomain.max - yDomain.min);
            yPosition = yScale(yValue);
            appendSvg(layer, "line", {
                class: "geneva-summary__grid-line",
                x1: margin.left,
                y1: yPosition,
                x2: margin.left + plotWidth,
                y2: yPosition
            });
            appendSvg(layer, "text", {
                class: "geneva-summary__tick-label",
                x: margin.left - 10,
                y: yPosition + 4,
                "text-anchor": "end"
            }).textContent = formatNumber(yValue, 1);
        }

        appendSvg(layer, "text", {
            class: "geneva-summary__axis-label",
            x: margin.left + plotWidth / 2,
            y: margin.top + plotHeight + 48,
            "text-anchor": "middle"
        }).textContent = chart.x_axis === "intensity_mm_per_hr" ? "Intensity (mm/hr)" : "Intensity";

        appendSvg(layer, "text", {
            class: "geneva-summary__axis-label",
            x: margin.left - 58,
            y: margin.top + plotHeight / 2,
            transform: "rotate(-90 " + String(margin.left - 58) + " " + String(margin.top + plotHeight / 2) + ")",
            "text-anchor": "middle"
        }).textContent = measureLabel(measure);
    };

    GenevaSummaryReportController.prototype.renderSeriesLines = function renderSeriesLines(layer, series, xScale, yScale) {
        series.forEach(function (entry, index) {
            var points = Array.isArray(entry.points) ? entry.points.slice() : [];
            points = points
                .map(function (point) {
                    return {
                        x: asNumber(point.intensity_mm_per_hr),
                        y: asNumber(point.measure_value)
                    };
                })
                .filter(function (point) {
                    return point.x !== null && point.y !== null;
                })
                .sort(function (left, right) {
                    return left.x - right.x;
                });

            if (points.length < 2) {
                return;
            }

            var pathData = points
                .map(function (point, pointIndex) {
                    var command = pointIndex === 0 ? "M" : "L";
                    return command + String(xScale(point.x)) + " " + String(yScale(point.y));
                })
                .join(" ");

            var className = SERIES_CLASS_NAMES[index] || "geneva-summary__series-line--fallback";
            appendSvg(layer, "path", {
                class: "geneva-summary__series-line " + className,
                d: pathData
            });
        });
    };

    GenevaSummaryReportController.prototype.renderMarkers = function renderMarkers(layer, series, xScale, yScale) {
        var selectedStormId = this.selectedStormId;
        var controller = this;

        series.forEach(function (entry, index) {
            var className = SERIES_CLASS_NAMES[index] || "geneva-summary__series-line--fallback";
            var markerClass = className.replace("geneva-summary__series-line", "geneva-summary__marker-circle");
            var points = Array.isArray(entry.points) ? entry.points : [];
            points.forEach(function (point) {
                var x = asNumber(point.intensity_mm_per_hr);
                var y = asNumber(point.measure_value);
                var stormId = asString(point.storm_id);
                if (x === null || y === null || !stormId) {
                    return;
                }

                var group = appendSvg(layer, "g", {
                    class: "geneva-summary__marker-group" + (stormId === selectedStormId ? " is-selected" : ""),
                    tabindex: "0",
                    role: "button",
                    "aria-pressed": stormId === selectedStormId ? "true" : "false",
                    transform: "translate(" + String(xScale(x)) + " " + String(yScale(y)) + ")",
                    "data-storm-id": stormId,
                    "aria-label": "Select storm " + stormId + " (" + durationLabel(point.duration_minutes) + ", ARI " + asString(entry.ari_years) + ")"
                });

                appendSvg(group, "circle", {
                    r: "14",
                    class: "geneva-summary__marker-circle " + markerClass
                });
                appendSvg(group, "text", {
                    class: "geneva-summary__marker-label"
                }).textContent = asString(point.marker_label || durationLabel(point.duration_minutes));

                group.addEventListener("click", function () {
                    controller.syncSelection(stormId, { focusSelection: true });
                });
                group.addEventListener("keydown", function (event) {
                    if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        controller.syncSelection(stormId, { focusSelection: true });
                    }
                });
            });
        });
    };

    GenevaSummaryReportController.prototype.renderMessages = function renderMessages(payload) {
        var warnings = Array.isArray(payload.warnings) ? payload.warnings : [];
        var errors = Array.isArray(payload.errors) ? payload.errors : [];
        var warningMessage = warnings.length ? this.summarizeMessageEntries(warnings, "warning") : null;
        var errorMessage = errors.length ? this.summarizeMessageEntries(errors, "error") : null;
        this.setMessageState({
            warning: warningMessage,
            error: errorMessage
        });
    };

    GenevaSummaryReportController.prototype.summarizeMessageEntries = function summarizeMessageEntries(entries, label) {
        if (!entries.length) {
            return null;
        }
        var samples = entries
            .slice(0, 3)
            .map(function (entry) {
                if (entry && typeof entry === "object") {
                    return asString(entry.code || entry.message || JSON.stringify(entry));
                }
                return asString(entry);
            })
            .filter(function (text) { return Boolean(text); });
        var suffix = entries.length > 3 ? " (+ " + String(entries.length - 3) + " more)" : "";
        return String(entries.length) + " " + label + "(s): " + samples.join(", ") + suffix;
    };

    GenevaSummaryReportController.prototype.setMessageState = function setMessageState(state) {
        var warningMessage = state && state.warning ? asString(state.warning) : "";
        var errorMessage = state && state.error ? asString(state.error) : "";

        if (this.warningBox && this.warningBody) {
            this.warningBody.textContent = warningMessage;
            this.warningBox.hidden = !warningMessage;
        }
        if (this.errorBox && this.errorBody) {
            this.errorBody.textContent = errorMessage;
            this.errorBox.hidden = !errorMessage;
        }
        if (this.messages) {
            this.messages.hidden = !warningMessage && !errorMessage;
        }
    };

    GenevaSummaryReportController.prototype.syncSelection = function syncSelection(stormId, options) {
        if (!this.payload) {
            return;
        }
        var rows = displayEventRows(this.payload);
        var normalized = asString(stormId).trim();
        var selected = null;

        if (normalized && rows.some(function (row) { return asString(row.storm_id) === normalized; })) {
            selected = normalized;
        } else {
            rows.some(function (row) {
                if (asString(row.status) === "completed") {
                    selected = asString(row.storm_id);
                    return true;
                }
                return false;
            });
            if (!selected && rows.length) {
                selected = asString(rows[0].storm_id);
            }
        }

        this.selectedStormId = selected || null;
        this.payload.selected_storm_id = this.selectedStormId;
        if (this.payloadNode) {
            this.payloadNode.textContent = JSON.stringify(this.payload);
        }

        this.updateSelectionStyles(options || {});
    };

    GenevaSummaryReportController.prototype.updateSelectionStyles = function updateSelectionStyles(options) {
        var selected = this.selectedStormId;
        var selectedRow = null;
        var rowNodes = this.tableBody ? this.tableBody.querySelectorAll("tr[data-storm-id]") : [];
        var markerNodes = this.chartNode ? this.chartNode.querySelectorAll("[data-storm-id]") : [];

        rowNodes.forEach(function (row) {
            var matches = selected && row.dataset.stormId === selected;
            row.classList.toggle("is-selected", Boolean(matches));
            if (matches) {
                selectedRow = row;
            }
        });

        markerNodes.forEach(function (marker) {
            var matches = selected && marker.getAttribute("data-storm-id") === selected;
            marker.classList.toggle("is-selected", Boolean(matches));
            marker.setAttribute("aria-pressed", matches ? "true" : "false");
        });

        if (options.focusSelection && selectedRow) {
            selectedRow.focus({ preventScroll: true });
            if (typeof selectedRow.scrollIntoView === "function") {
                selectedRow.scrollIntoView({ block: "center", inline: "nearest" });
            }
        }
    };

    function getInstance() {
        if (!instance) {
            instance = new GenevaSummaryReportController();
        }
        return instance;
    }

    document.addEventListener("DOMContentLoaded", function () {
        getInstance().init();
    });

    return {
        getInstance: getInstance
    };
})();

if (typeof window !== "undefined") {
    window.GenevaSummaryReport = GenevaSummaryReport;
}
