/* ----------------------------------------------------------------------------
 * LanduseModify
 * Doc: controllers_js/README.md — Landuse Modify Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var LanduseModify = (function () {
    var instance;

    var EVENT_NAMES = [
        "landuse:modify:started",
        "landuse:modify:completed",
        "landuse:modify:error",
        "landuse:selection:changed",
        "job:started",
        "job:completed",
        "job:error"
    ];

    var DEFAULT_STYLE = {
        color: "white",
        opacity: 1,
        weight: 1,
        fillColor: "#FFEDA0",
        fillOpacity: 0.0
    };

    var SELECTED_STYLE = {
        color: "red",
        opacity: 1,
        weight: 2,
        fillOpacity: 0.0
    };

    var HOVER_STYLE = {
        weight: 2,
        color: "#666",
        dashArray: "",
        fillOpacity: 0.0
    };

    var DRILLDOWN_SUPPRESSION_TOKEN = "landuse-modify";

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function") {
            throw new Error("LanduseModify controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.formToJSON !== "function") {
            throw new Error("LanduseModify controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("LanduseModify controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("LanduseModify controller requires WCEvents helpers.");
        }

        return { dom: dom, forms: forms, http: http, events: events };
    }

    function createLegacyAdapter(element) {
        if (!element) {
            return {
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
            length: 1,
            show: function () {
                element.hidden = false;
                if (element.style.display === "none") {
                    element.style.removeProperty("display");
                }
            },
            hide: function () {
                element.hidden = true;
                element.style.display = "none";
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
            var payload = body;
            if (payload.Error === undefined) {
                var fallback =
                    payload.detail ||
                    payload.message ||
                    payload.error ||
                    payload.errors;
                if (fallback !== undefined && fallback !== null) {
                    payload = Object.assign({}, payload, { Error: fallback });
                }
            }
            if (payload.StackTrace !== undefined || payload.Error !== undefined) {
                return payload;
            }
        } else if (typeof body === "string" && body) {
            return { Error: body };
        }

        if (error && typeof error === "object" && (error.Error !== undefined || error.StackTrace !== undefined)) {
            return error;
        }

        if (http && typeof http.isHttpError === "function" && http.isHttpError(error)) {
            var detail = error && (error.detail || error.message);
            return { Error: detail || "Request failed" };
        }

        return { Error: (error && error.message) || "Request failed" };
    }

    function normalizeTopazId(value) {
        if (value === null || value === undefined) {
            return null;
        }
        var token = String(value).trim();
        if (!token) {
            return null;
        }
        var parsed = parseInt(token, 10);
        if (Number.isNaN(parsed)) {
            return null;
        }
        return String(parsed);
    }

    function parseTopazField(value) {
        if (value === null || value === undefined) {
            return [];
        }
        if (Array.isArray(value)) {
            return value.map(normalizeTopazId).filter(Boolean);
        }
        var tokens = String(value).split(/[\s,]+/);
        return tokens.map(normalizeTopazId).filter(Boolean);
    }

    function sortIds(ids) {
        return ids.slice().sort(function (a, b) {
            var left = parseInt(a, 10);
            var right = parseInt(b, 10);
            if (Number.isNaN(left) || Number.isNaN(right)) {
                return a.localeCompare(b);
            }
            return left - right;
        });
    }

    function getMapController() {
        try {
            if (window.MapController && typeof window.MapController.getInstance === "function") {
                return window.MapController.getInstance();
            }
        } catch (err) {
            console.warn("LanduseModify unable to load MapController", err);
        }
        return null;
    }

    function refreshDependentControllers() {
        try {
            if (window.SubcatchmentDelineation && typeof window.SubcatchmentDelineation.getInstance === "function") {
                var subCtrl = window.SubcatchmentDelineation.getInstance();
                if (subCtrl && typeof subCtrl.getCmapMode === "function" && subCtrl.getCmapMode() === "dom_lc" &&
                    typeof subCtrl.setColorMap === "function") {
                    subCtrl.setColorMap("dom_lc");
                }
            }
        } catch (err) {
            console.warn("LanduseModify: SubcatchmentDelineation refresh failed", err);
        }

        try {
            if (window.Landuse && typeof window.Landuse.getInstance === "function") {
                var landuseController = window.Landuse.getInstance();
                if (landuseController && typeof landuseController.report === "function") {
                    landuseController.report();
                }
            }
        } catch (err2) {
            console.warn("LanduseModify: Landuse report refresh failed", err2);
        }
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var eventsApi = helpers.events;

        var modify = controlBase();
        var emitter = eventsApi.useEventMap(EVENT_NAMES, eventsApi.createEmitter());

        var formElement = dom.ensureElement("#modify_landuse_form", "Modify Landuse form not found.");
        var statusElement = dom.qs("#modify_landuse_form #status");
        var stacktraceElement = dom.qs("#modify_landuse_form #stacktrace");
        var rqJobElement = dom.qs("#modify_landuse_form #rq_job");
        var checkboxElement = dom.ensureElement(
            '#modify_landuse_form [data-landuse-modify-action="toggle-selection"]',
            "Modify Landuse selection toggle not found."
        );
        var textareaElement = dom.ensureElement(
            '#modify_landuse_form [data-landuse-modify-field="topaz-ids"]',
            "Modify Landuse topaz field not found."
        );
        var selectionElement = dom.ensureElement(
            '#modify_landuse_form [data-landuse-modify-field="landuse-code"]',
            "Modify Landuse selection dropdown not found."
        );
        var submitElement = dom.ensureElement(
            '#modify_landuse_form [data-landuse-modify-action="submit"]',
            "Modify Landuse submit button not found."
        );

        function tryApplyValues(values) {
            if (!forms || !formElement) {
                return false;
            }
            var tagName = formElement.tagName ? String(formElement.tagName).toLowerCase() : "";
            if (tagName === "form") {
                try {
                    forms.applyValues(formElement, values);
                    return true;
                } catch (err) {
                    console.warn("LanduseModify unable to apply values via WCForms", err);
                }
            }
            return false;
        }

        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);

        modify.form = formElement;
        modify.status = statusAdapter;
        modify.stacktrace = stacktraceAdapter;
        modify.rq_job = rqJobAdapter;
        modify.checkbox = checkboxElement;
        modify.textarea = textareaElement;
        modify.selection = selectionElement;
        modify.command_btn_id = submitElement.id || "btn_modify_landuse";
        modify.events = emitter;

        modify.hideStacktrace = function () {
            if (stacktraceAdapter && typeof stacktraceAdapter.hide === "function") {
                stacktraceAdapter.hide();
                return;
            }
            if (!stacktraceElement) {
                return;
            }
            stacktraceElement.hidden = true;
            if (stacktraceElement.style) {
                stacktraceElement.style.display = "none";
            }
        };

        var selectionSet = new Set();
        var selectionModeActive = false;
        var suppressSelectionSync = false;
        var suppressToggleSync = false;
        var mapSuppressionApplied = false;
        var geoJsonData = null;
        var geoLayer = null;
        var selectionRectangle = null;
        var dragStart = null;
        var layerIndex = Object.create(null);

        modify.selected = selectionSet;
        modify.data = geoJsonData;
        modify.glLayer = geoLayer;
        modify.selectionRect = selectionRectangle;
        modify.isSelectionModeActive = function () {
            return selectionModeActive;
        };

        function updateSelectionRect(map, bounds) {
            if (!map || !bounds) {
                return;
            }
            if (!selectionRectangle) {
                selectionRectangle = L.rectangle(bounds, { color: "blue", weight: 1 }).addTo(map);
            } else if (typeof selectionRectangle.setBounds === "function") {
                selectionRectangle.setBounds(bounds);
            }
            modify.selectionRect = selectionRectangle;
        }

        function clearSelectionRect(map) {
            if (selectionRectangle && map) {
                map.removeLayer(selectionRectangle);
            }
            selectionRectangle = null;
            modify.selectionRect = null;
        }

        function applyStylesToLayer(id) {
            var key = String(id);
            var layer = layerIndex[key];
            if (!layer || typeof layer.setStyle !== "function") {
                return;
            }
            if (selectionSet.has(key)) {
                layer.setStyle(SELECTED_STYLE);
            } else {
                layer.setStyle(DEFAULT_STYLE);
            }
        }

        function refreshLayerStyles() {
            Object.keys(layerIndex).forEach(function (key) {
                applyStylesToLayer(key);
            });
        }

        function syncTextarea(ids) {
            suppressSelectionSync = true;
            try {
                var value = ids.length ? ids.join(", ") : "";
                if (!tryApplyValues({ textarea_modify_landuse: value }) && textareaElement) {
                    textareaElement.value = value;
                }
            } finally {
                suppressSelectionSync = false;
            }
        }

        function emitSelectionChanged(ids, source, silent) {
            if (silent) {
                return;
            }
            emitter.emit("landuse:selection:changed", {
                topazIds: ids.slice(),
                source: source || "unknown"
            });
        }

        function applySelection(ids, options) {
            var opts = options || {};
            var unique = [];
            var seen = Object.create(null);
            ids.forEach(function (value) {
                var normalized = normalizeTopazId(value);
                if (!normalized || seen[normalized]) {
                    return;
                }
                seen[normalized] = true;
                unique.push(normalized);
            });
            var sorted = sortIds(unique);

            var changed = sorted.length !== selectionSet.size;
            if (!changed) {
                sorted.some(function (id) {
                    if (!selectionSet.has(id)) {
                        changed = true;
                    }
                    return !selectionSet.has(id);
                });
            }

            if (changed) {
                selectionSet.clear();
                sorted.forEach(function (id) {
                    selectionSet.add(id);
                });
            }

            syncTextarea(sorted);
            refreshLayerStyles();
            emitSelectionChanged(sorted, opts.source, opts.silent);

            return sorted;
        }

        function parseTextarea(value, options) {
            return applySelection(parseTopazField(value), options);
        }

        function ensureInitialSelection() {
            var initialValue = textareaElement ? textareaElement.value : "";
            if (initialValue) {
                parseTextarea(initialValue, { source: "initial", silent: true });
            } else {
                syncTextarea([]);
            }
        }

        function handleFeatureClick(topazId) {
            var ids = Array.from(selectionSet);
            var index = ids.indexOf(topazId);
            if (index !== -1) {
                ids.splice(index, 1);
            } else {
                ids.push(topazId);
            }
            applySelection(ids, { source: "map" });
        }

        function handleSubIntersection(topazIds) {
            var current = Array.from(selectionSet);
            (Array.isArray(topazIds) ? topazIds : []).forEach(function (value) {
                var normalized = normalizeTopazId(value);
                if (!normalized) {
                    return;
                }
                var idx = current.indexOf(normalized);
                if (idx === -1) {
                    current.push(normalized);
                } else {
                    current.splice(idx, 1);
                }
            });
            applySelection(current, { source: "box-select" });
        }

        function buildGeoLayerFeatures(data) {
            var map = getMapController();
            if (!map || !data || !data.features) {
                return;
            }
            layerIndex = Object.create(null);
            if (geoLayer) {
                map.removeLayer(geoLayer);
            }
            geoLayer = L.geoJSON(data.features, {
                style: DEFAULT_STYLE,
                onEachFeature: function (feature, layer) {
                    if (!feature || !feature.properties) {
                        return;
                    }
                    var topazId = normalizeTopazId(feature.properties.TopazID);
                    if (!topazId) {
                        return;
                    }
                    layerIndex[topazId] = layer;

                    layer.on({
                        mouseover: function () {
                            if (typeof layer.setStyle === "function") {
                                layer.setStyle(HOVER_STYLE);
                            }
                        },
                        mouseout: function () {
                            applyStylesToLayer(topazId);
                        },
                        click: function (event) {
                            if (event && event.originalEvent) {
                                event.originalEvent.preventDefault();
                                event.originalEvent.stopPropagation();
                            }
                            handleFeatureClick(topazId);
                        }
                    });

                    applyStylesToLayer(topazId);
                }
            });
            geoLayer.addTo(map);
            modify.glLayer = geoLayer;
        }

        function loadSubcatchments() {
            return http.getJson(url_for_run("resources/subcatchments.json"), {
                params: { _: Date.now() },
                form: formElement
            }).then(function (data) {
                geoJsonData = data || null;
                modify.data = geoJsonData;
                buildGeoLayerFeatures(geoJsonData);
            }).catch(function (error) {
                var payload = toResponsePayload(http, error);
                modify.pushResponseStacktrace(modify, payload);
                suppressToggleSync = true;
                try {
                    if (!tryApplyValues({ checkbox_modify_landuse: false }) && checkboxElement) {
                        checkboxElement.checked = false;
                    }
                } finally {
                    suppressToggleSync = false;
                }
                setSelectionMode(false);
            });
        }

        function onMapMouseDown(event) {
            if (!selectionModeActive) {
                return;
            }
            dragStart = event && event.latlng ? event.latlng : null;
        }

        function onMapMouseMove(event) {
            if (!selectionModeActive) {
                return;
            }
            var map = getMapController();
            if (!map) {
                return;
            }
            if (!dragStart) {
                clearSelectionRect(map);
                return;
            }
            if (!event || !event.latlng) {
                return;
            }
            var bounds = L.latLngBounds(dragStart, event.latlng);
            updateSelectionRect(map, bounds);
        }

        function onMapMouseUp(event) {
            if (!selectionModeActive) {
                dragStart = null;
                return;
            }
            var map = getMapController();
            if (!map) {
                dragStart = null;
                return;
            }
            if (!dragStart || !event || !event.latlng) {
                dragStart = null;
                clearSelectionRect(map);
                return;
            }
            var ll0 = dragStart;
            var ll1 = event.latlng;
            dragStart = null;

            if (ll0.lat === ll1.lat && ll0.lng === ll1.lng) {
                clearSelectionRect(map);
                return;
            }

            var bounds = L.latLngBounds(ll0, ll1);
            var sw = bounds.getSouthWest();
            var ne = bounds.getNorthEast();
            var extent = [sw.lng, sw.lat, ne.lng, ne.lat];

            http.postJson(url_for_run("tasks/sub_intersection/"), { extent: extent }, { form: formElement })
                .then(function (response) {
                    var payload = response.body;
                    handleSubIntersection(payload);
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    modify.pushResponseStacktrace(modify, payload);
                    emitter.emit("landuse:modify:error", {
                        context: "box-select",
                        error: payload
                    });
                })
                .then(function () {
                    clearSelectionRect(map);
                });
        }

        function attachMapListeners() {
            var map = getMapController();
            if (!map) {
                return;
            }
            if (typeof map.suppressDrilldown === "function" && !mapSuppressionApplied) {
                map.suppressDrilldown(DRILLDOWN_SUPPRESSION_TOKEN);
                mapSuppressionApplied = true;
            }
            map.boxZoom.disable();
            map.on("mousedown", onMapMouseDown);
            map.on("mousemove", onMapMouseMove);
            map.on("mouseup", onMapMouseUp);
        }

        function detachMapListeners() {
            var map = getMapController();
            if (!map) {
                return;
            }
            map.boxZoom.enable();
            map.off("mousedown", onMapMouseDown);
            map.off("mousemove", onMapMouseMove);
            map.off("mouseup", onMapMouseUp);
            if (geoLayer) {
                map.removeLayer(geoLayer);
            }
            geoLayer = null;
            modify.glLayer = null;
            layerIndex = Object.create(null);
            clearSelectionRect(map);
            if (mapSuppressionApplied && typeof map.releaseDrilldown === "function") {
                map.releaseDrilldown(DRILLDOWN_SUPPRESSION_TOKEN);
                mapSuppressionApplied = false;
            }
        }

        function setSelectionMode(enabled) {
            var targetState = Boolean(enabled);
            if (selectionModeActive === targetState) {
                return;
            }
            selectionModeActive = targetState;
            if (selectionModeActive) {
                attachMapListeners();
                if (geoJsonData) {
                    buildGeoLayerFeatures(geoJsonData);
                } else {
                    loadSubcatchments();
                }
            } else {
                detachMapListeners();
            }
        }

        function setStatusMessage(message) {
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(message);
            } else if (statusElement) {
                statusElement.textContent = message;
            }
        }

        function submitModification() {
            var taskMsg = "Modifying landuse";
            setStatusMessage(taskMsg + "...");
            modify.hideStacktrace();

            var formSnapshot;
            try {
                formSnapshot = forms.formToJSON(formElement);
            } catch (err) {
                formSnapshot = { textarea_modify_landuse: textareaElement ? textareaElement.value : "" };
            }

            var ids = Array.from(selectionSet);
            var landuseValue = normalizeTopazId(formSnapshot.selection_modify_landuse || selectionElement.value);
            if (!landuseValue) {
                var payload = { Error: "Select a landuse value before modifying." };
                modify.pushResponseStacktrace(modify, payload);
                emitter.emit("landuse:modify:error", { error: payload });
                return;
            }

            emitter.emit("landuse:modify:started", {
                topazIds: ids.slice(),
                landuse: landuseValue
            });
            modify.triggerEvent("job:started", {
                task: "landuse:modify",
                payload: { topazIds: ids.slice(), landuse: landuseValue }
            });

            http.postJson(url_for_run("tasks/modify_landuse/"), {
                topaz_ids: ids,
                landuse: landuseValue
            }, { form: formElement }).then(function (response) {
                var payload = response.body || {};
                if (payload.Success === true || payload.success === true) {
                    applySelection([], { source: "modify", silent: true });

                    suppressToggleSync = true;
                    try {
                        if (!tryApplyValues({ checkbox_modify_landuse: false }) && checkboxElement) {
                            checkboxElement.checked = false;
                        }
                        if (checkboxElement) {
                            checkboxElement.checked = false;
                        }
                    } finally {
                        suppressToggleSync = false;
                    }
                    setSelectionMode(false);

                    setStatusMessage(taskMsg + "... Success");
                    emitter.emit("landuse:modify:completed", {
                        topazIds: ids.slice(),
                        landuse: landuseValue,
                        response: payload
                    });
                    modify.triggerEvent("job:completed", {
                        task: "landuse:modify",
                        payload: { topazIds: ids.slice(), landuse: landuseValue },
                        response: payload
                    });
                    modify.triggerEvent("LANDCOVER_MODIFY_TASK_COMPLETED", {
                        topazIds: ids.slice(),
                        landuse: landuseValue
                    });
                    refreshDependentControllers();
                } else {
                    modify.pushResponseStacktrace(modify, payload);
                    emitter.emit("landuse:modify:error", { error: payload });
                    modify.triggerEvent("job:error", {
                        task: "landuse:modify",
                        payload: { topazIds: ids.slice(), landuse: landuseValue },
                        error: payload
                    });
                }
            }).catch(function (error) {
                var payload = toResponsePayload(http, error);
                modify.pushResponseStacktrace(modify, payload);
                emitter.emit("landuse:modify:error", { error: payload });
                modify.triggerEvent("job:error", {
                    task: "landuse:modify",
                    payload: { topazIds: ids.slice(), landuse: landuseValue },
                    error: payload
                });
            });
        }

        var baseTriggerEvent = modify.triggerEvent.bind(modify);
        modify.triggerEvent = function (eventName, payload) {
            if (eventName === "LANDCOVER_MODIFY_TASK_COMPLETED") {
                try {
                    refreshDependentControllers();
                } catch (err) {
                    console.warn("LanduseModify: dependent controller refresh failed", err);
                }
            }
            baseTriggerEvent(eventName, payload);
        };

        dom.delegate(formElement, "click", '[data-landuse-modify-action="submit"]', function (event) {
            event.preventDefault();
            submitModification();
        });

        dom.delegate(formElement, "change", '[data-landuse-modify-action="toggle-selection"]', function (event, matched) {
            if (suppressToggleSync) {
                return;
            }
            var checkbox = matched || event.target;
            setSelectionMode(Boolean(checkbox && checkbox.checked));
        });

        dom.delegate(formElement, "input", '[data-landuse-modify-field="topaz-ids"]', function (event, matched) {
            if (suppressSelectionSync) {
                return;
            }
            var value = matched ? matched.value : "";
            parseTextarea(value, { source: "manual" });
        });

        dom.delegate(formElement, "change", '[data-landuse-modify-field="landuse-code"]', function () {
            emitter.emit("landuse:selection:changed", {
                topazIds: Array.from(selectionSet),
                source: "landuse-code"
            });
        });

        ensureInitialSelection();
        if (checkboxElement && checkboxElement.checked) {
            setSelectionMode(true);
        }

        return modify;
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
    globalThis.LanduseModify = LanduseModify;
}
