/* ----------------------------------------------------------------------------
 * SubcatchmentDelineation (Deck.gl map parity)
 * ----------------------------------------------------------------------------
 */
var SubcatchmentDelineation = (function () {
    "use strict";

    var instance;

    var EVENT_NAMES = [
        "subcatchment:build:started",
        "subcatchment:build:completed",
        "subcatchment:build:error",
        "subcatchment:map:mode",
        "subcatchment:report:loaded",
        "subcatchment:legend:updated"
    ];

    var SUBCATCHMENT_LAYER_NAME = "Subcatchments";
    var SUBCATCHMENT_LAYER_ID = "wc-subcatchments";
    var SUBCATCHMENT_LABEL_LAYER_NAME = "Subcatchment Labels";
    var SUBCATCHMENT_LABEL_LAYER_ID = "wc-subcatchment-labels";
    var SUBCATCHMENT_HOVER_LABEL_LAYER_ID = "wc-subcatchment-hover-label";
    var SUBCATCHMENT_LABEL_COLOR = [255, 120, 0, 255];
    var SUBCATCHMENT_LABEL_OUTLINE_COLOR = [255, 255, 255, 255];
    var SUBCATCHMENT_LABEL_OUTLINE_WIDTH = 2;
    var SUBCATCHMENT_LABEL_FONT_SIZE = 16;

    var SUBCATCHMENT_ENDPOINT = "resources/subcatchments.json";
    var DEFAULT_STYLE = {
        color: "#ff7800",
        weight: 2,
        opacity: 0.65,
        fillColor: "#ff7800",
        fillOpacity: 0.3
    };
    var CLEAR_STYLE = {
        color: "#ff7800",
        weight: 2,
        opacity: 0.65,
        fillColor: "#ffffff",
        fillOpacity: 0.0
    };

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function") {
            throw new Error("SubcatchmentDelineation GL requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("SubcatchmentDelineation GL requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function" || typeof http.getJson !== "function" || typeof http.postJson !== "function") {
            throw new Error("SubcatchmentDelineation GL requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("SubcatchmentDelineation GL requires WCEvents helpers.");
        }

        return { dom: dom, forms: forms, http: http, events: events };
    }

    function ensureControlBase() {
        if (typeof window.controlBase !== "function") {
            throw new Error("SubcatchmentDelineation GL requires controlBase.");
        }
        return window.controlBase;
    }

    function ensureMap() {
        var map = window.MapController && typeof window.MapController.getInstance === "function"
            ? window.MapController.getInstance()
            : null;
        if (!map) {
            throw new Error("SubcatchmentDelineation GL requires MapController.");
        }
        return map;
    }

    function ensureDeck() {
        var deckApi = window.deck;
        if (!deckApi || typeof deckApi.GeoJsonLayer !== "function" ||
            typeof deckApi.TextLayer !== "function") {
            throw new Error("SubcatchmentDelineation GL requires deck.gl GeoJsonLayer/TextLayer.");
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

    function isFiniteNumber(value) {
        return typeof value === "number" && Number.isFinite(value);
    }

    function parseNumeric(value) {
        if (value === null || value === undefined || value === "") {
            return null;
        }
        if (Array.isArray(value)) {
            return parseNumeric(value[0]);
        }
        var num = Number(value);
        return Number.isFinite(num) ? num : null;
    }

    function hexToRgba(hex, alpha) {
        if (!hex || typeof hex !== "string") {
            return [0, 0, 0, 255];
        }
        var cleaned = hex.replace(/^#/, "");
        if (cleaned.length !== 6) {
            return [0, 0, 0, 255];
        }
        var intVal = parseInt(cleaned, 16);
        if (Number.isNaN(intVal)) {
            return [0, 0, 0, 255];
        }
        var r = (intVal >> 16) & 255;
        var g = (intVal >> 8) & 255;
        var b = intVal & 255;
        var a = 255;
        if (Number.isFinite(alpha)) {
            a = alpha <= 1 ? Math.round(alpha * 255) : Math.round(alpha);
        }
        return [r, g, b, a];
    }

    function resolveRunScopedUrl(path) {
        if (typeof window.url_for_run !== "function") {
            throw new Error("SubcatchmentDelineation GL requires url_for_run.");
        }
        return window.url_for_run(path);
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

    function setSubLegend(html) {
        try {
            var map = ensureMap();
            if (!map || !map.sub_legend) {
                return;
            }
            var target = map.sub_legend;
            if (typeof target.html === "function") {
                target.html(html || "");
                return;
            }
            if (typeof target === "string") {
                var el = document.querySelector(target);
                if (el) {
                    el.innerHTML = html || "";
                }
                return;
            }
            if (target && target instanceof Element) {
                target.innerHTML = html || "";
                return;
            }
            if (target && target[0] && target[0] instanceof Element) {
                target[0].innerHTML = html || "";
            }
        } catch (err) {
            console.warn("[Subcatchment GL] Failed to update legend", err);
        }
    }

    function loadLegend(http, name, emit) {
        if (!name) {
            return Promise.resolve();
        }
        var legendUrl = resolveRunScopedUrl("resources/legends/" + name + "/");
        return http.request(legendUrl, {
            method: "GET",
            headers: { Accept: "text/html,application/xhtml+xml" }
        }).then(function (result) {
            var html = typeof result.body === "string" ? result.body : "";
            setSubLegend(html);
            if (typeof emit === "function") {
                emit("subcatchment:legend:updated", { name: name });
            }
        }).catch(function (error) {
            console.warn("[Subcatchment GL] Legend load failed", error);
        });
    }

    function renderLegendIfPresent(palette, canvasId) {
        var canvas = document.getElementById(canvasId);
        if (!canvas) {
            return;
        }
        if (typeof window.render_legend === "function") {
            window.render_legend(palette, canvasId);
            return;
        }
        if (typeof window.createColormap !== "function") {
            return;
        }
        renderLegendCanvas(palette, canvas);
    }

    function renderLegendCanvas(palette, canvas) {
        if (!canvas || typeof canvas.getContext !== "function") {
            return;
        }
        var rect = canvas.getBoundingClientRect();
        var width = Math.round(rect.width || canvas.offsetWidth || canvas.clientWidth || canvas.width || 0);
        var height = Math.round(rect.height || canvas.offsetHeight || canvas.clientHeight || canvas.height || 0);
        if (width <= 0 || height <= 0) {
            return;
        }
        if (canvas.width !== width) {
            canvas.width = width;
        }
        if (canvas.height !== height) {
            canvas.height = height;
        }
        var mapper = window.createColormap({ colormap: palette, nshades: 64 });
        if (!mapper || typeof mapper.map !== "function") {
            return;
        }
        var ctx = canvas.getContext("2d");
        if (!ctx) {
            return;
        }
        var imgData = ctx.createImageData(width, height);
        var denom = width > 1 ? width - 1 : 1;
        for (var y = 0; y < height; y += 1) {
            var rowOffset = y * width * 4;
            for (var x = 0; x < width; x += 1) {
                var t = x / denom;
                var hex = mapper.map(t);
                var rgba = hexToRgba(hex, 1);
                var idx = rowOffset + x * 4;
                imgData.data[idx] = rgba[0];
                imgData.data[idx + 1] = rgba[1];
                imgData.data[idx + 2] = rgba[2];
                imgData.data[idx + 3] = rgba[3];
            }
        }
        ctx.putImageData(imgData, 0, 0);
    }

    function resolveColorMapAlias(mode) {
        if (mode === "slp_asp") {
            return "slope";
        }
        return mode;
    }

    function clampNormalized(value) {
        if (!Number.isFinite(value)) {
            return null;
        }
        if (value < 0) {
            return 0;
        }
        if (value > 1) {
            return 1;
        }
        return value;
    }

    function resolveSlopeAspectMapper(state) {
        if (!state.colorMappers.slopeAspect && typeof window.createColormap === "function") {
            state.colorMappers.slopeAspect = window.createColormap({ colormap: "viridis", nshades: 64 });
        }
        return state.colorMappers.slopeAspect;
    }

    function resolveAspectDegrees(record) {
        if (!record) {
            return null;
        }
        var source = record.watershed && typeof record.watershed === "object" ? record.watershed : record;
        return parseNumeric(source.aspect);
    }

    function aspectToRgb(degrees) {
        if (!Number.isFinite(degrees)) {
            return null;
        }
        var hue = degrees % 360;
        if (hue < 0) {
            hue += 360;
        }
        var h = hue / 60;
        var c = 200;
        var x = c * (1 - Math.abs((h % 2) - 1));
        var r;
        var g;
        var b;
        if (h < 1) { r = c; g = x; b = 0; } else if (h < 2) { r = x; g = c; b = 0; }
        else if (h < 3) { r = 0; g = c; b = x; } else if (h < 4) { r = 0; g = x; b = c; }
        else if (h < 5) { r = x; g = 0; b = c; } else { r = c; g = 0; b = x; }
        return [Math.round(r + 55), Math.round(g + 55), Math.round(b + 55)];
    }

    function aspectToRgba(degrees, alpha) {
        var rgb = aspectToRgb(degrees);
        if (!rgb) {
            return null;
        }
        var a = 255;
        if (Number.isFinite(alpha)) {
            a = alpha <= 1 ? Math.round(alpha * 255) : Math.round(alpha);
        }
        return [rgb[0], rgb[1], rgb[2], a];
    }

    function resolveSlopeAspectValue(mode, record) {
        if (!record) {
            return null;
        }
        var source = record.watershed && typeof record.watershed === "object" ? record.watershed : record;
        if (mode === "aspect") {
            var aspectValue = parseNumeric(source.aspect);
            if (aspectValue === null) {
                return null;
            }
            return clampNormalized(aspectValue / 360);
        }
        var slopeValue = parseNumeric(source.slope_scalar);
        if (slopeValue === null) {
            slopeValue = parseNumeric(source.slope);
        }
        return slopeValue === null ? null : clampNormalized(slopeValue);
    }

    function renderSlopeLegend(emit) {
        var canvasId = "sub_cmap_canvas_slope";
        var html = ""
            + "<div class=\"wc-map-legend__header\">Slope (rise/run)</div>"
            + "<div class=\"wc-color-scale\">"
            + "<div class=\"wc-color-scale__bar\">"
            + "<canvas id=\"" + canvasId + "\" class=\"wc-color-scale__canvas\" width=\"200\" height=\"20\"></canvas>"
            + "</div>"
            + "<div class=\"wc-color-scale__labels\">"
            + "<span>0</span>"
            + "<span>1</span>"
            + "</div>"
            + "</div>";
        setSubLegend(html);
        renderLegendIfPresent("viridis", canvasId);
        if (typeof emit === "function") {
            emit("subcatchment:legend:updated", { name: "slope" });
        }
    }

    function renderAspectLegend(emit) {
        var directions = [
            { label: "N (0°)", degrees: 0 },
            { label: "NE (45°)", degrees: 45 },
            { label: "E (90°)", degrees: 90 },
            { label: "SE (135°)", degrees: 135 },
            { label: "S (180°)", degrees: 180 },
            { label: "SW (225°)", degrees: 225 },
            { label: "W (270°)", degrees: 270 },
            { label: "NW (315°)", degrees: 315 }
        ];

        var html = "<div class=\"wc-map-legend__header\">Aspect (degrees)</div>"
            + "<div class=\"wc-legend\">";
        directions.forEach(function (dir) {
            var rgb = aspectToRgb(dir.degrees);
            var color = rgb ? "rgb(" + rgb[0] + ", " + rgb[1] + ", " + rgb[2] + ")" : "#999999";
            html += ""
                + "<div class=\"wc-legend-item\">"
                + "<span class=\"wc-legend-item__swatch\" style=\"--legend-color: " + color + ";\" aria-label=\"Color swatch for " + dir.label + "\"></span>"
                + "<span class=\"wc-legend-item__label\">" + dir.label + "</span>"
                + "</div>";
        });
        html += "</div>";
        setSubLegend(html);
        if (typeof emit === "function") {
            emit("subcatchment:legend:updated", { name: "aspect" });
        }
    }

    function renderSlopeAspectLegend(mode, emit) {
        var resolvedMode = resolveColorMapAlias(mode);
        if (resolvedMode === "aspect") {
            renderAspectLegend(emit);
            return;
        }
        renderSlopeLegend(emit);
    }

    function resolveLabelPosition(feature) {
        var geometry = feature && feature.geometry ? feature.geometry : null;
        if (!geometry) {
            return null;
        }
        if (typeof window.polylabel === "function" && (geometry.type === "Polygon" || geometry.type === "MultiPolygon")) {
            try {
                var polyCoords = geometry.type === "Polygon" ? geometry.coordinates : geometry.coordinates[0];
                var center = window.polylabel(polyCoords, 1.0);
                if (Array.isArray(center) && center.length >= 2) {
                    return [center[0], center[1]];
                }
            } catch (err) {
                // fall back to first coordinate
            }
        }
        var coords = null;
        if (geometry.type === "Point") {
            coords = geometry.coordinates;
        } else if (geometry.type === "MultiPoint") {
            coords = geometry.coordinates && geometry.coordinates[0];
        } else if (geometry.type === "LineString") {
            coords = geometry.coordinates && geometry.coordinates[0];
        } else if (geometry.type === "MultiLineString") {
            coords = geometry.coordinates && geometry.coordinates[0] && geometry.coordinates[0][0];
        } else if (geometry.type === "Polygon") {
            coords = geometry.coordinates && geometry.coordinates[0] && geometry.coordinates[0][0];
        } else if (geometry.type === "MultiPolygon") {
            coords = geometry.coordinates && geometry.coordinates[0] && geometry.coordinates[0][0] && geometry.coordinates[0][0][0];
        }
        if (!coords || coords.length < 2) {
            return null;
        }
        return [coords[0], coords[1]];
    }

    function buildLabelData(features) {
        var labels = [];
        var seen = typeof Set === "function" ? new Set() : null;
        (features || []).forEach(function (feature) {
            var topId = feature && feature.properties ? feature.properties.TopazID : null;
            if (topId === null || topId === undefined) {
                return;
            }
            var key = String(topId);
            if (seen) {
                if (seen.has(key)) {
                    return;
                }
                seen.add(key);
            } else {
                for (var i = 0; i < labels.length; i += 1) {
                    if (labels[i].text === key) {
                        return;
                    }
                }
            }
            var position = resolveLabelPosition(feature);
            if (!position) {
                return;
            }
            labels.push({
                text: key,
                position: position
            });
        });
        return labels;
    }

    function resolveLabelPositionFromData(labelData, key) {
        if (!labelData || !labelData.length) {
            return null;
        }
        for (var i = 0; i < labelData.length; i += 1) {
            var label = labelData[i];
            if (label && label.text === key && label.position) {
                return label.position;
            }
        }
        return null;
    }

    function buildHoverLabelData(feature, labelData) {
        if (!feature || !feature.properties) {
            return null;
        }
        var topId = feature.properties.TopazID;
        if (topId === null || topId === undefined) {
            return null;
        }
        var key = String(topId);
        var position = resolveLabelPositionFromData(labelData, key) || resolveLabelPosition(feature);
        if (!position) {
            return null;
        }
        return [{
            text: key,
            position: position
        }];
    }

    function buildLabelLayer(deckApi, labelData) {
        return new deckApi.TextLayer({
            id: SUBCATCHMENT_LABEL_LAYER_ID,
            data: labelData || [],
            pickable: false,
            getPosition: function (d) { return d.position; },
            getText: function (d) { return d.text; },
            getSize: function () { return SUBCATCHMENT_LABEL_FONT_SIZE; },
            sizeUnits: "pixels",
            getColor: function () { return SUBCATCHMENT_LABEL_COLOR; },
            outlineColor: SUBCATCHMENT_LABEL_OUTLINE_COLOR,
            outlineWidth: SUBCATCHMENT_LABEL_OUTLINE_WIDTH,
            fontSettings: { sdf: true }
        });
    }

    function buildHoverLabelLayer(deckApi, labelData) {
        return new deckApi.TextLayer({
            id: SUBCATCHMENT_HOVER_LABEL_LAYER_ID,
            data: labelData || [],
            pickable: false,
            getPosition: function (d) { return d.position; },
            getText: function (d) { return d.text; },
            getSize: function () { return SUBCATCHMENT_LABEL_FONT_SIZE; },
            sizeUnits: "pixels",
            getColor: function () { return SUBCATCHMENT_LABEL_COLOR; },
            outlineColor: SUBCATCHMENT_LABEL_OUTLINE_COLOR,
            outlineWidth: SUBCATCHMENT_LABEL_OUTLINE_WIDTH,
            fontSettings: { sdf: true }
        });
    }

    function clearHoverLabel(state, map) {
        if (!state) {
            return;
        }
        if (!state.hoverLabelLayer) {
            state.hoverLabelKey = null;
            return;
        }
        if (map && typeof map.removeLayer === "function") {
            map.removeLayer(state.hoverLabelLayer, { skipOverlay: true });
        }
        state.hoverLabelLayer = null;
        state.hoverLabelKey = null;
    }

    function updateHoverLabel(state, map, deckApi, info) {
        if (!state || !map || !deckApi) {
            return;
        }
        if (state.labelLayer && typeof map.hasLayer === "function" && map.hasLayer(state.labelLayer)) {
            clearHoverLabel(state, map);
            return;
        }
        var feature = info && info.object ? info.object : null;
        if (!feature) {
            clearHoverLabel(state, map);
            return;
        }
        var topId = feature && feature.properties ? feature.properties.TopazID : null;
        if (topId === null || topId === undefined) {
            clearHoverLabel(state, map);
            return;
        }
        var key = String(topId);
        if (state.hoverLabelKey === key && state.hoverLabelLayer) {
            return;
        }
        var data = buildHoverLabelData(feature, state.labelData);
        if (!data || !data.length) {
            clearHoverLabel(state, map);
            return;
        }
        var nextLayer = buildHoverLabelLayer(deckApi, data);
        if (!nextLayer) {
            return;
        }
        if (state.hoverLabelLayer && typeof map.removeLayer === "function") {
            map.removeLayer(state.hoverLabelLayer, { skipOverlay: true });
        }
        state.hoverLabelLayer = nextLayer;
        state.hoverLabelKey = key;
        if (typeof map.addLayer === "function") {
            map.addLayer(nextLayer, { skipRefresh: true });
        }
    }

    function buildSubcatchmentLayer(deckApi, data, colorFn, mode, onHover) {
        var lineColor = hexToRgba(DEFAULT_STYLE.color, DEFAULT_STYLE.opacity);
        return new deckApi.GeoJsonLayer({
            id: SUBCATCHMENT_LAYER_ID,
            data: data || { type: "FeatureCollection", features: [] },
            pickable: true,
            stroked: true,
            filled: true,
            lineWidthUnits: "pixels",
            lineWidthMinPixels: 1,
            getLineWidth: function () { return DEFAULT_STYLE.weight; },
            getLineColor: function (feature) { return colorFn(feature); },
            getFillColor: function (feature) { return colorFn(feature); },
            updateTriggers: {
                getFillColor: [mode],
                getLineColor: [mode]
            },
            onHover: typeof onHover === "function" ? onHover : null,
            onClick: function (info) {
                var feature = info && info.object ? info.object : null;
                var topId = feature && feature.properties ? feature.properties.TopazID : null;
                if (!topId) {
                    return;
                }
                var map = ensureMap();
                if (map && typeof map.subQuery === "function") {
                    map.subQuery(topId);
                }
            }
        });
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var events = helpers.events;
        var baseFactory = ensureControlBase();
        if (typeof window.createColormap !== "function") {
            throw new Error("SubcatchmentDelineation GL requires createColormap.");
        }

        var sub = baseFactory();

        var emitterBase = events.createEmitter();
        var subEvents = typeof events.useEventMap === "function"
            ? events.useEventMap(EVENT_NAMES, emitterBase)
            : emitterBase;
        sub.events = subEvents;

        var formElement = dom.ensureElement("#build_subcatchments_form", "Subcatchment form not found.");
        var infoElement = dom.qs("#build_subcatchments_form #info");
        var statusElement = dom.qs("#build_subcatchments_form #status");
        var stacktraceElement = dom.qs("#build_subcatchments_form #stacktrace");
        var stacktracePanelElement = dom.qs("#subcatchments_stacktrace_panel");
        var rqJobElement = dom.qs("#build_subcatchments_form #rq_job");
        var hintElement = dom.qs("#hint_build_subcatchments");
        var spinnerElement = dom.qs("#build_subcatchments_form #braille");

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);
        var hintAdapter = createLegacyAdapter(hintElement);

        sub.form = formElement;
        sub.info = infoAdapter;
        sub.status = statusAdapter;
        sub.stacktrace = stacktraceAdapter;
        sub.stacktracePanelEl = stacktracePanelElement;
        sub.rq_job = rqJobAdapter;
        sub.hint = hintAdapter;
        sub.command_btn_id = "btn_build_subcatchments";
        sub.statusSpinnerEl = spinnerElement;
        sub.attach_status_stream(sub, {
            form: formElement,
            channel: "subcatchment_delineation",
            runId: window.runid || window.runId || null,
            spinner: spinnerElement,
            stacktrace: stacktracePanelElement ? { element: stacktracePanelElement } : null
        });
        sub.poll_completion_event = "WATERSHED_ABSTRACTION_TASK_COMPLETED";

        function resetCompletionSeen() {
            sub._completion_seen = {
                BUILD_SUBCATCHMENTS_TASK_COMPLETED: false,
                WATERSHED_ABSTRACTION_TASK_COMPLETED: false
            };
        }
        resetCompletionSeen();

        var state = {
            data: null,
            glLayer: null,
            labelLayer: null,
            labelData: null,
            hoverLabelLayer: null,
            hoverLabelKey: null,
            cmapMode: "default",
            dataCover: null,
            dataSlpAsp: null,
            dataLanduse: null,
            dataSoils: null,
            colorMappers: {
                slopeAspect: typeof window.createColormap === "function" ? window.createColormap({ colormap: "viridis", nshades: 64 }) : null,
                cover: typeof window.createColormap === "function" ? window.createColormap({ colormap: "viridis", nshades: 64 }) : null
            },
            postBuildRefreshTimer: null
        };

        sub.state = state;
        sub.glLayer = null;

        var mapEventsBound = false;
        function bindMapEvents() {
            if (mapEventsBound) {
                return;
            }
            var map;
            try {
                map = ensureMap();
            } catch (err) {
                return;
            }
            if (map && map.events && typeof map.events.on === "function") {
                map.events.on("map:layer:toggled", function (payload) {
                    if (!payload || !payload.name) {
                        return;
                    }
                    if (payload.name === SUBCATCHMENT_LABEL_LAYER_NAME && payload.visible) {
                        clearHoverLabel(state, map);
                    }
                    if (payload.name === SUBCATCHMENT_LAYER_NAME && !payload.visible) {
                        clearHoverLabel(state, map);
                    }
                });
            }
            mapEventsBound = true;
        }

        bindMapEvents();

        function emit(eventName, payload) {
            if (subEvents && typeof subEvents.emit === "function") {
                subEvents.emit(eventName, payload || {});
            }
        }

        function handleError(error) {
            var payload = toResponsePayload(http, error);
            if (sub && typeof sub.pushResponseStacktrace === "function") {
                sub.pushResponseStacktrace(sub, payload);
            }
            return payload;
        }

        sub.hideStacktrace = function () {
            if (stacktraceAdapter && typeof stacktraceAdapter.hide === "function") {
                stacktraceAdapter.hide();
                return;
            }
            if (!stacktraceElement) {
                return;
            }
            stacktraceElement.hidden = true;
            stacktraceElement.style.display = "none";
        };

        function requestJson(url, options) {
            var opts = options || {};
            if (!opts.method) {
                opts.method = "GET";
            }
            if (!opts.headers) {
                opts.headers = { Accept: "application/json" };
            } else if (!opts.headers.Accept) {
                opts.headers.Accept = "application/json";
            }
            return http.request(url, opts).then(function (result) {
                if (!result) {
                    return null;
                }
                if (result.body !== undefined) {
                    return result.body;
                }
                return result.response || null;
            });
        }

        function colorFnFactory() {
            var defaultFill = hexToRgba(DEFAULT_STYLE.fillColor, DEFAULT_STYLE.fillOpacity);
            var clearFill = hexToRgba(CLEAR_STYLE.fillColor, CLEAR_STYLE.fillOpacity);
            switch (state.cmapMode) {
                case "default":
                    return function () { return defaultFill; };
                case "clear":
                    return function () { return clearFill; };
                case "slp_asp":
                case "slope":
                    return function (feature) {
                        var id = feature.properties.TopazID;
                        var record = state.dataSlpAsp && state.dataSlpAsp[id] ? state.dataSlpAsp[id] : null;
                        var normalized = resolveSlopeAspectValue("slope", record);
                        if (!Number.isFinite(normalized)) {
                            return defaultFill;
                        }
                        var mapper = resolveSlopeAspectMapper(state);
                        var hex = mapper ? mapper.map(normalized) : "#ffffff";
                        return hexToRgba(hex, 0.9);
                    };
                case "aspect":
                    return function (feature) {
                        var id = feature.properties.TopazID;
                        var record = state.dataSlpAsp && state.dataSlpAsp[id] ? state.dataSlpAsp[id] : null;
                        var aspectValue = resolveAspectDegrees(record);
                        var rgba = aspectToRgba(aspectValue, 0.9);
                        if (!rgba) {
                            return defaultFill;
                        }
                        return rgba;
                    };
                case "landuse":
                    return function (feature) {
                        var id = feature.properties.TopazID;
                        var rgbHex = state.dataLanduse && state.dataLanduse[id] ? state.dataLanduse[id].color : null;
                        return rgbHex ? hexToRgba(rgbHex, 0.7) : defaultFill;
                    };
                case "soils":
                    return function (feature) {
                        var id = feature.properties.TopazID;
                        var rgbHex = state.dataSoils && state.dataSoils[id] ? state.dataSoils[id].color : null;
                        return rgbHex ? hexToRgba(rgbHex, 0.7) : defaultFill;
                    };
                case "cover":
                    return function (feature) {
                        if (!state.dataCover) {
                            return defaultFill;
                        }
                        var id = feature.properties.TopazID;
                        var value = state.dataCover[id];
                        if (value === undefined || value === null) {
                            return defaultFill;
                        }
                        var mapper = state.colorMappers.cover;
                        var hex = mapper ? mapper.map(value) : "#ffffff";
                        return hexToRgba(hex, 0.9);
                    };
                default:
                    return function () { return defaultFill; };
            }
        }

        function attachLayerRebuild(layer) {
            if (!layer) {
                return;
            }
            layer.__wcRebuild = function () {
                if (!state.data) {
                    return layer;
                }
                var deckApi = ensureDeck();
                var map = ensureMap();
                var onHoverHandler = function (info) {
                    updateHoverLabel(state, map, deckApi, info);
                };
                var cmapFn = colorFnFactory();
                var nextLayer = buildSubcatchmentLayer(deckApi, state.data, cmapFn, state.cmapMode, onHoverHandler);
                attachLayerRebuild(nextLayer);
                state.glLayer = nextLayer;
                sub.glLayer = nextLayer;
                return nextLayer;
            };
        }

        function attachLabelRebuild(layer) {
            if (!layer) {
                return;
            }
            layer.__wcRebuild = function () {
                if (!state.labelData) {
                    return layer;
                }
                var deckApi = ensureDeck();
                var nextLayer = buildLabelLayer(deckApi, state.labelData);
                attachLabelRebuild(nextLayer);
                state.labelLayer = nextLayer;
                return nextLayer;
            };
        }

        function replaceOverlayLayer(map, name, currentLayer, nextLayer, wasVisible) {
            if (currentLayer && typeof map.removeLayer === "function") {
                map.removeLayer(currentLayer, { skipOverlay: true });
            }
            if (typeof map.registerOverlay === "function") {
                map.registerOverlay(nextLayer, name);
            } else if (map.ctrls && typeof map.ctrls.addOverlay === "function") {
                map.ctrls.addOverlay(nextLayer, name);
            }
            if (wasVisible && typeof map.addLayer === "function") {
                map.addLayer(nextLayer);
            }
        }

        function refreshGlLayer() {
            if (!state.data) {
                return;
            }
            var map = ensureMap();
            var deckApi = ensureDeck();
            var wasVisible = state.glLayer ? map.hasLayer(state.glLayer) : true;
            var cmapFn = colorFnFactory();
            var onHoverHandler = function (info) {
                updateHoverLabel(state, map, deckApi, info);
            };
            var nextLayer = buildSubcatchmentLayer(deckApi, state.data, cmapFn, state.cmapMode, onHoverHandler);
            attachLayerRebuild(nextLayer);
            replaceOverlayLayer(map, SUBCATCHMENT_LAYER_NAME, state.glLayer, nextLayer, wasVisible);
            state.glLayer = nextLayer;
            sub.glLayer = nextLayer;
        }

        function updateGlLayerStyle() {
            if (!state.glLayer) {
                return;
            }
            refreshGlLayer();
        }

        function buildLabels() {
            if (!state.data || !state.data.features) {
                state.labelData = [];
                return;
            }
            state.labelData = buildLabelData(state.data.features);
            var map = ensureMap();
            var deckApi = ensureDeck();
            var wasVisible = state.labelLayer ? map.hasLayer(state.labelLayer) : false;
            var nextLayer = buildLabelLayer(deckApi, state.labelData);
            attachLabelRebuild(nextLayer);
            replaceOverlayLayer(map, SUBCATCHMENT_LABEL_LAYER_NAME, state.labelLayer, nextLayer, wasVisible);
            state.labelLayer = nextLayer;
            if (wasVisible) {
                clearHoverLabel(state, map);
            }
        }

        function renderLayer(options) {
            var type = options.type;
            var dataProp = options.dataProp;
            var mode = options.mode;
            var legend = options.legend;
            var label = options.label || type;

            if (statusAdapter && typeof statusAdapter.text === "function") {
                statusAdapter.text("Loading " + label + " ...");
            }

            var targetUrl = resolveRunScopedUrl("query/" + type + "/subcatchments/");

            return requestJson(targetUrl)
                .then(function (data) {
                    state[dataProp] = data;
                    state.cmapMode = mode;
                    updateGlLayerStyle();
                    if (statusAdapter && typeof statusAdapter.text === "function") {
                        statusAdapter.text(label + " loaded.");
                    }
                })
                .catch(handleError)
                .then(function () {
                    if (legend) {
                        return loadLegend(http, legend, emit);
                    }
                    return undefined;
                });
        }

        function renderSlopeAspect(mode) {
            var resolvedMode = resolveColorMapAlias(mode);
            var label = resolvedMode === "aspect" ? "aspect" : "slope";
            if (statusAdapter && typeof statusAdapter.text === "function") {
                statusAdapter.text("Loading " + label + " ...");
            }
            return requestJson(resolveRunScopedUrl("query/watershed/subcatchments/"))
                .then(function (data) {
                    state.dataSlpAsp = data;
                    state.cmapMode = resolvedMode;
                    resolveSlopeAspectMapper(state);
                    updateGlLayerStyle();
                    if (statusAdapter && typeof statusAdapter.text === "function") {
                        statusAdapter.text(label + " loaded.");
                    }
                })
                .catch(handleError)
                .then(function () {
                    renderSlopeAspectLegend(resolvedMode, emit);
                });
        }

        function renderLanduse() {
            return renderLayer({
                type: "landuse",
                dataProp: "dataLanduse",
                mode: "landuse",
                legend: "landuse",
                label: "landuse"
            });
        }

        function renderRangelandCover() {
            return renderLayer({
                type: "rangeland_cover",
                dataProp: "dataLanduse",
                mode: "landuse",
                legend: "landuse",
                label: "rangeland cover"
            });
        }

        function renderSoils() {
            return renderLayer({
                type: "soils",
                dataProp: "dataSoils",
                mode: "soils",
                legend: "soils",
                label: "soils"
            });
        }

        function renderCover() {
            return requestJson(resolveRunScopedUrl("query/landuse/cover/subcatchments"))
                .then(function (data) {
                    state.dataCover = data;
                    state.cmapMode = "cover";
                    if (!state.colorMappers.cover && typeof window.createColormap === "function") {
                        state.colorMappers.cover = window.createColormap({ colormap: "viridis", nshades: 64 });
                    }
                    updateGlLayerStyle();
                })
                .catch(handleError);
        }

        function handleColorMapChange(value) {
            if (!value) {
                return;
            }
            var resolvedMode = resolveColorMapAlias(value);
            sub.setColorMap(resolvedMode);
            emit("subcatchment:map:mode", { mode: resolvedMode });
        }

        function setupDelegatedEvents() {
            dom.delegate(document, "click", "[data-subcatchment-action='build']", function (event) {
                event.preventDefault();
                sub.build();
            });

            dom.delegate(document, "change", "[data-subcatchment-role='cmap-option']", function () {
                handleColorMapChange(this.value);
            });
        }

        function disableRadio(id, disabled) {
            var radio = document.getElementById(id);
            if (!radio) {
                return;
            }
            radio.disabled = Boolean(disabled);
            if (disabled) {
                radio.setAttribute("aria-disabled", "true");
            } else {
                radio.removeAttribute("aria-disabled");
            }

            var label = radio.closest ? radio.closest("label") : null;
            if (label) {
                if (disabled) {
                    label.classList.add("is-disabled");
                } else {
                    label.classList.remove("is-disabled");
                }
            }
        }

        function enableSlopeAspectRadios() {
            disableRadio("sub_cmap_radio_slope", false);
            disableRadio("sub_cmap_radio_aspect", false);
        }

        sub.enableColorMap = function (cmapName) {
            var resolvedMode = resolveColorMapAlias(cmapName);
            switch (resolvedMode) {
                case "dom_lc":
                    disableRadio("sub_cmap_radio_dom_lc", false);
                    break;
                case "rangeland_cover":
                    disableRadio("sub_cmap_radio_rangeland_cover", false);
                    break;
                case "dom_soil":
                    disableRadio("sub_cmap_radio_dom_soil", false);
                    break;
                case "slope":
                case "aspect":
                    enableSlopeAspectRadios();
                    break;
                default:
                    throw new Error("Map.enableColorMap received unexpected parameter: " + cmapName);
            }
        };

        sub.getCmapMode = function () {
            return state.cmapMode;
        };

        sub.setColorMap = function (mode) {
            var resolvedMode = resolveColorMapAlias(mode);
            if (!state.glLayer && resolvedMode !== "default" && resolvedMode !== "clear") {
                throw new Error("Subcatchments have not been drawn");
            }

            if (resolvedMode === "default") {
                state.cmapMode = "default";
                updateGlLayerStyle();
                setSubLegend("");
            } else if (resolvedMode === "slope") {
                renderSlopeAspect("slope");
            } else if (resolvedMode === "aspect") {
                renderSlopeAspect("aspect");
            } else if (resolvedMode === "dom_lc" || resolvedMode === "landuse") {
                renderLanduse();
            } else if (resolvedMode === "rangeland_cover") {
                renderRangelandCover();
            } else if (resolvedMode === "dom_soil" || resolvedMode === "soils") {
                renderSoils();
            } else if (resolvedMode === "cover" || resolvedMode === "landuse_cover") {
                renderCover();
            }
        };

        sub.build = function () {
            var taskMsg = "Building Subcatchments";

            if (typeof sub.reset_panel_state === "function") {
                sub.reset_panel_state(sub, { taskMessage: taskMsg });
            }
            resetCompletionSeen();
            if (typeof sub.connect_status_stream === "function") {
                sub.connect_status_stream(sub);
            }
            if (stacktraceAdapter && typeof stacktraceAdapter.empty === "function") {
                stacktraceAdapter.empty();
            }
            sub.hideStacktrace();

            emit("subcatchment:build:started", {});

            var payload = forms.serializeForm(formElement, { format: "json" }) || {};

            return http.postJson(resolveRunScopedUrl("rq/api/build_subcatchments_and_abstract_watershed"), payload, { form: formElement })
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && response.Success === true) {
                        if (statusAdapter && typeof statusAdapter.html === "function") {
                            statusAdapter.html("build_subcatchments_and_abstract_watershed_rq job submitted: " + response.job_id);
                        }
                        sub.poll_completion_event = "WATERSHED_ABSTRACTION_TASK_COMPLETED";
                        if (typeof sub.set_rq_job_id === "function") {
                            sub.set_rq_job_id(sub, response.job_id);
                        }
                    } else if (response) {
                        if (typeof sub.pushResponseStacktrace === "function") {
                            sub.pushResponseStacktrace(sub, response);
                        }
                        emit("subcatchment:build:error", { error: response });
                    }
                    return response;
                })
                .catch(function (error) {
                    var payload = handleError(error);
                    emit("subcatchment:build:error", { error: payload });
                    throw error;
                });
        };

        sub.report = function () {
            var taskMsg = "Fetching Summary";

            if (infoAdapter && typeof infoAdapter.text === "function") {
                infoAdapter.text("");
            }
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(taskMsg + "...");
            }
            if (stacktraceAdapter && typeof stacktraceAdapter.text === "function") {
                stacktraceAdapter.text("");
            }

            return http.request(resolveRunScopedUrl("report/subcatchments/"), {
                method: "GET",
                headers: { Accept: "text/html,application/xhtml+xml" }
            }).then(function (result) {
                var html = typeof result.body === "string" ? result.body : "";
                if (infoAdapter && typeof infoAdapter.html === "function") {
                    infoAdapter.html(html);
                }
                if (statusAdapter && typeof statusAdapter.html === "function") {
                    statusAdapter.html(taskMsg + "... Success");
                }
                emit("subcatchment:report:loaded", {});
                if (window.Project && typeof window.Project.getInstance === "function") {
                    var project = window.Project.getInstance();
                    if (project && typeof project.set_preferred_units === "function") {
                        project.set_preferred_units();
                    }
                }
            }).catch(handleError);
        };

        sub.show = function () {
            state.cmapMode = "default";
            return requestJson(resolveRunScopedUrl(SUBCATCHMENT_ENDPOINT), { params: { _: Date.now() } })
                .then(function (geojson) {
                    if (!geojson) {
                        return null;
                    }
                    state.data = geojson;
                    var map = ensureMap();
                    if (map && typeof map.clearFindFlashCache === "function") {
                        map.clearFindFlashCache("subcatchments");
                    }
                    buildLabels();
                    refreshGlLayer();
                    return state.glLayer;
                })
                .catch(handleError);
        };

        sub.render = function () {
            state.cmapMode = "default";
            updateGlLayerStyle();
        };

        sub.renderClear = function () {
            state.cmapMode = "clear";
            updateGlLayerStyle();
        };

        var baseTriggerEvent = sub.triggerEvent.bind(sub);
        sub.triggerEvent = function (eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === "BUILD_SUBCATCHMENTS_TASK_COMPLETED") {
                if (sub._completion_seen && sub._completion_seen[normalized]) {
                    return baseTriggerEvent(eventName, payload);
                }
                if (sub._completion_seen) {
                    sub._completion_seen[normalized] = true;
                }
                if (typeof sub.show === "function") {
                    sub.show();
                }
                try {
                    if (typeof ChannelDelineation !== "undefined" && ChannelDelineation !== null) {
                        var channel = ChannelDelineation.getInstance();
                        if (channel && typeof channel.show === "function") {
                            channel.show();
                        }
                    }
                } catch (err) {
                    console.warn("[Subcatchment GL] Unable to show channel delineation", err);
                }
                emit("subcatchment:build:completed", payload || {});
            } else if (normalized === "WATERSHED_ABSTRACTION_TASK_COMPLETED") {
                if (sub._completion_seen && sub._completion_seen[normalized]) {
                    return baseTriggerEvent(eventName, payload);
                }
                if (sub._completion_seen) {
                    sub._completion_seen[normalized] = true;
                }
                var buildSeen = sub._completion_seen && sub._completion_seen.BUILD_SUBCATCHMENTS_TASK_COMPLETED;
                if (!buildSeen && typeof sub.show === "function") {
                    sub.show();
                    try {
                        if (typeof ChannelDelineation !== "undefined" && ChannelDelineation !== null) {
                            var delayedChannel = ChannelDelineation.getInstance();
                            if (delayedChannel && typeof delayedChannel.show === "function") {
                                delayedChannel.show();
                            }
                        }
                    } catch (err) {
                        console.warn("[Subcatchment GL] Unable to show channel delineation", err);
                    }
                    if (state.postBuildRefreshTimer) {
                        clearTimeout(state.postBuildRefreshTimer);
                    }
                    state.postBuildRefreshTimer = setTimeout(function () {
                        state.postBuildRefreshTimer = null;
                        if (typeof sub.show === "function") {
                            sub.show();
                        }
                        try {
                            if (typeof ChannelDelineation !== "undefined" && ChannelDelineation !== null) {
                                var followupChannel = ChannelDelineation.getInstance();
                                if (followupChannel && typeof followupChannel.show === "function") {
                                    followupChannel.show();
                                }
                            }
                        } catch (err) {
                            console.warn("[Subcatchment GL] Unable to show channel delineation", err);
                        }
                    }, 1500);
                }
                if (typeof sub.report === "function") {
                    sub.report();
                }
                if (typeof sub.disconnect_status_stream === "function") {
                    sub.disconnect_status_stream(sub);
                }
                if (typeof sub.enableColorMap === "function") {
                    sub.enableColorMap("slope");
                }
                try {
                    if (window.Wepp && typeof window.Wepp.getInstance === "function") {
                        var wepp = window.Wepp.getInstance();
                        if (wepp && typeof wepp.updatePhosphorus === "function") {
                            wepp.updatePhosphorus();
                        }
                    }
                } catch (err) {
                    console.warn("[Subcatchment GL] Unable to update WEPP phosphorus", err);
                }
            }

            return baseTriggerEvent(eventName, payload);
        };

        sub.initializeColorMapControls = function () {
            renderLegendIfPresent("viridis", "landuse_sub_cmap_canvas_cover");
        };

        sub.onMapChange = function () {
            return null;
        };

        sub.updateLayerAvailability = function () {
            var checklist = window.lastPreflightChecklist;
            if (!checklist) {
                return;
            }

            if (checklist.subcatchments) {
                enableSlopeAspectRadios();
            }
            if (checklist.landuse) {
                disableRadio("sub_cmap_radio_dom_lc", false);
            }
            if (checklist.rangeland_cover) {
                disableRadio("sub_cmap_radio_rangeland_cover", false);
            }
            if (checklist.soils) {
                disableRadio("sub_cmap_radio_dom_soil", false);
            }
        };

        var bootstrapState = {
            colorControlsInitialised: false,
            defaultColorMapEnabled: false,
            reportLoaded: false,
            preflightListenerAttached: false
        };

        sub.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            var controllerContext = helper && typeof helper.getControllerContext === "function"
                ? helper.getControllerContext(ctx, "subcatchment")
                : {};

            if (!bootstrapState.colorControlsInitialised && typeof sub.initializeColorMapControls === "function") {
                try {
                    sub.initializeColorMapControls();
                } catch (err) {
                    console.warn("[Subcatchment GL] Failed to initialize color map controls", err);
                }
                bootstrapState.colorControlsInitialised = true;
            }

            var jobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "build_subcatchments_and_abstract_watershed_rq")
                : null;
            if (!jobId && controllerContext.jobId) {
                jobId = controllerContext.jobId;
            }
            if (!jobId) {
                var jobIds = ctx && (ctx.jobIds || ctx.jobs);
                if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "build_subcatchments_and_abstract_watershed_rq")) {
                    var value = jobIds.build_subcatchments_and_abstract_watershed_rq;
                    if (value !== undefined && value !== null) {
                        jobId = String(value);
                    }
                }
            }

            if (typeof sub.set_rq_job_id === "function") {
                sub.set_rq_job_id(sub, jobId);
            }

            var watershed = (ctx.data && ctx.data.watershed) || {};
            var hasSubcatchments = Boolean(watershed.hasSubcatchments);

            if (hasSubcatchments) {
                if (typeof sub.show === "function") {
                    sub.show();
                }
                if (!bootstrapState.reportLoaded && typeof sub.report === "function") {
                    sub.report();
                    bootstrapState.reportLoaded = true;
                }
                var defaultColorMap = resolveColorMapAlias(controllerContext.defaultColorMap || "slp_asp");
                if (!bootstrapState.defaultColorMapEnabled && typeof sub.enableColorMap === "function") {
                    sub.enableColorMap(defaultColorMap);
                    bootstrapState.defaultColorMapEnabled = true;
                }
            }

            if (typeof sub.updateLayerAvailability === "function") {
                sub.updateLayerAvailability();
            }

            if (!bootstrapState.preflightListenerAttached && typeof document !== "undefined") {
                document.addEventListener("preflight:update", function () {
                    if (typeof sub.updateLayerAvailability === "function") {
                        sub.updateLayerAvailability();
                    }
                });
                bootstrapState.preflightListenerAttached = true;
            }

            return sub;
        };

        setupDelegatedEvents();

        return sub;
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

window.SubcatchmentDelineation = SubcatchmentDelineation;
