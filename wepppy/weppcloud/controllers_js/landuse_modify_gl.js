/* ----------------------------------------------------------------------------
 * LanduseModify (Deck.gl)
 * ----------------------------------------------------------------------------
 */
var LanduseModify = (function () {
    "use strict";

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
        color: "#ffffff",
        opacity: 1,
        weight: 1,
        fillColor: "#FFEDA0",
        fillOpacity: 0.0
    };

    var SELECTED_STYLE = {
        color: "#ff0000",
        opacity: 1,
        weight: 2,
        fillColor: "#ff0000",
        fillOpacity: 0.15
    };

    var HOVER_STYLE = {
        color: "#666666",
        opacity: 0.6
    };

    var DRILLDOWN_SUPPRESSION_TOKEN = "landuse-modify";
    var LAYER_ID = "wc-landuse-modify";
    var SELECTION_BOX_LAYER_ID = "wc-landuse-selection-box";
    var EMPTY_GEOJSON = { type: "FeatureCollection", features: [] };

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function") {
            throw new Error("LanduseModify GL requires WCDom helpers.");
        }
        if (!forms || typeof forms.formToJSON !== "function") {
            throw new Error("LanduseModify GL requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("LanduseModify GL requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("LanduseModify GL requires WCEvents helpers.");
        }

        return { dom: dom, forms: forms, http: http, events: events };
    }

    function ensureControlBase() {
        if (typeof window.controlBase !== "function") {
            throw new Error("LanduseModify GL requires controlBase.");
        }
        return window.controlBase;
    }

    function ensureDeck() {
        var deckApi = window.deck;
        if (!deckApi || typeof deckApi.GeoJsonLayer !== "function") {
            throw new Error("LanduseModify GL requires deck.gl GeoJsonLayer.");
        }
        return deckApi;
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

    function hexToRgba(hex, alpha) {
        var normalized = String(hex || "").replace("#", "");
        if (normalized.length === 3) {
            normalized = normalized[0] + normalized[0]
                + normalized[1] + normalized[1]
                + normalized[2] + normalized[2];
        }
        var intVal = parseInt(normalized, 16);
        if (!Number.isFinite(intVal)) {
            return [0, 0, 0, Math.round(alpha * 255)];
        }
        var r = (intVal >> 16) & 255;
        var g = (intVal >> 8) & 255;
        var b = intVal & 255;
        return [r, g, b, Math.round(alpha * 255)];
    }

    function getMapController() {
        try {
            if (window.MapController && typeof window.MapController.getInstance === "function") {
                return window.MapController.getInstance();
            }
        } catch (err) {
            console.warn("LanduseModify GL unable to load MapController", err);
        }
        return null;
    }

    function resolveMapElement(dom) {
        return dom.qs("#mapid");
    }

    function resolveMapCanvas(mapElement) {
        if (!mapElement) {
            return null;
        }
        var canvas = mapElement.querySelector("canvas");
        return canvas || mapElement;
    }

    function resolveEventLatLng(event, mapElement, map) {
        if (!event || !map || !map._deck) {
            return null;
        }
        var deckInstance = map._deck;
        var canvas = null;
        if (typeof deckInstance.getCanvas === "function") {
            canvas = deckInstance.getCanvas();
        } else if (deckInstance.canvas) {
            canvas = deckInstance.canvas;
        }
        var rectTarget = canvas || mapElement;
        if (!rectTarget || typeof rectTarget.getBoundingClientRect !== "function") {
            return null;
        }
        var rect = rectTarget.getBoundingClientRect();
        var x = event.clientX - rect.left;
        var y = event.clientY - rect.top;
        if (!Number.isFinite(x) || !Number.isFinite(y)) {
            return null;
        }

        var coords = null;
        if (deckInstance.viewManager && typeof deckInstance.viewManager.unproject === "function") {
            coords = deckInstance.viewManager.unproject([x, y]);
        } else if (typeof deckInstance.getViewports === "function") {
            var viewports = deckInstance.getViewports();
            var viewport = viewports && viewports.length ? viewports[0] : null;
            if (viewport && typeof viewport.unproject === "function") {
                coords = viewport.unproject([x - (viewport.x || 0), y - (viewport.y || 0)]);
            }
        } else if (typeof deckInstance.unproject === "function") {
            coords = deckInstance.unproject([x, y]);
        }

        if (!coords || coords.length < 2) {
            return null;
        }
        var lng = Number(coords[0]);
        var lat = Number(coords[1]);
        if (!Number.isFinite(lng) || !Number.isFinite(lat)) {
            return null;
        }
        return { lat: lat, lng: lng };
    }

    function buildSelectionBounds(sw, ne) {
        if (!sw || !ne) {
            return null;
        }
        return {
            sw: { lat: Math.min(sw.lat, ne.lat), lng: Math.min(sw.lng, ne.lng) },
            ne: { lat: Math.max(sw.lat, ne.lat), lng: Math.max(sw.lng, ne.lng) }
        };
    }

    function buildSelectionPolygon(bounds) {
        if (!bounds) {
            return null;
        }
        var sw = bounds.sw;
        var ne = bounds.ne;
        return [
            [sw.lng, sw.lat],
            [ne.lng, sw.lat],
            [ne.lng, ne.lat],
            [sw.lng, ne.lat],
            [sw.lng, sw.lat]
        ];
    }

    function buildSelectionBoxLayer(deckApi, bounds) {
        var polygon = buildSelectionPolygon(bounds);
        if (!polygon) {
            return null;
        }
        return new deckApi.GeoJsonLayer({
            id: SELECTION_BOX_LAYER_ID,
            data: {
                type: "FeatureCollection",
                features: [
                    {
                        type: "Feature",
                        properties: {},
                        geometry: {
                            type: "Polygon",
                            coordinates: [polygon]
                        }
                    }
                ]
            },
            pickable: false,
            stroked: true,
            filled: true,
            lineWidthUnits: "pixels",
            lineWidthMinPixels: 1,
            getLineWidth: function () { return 2; },
            getLineColor: function () { return hexToRgba("#1e90ff", 1); },
            getFillColor: function () { return hexToRgba("#1e90ff", 0.08); }
        });
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var controlBase = ensureControlBase();
        var deckApi = ensureDeck();
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
            "Modify Landuse selection textarea not found."
        );
        var selectionElement = dom.ensureElement(
            '#modify_landuse_form [data-landuse-modify-field="landuse-code"]',
            "Modify Landuse selection dropdown not found."
        );
        var submitElement = dom.ensureElement(
            '#modify_landuse_form [data-landuse-modify-action="submit"]',
            "Modify Landuse submit button not found."
        );

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
        var selectionRectLayer = null;
        var dragStart = null;
        var lastMoveLogTime = 0;
        var mapElement = resolveMapElement(dom);
        var mapCanvas = null;
        var mapDragTarget = null;

        modify.selected = selectionSet;
        modify.data = geoJsonData;
        modify.glLayer = geoLayer;
        modify.selectionRect = selectionRectLayer;
        modify.isSelectionModeActive = function () {
            return selectionModeActive;
        };

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
                    console.warn("LanduseModify GL unable to apply values via WCForms", err);
                }
            }
            return false;
        }

        function addLayer(map, layer) {
            if (!map || !layer || typeof map.addLayer !== "function") {
                return;
            }
            map.addLayer(layer, { skipRefresh: true });
        }

        function removeLayer(map, layer) {
            if (!map || !layer || typeof map.removeLayer !== "function") {
                return;
            }
            map.removeLayer(layer, { skipOverlay: true });
        }

        function updateSelectionRect(map, bounds) {
            if (!map || !bounds) {
                return;
            }
            var nextLayer = buildSelectionBoxLayer(deckApi, bounds);
            if (!nextLayer) {
                return;
            }
            if (selectionRectLayer) {
                removeLayer(map, selectionRectLayer);
            }
            selectionRectLayer = nextLayer;
            modify.selectionRect = selectionRectLayer;
            addLayer(map, selectionRectLayer);
        }

        function clearSelectionRect(map) {
            if (selectionRectLayer && map) {
                removeLayer(map, selectionRectLayer);
            }
            selectionRectLayer = null;
            modify.selectionRect = null;
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

        function selectionKey() {
            return sortIds(Array.from(selectionSet)).join("|");
        }

        function buildGeoLayer(data) {
            var key = selectionKey();
            var defaultLineColor = hexToRgba(DEFAULT_STYLE.color, DEFAULT_STYLE.opacity);
            var defaultFillColor = hexToRgba(DEFAULT_STYLE.fillColor, DEFAULT_STYLE.fillOpacity);
            var selectedLineColor = hexToRgba(SELECTED_STYLE.color, SELECTED_STYLE.opacity);
            var selectedFillColor = hexToRgba(SELECTED_STYLE.fillColor, SELECTED_STYLE.fillOpacity);
            var highlightColor = hexToRgba(HOVER_STYLE.color, HOVER_STYLE.opacity);
            return new deckApi.GeoJsonLayer({
                id: LAYER_ID,
                data: data || EMPTY_GEOJSON,
                pickable: true,
                autoHighlight: true,
                highlightColor: highlightColor,
                stroked: true,
                filled: true,
                lineWidthUnits: "pixels",
                lineWidthMinPixels: 1,
                getLineWidth: function (feature) {
                    var id = feature && feature.properties ? normalizeTopazId(feature.properties.TopazID) : null;
                    return selectionSet.has(id) ? SELECTED_STYLE.weight : DEFAULT_STYLE.weight;
                },
                getLineColor: function (feature) {
                    var id = feature && feature.properties ? normalizeTopazId(feature.properties.TopazID) : null;
                    return selectionSet.has(id) ? selectedLineColor : defaultLineColor;
                },
                getFillColor: function (feature) {
                    var id = feature && feature.properties ? normalizeTopazId(feature.properties.TopazID) : null;
                    return selectionSet.has(id) ? selectedFillColor : defaultFillColor;
                },
                updateTriggers: {
                    getLineWidth: [key],
                    getLineColor: [key],
                    getFillColor: [key]
                },
                onClick: function (info) {
                    if (!selectionModeActive) {
                        return;
                    }
                    var feature = info && info.object ? info.object : null;
                    var topazId = feature && feature.properties ? normalizeTopazId(feature.properties.TopazID) : null;
                    if (!topazId) {
                        return;
                    }
                    handleFeatureClick(topazId);
                }
            });
        }

        function rebuildGeoLayer() {
            if (!selectionModeActive || !geoJsonData) {
                return;
            }
            var map = getMapController();
            if (!map) {
                return;
            }
            if (geoLayer) {
                removeLayer(map, geoLayer);
            }
            geoLayer = buildGeoLayer(geoJsonData);
            modify.glLayer = geoLayer;
            addLayer(map, geoLayer);
            if (selectionRectLayer) {
                removeLayer(map, selectionRectLayer);
                addLayer(map, selectionRectLayer);
            }
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
            rebuildGeoLayer();
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

        function loadSubcatchments() {
            return http.getJson(url_for_run("resources/subcatchments.json"), {
                params: { _: Date.now() },
                form: formElement
            }).then(function (data) {
                geoJsonData = data || null;
                modify.data = geoJsonData;
                rebuildGeoLayer();
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
                setSelectionMode(false, { clearSelection: true });
            });
        }

        function onMapMouseDown(event) {
            if (!selectionModeActive || !event || event.button !== 0) {
                return;
            }
            var map = getMapController();
            if (!map) {
                return;
            }
            var startCandidate = resolveEventLatLng(event, mapElement, map);
            console.info("LanduseModify GL: pointerdown", {
                shiftKey: event.shiftKey === true,
                clientX: event.clientX,
                clientY: event.clientY,
                dragStart: startCandidate
            });
            if (!event.shiftKey) {
                dragStart = null;
                return;
            }
            if (event.cancelable) {
                event.preventDefault();
            }
            if (typeof event.stopPropagation === "function") {
                event.stopPropagation();
            }
            dragStart = startCandidate;
        }

        function onMapMouseMove(event) {
            if (!selectionModeActive) {
                return;
            }
            var map = getMapController();
            if (!map) {
                return;
            }
            var now = Date.now();
            if (now - lastMoveLogTime > 200) {
                console.info("LanduseModify GL: pointermove", {
                    shiftKey: event && event.shiftKey === true,
                    clientX: event ? event.clientX : null,
                    clientY: event ? event.clientY : null,
                    hasDragStart: Boolean(dragStart)
                });
                lastMoveLogTime = now;
            }
            if (dragStart && !(event && event.shiftKey)) {
                dragStart = null;
                clearSelectionRect(map);
                return;
            }
            if (!dragStart) {
                clearSelectionRect(map);
                return;
            }
            var current = resolveEventLatLng(event, mapElement, map);
            if (!current) {
                return;
            }
            var bounds = buildSelectionBounds(dragStart, current);
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
            console.info("LanduseModify GL: pointerup", {
                shiftKey: event && event.shiftKey === true,
                clientX: event ? event.clientX : null,
                clientY: event ? event.clientY : null,
                hasDragStart: Boolean(dragStart)
            });
            if (!dragStart) {
                clearSelectionRect(map);
                return;
            }
            var current = resolveEventLatLng(event, mapElement, map);
            if (!current) {
                dragStart = null;
                clearSelectionRect(map);
                return;
            }
            var bounds = buildSelectionBounds(dragStart, current);
            dragStart = null;
            if (!bounds || (bounds.sw.lat === bounds.ne.lat && bounds.sw.lng === bounds.ne.lng)) {
                clearSelectionRect(map);
                return;
            }

            var extent = [bounds.sw.lng, bounds.sw.lat, bounds.ne.lng, bounds.ne.lat];
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
            if (map.boxZoom && typeof map.boxZoom.disable === "function") {
                map.boxZoom.disable();
            }
            mapCanvas = resolveMapCanvas(mapElement);
            mapDragTarget = mapElement || mapCanvas;
            if (mapDragTarget) {
                mapDragTarget.addEventListener("pointerdown", onMapMouseDown, true);
                mapDragTarget.addEventListener("pointermove", onMapMouseMove, true);
            }
            window.addEventListener("pointerup", onMapMouseUp, true);
        }

        function detachMapListeners() {
            var map = getMapController();
            if (map && map.boxZoom && typeof map.boxZoom.enable === "function") {
                map.boxZoom.enable();
            }
            if (mapDragTarget) {
                mapDragTarget.removeEventListener("pointerdown", onMapMouseDown, true);
                mapDragTarget.removeEventListener("pointermove", onMapMouseMove, true);
            }
            window.removeEventListener("pointerup", onMapMouseUp, true);
            mapCanvas = null;
            mapDragTarget = null;
            if (geoLayer && map) {
                removeLayer(map, geoLayer);
            }
            geoLayer = null;
            modify.glLayer = null;
            clearSelectionRect(map);
            if (mapSuppressionApplied && map && typeof map.releaseDrilldown === "function") {
                map.releaseDrilldown(DRILLDOWN_SUPPRESSION_TOKEN);
                mapSuppressionApplied = false;
            }
        }

        function setSelectionMode(enabled, options) {
            var targetState = Boolean(enabled);
            if (selectionModeActive === targetState) {
                return;
            }
            selectionModeActive = targetState;
            if (selectionModeActive) {
                attachMapListeners();
                if (geoJsonData) {
                    rebuildGeoLayer();
                } else {
                    loadSubcatchments();
                }
            } else {
                detachMapListeners();
                if (options && options.clearSelection) {
                    applySelection([], { source: options.source || "cancel", silent: true });
                }
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
                    setSelectionMode(false, { clearSelection: false });

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
                console.warn("LanduseModify GL: SubcatchmentDelineation refresh failed", err);
            }

            try {
                if (window.Landuse && typeof window.Landuse.getInstance === "function") {
                    var landuseController = window.Landuse.getInstance();
                    if (landuseController && typeof landuseController.report === "function") {
                        landuseController.report();
                    }
                }
            } catch (err2) {
                console.warn("LanduseModify GL: Landuse report refresh failed", err2);
            }
        }

        var baseTriggerEvent = modify.triggerEvent.bind(modify);
        modify.triggerEvent = function (eventName, payload) {
            if (eventName === "LANDCOVER_MODIFY_TASK_COMPLETED") {
                try {
                    refreshDependentControllers();
                } catch (err) {
                    console.warn("LanduseModify GL: dependent controller refresh failed", err);
                }
            }
            baseTriggerEvent(eventName, payload);
        };

        modify.enableSelection = function () {
            setSelectionMode(true);
        };

        modify.disableSelection = function (options) {
            setSelectionMode(false, options || { clearSelection: true });
        };

        modify.clearSelection = function () {
            applySelection([], { source: "clear" });
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
            setSelectionMode(Boolean(checkbox && checkbox.checked), {
                clearSelection: !Boolean(checkbox && checkbox.checked),
                source: "toggle"
            });
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
