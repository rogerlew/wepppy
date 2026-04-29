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
    var CHART_MARGIN = { top: 20, right: 24, bottom: 62, left: 108 };
    var Y_AXIS_LABEL_OFFSET = 92;
    var UNITIZER_EVENT = "unitizer:preferences-changed";
    var UNITIZER_LISTENER_KEY = "__genevaSummaryUnitizerListener";
    var SERIES_CLASS_NAMES = [
        "geneva-summary__series-line--0",
        "geneva-summary__series-line--1",
        "geneva-summary__series-line--2",
        "geneva-summary__series-line--3",
        "geneva-summary__series-line--4"
    ];
    var MAP_MEASURE_IDS = ["runoff_depth", "runoff_volume"];

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

    function mapValueDecimals(measureId) {
        return asString(measureId) === "runoff_volume" ? 1 : 2;
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

    function stripHtml(value) {
        return asString(value).replace(/<[^>]*>/g, "");
    }

    function normalizeUnitLabel(value) {
        return asString(value).trim().replace(/\/hour\b/g, "/hr");
    }

    function resolvePreferredUnitInfo(unitKey) {
        var canonicalUnit = canonicalUnitKey(unitKey);
        var fallback = normalizeUnitLabel(canonicalUnit);
        var info = {
            baseUnit: canonicalUnit,
            activeUnit: canonicalUnit,
            label: fallback
        };

        if (!canonicalUnit) {
            return info;
        }

        var client = getUnitizerClientSync();
        if (!client || typeof client.getPreferencePayload !== "function" || typeof client.getCategory !== "function") {
            return info;
        }

        var preferences = client.getPreferencePayload() || {};
        var categoryKeys = Object.keys(preferences);
        var index;

        for (index = 0; index < categoryKeys.length; index += 1) {
            var categoryKey = categoryKeys[index];
            var category = client.getCategory(categoryKey);
            if (!category || !Array.isArray(category.units)) {
                continue;
            }

            var hasCanonical = category.units.some(function (unit) {
                return unit && unit.key === canonicalUnit;
            });
            if (!hasCanonical) {
                continue;
            }

            var preferredKey = asString(preferences[categoryKey]).trim() || canonicalUnit;
            var preferredUnit = category.units.find(function (unit) {
                return unit && unit.key === preferredKey;
            });
            var preferredLabel = preferredUnit
                ? asString(preferredUnit.label || preferredUnit.htmlLabel || preferredUnit.key)
                : preferredKey;

            info.activeUnit = preferredKey;
            info.label = normalizeUnitLabel(stripHtml(preferredLabel || preferredKey));
            return info;
        }

        return info;
    }

    function convertToPreferredUnit(value, unitInfo) {
        var parsed = asNumber(value);
        if (parsed === null) {
            return null;
        }
        if (!unitInfo || !unitInfo.baseUnit || !unitInfo.activeUnit || unitInfo.baseUnit === unitInfo.activeUnit) {
            return parsed;
        }

        var client = getUnitizerClientSync();
        if (!client || typeof client.convert !== "function") {
            return parsed;
        }

        try {
            return client.convert(parsed, unitInfo.baseUnit, unitInfo.activeUnit);
        } catch (error) {
            console.warn("[GenevaSummaryReport] Unit conversion failed.", error);
            return parsed;
        }
    }

    function measureBaseUnitKey(measure) {
        var map = {
            peak_discharge: "m^3/s",
            runoff_depth: "mm",
            runoff_volume: "m^3"
        };
        return map[asString(measure)] || "";
    }

    function chartXAxisBaseUnitKey(axisId) {
        return asString(axisId) === "intensity_mm_per_hr" ? "mm/hour" : "";
    }

    function labelWithParentheticalUnit(baseLabel, unitInfo) {
        var label = asString(baseLabel).trim();
        if (!label) {
            return "";
        }
        var unitLabel = unitInfo && unitInfo.label ? asString(unitInfo.label).trim() : "";
        if (!unitLabel) {
            return label;
        }
        return label + " (" + unitLabel + ")";
    }

    function metricCellValue(metric) {
        if (!metric || typeof metric !== "object") {
            return null;
        }
        return asNumber(metric.value);
    }

    function normalizeUnitForDisplay(value) {
        return normalizeUnitLabel(asString(value));
    }

    function winterColorFromNormalized(value) {
        var normalized = Math.max(0, Math.min(1, Number(value)));
        if (!Number.isFinite(normalized)) {
            return [0, 0, 0, 0];
        }
        return [
            0,
            Math.round(normalized * 255),
            Math.round(255 - normalized * 127),
            230
        ];
    }

    function normalizeToRange(value, min, max) {
        if (!Number.isFinite(value)) {
            return null;
        }
        if (!Number.isFinite(min) || !Number.isFinite(max)) {
            return null;
        }
        if (max <= min) {
            return 0.5;
        }
        return (value - min) / (max - min);
    }

    function isCompletedEventRow(row) {
        return asString(row && row.status).toLowerCase() === "completed";
    }

    function displayEventRows(payload) {
        var rows = Array.isArray(payload && payload.event_table) ? payload.event_table : [];
        return rows.filter(isCompletedEventRow);
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
        this.mapEventSelect = byId("geneva-summary-map-event");
        this.mapMeasureSelect = byId("geneva-summary-map-measure");
        this.mapCanvas = byId("geneva-summary-map-canvas");
        this.mapStatus = document.querySelector("[data-geneva-summary-map-status]");
        this.mapLegend = document.querySelector("[data-geneva-summary-map-legend]");
        this.mapLegendTitle = document.querySelector("[data-geneva-summary-map-legend-title]");
        this.mapLegendMin = document.querySelector("[data-geneva-summary-map-legend-min]");
        this.mapLegendMax = document.querySelector("[data-geneva-summary-map-legend-max]");
        this.mapEmptyBox = document.querySelector("[data-geneva-summary-map-empty]");
        this.mapEmptyBody = document.querySelector("[data-geneva-summary-map-empty-body]");
        this.mapErrorBox = document.querySelector("[data-geneva-summary-map-error]");
        this.mapErrorBody = document.querySelector("[data-geneva-summary-map-error-body]");
        this.mapRefreshButton = document.querySelector("[data-geneva-summary-map-refresh]");
        this.payload = null;
        this.selectedStormId = null;
        this.requestOrdinal = 0;
        this.mapRequestOrdinal = 0;
        this.mapGeometryPromise = null;
        this.mapFeaturesPayload = null;
        this.mapRowsPayload = null;
        this.deckInstance = null;
        this.lastMapQueryKey = null;
        this.boundUnitizerPreferenceHandler = this.handleUnitizerPreferenceChange.bind(this);
    }

    GenevaSummaryReportController.prototype.init = function init() {
        if (!this.root || !this.payloadNode) {
            return;
        }
        this.bindEvents();
        this.applyPayload(parseJsonNode(this.payloadNode), { focusSelection: false });
        this.bindUnitizerPreferenceEvents();
        this.ensureUnitizerHydration();
    };

    GenevaSummaryReportController.prototype.bindUnitizerPreferenceEvents = function bindUnitizerPreferenceEvents() {
        if (typeof document === "undefined" || !document.addEventListener) {
            return;
        }
        if (document[UNITIZER_LISTENER_KEY]) {
            document.removeEventListener(UNITIZER_EVENT, document[UNITIZER_LISTENER_KEY]);
        }
        document.addEventListener(UNITIZER_EVENT, this.boundUnitizerPreferenceHandler);
        document[UNITIZER_LISTENER_KEY] = this.boundUnitizerPreferenceHandler;
    };

    GenevaSummaryReportController.prototype.handleUnitizerPreferenceChange = function handleUnitizerPreferenceChange() {
        if (!this.payload) {
            return;
        }
        this.renderTable(this.payload);
        this.renderChart(this.payload);
        this.syncSelection(this.payload.selected_storm_id, { focusSelection: false });
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
                this.handleUnitizerPreferenceChange();
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
        if (this.mapEventSelect) {
            this.mapEventSelect.addEventListener("change", function () {
                controller.syncSelection(controller.mapEventSelect.value, { focusSelection: false });
            });
        }
        if (this.mapMeasureSelect) {
            this.mapMeasureSelect.addEventListener("change", function () {
                controller.refreshMapRows({ force: true });
            });
        }
        if (this.mapRefreshButton) {
            this.mapRefreshButton.addEventListener("click", function () {
                controller.refreshMapRows({ force: true });
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
        this.renderMapControls(payload);
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
        var measure = payload && payload.filters ? payload.filters.measure : "";
        var xUnitInfo = resolvePreferredUnitInfo(chartXAxisBaseUnitKey(chart.x_axis));
        var yUnitInfo = resolvePreferredUnitInfo(measureBaseUnitKey(measure));
        var chartSeries = this.buildChartSeries(series, xUnitInfo, yUnitInfo);
        var points = [];

        chartSeries.forEach(function (entry, seriesIndex) {
            var rowPoints = Array.isArray(entry.points) ? entry.points : [];
            rowPoints.forEach(function (point) {
                var x = asNumber(point.x);
                var y = asNumber(point.y);
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

        var margin = CHART_MARGIN;
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

        this.renderAxes(
            layer,
            margin,
            plotWidth,
            plotHeight,
            xDomain,
            yDomain,
            xScale,
            yScale,
            payload,
            xUnitInfo,
            yUnitInfo
        );
        this.renderSeriesLines(layer, chartSeries, xScale, yScale);
        this.renderMarkers(layer, chartSeries, xScale, yScale);
    };

    GenevaSummaryReportController.prototype.buildChartSeries = function buildChartSeries(
        series,
        xUnitInfo,
        yUnitInfo
    ) {
        return (Array.isArray(series) ? series : []).map(function (entry) {
            var rowPoints = Array.isArray(entry.points) ? entry.points : [];
            return {
                series_id: asString(entry.series_id),
                series_label: asString(entry.series_label),
                ari_years: asNumber(entry.ari_years),
                points: rowPoints.map(function (point) {
                    var convertedX = convertToPreferredUnit(point.intensity_mm_per_hr, xUnitInfo);
                    var convertedY = convertToPreferredUnit(point.measure_value, yUnitInfo);
                    return {
                        x: convertedX,
                        y: convertedY,
                        storm_id: asString(point.storm_id),
                        marker_label: asString(point.marker_label || durationLabel(point.duration_minutes)),
                        duration_minutes: asNumber(point.duration_minutes),
                        datasource_id: asString(point.datasource_id)
                    };
                }).filter(function (point) {
                    return point.x !== null && point.y !== null;
                })
            };
        });
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
        payload,
        xUnitInfo,
        yUnitInfo
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
        }).textContent = chart.x_axis === "intensity_mm_per_hr"
            ? labelWithParentheticalUnit("Intensity", xUnitInfo)
            : "Intensity";

        appendSvg(layer, "text", {
            class: "geneva-summary__axis-label",
            x: margin.left - Y_AXIS_LABEL_OFFSET,
            y: margin.top + plotHeight / 2,
            transform: "rotate(-90 " + String(margin.left - Y_AXIS_LABEL_OFFSET) + " " + String(margin.top + plotHeight / 2) + ")",
            "text-anchor": "middle"
        }).textContent = labelWithParentheticalUnit(measureLabel(measure), yUnitInfo);
    };

    GenevaSummaryReportController.prototype.renderSeriesLines = function renderSeriesLines(layer, series, xScale, yScale) {
        series.forEach(function (entry, index) {
            var points = Array.isArray(entry.points) ? entry.points.slice() : [];
            points = points
                .map(function (point) {
                    return {
                        x: asNumber(point.x),
                        y: asNumber(point.y)
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
                var x = asNumber(point.x);
                var y = asNumber(point.y);
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
        this.updateMapEventSelection();
        this.refreshMapRows();
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

    GenevaSummaryReportController.prototype.renderMapControls = function renderMapControls(payload) {
        if (!this.mapEventSelect && !this.mapMeasureSelect) {
            return;
        }

        if (this.mapMeasureSelect) {
            var selectedMeasure = asString(this.mapMeasureSelect.value).trim();
            if (MAP_MEASURE_IDS.indexOf(selectedMeasure) === -1) {
                selectedMeasure = asString(payload && payload.filters ? payload.filters.measure : "").trim();
                if (MAP_MEASURE_IDS.indexOf(selectedMeasure) === -1) {
                    selectedMeasure = MAP_MEASURE_IDS[0];
                }
            }
            this.replaceSelectOptions(this.mapMeasureSelect, MAP_MEASURE_IDS, selectedMeasure, measureLabel);
        }

        if (this.mapEventSelect) {
            var rows = displayEventRows(payload);
            var stormIds = [];
            var labelByStorm = {};
            rows.forEach(function (row) {
                var stormId = asString(row.storm_id).trim();
                if (!stormId) {
                    return;
                }
                stormIds.push(stormId);
                labelByStorm[stormId] = stormId
                    + " | " + datasourceLabel(row.datasource_id)
                    + " | " + durationLabel(row.duration_minutes)
                    + " | ARI " + asString(row.ari_years);
            });

            this.replaceSelectOptions(
                this.mapEventSelect,
                stormIds,
                this.selectedStormId,
                function (stormId) { return labelByStorm[stormId] || stormId; }
            );

            if (!this.mapEventSelect.options.length) {
                var option = document.createElement("option");
                option.value = "";
                option.textContent = "No completed events available";
                option.disabled = true;
                option.selected = true;
                this.mapEventSelect.appendChild(option);
            }
        }

        this.updateMapEventSelection();
    };

    GenevaSummaryReportController.prototype.updateMapEventSelection = function updateMapEventSelection() {
        if (!this.mapEventSelect) {
            return;
        }
        var selected = asString(this.selectedStormId).trim();
        if (!selected) {
            return;
        }
        var hasOption = Array.from(this.mapEventSelect.options || []).some(function (option) {
            return asString(option.value) === selected;
        });
        if (hasOption) {
            this.mapEventSelect.value = selected;
        }
    };

    GenevaSummaryReportController.prototype.currentMapMeasureId = function currentMapMeasureId() {
        var selected = this.mapMeasureSelect ? asString(this.mapMeasureSelect.value).trim() : "";
        return MAP_MEASURE_IDS.indexOf(selected) >= 0 ? selected : MAP_MEASURE_IDS[0];
    };

    GenevaSummaryReportController.prototype.currentMapStormId = function currentMapStormId() {
        if (this.selectedStormId) {
            return asString(this.selectedStormId).trim();
        }
        if (this.mapEventSelect) {
            return asString(this.mapEventSelect.value).trim();
        }
        return "";
    };

    GenevaSummaryReportController.prototype.mapFeaturesUrl = function mapFeaturesUrl() {
        return this.root ? asString(this.root.getAttribute("data-map-features-url")).trim() : "";
    };

    GenevaSummaryReportController.prototype.mapRowsUrl = function mapRowsUrl() {
        return this.root ? asString(this.root.getAttribute("data-map-rows-url")).trim() : "";
    };

    GenevaSummaryReportController.prototype.setMapStatus = function setMapStatus(message) {
        if (!this.mapStatus) {
            return;
        }
        this.mapStatus.textContent = asString(message || "");
    };

    GenevaSummaryReportController.prototype.setMapEmptyState = function setMapEmptyState(message) {
        if (this.mapEmptyBox && this.mapEmptyBody) {
            this.mapEmptyBody.textContent = asString(message || "");
            this.mapEmptyBox.hidden = !message;
        }
    };

    GenevaSummaryReportController.prototype.setMapErrorState = function setMapErrorState(message) {
        if (this.mapErrorBox && this.mapErrorBody) {
            this.mapErrorBody.textContent = asString(message || "");
            this.mapErrorBox.hidden = !message;
        }
    };

    GenevaSummaryReportController.prototype.setMapLegend = function setMapLegend(details) {
        if (!this.mapLegend || !this.mapLegendTitle || !this.mapLegendMin || !this.mapLegendMax) {
            return;
        }
        if (!details) {
            this.mapLegend.hidden = true;
            return;
        }
        this.mapLegend.hidden = false;
        this.mapLegendTitle.textContent = details.title;
        this.mapLegendMin.textContent = details.minLabel;
        this.mapLegendMax.textContent = details.maxLabel;
    };

    GenevaSummaryReportController.prototype.fetchJson = function fetchJson(url, options) {
        var opts = options || {};
        var method = opts.method || "GET";
        var body = opts.body;
        var headers = {
            Accept: "application/json"
        };
        if (body !== undefined && body !== null) {
            headers["Content-Type"] = "application/json";
        }

        return fetch(url, {
            method: method,
            headers: headers,
            body: body !== undefined && body !== null ? JSON.stringify(body) : undefined
        }).then(function (response) {
            return response.json()
                .catch(function () { return {}; })
                .then(function (payload) {
                    if (!response.ok) {
                        var serverMessage = payload
                            && payload.error
                            && asString(payload.error.message).trim();
                        var message = serverMessage || ("Request failed (" + String(response.status) + ").");
                        var error = new Error(message);
                        error.payload = payload;
                        throw error;
                    }
                    return payload;
                });
        });
    };

    GenevaSummaryReportController.prototype.ensureMapGeometryLoaded = function ensureMapGeometryLoaded() {
        if (!this.mapCanvas) {
            return Promise.resolve(null);
        }
        if (this.mapFeaturesPayload) {
            return Promise.resolve(this.mapFeaturesPayload);
        }
        if (this.mapGeometryPromise) {
            return this.mapGeometryPromise;
        }

        var url = this.mapFeaturesUrl();
        if (!url) {
            return Promise.resolve(null);
        }

        this.mapGeometryPromise = this.fetchJson(url, {
            method: "POST",
            body: { schema_version: 1 }
        }).then(function (payload) {
            this.mapFeaturesPayload = payload;
            return payload;
        }.bind(this)).catch(function (error) {
            this.mapGeometryPromise = null;
            throw error;
        }.bind(this));

        return this.mapGeometryPromise;
    };

    GenevaSummaryReportController.prototype.refreshMapRows = function refreshMapRows(options) {
        if (!this.mapCanvas || !this.payload) {
            return;
        }

        var stormId = this.currentMapStormId();
        var measureId = this.currentMapMeasureId();
        if (!stormId) {
            this.clearMapLayer();
            this.setMapLegend(null);
            this.setMapEmptyState("Select a completed storm event to render HRU values.");
            this.setMapErrorState(null);
            this.setMapStatus("No event selected.");
            return;
        }

        var queryKey = stormId + "|" + measureId;
        var force = Boolean(options && options.force);
        if (!force && this.lastMapQueryKey === queryKey) {
            return;
        }
        this.lastMapQueryKey = queryKey;

        var rowsUrl = this.mapRowsUrl();
        if (!rowsUrl) {
            this.setMapErrorState("HRU map rows endpoint is not configured for this report.");
            this.setMapStatus("Map rows endpoint unavailable.");
            return;
        }

        var requestId = this.mapRequestOrdinal + 1;
        this.mapRequestOrdinal = requestId;
        this.setMapEmptyState(null);
        this.setMapErrorState(null);
        this.setMapStatus("Loading HRU map values...");

        Promise.all([
            this.ensureMapGeometryLoaded(),
            this.fetchJson(rowsUrl, {
                method: "POST",
                body: {
                    schema_version: 1,
                    storm_id: stormId,
                    measure_id: measureId,
                    include_schema: false
                }
            })
        ]).then(function (results) {
            if (requestId !== this.mapRequestOrdinal) {
                return;
            }
            var geometryPayload = results[0];
            var rowsPayload = results[1];
            this.mapRowsPayload = rowsPayload;
            this.renderMapLayer(geometryPayload, rowsPayload, stormId, measureId);
        }.bind(this)).catch(function (error) {
            if (requestId !== this.mapRequestOrdinal) {
                return;
            }
            console.error("[GenevaSummaryReport] Map rows refresh failed.", error);
            this.clearMapLayer();
            this.setMapLegend(null);
            this.setMapEmptyState(null);
            this.setMapErrorState(asString(error.message || "Unable to load HRU map data."));
            this.setMapStatus("Failed to load HRU map values.");
        }.bind(this));
    };

    GenevaSummaryReportController.prototype.renderMapLayer = function renderMapLayer(
        geometryPayload,
        rowsPayload,
        stormId,
        measureId
    ) {
        var geometryAvailability = geometryPayload && geometryPayload.availability
            ? geometryPayload.availability
            : {};
        if (asString(geometryAvailability.status) !== "available") {
            this.clearMapLayer();
            this.setMapLegend(null);
            this.setMapErrorState(null);
            this.setMapEmptyState("HRU map geometry is unavailable for this run.");
            this.setMapStatus("HRU map geometry unavailable.");
            return;
        }

        var rowsAvailability = rowsPayload && rowsPayload.availability ? rowsPayload.availability : {};
        if (asString(rowsAvailability.status) !== "available") {
            var reasonCode = asString(rowsAvailability.reason_code);
            this.clearMapLayer();
            this.setMapLegend(null);
            this.setMapErrorState(null);
            this.setMapEmptyState(
                reasonCode === "legacy_hru_event_measures_missing"
                    ? "This run does not include Geneva HRU event-measure rows (legacy artifact missing)."
                    : "HRU map rows are unavailable for the selected event."
            );
            this.setMapStatus("HRU map rows unavailable for " + stormId + ".");
            return;
        }

        var featureCollection = geometryPayload.feature_collection || {};
        var baseFeatures = Array.isArray(featureCollection.features) ? featureCollection.features : [];
        if (!baseFeatures.length) {
            this.clearMapLayer();
            this.setMapLegend(null);
            this.setMapErrorState(null);
            this.setMapEmptyState("No HRU map polygons were returned for this run.");
            this.setMapStatus("No HRU map polygons available.");
            return;
        }

        var records = Array.isArray(rowsPayload.records) ? rowsPayload.records : [];
        if (!records.length) {
            this.clearMapLayer();
            this.setMapLegend(null);
            this.setMapErrorState(null);
            this.setMapEmptyState(
                "No HRU values were returned for storm "
                + stormId
                + " with "
                + measureLabel(measureId)
                + "."
            );
            this.setMapStatus("No HRU values for selected event.");
            return;
        }

        var valueByHruValue = new Map();
        var unitLabel = "";
        records.forEach(function (record) {
            var hruValue = asNumber(record.hru_value);
            var value = asNumber(record.value);
            if (hruValue === null || value === null) {
                return;
            }
            unitLabel = unitLabel || asString(record.unit);
            valueByHruValue.set(String(Math.trunc(hruValue)), value);
        });

        var joinedFeatures = baseFeatures.map(function (feature) {
            var props = feature && feature.properties ? Object.assign({}, feature.properties) : {};
            var hruValue = asNumber(props.hru_value);
            var lookupKey = hruValue === null ? "" : String(Math.trunc(hruValue));
            var value = valueByHruValue.has(lookupKey) ? valueByHruValue.get(lookupKey) : null;
            props.geneva_value = Number.isFinite(value) ? value : null;
            props.geneva_measure_id = measureId;
            props.geneva_unit = unitLabel;
            return {
                type: "Feature",
                properties: props,
                geometry: feature.geometry
            };
        });

        var populatedValues = joinedFeatures
            .map(function (feature) { return asNumber(feature.properties.geneva_value); })
            .filter(function (value) { return value !== null; });
        if (!populatedValues.length) {
            this.clearMapLayer();
            this.setMapLegend(null);
            this.setMapErrorState(null);
            this.setMapEmptyState("No HRU polygons matched the returned value rows for this event.");
            this.setMapStatus("No HRU polygon/value matches for selected event.");
            return;
        }

        var range = this.computeMapValueRange(populatedValues);
        var mapCollection = {
            type: "FeatureCollection",
            features: joinedFeatures
        };
        var deck = this.ensureDeckInstance(geometryPayload.bounds_wgs84 || featureCollection.bbox || null);
        if (!deck || !window.deck || typeof window.deck.GeoJsonLayer !== "function") {
            this.setMapErrorState("Deck.gl is unavailable; map layer could not be rendered.");
            this.setMapStatus("Deck.gl unavailable.");
            return;
        }

        var layer = new window.deck.GeoJsonLayer({
            id: "geneva-summary-hru-choropleth",
            data: mapCollection,
            pickable: true,
            stroked: true,
            filled: true,
            lineWidthMinPixels: 0.7,
            getLineColor: [25, 39, 52, 180],
            getFillColor: function (feature) {
                var value = asNumber(feature && feature.properties ? feature.properties.geneva_value : null);
                if (value === null) {
                    return [0, 0, 0, 0];
                }
                var normalized = normalizeToRange(value, range.min, range.max);
                return winterColorFromNormalized(normalized);
            },
            autoHighlight: true,
            highlightColor: [255, 255, 255, 96]
        });

        deck.setProps({ layers: [layer] });
        this.fitDeckToBounds(geometryPayload.bounds_wgs84 || featureCollection.bbox || null);
        this.setMapErrorState(null);
        this.setMapEmptyState(null);
        this.setMapStatus(
            "Rendered "
            + String(populatedValues.length)
            + " HRU value(s) for "
            + stormId
            + " ("
            + measureLabel(measureId)
            + ")."
        );

        this.setMapLegend({
            title: measureLabel(measureId) + (unitLabel ? " (" + normalizeUnitForDisplay(unitLabel) + ")" : ""),
            minLabel: formatNumber(range.min, mapValueDecimals(measureId)),
            maxLabel: formatNumber(range.max, mapValueDecimals(measureId))
        });
    };

    GenevaSummaryReportController.prototype.ensureDeckInstance = function ensureDeckInstance(bounds) {
        if (this.deckInstance) {
            if (bounds) {
                this.fitDeckToBounds(bounds);
            }
            return this.deckInstance;
        }
        if (!this.mapCanvas || !window.deck || typeof window.deck.Deck !== "function") {
            return null;
        }

        var props = {
            parent: this.mapCanvas,
            controller: true,
            layers: [],
            initialViewState: {
                longitude: 0,
                latitude: 0,
                zoom: 2,
                pitch: 0,
                bearing: 0
            },
            getTooltip: this.buildMapTooltip.bind(this)
        };
        if (typeof window.deck.MapView === "function") {
            props.views = new window.deck.MapView({ repeat: false });
        }
        this.deckInstance = new window.deck.Deck(props);
        this._mapBoundsFitted = false;
        if (bounds) {
            this.fitDeckToBounds(bounds);
        }
        return this.deckInstance;
    };

    GenevaSummaryReportController.prototype.clearMapLayer = function clearMapLayer() {
        if (this.deckInstance && typeof this.deckInstance.setProps === "function") {
            this.deckInstance.setProps({ layers: [] });
        }
    };

    GenevaSummaryReportController.prototype.fitDeckToBounds = function fitDeckToBounds(bounds) {
        if (!this.deckInstance || !window.deck || typeof window.deck.WebMercatorViewport !== "function") {
            return;
        }
        if (!Array.isArray(bounds) || bounds.length !== 4) {
            return;
        }
        var minX = Number(bounds[0]);
        var minY = Number(bounds[1]);
        var maxX = Number(bounds[2]);
        var maxY = Number(bounds[3]);
        if (!Number.isFinite(minX) || !Number.isFinite(minY) || !Number.isFinite(maxX) || !Number.isFinite(maxY)) {
            return;
        }
        if (maxX <= minX || maxY <= minY) {
            return;
        }
        if (this._mapBoundsFitted) {
            return;
        }

        try {
            var width = Math.max(1, this.mapCanvas ? this.mapCanvas.clientWidth : 640);
            var height = Math.max(1, this.mapCanvas ? this.mapCanvas.clientHeight : 420);
            var viewport = new window.deck.WebMercatorViewport({
                width: width,
                height: height
            });
            var viewState = viewport.fitBounds(
                [ [minX, minY], [maxX, maxY] ],
                { padding: 28 }
            );
            viewState.pitch = 0;
            viewState.bearing = 0;
            this.deckInstance.setProps({
                initialViewState: viewState
            });
            this._mapBoundsFitted = true;
        } catch (error) {
            console.warn("[GenevaSummaryReport] Failed to fit map bounds.", error);
        }
    };

    GenevaSummaryReportController.prototype.buildMapTooltip = function buildMapTooltip(context) {
        var feature = context && context.object;
        if (!feature || !feature.properties) {
            return null;
        }
        var props = feature.properties;
        var value = asNumber(props.geneva_value);
        if (value === null) {
            return {
                text: "HRU " + asString(props.hru_id || props.hru_value || "") + "\nNo value for selected event."
            };
        }
        var measureId = asString(props.geneva_measure_id).trim();
        var unitLabel = normalizeUnitForDisplay(props.geneva_unit);
        return {
            text:
                "HRU " + asString(props.hru_id || props.hru_value || "")
                + "\n" + measureLabel(measureId)
                + ": " + formatNumber(value, mapValueDecimals(measureId))
                + (unitLabel ? " " + unitLabel : "")
        };
    };

    GenevaSummaryReportController.prototype.computeMapValueRange = function computeMapValueRange(values) {
        var min = Math.min.apply(null, values);
        var max = Math.max.apply(null, values);
        if (!Number.isFinite(min) || !Number.isFinite(max)) {
            return { min: 0, max: 1 };
        }
        return { min: min, max: max };
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
