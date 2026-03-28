/* ----------------------------------------------------------------------------
 * Features Export
 * ----------------------------------------------------------------------------
 */
var FeaturesExport = (function () {
    "use strict";

    var instance;

    var FORM_ID = "features_export_form";
    var STATUS_CHANNEL = "features_export";
    var COMPLETION_EVENT = "FEATURES_EXPORT_TASK_COMPLETED";

    var SELECTORS = {
        form: "#" + FORM_ID,
        config: "[data-features-export-config]",
        catalogScript: "#features_export_catalog_data",
        bootstrapScript: "#features_export_bootstrap_data",
        message: "#features_export_message",
        stacktrace: "#features_export_stacktrace",
        stacktracePanel: "#features_export_stacktrace_panel",
        rqJob: "#features_export_rq_job",
        hint: "#hint_run_features_export",
        statusPanel: "#features_export_status_panel",
        statusLog: "#features_export_status_log",
        statusSpinner: "#features_export_braille",
        submitButton: "#btn_run_features_export",
        resultState: "#features_export_result_state",
        resultsPanel: "#features_export_results_panel",
        catalogList: "#features_export_catalog_list",
        swatTables: "#features_export_swat_tables"
    };

    var GROUPS = ["settings", "summary", "catalog", "scopes", "temporal", "omni", "swat", "actions"];

    var ACTIONS = {
        toggleLayer: '[data-features-export-action="toggle-layer"]',
        loadDefaults: '[data-features-export-action="load-defaults"]',
        clearSelection: '[data-features-export-action="clear-selection"]',
        toggleSwatTable: '[data-features-export-action="toggle-swat-table"]',
        toggleColumn: '[data-features-export-action="toggle-column"]',
        omniSelectAll: '[data-features-export-action="omni-select-all"]',
        omniUnselectAll: '[data-features-export-action="omni-unselect-all"]'
    };

    var FIELDS = {
        format: '[data-features-export-field="format"]',
        units: '[data-features-export-field="units"]',
        crs: '[data-features-export-field="crs"]',
        outputScope: '[data-features-export-field="output-scope"]',
        temporalMode: '[data-features-export-field="layer-temporal-mode"]',
        temporalYearSelection: '[data-features-export-field="temporal-year-selection"]',
        temporalExcludeIndices: '[data-features-export-field="temporal-exclude-year-indices"]',
        temporalEventSelector: '[data-features-export-field="temporal-event-selector"]',
        temporalEventDates: '[data-features-export-field="temporal-event-dates"]',
        temporalEventReturnPeriods: '[data-features-export-field="temporal-event-return-periods"]',
        scenario: '[data-features-export-field="scenario"]',
        contrastId: '[data-features-export-field="contrast-id"]',
        swatRunId: '[data-features-export-field="swat-run-id"]',
        swatTableMode: '[data-features-export-field="swat-table-mode"]'
    };

    var FILTER_SELECTOR = "[data-features-export-filter]";

    var EVENT_NAMES = [
        "features_export:catalog:loaded",
        "features_export:selection:changed",
        "features_export:validation:changed",
        "features_export:defaults:loaded",
        "features_export:scope:changed",
        "features_export:temporal:changed",
        "features_export:omni:changed",
        "features_export:swat:changed",
        "features_export:submit:started",
        "features_export:submit:queued",
        "features_export:jobinfo:loaded",
        "features_export:completed",
        "features_export:error",
        "job:started",
        "job:completed",
        "job:error"
    ];

    var DEFAULT_PROFILE_KEY = "gpkg_adjacent";
    var DEFAULT_FAMILY_ORDER = [
        "watershed",
        "landuse",
        "soils",
        "wepp_summary",
        "wepp_temporal",
        "wepp_interchange",
        "ash_watar",
        "omni_scenarios",
        "omni_contrasts",
        "swat_interchange",
        "agfields_spatial",
        "agfields_metrics"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.qs !== "function" || typeof dom.delegate !== "function" || typeof dom.show !== "function" || typeof dom.hide !== "function") {
            throw new Error("FeaturesExport controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("FeaturesExport controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function" || typeof http.postJsonWithSessionToken !== "function") {
            throw new Error("FeaturesExport controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("FeaturesExport controller requires WCEvents helpers.");
        }

        return { dom: dom, forms: forms, http: http, events: events };
    }

    function createLegacyAdapter(element) {
        if (!element) {
            return {
                element: element,
                length: 0,
                show: function () {},
                hide: function () {},
                text: function () {},
                html: function () {},
                append: function () {},
                empty: function () {}
            };
        }

        return {
            element: element,
            length: 1,
            show: function () {
                element.hidden = false;
                if (element.style && element.style.display === "none") {
                    element.style.removeProperty("display");
                }
            },
            hide: function () {
                element.hidden = true;
                if (element.style) {
                    element.style.display = "none";
                }
            },
            text: function (value) {
                if (value === undefined) {
                    return element.textContent;
                }
                element.textContent = value === null ? "" : String(value);
            },
            html: function (value) {
                if (value === undefined) {
                    return element.innerHTML;
                }
                element.innerHTML = value === null ? "" : String(value);
            },
            append: function (content) {
                if (content === null || content === undefined) {
                    return;
                }
                if (typeof content === "string") {
                    element.insertAdjacentHTML("beforeend", content);
                    return;
                }
                if (content instanceof window.Node) {
                    element.appendChild(content);
                }
            },
            empty: function () {
                element.textContent = "";
            }
        };
    }

    function toResponsePayload(http, error) {
        function coerceBody(raw) {
            if (!raw) {
                return null;
            }
            if (typeof raw === "string") {
                try {
                    return JSON.parse(raw);
                } catch (err) {
                    return raw;
                }
            }
            return raw;
        }

        var body = coerceBody(error && error.body ? error.body : null);

        if (body && typeof body === "object") {
            if (body.error || body.errors) {
                return body;
            }
            if (body.message || body.detail) {
                return { error: { message: body.message || body.detail, details: body.details } };
            }
            return body;
        }

        if (typeof body === "string" && body) {
            return { error: { message: body } };
        }

        if (http && typeof http.isHttpError === "function" && http.isHttpError(error)) {
            var detail = error && (error.detail || error.message);
            if (detail && typeof detail === "object" && (detail.error || detail.errors)) {
                return detail;
            }
            return { error: { message: detail || "Request failed" } };
        }

        return { error: { message: (error && error.message) || "Request failed" } };
    }

    function unwrapResponseBody(response) {
        var body = response && response.body !== undefined ? response.body : response;
        if (body && typeof body === "object" && !Array.isArray(body)) {
            if (!body.error && !body.errors && body.Content && typeof body.Content === "object") {
                return body.Content;
            }
        }
        return body;
    }

    function extractJobId(payload, preferredJobKey) {
        if (!payload || typeof payload !== "object") {
            return null;
        }

        var rawJobId = null;
        if (Object.prototype.hasOwnProperty.call(payload, "job_id")) {
            rawJobId = payload.job_id;
        }
        if ((rawJobId === null || rawJobId === undefined || String(rawJobId).trim() === "") &&
            payload.status &&
            typeof payload.status === "object" &&
            Object.prototype.hasOwnProperty.call(payload.status, "job_id")) {
            rawJobId = payload.status.job_id;
        }
        if ((rawJobId === null || rawJobId === undefined || String(rawJobId).trim() === "") &&
            Array.isArray(payload.job_ids) &&
            payload.job_ids.length > 0) {
            rawJobId = payload.job_ids[0];
        }
        if ((rawJobId === null || rawJobId === undefined || String(rawJobId).trim() === "") &&
            payload.job_ids &&
            typeof payload.job_ids === "object") {
            if (preferredJobKey && Object.prototype.hasOwnProperty.call(payload.job_ids, preferredJobKey)) {
                rawJobId = payload.job_ids[preferredJobKey];
            } else {
                var keyedJobIds = Object.keys(payload.job_ids);
                if (keyedJobIds.length > 0) {
                    rawJobId = payload.job_ids[keyedJobIds[0]];
                }
            }
        }
        if ((rawJobId === null || rawJobId === undefined || String(rawJobId).trim() === "") &&
            payload.Content &&
            typeof payload.Content === "object") {
            return extractJobId(payload.Content, preferredJobKey);
        }

        if (rawJobId === null || rawJobId === undefined) {
            return null;
        }
        var normalized = String(rawJobId).trim();
        return normalized || null;
    }

    function normalizeArray(value) {
        if (!Array.isArray(value)) {
            return [];
        }
        return value.slice();
    }

    function uniqueStrings(values) {
        var seen = new Set();
        var out = [];
        normalizeArray(values).forEach(function (value) {
            if (value === undefined || value === null) {
                return;
            }
            var token = String(value).trim();
            if (!token || seen.has(token)) {
                return;
            }
            seen.add(token);
            out.push(token);
        });
        return out;
    }

    function columnMatchKey(value) {
        if (value === undefined || value === null) {
            return "";
        }
        return String(value).trim().toLowerCase().replace(/[^a-z0-9]+/g, "");
    }

    function labelsMatchColumnId(label, columnId) {
        var labelKey = columnMatchKey(label);
        var idKey = columnMatchKey(columnId);
        return Boolean(labelKey && idKey && labelKey === idKey);
    }

    function parseJsonScript(node, fallback) {
        if (!node) {
            return fallback;
        }
        var raw = "";
        if (typeof node.textContent === "string") {
            raw = node.textContent;
        } else if (typeof node.value === "string") {
            raw = node.value;
        }
        var trimmed = raw.trim();
        if (!trimmed) {
            return fallback;
        }
        try {
            return JSON.parse(trimmed);
        } catch (err) {
            console.warn("[FeaturesExport] Unable to parse JSON script payload", err);
            return fallback;
        }
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function applySitePrefixToRunsUrl(rawUrl) {
        var url = rawUrl === undefined || rawUrl === null ? "" : String(rawUrl).trim();
        if (!url || url.indexOf("/runs/") !== 0) {
            return url;
        }
        var prefix = typeof window.site_prefix === "string" ? window.site_prefix : "";
        var normalizedPrefix = prefix.replace(/\/+$/, "");
        if (!normalizedPrefix) {
            return url;
        }
        if (url.indexOf(normalizedPrefix + "/") === 0) {
            return url;
        }
        return normalizedPrefix + url;
    }

    function normalizeFormat(formatValue) {
        if (!formatValue) {
            return "";
        }
        var token = String(formatValue).trim().toLowerCase();
        if (token === "f_esri") {
            return "geodatabase";
        }
        return token;
    }

    function parseCommaList(value) {
        if (value === undefined || value === null) {
            return [];
        }
        if (Array.isArray(value)) {
            return uniqueStrings(value);
        }
        return uniqueStrings(String(value).split(/[\n,;\s]+/));
    }

    function parseIntList(value) {
        var rawValues = parseCommaList(value);
        var seen = new Set();
        var out = [];
        rawValues.forEach(function (entry) {
            var parsed = parseInt(entry, 10);
            if (Number.isNaN(parsed)) {
                return;
            }
            if (seen.has(parsed)) {
                return;
            }
            seen.add(parsed);
            out.push(parsed);
        });
        return out;
    }

    function parseFloatList(value) {
        var rawValues = parseCommaList(value);
        var seen = new Set();
        var out = [];
        rawValues.forEach(function (entry) {
            var parsed = Number(entry);
            if (!Number.isFinite(parsed)) {
                return;
            }
            if (seen.has(parsed)) {
                return;
            }
            seen.add(parsed);
            out.push(parsed);
        });
        return out;
    }

    function buildFamilyLabel(rawFamily) {
        if (!rawFamily) {
            return "Unknown";
        }
        var tokens = String(rawFamily).split("_").filter(function (token) {
            return token;
        });
        if (!tokens.length) {
            return String(rawFamily);
        }
        return tokens.map(function (token) {
            return token.charAt(0).toUpperCase() + token.slice(1);
        }).join(" ");
    }

    function createInstance() {
        if (typeof controlBase !== "function") {
            throw new Error("FeaturesExport controller requires controlBase helper.");
        }

        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var eventsApi = helpers.events;

        var base = controlBase();
        var emitter = null;
        if (eventsApi && typeof eventsApi.createEmitter === "function") {
            var baseEmitter = eventsApi.createEmitter();
            emitter = typeof eventsApi.useEventMap === "function"
                ? eventsApi.useEventMap(EVENT_NAMES, baseEmitter)
                : baseEmitter;
        }

        var controller = Object.assign(base, {
            dom: dom,
            forms: forms,
            http: http,
            events: emitter,
            form: null,
            configNode: null,
            catalogNode: null,
            bootstrapNode: null,
            hint: createLegacyAdapter(null),
            status: createLegacyAdapter(null),
            stacktrace: createLegacyAdapter(null),
            rq_job: createLegacyAdapter(null),
            statusPanelEl: null,
            statusLogEl: null,
            stacktracePanelEl: null,
            statusSpinnerEl: null,
            resultStateEl: null,
            resultsPanelEl: null,
            downloadRegionEl: null,
            artifactMetaRegionEl: null,
            warningsRegionEl: null,
            catalogListEl: null,
            swatTablesEl: null,
            submitButtonEl: null,
            groups: {},
            command_btn_id: "btn_run_features_export",
            statusStream: null,
            _delegates: [],
            _delegateRoot: null,
            _completion_seen: false,
            _completion_jobinfo_job_id: null,
            _completion_jobinfo_inflight: null,
            _completion_source: null,
            _last_jobinfo_result: null,
            _last_submission_payload: null,
            _defaults_skipped_layers: [],
            state: {
                config: {},
                catalog: {},
                bootstrap: {},
                layers: [],
                layersById: {},
                selectedLayerIds: [],
                selectedSwatTables: [],
                selectedScenarios: [],
                selectedContrasts: [],
                layerTemporalModes: {},
                layerColumnSelection: {},
                discovery: {
                    roads_scope_available: true,
                    available_layer_ids: [],
                    available_families: []
                },
                familyOpen: {},
                validation: {
                    valid: false,
                    errors: [],
                    warnings: []
                }
            }
        });

        function clearDelegates() {
            controller._delegates.forEach(function (unsubscribe) {
                if (typeof unsubscribe === "function") {
                    unsubscribe();
                }
            });
            controller._delegates = [];
            controller._delegateRoot = null;
        }

        function getGroupNode(groupName) {
            if (!controller.form) {
                return null;
            }
            return controller.form.querySelector('[data-features-export-group="' + groupName + '"]');
        }

        function queryAllWithinForm(selector) {
            if (!controller.form) {
                return [];
            }
            try {
                var nodes = controller.form.querySelectorAll(selector);
                return Array.prototype.slice.call(nodes || []);
            } catch (err) {
                return [];
            }
        }

        function getFieldNode(selector) {
            if (!controller.form) {
                return null;
            }
            try {
                return controller.form.querySelector(selector);
            } catch (err) {
                return null;
            }
        }

        function readFieldValue(selector) {
            var node = getFieldNode(selector);
            if (!node) {
                return "";
            }
            if (node.type === "checkbox") {
                return node.checked;
            }
            return node.value === undefined || node.value === null ? "" : String(node.value);
        }

        function readCheckedRadio(selector) {
            var nodes = queryAllWithinForm(selector);
            var checked = nodes.find(function (node) {
                return Boolean(node && node.checked);
            });
            return checked ? String(checked.value || "") : "";
        }

        function setSelectOrInput(selector, value) {
            var node = getFieldNode(selector);
            if (!node) {
                return;
            }
            node.value = value === undefined || value === null ? "" : String(value);
        }

        function setRadioValue(selector, value) {
            var target = value === undefined || value === null ? "" : String(value);
            queryAllWithinForm(selector).forEach(function (node) {
                node.checked = String(node.value || "") === target;
            });
        }

        function setCheckboxValue(selector, checked) {
            queryAllWithinForm(selector).forEach(function (node) {
                node.checked = Boolean(checked);
            });
        }

        function setOutputScopes(scopes) {
            var selected = new Set(uniqueStrings(scopes));
            queryAllWithinForm(FIELDS.outputScope).forEach(function (node) {
                var token = String(node.value || "").trim();
                node.checked = selected.has(token);
            });
        }

        function readOutputScopes() {
            var selected = [];
            queryAllWithinForm(FIELDS.outputScope).forEach(function (node) {
                if (node.checked) {
                    selected.push(String(node.value || "").trim());
                }
            });
            var normalized = [];
            ["baseline", "roads"].forEach(function (scope) {
                if (selected.indexOf(scope) !== -1) {
                    normalized.push(scope);
                }
            });
            return normalized;
        }

        function readSelectedScenarios() {
            return uniqueStrings(
                queryAllWithinForm(FIELDS.scenario)
                    .filter(function (node) {
                        return Boolean(node && node.checked);
                    })
                    .map(function (node) {
                        return String(node.value || "").trim();
                    })
            );
        }

        function readSelectedContrasts() {
            return uniqueStrings(
                queryAllWithinForm(FIELDS.contrastId)
                    .filter(function (node) {
                        return Boolean(node && node.checked);
                    })
                    .map(function (node) {
                        return String(node.value || "").trim();
                    })
            );
        }

        function updateTemporalVisibility() {
            var selected = selectedLayers();
            var modes = selected.map(function (layer) {
                return effectiveLayerTemporalMode(layer);
            }).filter(function (modeToken) {
                return Boolean(modeToken);
            });
            var yearWrap = getFieldNode("[data-features-export-temporal-year-options]");
            var customWrap = getFieldNode("[data-features-export-temporal-custom-wrap]");
            var eventWrap = getFieldNode("[data-features-export-temporal-event-options]");
            var datesWrap = getFieldNode("[data-features-export-temporal-dates-wrap]");
            var returnPeriodsWrap = getFieldNode("[data-features-export-temporal-return-periods-wrap]");

            var isYearMode = modes.some(function (modeToken) {
                return modeToken === "annual_average" || modeToken === "yearly";
            });
            if (yearWrap) {
                yearWrap.hidden = !isYearMode;
            }
            if (customWrap) {
                var yearSelection = readFieldValue(FIELDS.temporalYearSelection);
                customWrap.hidden = !isYearMode || yearSelection !== "custom";
            }

            var isEventMode = modes.indexOf("event") !== -1;
            if (eventWrap) {
                eventWrap.hidden = !isEventMode;
            }
            var selector = readCheckedRadio(FIELDS.temporalEventSelector);
            if (datesWrap) {
                datesWrap.hidden = !isEventMode || selector !== "date";
            }
            if (returnPeriodsWrap) {
                returnPeriodsWrap.hidden = !isEventMode || selector !== "return_period";
            }
        }

        function captureFamilyOpenState() {
            if (!controller.catalogListEl) {
                return;
            }
            var nextState = {};
            var families = controller.catalogListEl.querySelectorAll("[data-features-export-family]");
            Array.prototype.forEach.call(families, function (detailsNode) {
                var family = detailsNode.getAttribute("data-family");
                if (!family) {
                    return;
                }
                nextState[family] = Boolean(detailsNode.open);
            });
            controller.state.familyOpen = nextState;
        }

        function familyOrder() {
            var payloadOrder = uniqueStrings(controller.state.catalog && controller.state.catalog.family_order);
            if (payloadOrder.length) {
                return payloadOrder;
            }
            return DEFAULT_FAMILY_ORDER.slice();
        }

        function familyLabel(family) {
            var labels = controller.state.catalog && controller.state.catalog.family_labels;
            if (labels && typeof labels === "object" && labels[family]) {
                return String(labels[family]);
            }
            return buildFamilyLabel(family);
        }

        function selectedLayerSet() {
            return new Set(uniqueStrings(controller.state.selectedLayerIds));
        }

        function hasSelectedLayer(layerId) {
            return selectedLayerSet().has(layerId);
        }

        function getLayerById(layerId) {
            return controller.state.layersById[layerId] || null;
        }

        function addSelectedLayers(layerIds) {
            var next = uniqueStrings(controller.state.selectedLayerIds.concat(layerIds || []));
            controller.state.selectedLayerIds = next;
        }

        function setSelectedLayers(layerIds) {
            controller.state.selectedLayerIds = uniqueStrings(layerIds || []);
        }

        function removeSelectedLayer(layerId) {
            controller.state.selectedLayerIds = uniqueStrings(controller.state.selectedLayerIds).filter(function (entry) {
                return entry !== layerId;
            });
        }

        function clearSelectedLayers() {
            controller.state.selectedLayerIds = [];
            controller.state.layerTemporalModes = {};
            controller.state.layerColumnSelection = {};
        }

        function selectedLayers() {
            var selectedSet = selectedLayerSet();
            return controller.state.layers.filter(function (layer) {
                return selectedSet.has(layer.layer_id);
            });
        }

        function defaultLayerTemporalMode(layer) {
            if (!layer.temporal_modes || !layer.temporal_modes.length) {
                return "";
            }
            if (layer.temporal_modes.indexOf("annual_average") !== -1) {
                return "annual_average";
            }
            return String(layer.temporal_modes[0]);
        }

        function effectiveLayerTemporalMode(layer) {
            var layerModes = controller.state.layerTemporalModes || {};
            if (Object.prototype.hasOwnProperty.call(layerModes, layer.layer_id)) {
                return String(layerModes[layer.layer_id] || "");
            }
            return defaultLayerTemporalMode(layer);
        }

        function defaultColumnsForLayer(layer) {
            var columnIds = (layer.columns || []).map(function (entry) {
                return entry.column_id;
            });
            var required = new Set(uniqueStrings(layer.required_columns || []));
            var defaults = [];
            (layer.columns || []).forEach(function (entry) {
                if (entry.required || entry.default_selected) {
                    defaults.push(entry.column_id);
                }
            });
            var selected = uniqueStrings(defaults);
            if (!selected.length) {
                selected = uniqueStrings(columnIds);
            }
            required.forEach(function (columnId) {
                if (selected.indexOf(columnId) === -1) {
                    selected.push(columnId);
                }
            });
            return selected;
        }

        function effectiveColumnsForLayer(layer) {
            var layerSelection = controller.state.layerColumnSelection || {};
            var selected = layerSelection[layer.layer_id];
            if (Array.isArray(selected) && selected.length) {
                return uniqueStrings(selected);
            }
            return defaultColumnsForLayer(layer);
        }

        function setLayerTemporalMode(layerId, mode) {
            if (!controller.state.layerTemporalModes || typeof controller.state.layerTemporalModes !== "object") {
                controller.state.layerTemporalModes = {};
            }
            controller.state.layerTemporalModes[layerId] = mode;
        }

        function setLayerColumns(layerId, columnIds) {
            if (!controller.state.layerColumnSelection || typeof controller.state.layerColumnSelection !== "object") {
                controller.state.layerColumnSelection = {};
            }
            controller.state.layerColumnSelection[layerId] = uniqueStrings(columnIds);
        }

        function normalizeLayer(rawLayer) {
            if (!rawLayer || typeof rawLayer !== "object") {
                return null;
            }
            var layerId = rawLayer.layer_id ? String(rawLayer.layer_id) : "";
            if (!layerId) {
                return null;
            }
            var family = rawLayer.family ? String(rawLayer.family) : "unknown";
            var temporalModes = uniqueStrings(rawLayer.temporal_modes || []);
            var requirements = uniqueStrings(rawLayer.selector_requirements || []);
            var scopeClass = rawLayer.scope_class ? String(rawLayer.scope_class) : "scope_invariant";
            var geometryType = rawLayer.geometry_type ? String(rawLayer.geometry_type) : "unknown";
            var requiredColumns = uniqueStrings(rawLayer.required_columns || []);
            var columns = normalizeArray(rawLayer.columns).map(function (entry) {
                if (!entry || typeof entry !== "object") {
                    return null;
                }
                var columnId = entry.column_id ? String(entry.column_id) : "";
                if (!columnId) {
                    return null;
                }
                return {
                    column_id: columnId,
                    label: entry.label ? String(entry.label) : columnId,
                    description: entry.description ? String(entry.description) : "",
                    display_unit: entry.display_unit ? String(entry.display_unit) : "non-unitized",
                    required: Boolean(entry.required),
                    default_selected: Boolean(entry.default_selected)
                };
            }).filter(Boolean);
            return {
                layer_id: layerId,
                label: rawLayer.label ? String(rawLayer.label) : layerId,
                family: family,
                family_label: rawLayer.family_label ? String(rawLayer.family_label) : familyLabel(family),
                family_raw: rawLayer.family_raw ? String(rawLayer.family_raw) : family,
                scope_class: scopeClass,
                geometry_type: geometryType,
                temporal_modes: temporalModes,
                selector_requirements: requirements,
                required_columns: requiredColumns,
                columns: columns,
                raw: rawLayer.raw && typeof rawLayer.raw === "object" ? rawLayer.raw : {}
            };
        }

        function parseCatalogPayload() {
            var parsed = parseJsonScript(controller.catalogNode, {});
            if (!parsed || typeof parsed !== "object") {
                parsed = {};
            }
            var layers = [];
            var layerIndex = {};
            normalizeArray(parsed.layers).forEach(function (entry) {
                var normalized = normalizeLayer(entry);
                if (!normalized) {
                    return;
                }
                layers.push(normalized);
                layerIndex[normalized.layer_id] = normalized;
            });
            controller.state.catalog = parsed;
            controller.state.layers = layers;
            controller.state.layersById = layerIndex;
            controller.state.selectedLayerIds = uniqueStrings(controller.state.selectedLayerIds).filter(function (layerId) {
                return Boolean(layerIndex[layerId]);
            });
        }

        function parseBootstrapPayload() {
            var parsed = parseJsonScript(controller.bootstrapNode, {});
            if (!parsed || typeof parsed !== "object") {
                parsed = {};
            }
            controller.state.bootstrap = parsed;
            controller.state.discovery = normalizeDiscoveryPayload(parsed.discovery);
        }

        function normalizeDiscoveryPayload(discovery) {
            var payload = discovery && typeof discovery === "object" ? discovery : {};
            return {
                roads_scope_available: payload.roads_scope_available !== false,
                available_layer_ids: uniqueStrings(payload.available_layer_ids || []),
                available_families: uniqueStrings(payload.available_families || [])
            };
        }

        function discoveryPayloadEqual(a, b) {
            var left = normalizeDiscoveryPayload(a);
            var right = normalizeDiscoveryPayload(b);
            return (
                left.roads_scope_available === right.roads_scope_available
                && JSON.stringify(left.available_layer_ids) === JSON.stringify(right.available_layer_ids)
                && JSON.stringify(left.available_families) === JSON.stringify(right.available_families)
            );
        }

        function parseDiscoveryRefreshPayload(detail) {
            var raw = detail && detail.raw !== undefined
                ? detail.raw
                : detail && detail.detail !== undefined
                    ? detail.detail
                    : detail;
            var candidate = raw;
            if (typeof candidate === "string") {
                var trimmed = candidate.trim();
                if (!trimmed) {
                    return null;
                }
                try {
                    candidate = JSON.parse(trimmed);
                } catch (_error) {
                    return null;
                }
            }
            if (!candidate || typeof candidate !== "object") {
                return null;
            }
            if (candidate.discovery && typeof candidate.discovery === "object") {
                candidate = candidate.discovery;
            }
            if (candidate.refresh_channel && String(candidate.refresh_channel).trim() !== STATUS_CHANNEL) {
                return null;
            }
            if (
                !Object.prototype.hasOwnProperty.call(candidate, "roads_scope_available")
                && !Object.prototype.hasOwnProperty.call(candidate, "available_layer_ids")
                && !Object.prototype.hasOwnProperty.call(candidate, "available_families")
            ) {
                return null;
            }
            return candidate;
        }

        function applyDiscoveryRefresh(detail) {
            var refreshPayload = parseDiscoveryRefreshPayload(detail);
            if (!refreshPayload) {
                return false;
            }
            if (discoveryPayloadEqual(controller.state.discovery, refreshPayload)) {
                return false;
            }
            controller.state.discovery = normalizeDiscoveryPayload(refreshPayload);
            rerender();
            return true;
        }

        function getDefaultsProfile() {
            var bootstrap = controller.state.bootstrap || {};
            var profiles = bootstrap.profiles && typeof bootstrap.profiles === "object"
                ? bootstrap.profiles
                : {};
            var profileKey = controller.state.config.defaultProfileKey || DEFAULT_PROFILE_KEY;
            var profile = profiles[profileKey];
            if (!profile || typeof profile !== "object") {
                return null;
            }
            return profile;
        }

        function getUtmAvailable() {
            return Boolean(controller.state.config.utmAvailable);
        }

        function getCatalogLoadError() {
            var catalog = controller.state.catalog || {};
            if (typeof catalog.load_error === "string" && catalog.load_error.trim()) {
                return catalog.load_error.trim();
            }
            return null;
        }

        function isLayerDiscoveryAvailable(layer) {
            var discovery = controller.state.discovery || {};
            var availableIds = uniqueStrings(discovery.available_layer_ids || []);
            var availableFamilies = uniqueStrings(discovery.available_families || []);
            if (availableIds.length && availableIds.indexOf(layer.layer_id) === -1) {
                return false;
            }
            if (availableFamilies.length && availableFamilies.indexOf(layer.family) === -1) {
                return false;
            }
            return true;
        }

        function temporalBadge(layer) {
            var modes = layer.temporal_modes;
            if (!modes.length) {
                return "none";
            }
            if (modes.length === 1) {
                if (modes[0] === "annual_average" || modes[0] === "yearly") {
                    return "annual/yearly";
                }
                return modes[0].replace(/_/g, "/");
            }
            var hasAnnual = modes.indexOf("annual_average") !== -1;
            var hasYearly = modes.indexOf("yearly") !== -1;
            var hasEvent = modes.indexOf("event") !== -1;
            if (hasAnnual || hasYearly) {
                if (hasEvent) {
                    return "annual/yearly/event";
                }
                return "annual/yearly";
            }
            return modes.join("/");
        }

        function selectorBadge(layer) {
            if (!layer.selector_requirements.length) {
                return "";
            }
            var map = {
                omni_scenario: "Omni scenario",
                omni_contrast: "Omni contrast",
                swat: "SWAT",
                agfields_auto_prep: "AgFields auto-prep"
            };
            return layer.selector_requirements.map(function (token) {
                return map[token] || token;
            }).join(", ");
        }

        function renderLayerColumns(layer) {
            var seenColumnKeys = new Set();
            var columns = normalizeArray(layer.columns).filter(function (entry) {
                if (!entry || typeof entry !== "object") {
                    return false;
                }
                var columnId = String(entry.column_id || "").trim();
                var dedupeKey = columnMatchKey(columnId) || columnId;
                if (!columnId || seenColumnKeys.has(dedupeKey)) {
                    return false;
                }
                seenColumnKeys.add(dedupeKey);
                return true;
            });
            if (!columns.length) {
                return '<p class="wc-field__help">No schema columns were discovered for this dataset.</p>';
            }
            var selectedSet = new Set(effectiveColumnsForLayer(layer));
            var requiredSet = new Set(uniqueStrings(layer.required_columns || []));
            var requiredKeys = new Set(
                uniqueStrings(layer.required_columns || [])
                    .map(function (entry) {
                        return columnMatchKey(entry);
                    })
                    .filter(Boolean)
            );
            var rows = columns.map(function (column) {
                var columnId = String(column.column_id || "").trim();
                var columnKey = columnMatchKey(columnId);
                var checked = selectedSet.has(column.column_id) ? " checked" : "";
                var isRequired = requiredSet.has(column.column_id)
                    || requiredKeys.has(columnKey)
                    || Boolean(column.required);
                var disabled = isRequired ? " disabled" : "";
                var requirementLabel = isRequired ? "required" : "optional";
                var unitLabel = column.display_unit || "non-unitized";
                var description = String(column.description || "").trim();
                var label = String(column.label || columnId).trim();
                var showInlineId = !labelsMatchColumnId(label, columnId);
                return (
                    '<label class="wc-choice wc-choice--checkbox features-export-tree__column">'
                    + '<input type="checkbox"'
                    + ' data-features-export-action="toggle-column"'
                    + ' data-layer-id="' + escapeHtml(layer.layer_id) + '"'
                    + ' data-column-id="' + escapeHtml(column.column_id) + '"'
                    + checked + disabled + '>'
                    + '<span class="wc-choice__body">'
                    + '<span class="wc-choice__label"><strong>' + escapeHtml(label) + '</strong>'
                    + (showInlineId ? ' <code>' + escapeHtml(columnId) + '</code>' : '')
                    + '</span>'
                    + (!showInlineId ? '<span class="wc-choice__description"><code>' + escapeHtml(columnId) + '</code></span>' : '')
                    + (description ? '<span class="wc-choice__description">' + escapeHtml(description) + '</span>' : '')
                    + '<span class="wc-choice__description">unit: ' + escapeHtml(unitLabel) + ' | ' + requirementLabel + '</span>'
                    + '</span>'
                    + '</label>'
                );
            });
            return rows.join("");
        }

        function renderTemporalModeControl(layer) {
            if (!layer.temporal_modes.length) {
                return '<p class="wc-field__help">Temporal: not supported.</p>';
            }
            var selectedMode = effectiveLayerTemporalMode(layer);
            var selectId = "features_export_temporal_mode_" + layer.layer_id.replace(/[^A-Za-z0-9_]/g, "_");
            var options = layer.temporal_modes.map(function (modeToken) {
                var selected = modeToken === selectedMode ? " selected" : "";
                var label = modeToken.replace(/_/g, " ");
                return '<option value="' + escapeHtml(modeToken) + '"' + selected + '>' + escapeHtml(label) + '</option>';
            });
            return (
                '<div class="wc-field features-export-tree__temporal-field">'
                + '<label class="wc-field__label" for="' + escapeHtml(selectId) + '">Temporal mode</label>'
                + '<select id="' + escapeHtml(selectId) + '" class="wc-field__control"'
                + ' data-features-export-field="layer-temporal-mode"'
                + ' data-layer-id="' + escapeHtml(layer.layer_id) + '">'
                + options.join("")
                + '</select>'
                + '</div>'
            );
        }

        function renderCatalog() {
            if (!controller.catalogListEl) {
                return;
            }

            var selectedSet = selectedLayerSet();
            var groups = {};
            var order = familyOrder();

            controller.state.layers.forEach(function (layer) {
                if (!isLayerDiscoveryAvailable(layer)) {
                    return;
                }
                if (!groups[layer.family]) {
                    groups[layer.family] = [];
                }
                groups[layer.family].push(layer);
            });

            var htmlParts = [];
            var familyIndex = 0;
            order.concat(Object.keys(groups).filter(function (family) {
                return order.indexOf(family) === -1;
            })).forEach(function (family) {
                var layers = groups[family] || [];
                if (!layers.length) {
                    return;
                }

                var selectedCount = layers.filter(function (layer) {
                    return selectedSet.has(layer.layer_id);
                }).length;

                var defaultOpen = familyIndex < 2;
                var isOpen = Object.prototype.hasOwnProperty.call(controller.state.familyOpen, family)
                    ? Boolean(controller.state.familyOpen[family])
                    : defaultOpen;
                familyIndex += 1;

                htmlParts.push(
                    '<details class="features-export-tree__family" data-features-export-family data-family="' + escapeHtml(family) + '"' + (isOpen ? " open" : "") + '>'
                );
                htmlParts.push(
                    '<summary class="features-export-tree__family-summary">'
                    + '<span class="features-export-tree__family-title">' + escapeHtml(familyLabel(family)) + "</span>"
                    + '<span class="features-export-tree__family-count">(' + selectedCount + ' / ' + layers.length + ")</span>"
                    + '</summary>'
                );
                htmlParts.push('<div class="features-export-tree__family-children">');

                layers.forEach(function (layer) {
                    var checked = selectedSet.has(layer.layer_id) ? " checked" : "";
                    var scopeBadge = layer.scope_class === "scope_aware" ? "scope-aware" : "shared";
                    var temporal = temporalBadge(layer);
                    var selector = selectorBadge(layer);
                    var detailsOpen = selectedSet.has(layer.layer_id) ? " open" : "";
                    htmlParts.push(
                        '<article class="wc-stack features-export-tree__dataset" data-features-export-layer data-layer-id="' + escapeHtml(layer.layer_id)
                        + '" data-family="' + escapeHtml(layer.family)
                        + '" data-scope-class="' + escapeHtml(layer.scope_class)
                        + '">'
                    );
                    htmlParts.push(
                        '<label class="wc-choice wc-choice--checkbox features-export-tree__dataset-toggle">'
                        + '<input type="checkbox" data-features-export-action="toggle-layer" value="' + escapeHtml(layer.layer_id) + '"' + checked + '>'
                        + '<span class="wc-choice__body">'
                        + '<span class="wc-choice__label"><strong>' + escapeHtml(layer.label) + '</strong></span>'
                        + '<span class="wc-choice__description"><code>' + escapeHtml(layer.layer_id) + '</code></span>'
                        + '</span>'
                        + '</label>'
                    );
                    htmlParts.push(
                        '<p class="wc-field__help features-export-tree__dataset-meta">'
                        + 'geometry: ' + escapeHtml(layer.geometry_type)
                        + ' | scope: ' + escapeHtml(scopeBadge)
                        + ' | temporal: ' + escapeHtml(temporal)
                        + (selector ? ' | selector: ' + escapeHtml(selector) : '')
                        + '</p>'
                    );
                    htmlParts.push('<details class="wc-stack features-export-tree__dataset-options" data-features-export-layer-columns' + detailsOpen + '>');
                    htmlParts.push('<summary class="features-export-tree__dataset-options-summary">Dataset options</summary>');
                    htmlParts.push('<div class="wc-stack features-export-tree__dataset-options-body" data-features-export-layer-details>');
                    htmlParts.push(renderTemporalModeControl(layer));
                    htmlParts.push('<div class="features-export-tree__columns">');
                    htmlParts.push('<label class="wc-field__label">Columns</label>');
                    htmlParts.push('<div class="features-export-tree__column-list">');
                    htmlParts.push(renderLayerColumns(layer));
                    htmlParts.push("</div>");
                    htmlParts.push("</div>");
                    htmlParts.push("</div>");
                    htmlParts.push("</details>");
                    htmlParts.push("</article>");
                });

                htmlParts.push("</div>");
                htmlParts.push("</details>");
            });

            controller.catalogListEl.innerHTML = htmlParts.join("");
        }

        function setElementText(selector, value) {
            var node = getFieldNode(selector);
            if (!node) {
                return;
            }
            node.textContent = value;
        }

        function setRegionText(regionName, value) {
            if (!controller.form) {
                return;
            }
            var node = controller.form.querySelector('[data-features-export-region="' + regionName + '"]');
            if (!node) {
                return;
            }
            node.textContent = value;
        }

        function renderSummary(validation) {
            var selected = selectedLayers();
            var families = {};
            var scopeAwareCount = 0;
            var temporalCount = 0;

            selected.forEach(function (layer) {
                families[layer.family] = (families[layer.family] || 0) + 1;
                if (layer.scope_class === "scope_aware") {
                    scopeAwareCount += 1;
                }
                if (layer.temporal_modes.length > 0) {
                    temporalCount += 1;
                }
            });

            var familySummary = Object.keys(families).sort().map(function (family) {
                return familyLabel(family) + " (" + families[family] + ")";
            });
            setRegionText("selected-count", "Selected: " + selected.length + " layers");
            setRegionText("family-counts", "Families: " + (familySummary.length ? familySummary.join(", ") : "none"));
            setRegionText("capability-counts", "Scope-aware: " + scopeAwareCount + " | Temporal-capable: " + temporalCount);

            var validationText = "";
            if (validation.errors.length) {
                validationText = "Validation: " + validation.errors[0].message;
            } else if (validation.valid) {
                validationText = "Validation: Ready to export.";
            } else {
                validationText = "Validation: Waiting for required selections.";
            }
            setRegionText("validation", validationText);

            var warningLines = validation.warnings.map(function (entry) {
                return entry.message;
            });
            if (controller._defaults_skipped_layers.length) {
                warningLines.push(
                    "Load Defaults skipped unavailable layers: " + controller._defaults_skipped_layers.join(", ")
                );
            }
            setRegionText("summary-warnings", warningLines.join(" | "));
        }

        function showGroup(groupName, shouldShow) {
            var node = controller.groups[groupName] || null;
            if (!node) {
                return;
            }
            node.hidden = !shouldShow;
        }

        function selectedFamilies() {
            var set = new Set();
            selectedLayers().forEach(function (layer) {
                set.add(layer.family);
            });
            return set;
        }

        function updateOmniVisibility(familiesSet) {
            var omniGroup = controller.groups.omni;
            if (!omniGroup) {
                return;
            }
            var hasScenario = familiesSet.has("omni_scenarios");
            var hasContrast = familiesSet.has("omni_contrasts");
            var hasWepp = familiesSet.has("wepp");
            var show = hasScenario || hasContrast || hasWepp;
            omniGroup.hidden = !show;

            var scenarioWrap = getFieldNode("[data-features-export-omni-scenario-wrap]");
            var contrastWrap = getFieldNode("[data-features-export-omni-contrast-wrap]");
            var omniTitle = controller.form.querySelector('[data-features-export-region="omni-title"]');

            if (scenarioWrap) {
                scenarioWrap.hidden = !(hasScenario || hasWepp);
            }
            if (contrastWrap) {
                contrastWrap.hidden = !(hasContrast || hasWepp);
            }
            if (omniTitle) {
                if (hasScenario && !hasContrast && !hasWepp) {
                    omniTitle.textContent = "Omni Scenario";
                } else if (!hasScenario && hasContrast && !hasWepp) {
                    omniTitle.textContent = "Omni Contrast";
                } else {
                    omniTitle.textContent = "Omni Scenarios / Contrasts";
                }
            }
        }

        function updateSwatTables() {
            if (!controller.swatTablesEl) {
                return;
            }
            var bootstrap = controller.state.bootstrap || {};
            var swat = bootstrap.swat && typeof bootstrap.swat === "object" ? bootstrap.swat : {};
            var tablesByRun = swat.tables_by_run && typeof swat.tables_by_run === "object"
                ? swat.tables_by_run
                : {};
            var allTables = uniqueStrings(swat.all_tables || []);
            var runId = readFieldValue(FIELDS.swatRunId) || "latest";
            var runTables = uniqueStrings(tablesByRun[runId] || []);
            var tables = runTables.length ? runTables : allTables;

            controller.state.selectedSwatTables = uniqueStrings(controller.state.selectedSwatTables).filter(function (tableName) {
                return tables.indexOf(tableName) !== -1;
            });

            if (!tables.length) {
                controller.swatTablesEl.innerHTML = '<p class="wc-field__help">No SWAT tables discovered for this run.</p>';
                return;
            }

            var selectedSet = new Set(controller.state.selectedSwatTables);
            var rows = tables.map(function (tableName) {
                var checked = selectedSet.has(tableName) ? " checked" : "";
                return '<label class="wc-toggle-inline">'
                    + '<input type="checkbox" data-features-export-action="toggle-swat-table" value="' + escapeHtml(tableName) + '"' + checked + '>'
                    + '<span>' + escapeHtml(tableName) + '</span>'
                    + '</label>';
            });
            controller.swatTablesEl.innerHTML = rows.join("");
        }

        function updateRoadsScopeAvailability() {
            var discovery = controller.state.discovery || {};
            var roadsAvailable = discovery.roads_scope_available !== false;
            queryAllWithinForm(FIELDS.outputScope).forEach(function (node) {
                if (String(node.value || "") !== "roads") {
                    return;
                }
                node.disabled = !roadsAvailable;
                if (!roadsAvailable) {
                    node.checked = false;
                }
            });
            if (roadsAvailable) {
                setRegionText("roads-scope-note", "Scope-invariant layers export once as shared output.");
            } else {
                setRegionText("roads-scope-note", "Roads scope is unavailable for this run.");
            }
        }

        function updateProgressiveDisclosure() {
            var selected = selectedLayers();
            var families = selectedFamilies();
            var hasScopeAware = selected.some(function (layer) {
                return layer.scope_class === "scope_aware";
            });
            var hasTemporal = selected.some(function (layer) {
                return layer.temporal_modes.length > 0;
            });
            var hasSwat = families.has("swat_interchange");

            showGroup("scopes", hasScopeAware);
            showGroup("temporal", hasTemporal);
            showGroup("swat", hasSwat);
            updateOmniVisibility(families);
            updateTemporalVisibility();
            updateRoadsScopeAvailability();

            if (hasSwat) {
                updateSwatTables();
            }
        }

        function buildValidation() {
            var errors = [];
            var warnings = [];

            var loadError = getCatalogLoadError();
            if (loadError) {
                errors.push({ group: "catalog", message: loadError });
            }

            var selected = selectedLayers();
            if (!selected.length) {
                errors.push({ group: "catalog", message: "Select at least one layer." });
            }

            var format = normalizeFormat(readFieldValue(FIELDS.format));
            var units = readCheckedRadio(FIELDS.units);
            var crs = readCheckedRadio(FIELDS.crs);
            if (!format) {
                errors.push({ group: "settings", message: "Format is required." });
            }
            if (!units) {
                errors.push({ group: "settings", message: "Units is required." });
            }
            if (!crs) {
                errors.push({ group: "settings", message: "CRS is required." });
            }
            if (crs === "utm" && !getUtmAvailable()) {
                errors.push({ group: "settings", message: "UTM CRS is unavailable for this run." });
            }

            if (!controller.groups.scopes.hidden) {
                var scopes = readOutputScopes();
                if (!scopes.length) {
                    errors.push({ group: "scopes", message: "Choose at least one output scope." });
                }
            }

            if (!controller.groups.temporal.hidden) {
                var temporalModes = selected
                    .filter(function (layer) {
                        return layer.temporal_modes.length > 0;
                    })
                    .map(function (layer) {
                        return {
                            layer_id: layer.layer_id,
                            mode: effectiveLayerTemporalMode(layer)
                        };
                    });
                temporalModes.forEach(function (entry) {
                    if (!entry.mode) {
                        errors.push({
                            group: "temporal",
                            message: "Temporal mode is required for " + entry.layer_id + "."
                        });
                    }
                });

                var usesYearSelectors = temporalModes.some(function (entry) {
                    return entry.mode === "annual_average" || entry.mode === "yearly";
                });
                var usesEventSelectors = temporalModes.some(function (entry) {
                    return entry.mode === "event";
                });

                if (usesYearSelectors) {
                    var yearSelection = readFieldValue(FIELDS.temporalYearSelection) || "all";
                    if (yearSelection === "custom") {
                        var customIndices = parseIntList(readFieldValue(FIELDS.temporalExcludeIndices));
                        if (!customIndices.length) {
                            errors.push({ group: "temporal", message: "Provide at least one custom excluded year index." });
                        }
                    }
                }
                if (usesEventSelectors) {
                    var selector = readCheckedRadio(FIELDS.temporalEventSelector);
                    if (!selector) {
                        errors.push({ group: "temporal", message: "Event selector is required when any temporal mode is event." });
                    } else if (selector === "date") {
                        if (!parseCommaList(readFieldValue(FIELDS.temporalEventDates)).length) {
                            errors.push({ group: "temporal", message: "Provide at least one event date." });
                        }
                    } else if (selector === "return_period") {
                        if (!parseFloatList(readFieldValue(FIELDS.temporalEventReturnPeriods)).length) {
                            errors.push({ group: "temporal", message: "Provide at least one return period." });
                        }
                    }
                }
            }

            if (!controller.groups.omni.hidden) {
                var hasScenario = selected.some(function (layer) {
                    return layer.family === "omni_scenarios";
                });
                var hasContrast = selected.some(function (layer) {
                    return layer.family === "omni_contrasts";
                });
                var selectedScenarioIds = readSelectedScenarios();
                var selectedContrastIds = readSelectedContrasts();
                if ((hasScenario && hasContrast) || (selectedScenarioIds.length && selectedContrastIds.length)) {
                    errors.push({ group: "omni", message: "Omni scenario and contrast layer families cannot be mixed." });
                }
                if (hasScenario && !selectedScenarioIds.length) {
                    errors.push({ group: "omni", message: "Select an Omni scenario." });
                }
                if (hasContrast && !selectedContrastIds.length) {
                    errors.push({ group: "omni", message: "Select an Omni contrast." });
                }
            }

            if (!controller.groups.swat.hidden) {
                var bootstrap = controller.state.bootstrap || {};
                var swat = bootstrap.swat && typeof bootstrap.swat === "object" ? bootstrap.swat : {};
                var swatRuns = normalizeArray(swat.runs);
                if (!swatRuns.length) {
                    errors.push({ group: "swat", message: "No SWAT runs are available for selected SWAT layers." });
                }
                var tableMode = readFieldValue(FIELDS.swatTableMode) || "all";
                if ((tableMode === "include" || tableMode === "exclude") && !controller.state.selectedSwatTables.length) {
                    errors.push({ group: "swat", message: "Select at least one SWAT table for include/exclude mode." });
                }
            }

            return {
                valid: errors.length === 0,
                errors: errors,
                warnings: warnings
            };
        }

        function emitSelectionChanged() {
            var availableLayerIds = controller.state.layers.filter(function (layer) {
                return isLayerDiscoveryAvailable(layer);
            }).map(function (layer) {
                return layer.layer_id;
            });
            var payload = {
                selectedLayerIds: uniqueStrings(controller.state.selectedLayerIds),
                counts: {
                    selected: uniqueStrings(controller.state.selectedLayerIds).length,
                    visible: uniqueStrings(availableLayerIds).length,
                    total: controller.state.layers.length
                },
                visibleLayerIds: uniqueStrings(availableLayerIds)
            };
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("features_export:selection:changed", payload);
            }
        }

        function emitValidationChanged(validation) {
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("features_export:validation:changed", {
                    valid: validation.valid,
                    errors: validation.errors,
                    warnings: validation.warnings
                });
            }
        }

        function emitScopeChanged() {
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("features_export:scope:changed", {
                    output_scopes: readOutputScopes()
                });
            }
        }

        function emitTemporalChanged() {
            var selected = selectedLayers();
            var layerModes = {};
            selected.forEach(function (layer) {
                if (!layer.temporal_modes.length) {
                    return;
                }
                var mode = effectiveLayerTemporalMode(layer);
                if (mode) {
                    layerModes[layer.layer_id] = mode;
                }
            });
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("features_export:temporal:changed", {
                    temporal: buildTemporalPayload(),
                    layer_modes: layerModes
                });
            }
        }

        function emitOmniChanged() {
            var mode = null;
            if (!controller.groups.omni.hidden) {
                var selectedFamiliesSet = selectedFamilies();
                if (selectedFamiliesSet.has("omni_scenarios")) {
                    mode = "scenario";
                } else if (selectedFamiliesSet.has("omni_contrasts")) {
                    mode = "contrast";
                }
            }
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("features_export:omni:changed", {
                    mode: mode,
                    scenarios: readSelectedScenarios(),
                    contrast_ids: readSelectedContrasts()
                });
            }
        }

        function emitSwatChanged() {
            var tableMode = readFieldValue(FIELDS.swatTableMode) || "all";
            var swatTables = null;
            if (tableMode === "include") {
                swatTables = { include: uniqueStrings(controller.state.selectedSwatTables) };
            } else if (tableMode === "exclude") {
                swatTables = { exclude: uniqueStrings(controller.state.selectedSwatTables) };
            }
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("features_export:swat:changed", {
                    swat_run_id: readFieldValue(FIELDS.swatRunId) || "latest",
                    swat_tables: swatTables
                });
            }
        }

        function setSubmitEnabled(enabled) {
            if (!controller.submitButtonEl) {
                return;
            }
            controller.submitButtonEl.disabled = !enabled;
        }

        function rerender(options) {
            var skipCatalog = Boolean(options && options.skipCatalog);
            if (!skipCatalog) {
                captureFamilyOpenState();
                renderCatalog();
            }
            updateProgressiveDisclosure();
            var validation = buildValidation();
            controller.state.validation = validation;
            setSubmitEnabled(validation.valid);
            renderSummary(validation);
            emitSelectionChanged();
            emitValidationChanged(validation);
            emitScopeChanged();
            emitTemporalChanged();
            emitOmniChanged();
            emitSwatChanged();
            updatePackagingHint();
        }

        function updatePackagingHint() {
            var format = normalizeFormat(readFieldValue(FIELDS.format));
            var selectedCount = uniqueStrings(controller.state.selectedLayerIds).length;
            var hint = "";
            if (!format || !selectedCount) {
                hint = "";
            } else if (format === "geopackage" || format === "geodatabase") {
                hint = "Packaging: 1 container artifact.";
            } else {
                hint = "Packaging: zip bundle with " + selectedCount + " file" + (selectedCount === 1 ? "" : "s") + ".";
            }
            setRegionText("packaging-hint", hint);
        }

        function clearResultsPanel() {
            if (controller.resultStateEl) {
                controller.resultStateEl.textContent = "Idle";
            }
            if (controller.downloadRegionEl) {
                controller.downloadRegionEl.innerHTML = "";
            }
            if (controller.artifactMetaRegionEl) {
                controller.artifactMetaRegionEl.innerHTML = "";
            }
            if (controller.warningsRegionEl) {
                controller.warningsRegionEl.innerHTML = "";
            }
        }

        function hideStacktracePanel() {
            if (controller.stacktrace && typeof controller.stacktrace.empty === "function") {
                controller.stacktrace.empty();
            }
            if (controller.stacktracePanelEl) {
                controller.stacktracePanelEl.open = false;
                controller.stacktracePanelEl.hidden = true;
            }
            if (controller.stacktrace && typeof controller.stacktrace.hide === "function") {
                controller.stacktrace.hide();
            }
        }

        function showStacktracePanel() {
            if (!controller.stacktracePanelEl) {
                return;
            }
            controller.stacktracePanelEl.hidden = false;
            controller.stacktracePanelEl.open = true;
            if (controller.stacktrace && typeof controller.stacktrace.show === "function") {
                controller.stacktrace.show();
            }
        }

        function resetSubmitState() {
            clearResultsPanel();
            hideStacktracePanel();
            controller.clear_status_messages(controller);
            controller.append_status_message(controller, "Submitting features export request...");
        }

        function openGroup(groupName) {
            var group = controller.groups[groupName];
            if (!group) {
                return;
            }
            group.hidden = false;
            var focusable = group.querySelector("input, select, textarea, button");
            if (focusable && typeof focusable.focus === "function") {
                focusable.focus();
            }
        }

        function buildTemporalPayload() {
            if (controller.groups.temporal && controller.groups.temporal.hidden) {
                return null;
            }
            var selected = selectedLayers();
            var layerModes = {};
            selected.forEach(function (layer) {
                if (!layer.temporal_modes.length) {
                    return;
                }
                var mode = effectiveLayerTemporalMode(layer);
                if (mode) {
                    layerModes[layer.layer_id] = mode;
                }
            });
            if (!Object.keys(layerModes).length) {
                return null;
            }
            var temporal = { layer_modes: layerModes };
            var modes = Object.keys(layerModes).map(function (layerId) {
                return layerModes[layerId];
            });
            var usesYearSelectors = modes.some(function (mode) {
                return mode === "annual_average" || mode === "yearly";
            });
            var usesEventSelectors = modes.indexOf("event") !== -1;

            if (usesYearSelectors) {
                var yearSelection = readFieldValue(FIELDS.temporalYearSelection) || "all";
                temporal.year_selection = yearSelection;
                if (yearSelection === "custom") {
                    temporal.exclude_yr_indxs = parseIntList(readFieldValue(FIELDS.temporalExcludeIndices));
                }
            }
            if (usesEventSelectors) {
                var selector = readCheckedRadio(FIELDS.temporalEventSelector);
                if (!selector) {
                    return temporal;
                }
                temporal.event = { selector: selector };
                if (selector === "date") {
                    temporal.event.dates = parseCommaList(readFieldValue(FIELDS.temporalEventDates));
                } else if (selector === "return_period") {
                    temporal.event.return_periods = parseFloatList(readFieldValue(FIELDS.temporalEventReturnPeriods));
                }
            }
            return temporal;
        }

        function buildColumnSelectionPayload() {
            var payload = {};
            selectedLayers().forEach(function (layer) {
                var selectedColumns = effectiveColumnsForLayer(layer);
                if (!selectedColumns.length) {
                    return;
                }
                payload[layer.layer_id] = { include: selectedColumns };
            });
            return payload;
        }

        function buildPayload() {
            var payload = {
                format: normalizeFormat(readFieldValue(FIELDS.format)),
                units: readCheckedRadio(FIELDS.units),
                crs: readCheckedRadio(FIELDS.crs),
                layers: uniqueStrings(controller.state.selectedLayerIds)
            };

            if (!controller.groups.scopes.hidden) {
                var outputScopes = readOutputScopes();
                if (outputScopes.length) {
                    payload.output_scopes = outputScopes;
                }
            }

            var temporal = buildTemporalPayload();
            if (temporal) {
                payload.temporal = temporal;
            }

            var scenarios = readSelectedScenarios();
            var contrastIds = readSelectedContrasts();
            if (scenarios.length) {
                payload.scenarios = scenarios;
            }
            if (contrastIds.length) {
                payload.contrast_ids = contrastIds;
            }

            if (!controller.groups.swat.hidden) {
                payload.swat_run_id = readFieldValue(FIELDS.swatRunId) || "latest";
                var tableMode = readFieldValue(FIELDS.swatTableMode) || "all";
                var selectedTables = uniqueStrings(controller.state.selectedSwatTables);
                if (tableMode === "include") {
                    payload.swat_tables = { include: selectedTables };
                } else if (tableMode === "exclude") {
                    payload.swat_tables = { exclude: selectedTables };
                }
            }

            var columnSelection = buildColumnSelectionPayload();
            if (Object.keys(columnSelection).length) {
                payload.column_selection = columnSelection;
            }

            return payload;
        }

        function renderResult(result) {
            var warnings = Array.isArray(result && result.warnings) ? result.warnings : [];
            var hasWarnings = warnings.length > 0;
            if (controller.resultStateEl) {
                controller.resultStateEl.textContent = hasWarnings ? "Partial success" : "Success";
            }

            if (controller.downloadRegionEl) {
                var downloadUrl = result && result.download_url ? String(result.download_url) : "";
                downloadUrl = applySitePrefixToRunsUrl(downloadUrl);
                if (downloadUrl) {
                    controller.downloadRegionEl.innerHTML = '<a class="pure-button pure-button-primary" data-features-export-action="download" href="'
                        + escapeHtml(downloadUrl)
                        + '" target="_blank" rel="noopener">Download Artifact</a>';
                } else {
                    controller.downloadRegionEl.innerHTML = "";
                }
            }

            if (controller.artifactMetaRegionEl) {
                var rows = [];
                if (result && result.artifact_id) {
                    rows.push("artifact_id: <code>" + escapeHtml(String(result.artifact_id)) + "</code>");
                }
                if (result && Object.prototype.hasOwnProperty.call(result, "cache_hit")) {
                    rows.push("cache_hit: <code>" + escapeHtml(String(Boolean(result.cache_hit))) + "</code>");
                }
                if (result && result.source_job_id) {
                    rows.push("source_job_id: <code>" + escapeHtml(String(result.source_job_id)) + "</code>");
                }
                if (result && result.manifest_relpath) {
                    rows.push("manifest_relpath: <code>" + escapeHtml(String(result.manifest_relpath)) + "</code>");
                }
                controller.artifactMetaRegionEl.innerHTML = rows.length
                    ? "<ul class=\"wc-list\"><li>" + rows.join("</li><li>") + "</li></ul>"
                    : "";
            }

            if (controller.warningsRegionEl) {
                if (!warnings.length) {
                    controller.warningsRegionEl.innerHTML = "";
                } else {
                    var warningRows = warnings.map(function (warning) {
                        if (warning && typeof warning === "object") {
                            var code = warning.code ? String(warning.code) : "warning";
                            var message = warning.message ? String(warning.message) : "";
                            return "<li><code>" + escapeHtml(code) + "</code> " + escapeHtml(message) + "</li>";
                        }
                        return "<li>" + escapeHtml(String(warning)) + "</li>";
                    });
                    controller.warningsRegionEl.innerHTML = warningRows.join("");
                }
            }
        }

        function requestJobInfo(jobId) {
            var normalizedJobId = jobId ? String(jobId).trim() : "";
            if (!normalizedJobId) {
                return Promise.resolve(null);
            }
            if (controller._completion_jobinfo_job_id === normalizedJobId) {
                if (controller._completion_jobinfo_inflight) {
                    return controller._completion_jobinfo_inflight;
                }
                return Promise.resolve(controller._last_jobinfo_result);
            }

            var url = "/rq-engine/api/jobinfo/" + encodeURIComponent(normalizedJobId);
            var requestOptions = {
                method: "GET",
                params: { _: Date.now() }
            };

            var requestPromise;
            if (typeof http.requestWithSessionToken === "function") {
                requestPromise = http.requestWithSessionToken(url, Object.assign({ form: controller.form }, requestOptions));
            } else {
                requestPromise = http.request(url, requestOptions);
            }

            controller._completion_jobinfo_job_id = normalizedJobId;
            controller._completion_jobinfo_inflight = Promise.resolve(requestPromise)
                .then(function (response) {
                    var body = unwrapResponseBody(response);
                    if (body && (body.error || body.errors)) {
                        controller.pushResponseStacktrace(controller, body);
                        throw new Error("Features export jobinfo request failed");
                    }
                    var result = body && typeof body.result === "object" && body.result !== null
                        ? body.result
                        : {};
                    controller._last_jobinfo_result = result;
                    if (controller.events && typeof controller.events.emit === "function") {
                        controller.events.emit("features_export:jobinfo:loaded", {
                            job_id: normalizedJobId,
                            result: result
                        });
                    }
                    return result;
                })
                .finally(function () {
                    controller._completion_jobinfo_inflight = null;
                });

            return controller._completion_jobinfo_inflight;
        }

        function handleCompletion(detail, source) {
            var jobId = (controller.rq_job_id || (detail && detail.job_id) || "").toString().trim();
            controller._completion_source = source || "unknown";
            controller.disconnect_status_stream(controller);
            if (!jobId) {
                return;
            }
            controller.append_status_message(controller, "Features export completed. Loading job details...");
            requestJobInfo(jobId)
                .then(function (result) {
                    if (!result) {
                        return;
                    }
                    renderResult(result);
                    var warnings = Array.isArray(result.warnings) ? result.warnings : [];
                    if (controller.events && typeof controller.events.emit === "function") {
                        controller.events.emit("features_export:completed", {
                            job_id: jobId,
                            result: result,
                            warnings: warnings
                        });
                    }
                    controller.append_status_message(
                        controller,
                        warnings.length
                            ? "Features export completed with warnings."
                            : "Features export completed successfully."
                    );
                })
                .catch(function (error) {
                    controller.pushErrorStacktrace(controller, error, "jobinfo", "Failed to load job info.");
                    showStacktracePanel();
                    if (controller.events && typeof controller.events.emit === "function") {
                        controller.events.emit("features_export:error", {
                            job_id: jobId,
                            error: error
                        });
                    }
                });
        }

        function attachDelegates(force) {
            if (!controller.form) {
                clearDelegates();
                return;
            }
            if (!force && controller._delegateRoot === controller.form && controller._delegates.length) {
                return;
            }

            clearDelegates();

            controller._delegates.push(dom.delegate(controller.form, "change", ACTIONS.toggleLayer, function (_event, target) {
                var layerId = String(target.value || "").trim();
                if (!layerId) {
                    return;
                }
                if (target.checked) {
                    addSelectedLayers([layerId]);
                } else {
                    removeSelectedLayer(layerId);
                }
                rerender({ skipCatalog: true });
            }));

            controller._delegates.push(dom.delegate(controller.form, "change", FIELDS.temporalMode, function (_event, target) {
                var layerId = String(target.getAttribute("data-layer-id") || "").trim();
                if (!layerId) {
                    return;
                }
                var mode = String(target.value || "").trim();
                setLayerTemporalMode(layerId, mode);
                rerender();
            }));

            controller._delegates.push(dom.delegate(controller.form, "change", ACTIONS.toggleColumn, function (_event, target) {
                var layerId = String(target.getAttribute("data-layer-id") || "").trim();
                var columnId = String(target.getAttribute("data-column-id") || "").trim();
                if (!layerId || !columnId) {
                    return;
                }
                var layer = getLayerById(layerId);
                if (!layer) {
                    return;
                }
                var requiredSet = new Set(uniqueStrings(layer.required_columns || []));
                var nextSelection = effectiveColumnsForLayer(layer).slice();
                if (target.checked || requiredSet.has(columnId)) {
                    if (nextSelection.indexOf(columnId) === -1) {
                        nextSelection.push(columnId);
                    }
                } else {
                    nextSelection = nextSelection.filter(function (entry) {
                        return entry !== columnId;
                    });
                }
                requiredSet.forEach(function (requiredColumn) {
                    if (nextSelection.indexOf(requiredColumn) === -1) {
                        nextSelection.push(requiredColumn);
                    }
                });
                setLayerColumns(layerId, nextSelection);
                rerender();
            }));

            controller._delegates.push(dom.delegate(controller.form, "click", ACTIONS.omniSelectAll, function (event, target) {
                event.preventDefault();
                var omniTarget = String(target.getAttribute("data-omni-target") || "").trim();
                if (omniTarget === "scenarios") {
                    queryAllWithinForm(FIELDS.scenario).forEach(function (node) {
                        node.checked = true;
                    });
                } else if (omniTarget === "contrasts") {
                    queryAllWithinForm(FIELDS.contrastId).forEach(function (node) {
                        node.checked = true;
                    });
                }
                rerender();
            }));

            controller._delegates.push(dom.delegate(controller.form, "click", ACTIONS.omniUnselectAll, function (event, target) {
                event.preventDefault();
                var omniTarget = String(target.getAttribute("data-omni-target") || "").trim();
                if (omniTarget === "scenarios") {
                    queryAllWithinForm(FIELDS.scenario).forEach(function (node) {
                        node.checked = false;
                    });
                } else if (omniTarget === "contrasts") {
                    queryAllWithinForm(FIELDS.contrastId).forEach(function (node) {
                        node.checked = false;
                    });
                }
                rerender();
            }));

            controller._delegates.push(dom.delegate(controller.form, "click", ACTIONS.clearSelection, function (event) {
                event.preventDefault();
                clearSelectedLayers();
                rerender();
            }));

            controller._delegates.push(dom.delegate(controller.form, "click", ACTIONS.loadDefaults, function (event) {
                event.preventDefault();
                applyDefaultsProfile();
            }));

            controller._delegates.push(dom.delegate(controller.form, "change", ACTIONS.toggleSwatTable, function (_event, target) {
                var tableName = String(target.value || "").trim();
                if (!tableName) {
                    return;
                }
                if (target.checked) {
                    controller.state.selectedSwatTables = uniqueStrings(controller.state.selectedSwatTables.concat([tableName]));
                } else {
                    controller.state.selectedSwatTables = uniqueStrings(controller.state.selectedSwatTables).filter(function (entry) {
                        return entry !== tableName;
                    });
                }
                rerender();
            }));

            controller._delegates.push(dom.delegate(controller.form, "change", FIELDS.format + ", " + FIELDS.units + ", " + FIELDS.crs + ", " + FIELDS.outputScope + ", " + FIELDS.temporalYearSelection + ", " + FIELDS.temporalEventSelector + ", " + FIELDS.scenario + ", " + FIELDS.contrastId + ", " + FIELDS.swatRunId + ", " + FIELDS.swatTableMode, function () {
                if (this && this.matches && this.matches(FIELDS.swatRunId)) {
                    updateSwatTables();
                }
                rerender();
            }));

            controller._delegates.push(dom.delegate(controller.form, "input", FIELDS.temporalExcludeIndices + ", " + FIELDS.temporalEventDates + ", " + FIELDS.temporalEventReturnPeriods, function () {
                rerender();
            }));

            controller.form.addEventListener("submit", onSubmit);
            controller._delegates.push(function () {
                if (controller.form) {
                    controller.form.removeEventListener("submit", onSubmit);
                }
            });

            controller._delegateRoot = controller.form;
        }

        function applyDefaultsProfile() {
            var profile = getDefaultsProfile();
            if (!profile) {
                setRegionText("summary-warnings", "Load Defaults profile is unavailable.");
                return;
            }

            var changedFields = [];

            var nextFormat = normalizeFormat(profile.format || controller.state.config.defaultFormat || "geopackage");
            var nextUnits = String(profile.units || controller.state.config.defaultUnits || "project");
            var nextCrs = String(profile.crs || controller.state.config.defaultCrs || "wgs");
            setSelectOrInput(FIELDS.format, nextFormat);
            changedFields.push("format");
            setRadioValue(FIELDS.units, nextUnits);
            changedFields.push("units");
            setRadioValue(FIELDS.crs, nextCrs);
            changedFields.push("crs");

            setOutputScopes(profile.output_scopes || ["baseline"]);
            changedFields.push("output_scopes");

            controller.state.layerTemporalModes = {};
            setSelectOrInput(FIELDS.temporalYearSelection, "all");
            setSelectOrInput(FIELDS.temporalExcludeIndices, "");
            setRadioValue(FIELDS.temporalEventSelector, "");
            setSelectOrInput(FIELDS.temporalEventDates, "");
            setSelectOrInput(FIELDS.temporalEventReturnPeriods, "");
            changedFields.push("temporal");

            queryAllWithinForm(FIELDS.scenario).forEach(function (node) {
                node.checked = false;
            });
            queryAllWithinForm(FIELDS.contrastId).forEach(function (node) {
                node.checked = false;
            });
            changedFields.push("omni");

            setSelectOrInput(FIELDS.swatRunId, profile.swat_run_id || "latest");
            setSelectOrInput(FIELDS.swatTableMode, "all");
            controller.state.selectedSwatTables = [];
            controller.state.layerColumnSelection = {};
            changedFields.push("swat");

            var availableLayerIds = new Set(controller.state.layers.map(function (layer) {
                return layer.layer_id;
            }));
            var requested = uniqueStrings(profile.layers || []);
            var selected = [];
            var skipped = [];
            requested.forEach(function (layerId) {
                if (availableLayerIds.has(layerId)) {
                    selected.push(layerId);
                } else {
                    skipped.push(layerId);
                }
            });
            setSelectedLayers(selected);
            selected.forEach(function (layerId) {
                var layer = getLayerById(layerId);
                if (!layer) {
                    return;
                }
                if (layer.temporal_modes.length) {
                    setLayerTemporalMode(layerId, defaultLayerTemporalMode(layer));
                }
                setLayerColumns(layerId, defaultColumnsForLayer(layer));
            });
            controller._defaults_skipped_layers = skipped;

            updateSwatTables();
            rerender();

            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("features_export:defaults:loaded", {
                    profileKey: controller.state.config.defaultProfileKey || DEFAULT_PROFILE_KEY,
                    selectedLayerIds: uniqueStrings(controller.state.selectedLayerIds),
                    changedFields: changedFields,
                    skippedLayerIds: skipped
                });
            }
        }

        function readConfigNode() {
            var sitePrefix = typeof window.site_prefix === "string"
                ? window.site_prefix.replace(/\/+$/, "")
                : "";
            var config = {
                jobKey: "run_features_export",
                channel: STATUS_CHANNEL,
                submitUrl: "/rq-engine/api/runs/" + encodeURIComponent(window.runid || window.runId || "") + "/" + encodeURIComponent(window.config || "") + "/export/features",
                downloadUrlTemplate: (sitePrefix ? sitePrefix : "") + "/runs/" + encodeURIComponent(window.runid || window.runId || "") + "/" + encodeURIComponent(window.config || "") + "/download/__ARTIFACT_RELPATH__",
                utmAvailable: false,
                defaultFormat: "geopackage",
                defaultUnits: "project",
                defaultCrs: "wgs",
                defaultProfileKey: DEFAULT_PROFILE_KEY
            };
            if (!controller.configNode) {
                controller.state.config = config;
                return;
            }

            var dataset = controller.configNode.dataset || {};
            if (dataset.featuresExportJobKey) {
                config.jobKey = String(dataset.featuresExportJobKey);
            }
            if (dataset.featuresExportChannel) {
                config.channel = String(dataset.featuresExportChannel);
            }
            if (dataset.featuresExportSubmitUrl) {
                config.submitUrl = String(dataset.featuresExportSubmitUrl);
            }
            if (dataset.featuresExportDownloadUrlTemplate) {
                config.downloadUrlTemplate = String(dataset.featuresExportDownloadUrlTemplate);
            }
            if (dataset.featuresExportUtmAvailable !== undefined) {
                config.utmAvailable = String(dataset.featuresExportUtmAvailable).toLowerCase() === "true";
            }
            if (dataset.featuresExportDefaultFormat) {
                config.defaultFormat = normalizeFormat(dataset.featuresExportDefaultFormat);
            }
            if (dataset.featuresExportDefaultUnits) {
                config.defaultUnits = String(dataset.featuresExportDefaultUnits);
            }
            if (dataset.featuresExportDefaultCrs) {
                config.defaultCrs = String(dataset.featuresExportDefaultCrs);
            }
            if (dataset.featuresExportDefaultProfileKey) {
                config.defaultProfileKey = String(dataset.featuresExportDefaultProfileKey);
            }

            controller.state.config = config;
        }

        function onSubmit(event) {
            event.preventDefault();
            var validation = buildValidation();
            controller.state.validation = validation;
            setSubmitEnabled(validation.valid);
            renderSummary(validation);
            emitValidationChanged(validation);

            if (!validation.valid) {
                var firstError = validation.errors[0];
                if (firstError && firstError.group) {
                    openGroup(firstError.group);
                }
                var validationPayload = {
                    error: {
                        message: "Features export form validation failed.",
                        details: validation.errors.map(function (entry) {
                            return entry.message;
                        })
                    }
                };
                controller.pushResponseStacktrace(controller, validationPayload);
                showStacktracePanel();
                return;
            }

            resetSubmitState();
            controller._completion_seen = false;
            controller._completion_jobinfo_job_id = null;
            controller._completion_jobinfo_inflight = null;
            controller._last_jobinfo_result = null;
            controller._completion_source = null;

            var payload = buildPayload();
            controller._last_submission_payload = payload;

            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("features_export:submit:started", {
                    payload: payload,
                    task: "features_export:submit"
                });
            }
            controller.triggerEvent("job:started", {
                payload: payload,
                task: "features_export:submit"
            });

            controller.connect_status_stream(controller);

            http.postJsonWithSessionToken(controller.state.config.submitUrl, payload, { form: controller.form })
                .then(function (response) {
                    var body = unwrapResponseBody(response);
                    var preferredJobKey = controller.state.config && controller.state.config.jobKey
                        ? String(controller.state.config.jobKey)
                        : "run_features_export";
                    var jobId = extractJobId(body, preferredJobKey);
                    if (!body || body.error || body.errors || !jobId) {
                        var failurePayload = body || { error: { message: "Submit failed." } };
                        if (!body || (!body.error && !body.errors && !jobId)) {
                            failurePayload = {
                                error: {
                                    message: "Submit response did not include a job_id.",
                                    details: body || null
                                }
                            };
                        }
                        controller.pushResponseStacktrace(controller, failurePayload);
                        showStacktracePanel();
                        controller.disconnect_status_stream(controller);
                        if (controller.events && typeof controller.events.emit === "function") {
                            controller.events.emit("features_export:error", {
                                job_id: null,
                                error: failurePayload
                            });
                        }
                        controller.triggerEvent("job:error", {
                            payload: payload,
                            error: failurePayload,
                            task: "features_export:submit"
                        });
                        return;
                    }

                    controller.poll_completion_event = COMPLETION_EVENT;
                    controller.set_rq_job_id(controller, jobId);
                    controller.append_status_message(controller, "Features export job queued: " + jobId);
                    if (controller.events && typeof controller.events.emit === "function") {
                        controller.events.emit("features_export:submit:queued", {
                            payload: payload,
                            job_id: jobId,
                            status: "queued"
                        });
                    }
                })
                .catch(function (error) {
                    var payloadError = toResponsePayload(http, error);
                    if (payloadError && (payloadError.error || payloadError.errors)) {
                        controller.pushResponseStacktrace(controller, payloadError);
                    } else {
                        controller.pushErrorStacktrace(controller, error, "submit", "Failed to submit features export request.");
                    }
                    showStacktracePanel();
                    controller.disconnect_status_stream(controller);
                    if (controller.events && typeof controller.events.emit === "function") {
                        controller.events.emit("features_export:error", {
                            job_id: null,
                            error: payloadError || error
                        });
                    }
                    controller.triggerEvent("job:error", {
                        payload: payload,
                        error: payloadError || error,
                        task: "features_export:submit"
                    });
                });
        }

        function rebindDomReferences() {
            var updated = { formChanged: false, streamNodesChanged: false };

            var nextForm = dom.qs(SELECTORS.form);
            if (nextForm !== controller.form) {
                controller.form = nextForm || null;
                updated.formChanged = true;
            }

            controller.configNode = controller.form ? dom.qs(SELECTORS.config, controller.form) : null;
            controller.catalogNode = controller.form ? dom.qs(SELECTORS.catalogScript, controller.form) : null;
            controller.bootstrapNode = controller.form ? dom.qs(SELECTORS.bootstrapScript, controller.form) : null;

            var nextMessageEl = controller.form ? dom.qs(SELECTORS.message, controller.form) : null;
            var nextStacktraceEl = controller.form ? dom.qs(SELECTORS.stacktrace, controller.form) : null;
            var nextRqJobEl = controller.form ? dom.qs(SELECTORS.rqJob, controller.form) : null;
            var nextHintEl = controller.form ? dom.qs(SELECTORS.hint, controller.form) : null;

            controller.status = createLegacyAdapter(nextMessageEl);
            controller.stacktrace = createLegacyAdapter(nextStacktraceEl);
            controller.rq_job = createLegacyAdapter(nextRqJobEl);
            controller.hint = createLegacyAdapter(nextHintEl);

            var nextStatusPanel = controller.form ? dom.qs(SELECTORS.statusPanel, controller.form) : null;
            var nextStatusLog = controller.form ? dom.qs(SELECTORS.statusLog, controller.form) : null;
            var nextStacktracePanel = controller.form ? dom.qs(SELECTORS.stacktracePanel, controller.form) : null;
            var nextSpinner = controller.form ? dom.qs(SELECTORS.statusSpinner, controller.form) : null;

            if (nextStatusPanel !== controller.statusPanelEl) {
                updated.streamNodesChanged = true;
            }
            if (nextStatusLog !== controller.statusLogEl) {
                updated.streamNodesChanged = true;
            }
            if (nextStacktracePanel !== controller.stacktracePanelEl) {
                updated.streamNodesChanged = true;
            }
            if (nextSpinner !== controller.statusSpinnerEl) {
                updated.streamNodesChanged = true;
            }

            controller.statusPanelEl = nextStatusPanel;
            controller.statusLogEl = nextStatusLog;
            controller.stacktracePanelEl = nextStacktracePanel;
            controller.statusSpinnerEl = nextSpinner;

            controller.submitButtonEl = controller.form ? dom.qs(SELECTORS.submitButton, controller.form) : null;
            controller.resultStateEl = controller.form ? dom.qs(SELECTORS.resultState, controller.form) : null;
            controller.resultsPanelEl = controller.form ? dom.qs(SELECTORS.resultsPanel, controller.form) : null;
            controller.catalogListEl = controller.form ? dom.qs(SELECTORS.catalogList, controller.form) : null;
            controller.swatTablesEl = controller.form ? dom.qs(SELECTORS.swatTables, controller.form) : null;

            controller.downloadRegionEl = controller.form
                ? controller.form.querySelector('[data-features-export-region="download"]')
                : null;
            controller.artifactMetaRegionEl = controller.form
                ? controller.form.querySelector('[data-features-export-region="artifact-meta"]')
                : null;
            controller.warningsRegionEl = controller.form
                ? controller.form.querySelector('[data-features-export-region="warnings"]')
                : null;

            var groupMap = {};
            GROUPS.forEach(function (groupName) {
                groupMap[groupName] = getGroupNode(groupName);
            });
            controller.groups = groupMap;

            return updated;
        }

        function attachStatusStream() {
            if (!controller.form) {
                return;
            }
            if (!controller.statusPanelEl) {
                return;
            }
            controller.attach_status_stream(controller, {
                element: controller.statusPanelEl,
                logElement: controller.statusLogEl,
                channel: controller.state.config.channel || STATUS_CHANNEL,
                runId: window.runid || window.runId || null,
                stacktrace: controller.stacktracePanelEl
                    ? { element: controller.stacktracePanelEl, body: controller.stacktrace.element || null }
                    : null,
                spinner: controller.statusSpinnerEl,
                logLimit: 300,
                onStatus: function (statusDetail) {
                    applyDiscoveryRefresh(statusDetail);
                }
            });
        }

        function getControllerContext(ctx) {
            if (!ctx || typeof ctx !== "object") {
                return {};
            }
            var controllers = ctx.controllers;
            if (controllers && typeof controllers === "object") {
                if (controllers.featuresExport && typeof controllers.featuresExport === "object") {
                    return controllers.featuresExport;
                }
                if (controllers.features_export && typeof controllers.features_export === "object") {
                    return controllers.features_export;
                }
            }
            return {};
        }

        function resolveBootstrapJobId(ctx) {
            var helper = window.WCControllerBootstrap || null;
            var configuredJobKey = controller.state.config && controller.state.config.jobKey
                ? String(controller.state.config.jobKey)
                : "run_features_export";
            var jobKeyCandidates = uniqueStrings([
                configuredJobKey,
                configuredJobKey.endsWith("_rq") ? configuredJobKey.slice(0, -3) : configuredJobKey + "_rq",
                "run_features_export",
                "run_features_export_rq"
            ]);

            if (helper && typeof helper.resolveJobId === "function") {
                for (var i = 0; i < jobKeyCandidates.length; i += 1) {
                    var resolvedByHelper = helper.resolveJobId(ctx, jobKeyCandidates[i]);
                    if (resolvedByHelper) {
                        return String(resolvedByHelper);
                    }
                }
            }

            var controllerContext = getControllerContext(ctx);
            var contextJobId = extractJobId(controllerContext, configuredJobKey);
            if (contextJobId) {
                return contextJobId;
            }

            var jobIds = ctx && (ctx.jobIds || ctx.jobs);
            if (jobIds && typeof jobIds === "object") {
                for (var index = 0; index < jobKeyCandidates.length; index += 1) {
                    var key = jobKeyCandidates[index];
                    if (Object.prototype.hasOwnProperty.call(jobIds, key) && jobIds[key] !== null && jobIds[key] !== undefined) {
                        var normalized = String(jobIds[key]).trim();
                        if (normalized) {
                            return normalized;
                        }
                    }
                }
            }
            return null;
        }

        function emitCatalogLoaded() {
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("features_export:catalog:loaded", {
                    families: familyOrder(),
                    layerCount: controller.state.layers.length
                });
            }
        }

        var baseTriggerEvent = controller.triggerEvent.bind(controller);
        controller.triggerEvent = function triggerEvent(eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === COMPLETION_EVENT) {
                if (!controller._completion_seen) {
                    controller._completion_seen = true;
                    handleCompletion(payload || null, "completion-event");
                }
            } else if (normalized === "JOB:COMPLETED") {
                if (!controller._completion_seen) {
                    controller._completion_seen = true;
                    handleCompletion(payload || null, "job-completed");
                }
            } else if (normalized === "JOB:ERROR") {
                showStacktracePanel();
                controller.append_status_message(controller, "Features export failed. Review stack trace for details.");
                if (controller.events && typeof controller.events.emit === "function") {
                    controller.events.emit("features_export:error", {
                        job_id: controller.rq_job_id || null,
                        error: payload || null
                    });
                }
            }
            return baseTriggerEvent(eventName, payload);
        };

        controller._rebindDomReferences = rebindDomReferences;
        controller._attachDelegates = attachDelegates;
        controller._detachDelegates = clearDelegates;

        controller.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var rebindResult = controller._rebindDomReferences();

            if (!controller.form) {
                controller._detachDelegates();
                return controller;
            }

            controller._attachDelegates(Boolean(rebindResult && rebindResult.formChanged));

            readConfigNode();
            parseCatalogPayload();
            parseBootstrapPayload();
            emitCatalogLoaded();

            if (rebindResult && rebindResult.streamNodesChanged) {
                controller.detach_status_stream(controller);
            }
            if (!controller.statusStream || (rebindResult && rebindResult.streamNodesChanged)) {
                attachStatusStream();
            }

            updateSwatTables();
            rerender();

            var defaultsButton = getFieldNode(ACTIONS.loadDefaults);
            if (defaultsButton) {
                defaultsButton.disabled = !controller.state.layers.length || Boolean(getCatalogLoadError());
            }

            var jobId = resolveBootstrapJobId(ctx);
            if (jobId) {
                controller._completion_seen = false;
                controller._completion_jobinfo_job_id = null;
                controller._completion_jobinfo_inflight = null;
                controller.poll_completion_event = COMPLETION_EVENT;
            }
            controller.set_rq_job_id(controller, jobId || null);
            return controller;
        };

        return controller;
    }

    return {
        getInstance: function getInstance() {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        }
    };
}());

if (typeof globalThis !== "undefined") {
    globalThis.FeaturesExport = FeaturesExport;
}
