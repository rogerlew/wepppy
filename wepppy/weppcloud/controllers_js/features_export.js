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
        selectVisible: '[data-features-export-action="select-visible"]',
        clearSelection: '[data-features-export-action="clear-selection"]',
        clearFilters: '[data-features-export-action="clear-filters"]',
        toggleSwatTable: '[data-features-export-action="toggle-swat-table"]'
    };

    var FIELDS = {
        layerSearch: '[data-features-export-field="layer-search"]',
        format: '[data-features-export-field="format"]',
        units: '[data-features-export-field="units"]',
        crs: '[data-features-export-field="crs"]',
        outputScope: '[data-features-export-field="output-scope"]',
        temporalMode: '[data-features-export-field="temporal-mode"]',
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
                visibleLayerIds: [],
                filter: "all",
                search: "",
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

        function updateTemporalVisibility() {
            var mode = readCheckedRadio(FIELDS.temporalMode);
            var yearWrap = getFieldNode("[data-features-export-temporal-year-options]");
            var customWrap = getFieldNode("[data-features-export-temporal-custom-wrap]");
            var eventWrap = getFieldNode("[data-features-export-temporal-event-options]");
            var datesWrap = getFieldNode("[data-features-export-temporal-dates-wrap]");
            var returnPeriodsWrap = getFieldNode("[data-features-export-temporal-return-periods-wrap]");

            var isYearMode = mode === "annual_average" || mode === "yearly";
            if (yearWrap) {
                yearWrap.hidden = !isYearMode;
            }
            if (customWrap) {
                var yearSelection = readFieldValue(FIELDS.temporalYearSelection);
                customWrap.hidden = !isYearMode || yearSelection !== "custom";
            }

            var isEventMode = mode === "event";
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
        }

        function selectedLayers() {
            var selectedSet = selectedLayerSet();
            return controller.state.layers.filter(function (layer) {
                return selectedSet.has(layer.layer_id);
            });
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
            return {
                layer_id: layerId,
                label: rawLayer.label ? String(rawLayer.label) : layerId,
                family: family,
                family_label: rawLayer.family_label ? String(rawLayer.family_label) : familyLabel(family),
                scope_class: scopeClass,
                geometry_type: geometryType,
                temporal_modes: temporalModes,
                selector_requirements: requirements,
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

        function rowMatchesSearch(layer, searchTerm) {
            if (!searchTerm) {
                return true;
            }
            var haystack = [
                layer.layer_id,
                layer.label,
                layer.family,
                layer.family_label
            ].join(" ").toLowerCase();
            return haystack.indexOf(searchTerm) !== -1;
        }

        function rowMatchesFilter(layer, filterMode, selectedSet) {
            if (filterMode === "selected") {
                return selectedSet.has(layer.layer_id);
            }
            if (filterMode === "temporal") {
                return layer.temporal_modes.length > 0;
            }
            if (filterMode === "scope-aware") {
                return layer.scope_class === "scope_aware";
            }
            if (filterMode === "needs-selector") {
                return layer.selector_requirements.length > 0;
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

        function renderCatalog() {
            if (!controller.catalogListEl) {
                return;
            }

            var selectedSet = selectedLayerSet();
            var search = (controller.state.search || "").toLowerCase().trim();
            var filterMode = controller.state.filter || "all";
            var groups = {};
            var order = familyOrder();

            controller.state.layers.forEach(function (layer) {
                if (!groups[layer.family]) {
                    groups[layer.family] = [];
                }
                groups[layer.family].push(layer);
            });

            var visibleLayerIds = [];
            var htmlParts = [];
            var familyIndex = 0;
            order.concat(Object.keys(groups).filter(function (family) {
                return order.indexOf(family) === -1;
            })).forEach(function (family) {
                var layers = groups[family] || [];
                if (!layers.length) {
                    return;
                }

                var visibleRows = layers.filter(function (layer) {
                    return rowMatchesSearch(layer, search) && rowMatchesFilter(layer, filterMode, selectedSet);
                });
                var selectedCount = layers.filter(function (layer) {
                    return selectedSet.has(layer.layer_id);
                }).length;

                if (visibleRows.length) {
                    visibleRows.forEach(function (layer) {
                        visibleLayerIds.push(layer.layer_id);
                    });
                }

                var defaultOpen = familyIndex < 2;
                var isOpen = Object.prototype.hasOwnProperty.call(controller.state.familyOpen, family)
                    ? Boolean(controller.state.familyOpen[family])
                    : defaultOpen;
                familyIndex += 1;

                htmlParts.push(
                    '<details data-features-export-family data-family="' + escapeHtml(family) + '"' + (isOpen ? " open" : "") + '>'
                );
                htmlParts.push(
                    '<summary>'
                    + escapeHtml(familyLabel(family))
                    + ' (' + selectedCount + ' / ' + layers.length + ')'
                    + '</summary>'
                );

                if (!visibleRows.length) {
                    htmlParts.push('<p class="wc-field__help">No layers match current filters.</p>');
                } else {
                    visibleRows.forEach(function (layer) {
                        var checked = selectedSet.has(layer.layer_id) ? " checked" : "";
                        var scopeBadge = layer.scope_class === "scope_aware" ? "scope-aware" : "shared";
                        var temporal = temporalBadge(layer);
                        var selector = selectorBadge(layer);
                        htmlParts.push(
                            '<div class="wc-stack-sm" data-features-export-layer data-layer-id="' + escapeHtml(layer.layer_id)
                            + '" data-family="' + escapeHtml(layer.family)
                            + '" data-scope-class="' + escapeHtml(layer.scope_class)
                            + '">'
                        );
                        htmlParts.push(
                            '<label class="wc-toggle-inline">'
                            + '<input type="checkbox" data-features-export-action="toggle-layer" value="' + escapeHtml(layer.layer_id) + '"' + checked + '>'
                            + '<span><strong>' + escapeHtml(layer.label) + '</strong> '
                            + '<code>' + escapeHtml(layer.layer_id) + '</code>'
                            + '</span>'
                            + '</label>'
                        );
                        htmlParts.push(
                            '<p class="wc-field__help">'
                            + 'geometry: ' + escapeHtml(layer.geometry_type)
                            + ' | scope: ' + escapeHtml(scopeBadge)
                            + ' | temporal: ' + escapeHtml(temporal)
                            + (selector ? ' | selector: ' + escapeHtml(selector) : '')
                            + '</p>'
                        );
                        htmlParts.push("</div>");
                    });
                }

                htmlParts.push("</details>");
            });

            controller.state.visibleLayerIds = uniqueStrings(visibleLayerIds);
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
            var show = hasScenario || hasContrast;
            omniGroup.hidden = !show;

            var scenarioWrap = getFieldNode("[data-features-export-omni-scenario-wrap]");
            var contrastWrap = getFieldNode("[data-features-export-omni-contrast-wrap]");
            var omniTitle = controller.form.querySelector('[data-features-export-region="omni-title"]');

            if (scenarioWrap) {
                scenarioWrap.hidden = !hasScenario;
            }
            if (contrastWrap) {
                contrastWrap.hidden = !hasContrast;
            }
            if (omniTitle) {
                if (hasScenario && !hasContrast) {
                    omniTitle.textContent = "Omni Scenario";
                } else if (!hasScenario && hasContrast) {
                    omniTitle.textContent = "Omni Contrast";
                } else {
                    omniTitle.textContent = "Omni Selector";
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
                var temporalMode = readCheckedRadio(FIELDS.temporalMode);
                if (!temporalMode) {
                    errors.push({ group: "temporal", message: "Temporal mode is required when temporal layers are selected." });
                } else if (temporalMode === "annual_average" || temporalMode === "yearly") {
                    var yearSelection = readFieldValue(FIELDS.temporalYearSelection) || "all";
                    if (yearSelection === "custom") {
                        var customIndices = parseIntList(readFieldValue(FIELDS.temporalExcludeIndices));
                        if (!customIndices.length) {
                            errors.push({ group: "temporal", message: "Provide at least one custom excluded year index." });
                        }
                    }
                } else if (temporalMode === "event") {
                    var selector = readCheckedRadio(FIELDS.temporalEventSelector);
                    if (!selector) {
                        errors.push({ group: "temporal", message: "Event selector is required for event mode." });
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

                if (temporalMode) {
                    var incompatible = selected.filter(function (layer) {
                        return layer.temporal_modes.indexOf(temporalMode) === -1;
                    });
                    if (incompatible.length && incompatible.length < selected.length) {
                        warnings.push({
                            group: "temporal",
                            message: "Some selected layers do not support temporal mode " + temporalMode + " and may be skipped."
                        });
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
                if (hasScenario && hasContrast) {
                    errors.push({ group: "omni", message: "Omni scenario and contrast layer families cannot be mixed." });
                }
                if (hasScenario && !readFieldValue(FIELDS.scenario)) {
                    errors.push({ group: "omni", message: "Select an Omni scenario." });
                }
                if (hasContrast && !readFieldValue(FIELDS.contrastId)) {
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
            var payload = {
                selectedLayerIds: uniqueStrings(controller.state.selectedLayerIds),
                counts: {
                    selected: uniqueStrings(controller.state.selectedLayerIds).length,
                    visible: uniqueStrings(controller.state.visibleLayerIds).length,
                    total: controller.state.layers.length
                },
                visibleLayerIds: uniqueStrings(controller.state.visibleLayerIds)
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
            var mode = readCheckedRadio(FIELDS.temporalMode);
            var selected = selectedLayers();
            var compatible = [];
            var excluded = [];
            if (mode) {
                selected.forEach(function (layer) {
                    if (layer.temporal_modes.indexOf(mode) !== -1) {
                        compatible.push(layer.layer_id);
                    } else {
                        excluded.push(layer.layer_id);
                    }
                });
            }
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("features_export:temporal:changed", {
                    temporal: buildTemporalPayload(),
                    compatibleLayerIds: compatible,
                    excludedLayerIds: excluded
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
                    scenario: readFieldValue(FIELDS.scenario) || null,
                    contrast_id: readFieldValue(FIELDS.contrastId) || null
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

        function rerender() {
            captureFamilyOpenState();
            renderCatalog();
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
            var mode = readCheckedRadio(FIELDS.temporalMode);
            if (!mode) {
                return null;
            }
            var temporal = { mode: mode };
            if (mode === "annual_average" || mode === "yearly") {
                var yearSelection = readFieldValue(FIELDS.temporalYearSelection) || "all";
                temporal.year_selection = yearSelection;
                if (yearSelection === "custom") {
                    temporal.exclude_yr_indxs = parseIntList(readFieldValue(FIELDS.temporalExcludeIndices));
                }
            } else if (mode === "event") {
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

            if (!controller.groups.omni.hidden) {
                var selectedFamiliesSet = selectedFamilies();
                if (selectedFamiliesSet.has("omni_scenarios")) {
                    var scenario = readFieldValue(FIELDS.scenario);
                    if (scenario) {
                        payload.scenario = scenario;
                    }
                }
                if (selectedFamiliesSet.has("omni_contrasts")) {
                    var contrastId = readFieldValue(FIELDS.contrastId);
                    if (contrastId) {
                        payload.contrast_id = contrastId;
                    }
                }
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
                    var body = response && response.body !== undefined ? response.body : response;
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
                rerender();
            }));

            controller._delegates.push(dom.delegate(controller.form, "click", FILTER_SELECTOR, function (event, target) {
                event.preventDefault();
                controller.state.filter = String(target.getAttribute("data-features-export-filter") || "all");
                rerender();
            }));

            controller._delegates.push(dom.delegate(controller.form, "input", FIELDS.layerSearch, function (_event, target) {
                controller.state.search = String(target.value || "");
                rerender();
            }));

            controller._delegates.push(dom.delegate(controller.form, "click", ACTIONS.clearFilters, function (event) {
                event.preventDefault();
                controller.state.filter = "all";
                controller.state.search = "";
                setSelectOrInput(FIELDS.layerSearch, "");
                rerender();
            }));

            controller._delegates.push(dom.delegate(controller.form, "click", ACTIONS.selectVisible, function (event) {
                event.preventDefault();
                addSelectedLayers(controller.state.visibleLayerIds);
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

            controller._delegates.push(dom.delegate(controller.form, "change", FIELDS.format + ", " + FIELDS.units + ", " + FIELDS.crs + ", " + FIELDS.outputScope + ", " + FIELDS.temporalMode + ", " + FIELDS.temporalYearSelection + ", " + FIELDS.temporalEventSelector + ", " + FIELDS.scenario + ", " + FIELDS.contrastId + ", " + FIELDS.swatRunId + ", " + FIELDS.swatTableMode, function () {
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

            setRadioValue(FIELDS.temporalMode, "");
            setSelectOrInput(FIELDS.temporalYearSelection, "all");
            setSelectOrInput(FIELDS.temporalExcludeIndices, "");
            setRadioValue(FIELDS.temporalEventSelector, "");
            setSelectOrInput(FIELDS.temporalEventDates, "");
            setSelectOrInput(FIELDS.temporalEventReturnPeriods, "");
            changedFields.push("temporal");

            setSelectOrInput(FIELDS.scenario, "");
            setSelectOrInput(FIELDS.contrastId, "");
            changedFields.push("omni");

            setSelectOrInput(FIELDS.swatRunId, profile.swat_run_id || "latest");
            setSelectOrInput(FIELDS.swatTableMode, "all");
            controller.state.selectedSwatTables = [];
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
            var config = {
                jobKey: "run_features_export",
                channel: STATUS_CHANNEL,
                submitUrl: "/rq-engine/api/runs/" + encodeURIComponent(window.runid || window.runId || "") + "/" + encodeURIComponent(window.config || "") + "/export/features",
                downloadUrlTemplate: "/rq-engine/api/runs/" + encodeURIComponent(window.runid || window.runId || "") + "/" + encodeURIComponent(window.config || "") + "/export/features/__JOB_ID__/download",
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
                    var body = response && response.body !== undefined ? response.body : response;
                    if (!body || body.error || body.errors || !body.job_id) {
                        controller.pushResponseStacktrace(controller, body || { error: { message: "Submit failed." } });
                        showStacktracePanel();
                        controller.disconnect_status_stream(controller);
                        if (controller.events && typeof controller.events.emit === "function") {
                            controller.events.emit("features_export:error", {
                                job_id: null,
                                error: body || null
                            });
                        }
                        controller.triggerEvent("job:error", {
                            payload: payload,
                            error: body || null,
                            task: "features_export:submit"
                        });
                        return;
                    }

                    var jobId = String(body.job_id);
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
                logLimit: 300
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
            var resolvedByHelper = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "run_features_export")
                : null;
            if (resolvedByHelper) {
                return String(resolvedByHelper);
            }

            var controllerContext = getControllerContext(ctx);
            if (controllerContext && controllerContext.job_id) {
                return String(controllerContext.job_id);
            }

            var jobIds = ctx && (ctx.jobIds || ctx.jobs);
            if (jobIds && typeof jobIds === "object" && jobIds.run_features_export) {
                return String(jobIds.run_features_export);
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
