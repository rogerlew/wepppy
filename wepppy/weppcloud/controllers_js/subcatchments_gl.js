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
    var GRID_LAYER_NAME = "Gridded Output";
    var GRID_LAYER_ID = "wc-gridded-loss";

    var SUBCATCHMENT_ENDPOINT = "resources/subcatchments.json";
    var GRID_LOSS_ENDPOINT = "resources/flowpaths_loss.tif";

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

    var DEFAULT_LINEAR_RANGE = 50;

    var WEPP_LOSS_METRIC_EXPRESSIONS = Object.freeze({
        runoff: 'CAST(loss."Runoff Volume" / (NULLIF(loss."Hillslope Area", 0) * 10.0) AS DOUBLE)',
        subrunoff: 'CAST(loss."Subrunoff Volume" / (NULLIF(loss."Hillslope Area", 0) * 10.0) AS DOUBLE)',
        baseflow: 'CAST(loss."Baseflow Volume" / (NULLIF(loss."Hillslope Area", 0) * 10.0) AS DOUBLE)',
        loss: 'CAST(loss."Soil Loss" / NULLIF(loss."Hillslope Area", 0) AS DOUBLE)'
    });

    var RANGE_LABEL_CONFIG = {
        phosphorus: {
            rangeKey: "phosphorus",
            labelMinKey: "phosphorusMin",
            labelMaxKey: "phosphorusMax",
            unit: "kg/ha",
            log: { min: 0.001, max: 10.0, maxLinear: 100 }
        },
        runoff: {
            rangeKey: "runoff",
            labelMinKey: "runoffMin",
            labelMaxKey: "runoffMax",
            unit: "mm",
            log: { min: 0.1, max: 1000, maxLinear: 100 }
        },
        loss: {
            rangeKey: "loss",
            labelMinKey: "lossMin",
            labelMaxKey: "lossMax",
            unit: "kg/ha",
            log: { min: 1, max: 10000, maxLinear: 100 }
        },
        ash_load: {
            rangeKey: "ashLoad",
            labelMinKey: "ashLoadMin",
            labelMaxKey: "ashLoadMax",
            unit: "tonne/ha",
            log: { min: 0.001, max: 100, maxLinear: 100 }
        },
        ash_transport: {
            rangeKey: "ashTransport",
            labelMinKey: "ashTransportMin",
            labelMaxKey: "ashTransportMax",
            unit: "tonne/ha",
            log: { min: 0.001, max: 20, maxLinear: 100 }
        },
        rhem_runoff: {
            rangeKey: "rhemRunoff",
            labelMinKey: "rhemRunoffMin",
            labelMaxKey: "rhemRunoffMax",
            unit: "mm",
            log: { min: 0.1, max: 1000, maxLinear: 100 }
        },
        rhem_sed_yield: {
            rangeKey: "rhemSedYield",
            labelMinKey: "rhemSedYieldMin",
            labelMaxKey: "rhemSedYieldMax",
            unit: "mm",
            log: { min: 1, max: 10000, maxLinear: 100 }
        },
        rhem_soil_loss: {
            rangeKey: "rhemSoilLoss",
            labelMinKey: "rhemSoilLossMin",
            labelMaxKey: "rhemSoilLossMax",
            unit: "kg/ha",
            log: { min: 0.001, max: 10000, maxLinear: 100 }
        }
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
            typeof deckApi.TextLayer !== "function" || typeof deckApi.BitmapLayer !== "function") {
            throw new Error("SubcatchmentDelineation GL requires deck.gl GeoJsonLayer/TextLayer/BitmapLayer.");
        }
        return deckApi;
    }

    function ensureGeoTiff() {
        var win = typeof window !== "undefined" ? window : null;
        var globalGeoTiff = win && win.GeoTIFF && typeof win.GeoTIFF.fromArrayBuffer === "function"
            ? win.GeoTIFF
            : null;
        if (globalGeoTiff) {
            return Promise.resolve(globalGeoTiff);
        }
        if (win && win.geotiff) {
            if (win.geotiff.GeoTIFF && typeof win.geotiff.GeoTIFF.fromArrayBuffer === "function") {
                return Promise.resolve(win.geotiff.GeoTIFF);
            }
            if (win.geotiff.default && typeof win.geotiff.default.fromArrayBuffer === "function") {
                return Promise.resolve(win.geotiff.default);
            }
        }
        return new Promise(function (resolve, reject) {
            if (typeof document === "undefined") {
                reject(new Error("GeoTIFF loader unavailable in this context."));
                return;
            }
            var script = document.createElement("script");
            script.src = "https://unpkg.com/geotiff@2.1.3/dist-browser/geotiff.js";
            script.async = true;
            script.onload = function () {
                var loadedWin = typeof window !== "undefined" ? window : null;
                if (loadedWin && loadedWin.GeoTIFF && typeof loadedWin.GeoTIFF.fromArrayBuffer === "function") {
                    resolve(loadedWin.GeoTIFF);
                } else {
                    reject(new Error("GeoTIFF global missing after script load."));
                }
            };
            script.onerror = function () {
                reject(new Error("GeoTIFF script failed to load."));
            };
            document.head.appendChild(script);
        });
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

    function renderUnitLabel(value, unit, target, fallbackText) {
        if (!target) {
            return;
        }
        var fallback = fallbackText !== undefined
            ? fallbackText
            : (isFiniteNumber(value) ? (unit ? value + " " + unit : String(value)) : "");
        var applyHtml = typeof window !== "undefined" && typeof window.applyLabelHtml === "function"
            ? window.applyLabelHtml
            : function (label, html) {
                if (label && "innerHTML" in label) {
                    label.innerHTML = html;
                } else if (label && "textContent" in label) {
                    label.textContent = html;
                }
            };

        if (!window.UnitizerClient || typeof window.UnitizerClient.ready !== "function") {
            applyHtml(target, fallback);
            return;
        }

        window.UnitizerClient.ready()
            .then(function (client) {
                var html = client.renderValue(value, unit, { includeUnits: true });
                applyHtml(target, html);
            })
            .catch(function (error) {
                console.warn("[Subcatchment GL] Failed to update unitized label", error);
                applyHtml(target, fallback);
            });
    }

    function resolveRangeMax(state, mode) {
        var cfg = RANGE_LABEL_CONFIG[mode];
        if (!cfg) {
            return null;
        }
        var rangeEl = state.rangeElements[cfg.rangeKey];
        if (!rangeEl) {
            return null;
        }
        var sliderValue = parseNumeric(rangeEl && rangeEl.value);
        var linearValue = isFiniteNumber(sliderValue) ? sliderValue : DEFAULT_LINEAR_RANGE;
        if (cfg.log) {
            if (typeof window.linearToLog === "function") {
                return window.linearToLog(linearValue, cfg.log.min, cfg.log.max, cfg.log.maxLinear);
            }
            return cfg.log.min * Math.pow(cfg.log.max / cfg.log.min, linearValue / cfg.log.maxLinear);
        }
        return linearValue;
    }

    function updateLegendLabels(state, mode) {
        var cfg = RANGE_LABEL_CONFIG[mode];
        if (!cfg) {
            return;
        }
        var maxValue = resolveRangeMax(state, mode);
        if (!isFiniteNumber(maxValue)) {
            return;
        }
        var minValue;
        if (typeof cfg.minValue === "function") {
            minValue = cfg.minValue(maxValue);
        } else if (cfg.minValue !== undefined) {
            minValue = cfg.minValue;
        } else {
            minValue = 0;
        }

        renderUnitLabel(minValue, cfg.unit, state.labelElements[cfg.labelMinKey]);
        renderUnitLabel(maxValue, cfg.unit, state.labelElements[cfg.labelMaxKey]);
    }

    function resolveWeppKey(feature) {
        if (!feature || !feature.properties) {
            return null;
        }
        var props = feature.properties;
        var candidates = [
            props.WeppID,
            props.wepp_id,
            props.weppId,
            props.Hillslopes,
            props.hillslope
        ];
        for (var i = 0; i < candidates.length; i += 1) {
            var candidate = candidates[i];
            if (candidate !== undefined && candidate !== null && candidate !== "") {
                return String(candidate);
            }
        }
        return null;
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

    function buildLabelLayer(deckApi, labelData) {
        return new deckApi.TextLayer({
            id: SUBCATCHMENT_LABEL_LAYER_ID,
            data: labelData || [],
            pickable: false,
            getPosition: function (d) { return d.position; },
            getText: function (d) { return d.text; },
            getSize: function () { return 14; },
            sizeUnits: "pixels",
            getColor: function () { return [255, 120, 0, 255]; },
            outlineColor: [255, 255, 255, 255],
            outlineWidth: 2,
            fontSettings: { sdf: true }
        });
    }

    function buildSubcatchmentLayer(deckApi, data, colorFn, mode) {
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

    function buildBitmapLayer(deckApi, canvas, bounds) {
        var hasData = Boolean(canvas && bounds);
        return new deckApi.BitmapLayer({
            id: GRID_LAYER_ID,
            image: canvas || null,
            bounds: bounds || [0, 0, 0, 0],
            opacity: 1.0,
            pickable: false,
            visible: hasData
        });
    }

    function colorizeRaster(values, width, height, colorFn) {
        var canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        var ctx2d = canvas.getContext("2d");
        var imgData = ctx2d.createImageData(width, height);
        for (var i = 0, j = 0; i < values.length; i += 1, j += 4) {
            var v = values[i];
            var color = colorFn && typeof colorFn === "function" ? colorFn(v) : [180, 180, 180, 230];
            if (!color || color.length < 3) {
                color = [180, 180, 180, 230];
            }
            imgData.data[j] = color[0];
            imgData.data[j + 1] = color[1];
            imgData.data[j + 2] = color[2];
            imgData.data[j + 3] = color.length > 3 ? color[3] : 230;
        }
        ctx2d.putImageData(imgData, 0, 0);
        return canvas;
    }

    function loadRaster(path, colorFn) {
        var url = resolveRunScopedUrl("browse/" + path);
        return ensureGeoTiff().then(function (GeoTiffApi) {
            return fetch(url).then(function (resp) {
                if (!resp.ok) {
                    throw new Error("Raster fetch failed " + resp.status + ": " + url);
                }
                return resp.arrayBuffer();
            }).then(function (arrayBuffer) {
                return GeoTiffApi.fromArrayBuffer(arrayBuffer);
            }).then(function (tiff) {
                return tiff.getImage();
            }).then(function (image) {
                var width = image.getWidth();
                var height = image.getHeight();
                return image.readRasters({ interleave: true, samples: [0] }).then(function (raster) {
                    var values = ArrayBuffer.isView(raster) ? raster : raster[0];
                    var canvas = colorizeRaster(values, width, height, colorFn);
                    var bounds = image.getBoundingBox();
                    return {
                        canvas: canvas,
                        bounds: bounds,
                        values: values,
                        width: width,
                        height: height
                    };
                });
            });
        });
    }

    function resolveRunSlugForQuery() {
        var prefix = typeof window.site_prefix === "string" ? window.site_prefix : "";
        if (prefix && prefix !== "/" && prefix.charAt(0) !== "/") {
            prefix = "/" + prefix;
        }
        if (prefix === "/") {
            prefix = "";
        }

        var path = window.location && window.location.pathname ? window.location.pathname : "";
        if (prefix && path.indexOf(prefix) === 0) {
            path = path.slice(prefix.length);
        }

        var parts = path.split("/").filter(function (segment) {
            return segment.length > 0;
        });
        var runsIndex = parts.indexOf("runs");
        if (runsIndex === -1 || parts.length <= runsIndex + 1) {
            return null;
        }
        return decodeURIComponent(parts[runsIndex + 1]);
    }

    function postQueryEngine(http, payload) {
        var runSlug = resolveRunSlugForQuery();
        if (!runSlug) {
            return Promise.reject(new Error("Unable to resolve run identifier from the current URL."));
        }
        var origin = "";
        if (window && window.location) {
            if (window.location.origin) {
                origin = window.location.origin;
            } else if (window.location.protocol && window.location.host) {
                origin = window.location.protocol + "//" + window.location.host;
            }
        }
        var targetPath = "/query-engine/runs/" + encodeURIComponent(runSlug) + "/query";
        var targetUrl = origin ? origin.replace(/\/+$/, "") + targetPath : targetPath;
        return http.postJson(targetUrl, payload, {
            headers: { Accept: "application/json" }
        }).then(function (result) {
            return result && result.body ? result.body : null;
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
            cmapMode: "default",
            dataCover: null,
            dataSlpAsp: null,
            dataLanduse: null,
            dataSoils: null,
            dataRunoff: null,
            dataLoss: null,
            dataPhosphorus: null,
            dataAshLoad: null,
            dataAshTransport: null,
            dataRhemRunoff: null,
            dataRhemSedYield: null,
            dataRhemSoilLoss: null,
            ashMeasure: null,
            grid: null,
            gridData: null,
            gridBounds: null,
            gridRangeMax: null,
            rangeElements: {
                phosphorus: document.getElementById("wepp_sub_cmap_range_phosphorus"),
                runoff: document.getElementById("wepp_sub_cmap_range_runoff"),
                loss: document.getElementById("wepp_sub_cmap_range_loss"),
                griddedLoss: document.getElementById("wepp_grd_cmap_range_loss"),
                ashLoad: document.getElementById("ash_sub_cmap_range_load"),
                ashTransport: document.getElementById("ash_sub_cmap_range_transport"),
                rhemRunoff: document.getElementById("rhem_sub_cmap_range_runoff"),
                rhemSedYield: document.getElementById("rhem_sub_cmap_range_sed_yield"),
                rhemSoilLoss: document.getElementById("rhem_sub_cmap_range_soil_loss")
            },
            labelElements: {
                phosphorusMin: document.getElementById("wepp_sub_cmap_canvas_phosphorus_min"),
                phosphorusMax: document.getElementById("wepp_sub_cmap_canvas_phosphorus_max"),
                runoffMin: document.getElementById("wepp_sub_cmap_canvas_runoff_min"),
                runoffMax: document.getElementById("wepp_sub_cmap_canvas_runoff_max"),
                lossMin: document.getElementById("wepp_sub_cmap_canvas_loss_min"),
                lossMax: document.getElementById("wepp_sub_cmap_canvas_loss_max"),
                griddedLossMin: document.getElementById("wepp_grd_cmap_range_loss_min"),
                griddedLossMax: document.getElementById("wepp_grd_cmap_range_loss_max"),
                griddedLossUnits: document.getElementById("wepp_grd_cmap_range_loss_units"),
                ashLoadMin: document.getElementById("ash_sub_cmap_canvas_load_min"),
                ashLoadMax: document.getElementById("ash_sub_cmap_canvas_load_max"),
                ashTransportMin: document.getElementById("ash_sub_cmap_canvas_transport_min"),
                ashTransportMax: document.getElementById("ash_sub_cmap_canvas_transport_max"),
                rhemRunoffMin: document.getElementById("rhem_sub_cmap_canvas_runoff_min"),
                rhemRunoffMax: document.getElementById("rhem_sub_cmap_canvas_runoff_max"),
                rhemSedYieldMin: document.getElementById("rhem_sub_cmap_canvas_sed_yield_min"),
                rhemSedYieldMax: document.getElementById("rhem_sub_cmap_canvas_sed_yield_max"),
                rhemSoilLossMin: document.getElementById("rhem_sub_cmap_canvas_soil_loss_min"),
                rhemSoilLossMax: document.getElementById("rhem_sub_cmap_canvas_soil_loss_max"),
                rhemSoilLossUnits: document.getElementById("rhem_sub_cmap_canvas_soil_loss_units")
            },
            colorMappers: {
                runoff: typeof window.createColormap === "function" ? window.createColormap({ colormap: "winter", nshades: 64 }) : null,
                loss: typeof window.createColormap === "function" ? window.createColormap({ colormap: "jet2", nshades: 64 }) : null,
                phosphorus: typeof window.createColormap === "function" ? window.createColormap({ colormap: "viridis", nshades: 64 }) : null,
                slopeAspect: typeof window.createColormap === "function" ? window.createColormap({ colormap: "viridis", nshades: 64 }) : null,
                ashLoad: typeof window.createColormap === "function" ? window.createColormap({ colormap: "jet2", nshades: 64 }) : null,
                ashTransport: typeof window.createColormap === "function" ? window.createColormap({ colormap: "jet2", nshades: 64 }) : null,
                rhemRunoff: typeof window.createColormap === "function" ? window.createColormap({ colormap: "winter", nshades: 64 }) : null,
                rhemSedYield: typeof window.createColormap === "function" ? window.createColormap({ colormap: "viridis", nshades: 64 }) : null,
                rhemSoilLoss: typeof window.createColormap === "function" ? window.createColormap({ colormap: "jet2", nshades: 64 }) : null,
                cover: typeof window.createColormap === "function" ? window.createColormap({ colormap: "viridis", nshades: 64 }) : null
            },
            postBuildRefreshTimer: null
        };

        sub.state = state;
        sub.glLayer = null;

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
                case "phosphorus":
                    return function (feature) {
                        var id = feature.properties.TopazID;
                        var record = state.dataPhosphorus ? state.dataPhosphorus[id] : null;
                        if (!record) {
                            return defaultFill;
                        }
                        var v = parseFloat(record.value);
                        if (!Number.isFinite(v)) {
                            return defaultFill;
                        }
                        var r = resolveRangeMax(state, "phosphorus");
                        if (!isFiniteNumber(r) || r <= 0) {
                            return defaultFill;
                        }
                        var hex = state.colorMappers.phosphorus.map(v / r);
                        return hexToRgba(hex, 0.9);
                    };
                case "runoff":
                    return function (feature) {
                        var key = resolveWeppKey(feature);
                        var record = key && state.dataRunoff ? state.dataRunoff[key] : null;
                        var v = record ? parseFloat(record.value) : NaN;
                        if (!record || Number.isNaN(v)) {
                            return defaultFill;
                        }
                        var r = resolveRangeMax(state, "runoff");
                        if (!isFiniteNumber(r) || r <= 0) {
                            return defaultFill;
                        }
                        var hex = state.colorMappers.runoff.map(v / r);
                        return hexToRgba(hex, 0.9);
                    };
                case "loss":
                    return function (feature) {
                        var key = resolveWeppKey(feature);
                        var record = key && state.dataLoss ? state.dataLoss[key] : null;
                        var v = record ? parseFloat(record.value) : NaN;
                        if (!record || Number.isNaN(v)) {
                            return defaultFill;
                        }
                        var r = resolveRangeMax(state, "loss");
                        if (!isFiniteNumber(r) || r <= 0) {
                            return defaultFill;
                        }
                        var hex = state.colorMappers.loss.map(v / r);
                        return hexToRgba(hex, 0.9);
                    };
                case "ash_load":
                    return function (feature) {
                        var id = feature.properties.TopazID;
                        var bucket = state.dataAshLoad && state.dataAshLoad[id] ? state.dataAshLoad[id] : null;
                        if (!bucket || !state.ashMeasure) {
                            return defaultFill;
                        }
                        var record = bucket[state.ashMeasure];
                        if (!record) {
                            return defaultFill;
                        }
                        var v = parseFloat(record.value);
                        if (!Number.isFinite(v)) {
                            return defaultFill;
                        }
                        var r = resolveRangeMax(state, "ash_load");
                        if (!isFiniteNumber(r) || r <= 0) {
                            return defaultFill;
                        }
                        var hex = state.colorMappers.ashLoad.map(v / r);
                        return hexToRgba(hex, 0.9);
                    };
                case "ash_transport":
                    return function (feature) {
                        var id = feature.properties.TopazID;
                        var record = state.dataAshTransport ? state.dataAshTransport[id] : null;
                        if (!record) {
                            return defaultFill;
                        }
                        var value = parseFloat(record.value);
                        if (!Number.isFinite(value)) {
                            return defaultFill;
                        }
                        var r = resolveRangeMax(state, "ash_transport");
                        if (!isFiniteNumber(r) || r <= 0) {
                            return defaultFill;
                        }
                        var hex = state.colorMappers.ashTransport.map(value / r);
                        return hexToRgba(hex, 0.9);
                    };
                case "rhem_runoff":
                    return function (feature) {
                        var id = feature.properties.TopazID;
                        var record = state.dataRhemRunoff ? state.dataRhemRunoff[id] : null;
                        if (!record) {
                            return defaultFill;
                        }
                        var value = parseFloat(record.value);
                        if (!Number.isFinite(value)) {
                            return defaultFill;
                        }
                        var r = resolveRangeMax(state, "rhem_runoff");
                        if (!isFiniteNumber(r) || r <= 0) {
                            return defaultFill;
                        }
                        var hex = state.colorMappers.rhemRunoff.map(value / r);
                        return hexToRgba(hex, 0.9);
                    };
                case "rhem_sed_yield":
                    return function (feature) {
                        var id = feature.properties.TopazID;
                        var record = state.dataRhemSedYield ? state.dataRhemSedYield[id] : null;
                        if (!record) {
                            return defaultFill;
                        }
                        var value = parseFloat(record.value);
                        if (!Number.isFinite(value)) {
                            return defaultFill;
                        }
                        var r = resolveRangeMax(state, "rhem_sed_yield");
                        if (!isFiniteNumber(r) || r <= 0) {
                            return defaultFill;
                        }
                        var hex = state.colorMappers.rhemSedYield.map(value / r);
                        return hexToRgba(hex, 0.9);
                    };
                case "rhem_soil_loss":
                    return function (feature) {
                        var id = feature.properties.TopazID;
                        var record = state.dataRhemSoilLoss ? state.dataRhemSoilLoss[id] : null;
                        if (!record) {
                            return defaultFill;
                        }
                        var value = parseFloat(record.value);
                        if (!Number.isFinite(value)) {
                            return defaultFill;
                        }
                        var r = resolveRangeMax(state, "rhem_soil_loss");
                        if (!isFiniteNumber(r) || r <= 0) {
                            return defaultFill;
                        }
                        var hex = state.colorMappers.rhemSoilLoss.map(value / r);
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
                var cmapFn = colorFnFactory();
                var nextLayer = buildSubcatchmentLayer(deckApi, state.data, cmapFn, state.cmapMode);
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
            var nextLayer = buildSubcatchmentLayer(deckApi, state.data, cmapFn, state.cmapMode);
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
        }

        function removeGrid() {
            if (!state.grid) {
                return;
            }
            var map = ensureMap();
            try {
                if (typeof map.unregisterOverlay === "function") {
                    map.unregisterOverlay(state.grid);
                } else if (map.ctrls && typeof map.ctrls.removeLayer === "function") {
                    map.ctrls.removeLayer(state.grid);
                }
            } catch (err) {
                // ignore
            }
            try {
                map.removeLayer(state.grid, { skipOverlay: true });
            } catch (err) {
                console.warn("[Subcatchment GL] Failed to remove grid layer", err);
            }
            state.grid = null;
            state.gridData = null;
            state.gridBounds = null;
            state.gridRangeMax = null;
        }

        function gridColorFnFactory(rangeMax) {
            var mapper = state.colorMappers.loss;
            var safeRange = isFiniteNumber(rangeMax) && rangeMax > 0 ? rangeMax : null;
            return function (value) {
                if (!Number.isFinite(value) || safeRange === null) {
                    return [0, 0, 0, 0];
                }
                var t = (value + safeRange) / (2 * safeRange);
                if (t < 0) {
                    t = 0;
                } else if (t > 1) {
                    t = 1;
                }
                var hex = mapper ? mapper.map(t) : "#ffffff";
                return hexToRgba(hex, 0.9);
            };
        }

        function updateGriddedLossLabels(rangeMax) {
            if (!isFiniteNumber(rangeMax)) {
                return;
            }
            renderUnitLabel(-1.0 * rangeMax, "kg/m^2", state.labelElements.griddedLossMin);
            renderUnitLabel(rangeMax, "kg/m^2", state.labelElements.griddedLossMax);
            if (state.labelElements.griddedLossUnits) {
                if (window.UnitizerClient && typeof window.UnitizerClient.ready === "function") {
                    window.UnitizerClient.ready().then(function (client) {
                        state.labelElements.griddedLossUnits.innerHTML = client.renderUnits("kg/m^2");
                    }).catch(function () {});
                } else {
                    state.labelElements.griddedLossUnits.textContent = "kg/m^2";
                }
            }
        }

        function updateGriddedLoss() {
            var range = state.rangeElements.griddedLoss;
            if (!range) {
                return;
            }
            var value = parseFloat(range.value);
            if (!Number.isFinite(value)) {
                return;
            }
            state.gridRangeMax = value;
            updateGriddedLossLabels(value);
            if (!state.gridData || !state.gridBounds) {
                return;
            }
            var deckApi = ensureDeck();
            var map = ensureMap();
            var colorFn = gridColorFnFactory(value);
            var canvas = colorizeRaster(state.gridData.values, state.gridData.width, state.gridData.height, colorFn);
            var nextLayer = buildBitmapLayer(deckApi, canvas, state.gridBounds);
            replaceOverlayLayer(map, GRID_LAYER_NAME, state.grid, nextLayer, true);
            state.grid = nextLayer;
        }

        function renderGriddedLoss() {
            removeGrid();
            var deckApi = ensureDeck();
            var map = ensureMap();
            var range = state.rangeElements.griddedLoss;
            var rangeValue = range ? parseFloat(range.value) : null;
            var rangeMax = Number.isFinite(rangeValue) ? rangeValue : 1;
            var colorFn = gridColorFnFactory(rangeMax);
            return loadRaster(GRID_LOSS_ENDPOINT, colorFn)
                .then(function (raster) {
                    state.gridData = raster;
                    state.gridBounds = raster.bounds;
                    state.gridRangeMax = rangeMax;
                    var layer = buildBitmapLayer(deckApi, raster.canvas, raster.bounds);
                    state.grid = layer;
                    if (typeof map.registerOverlay === "function") {
                        map.registerOverlay(layer, GRID_LAYER_NAME);
                    } else if (map.ctrls && typeof map.ctrls.addOverlay === "function") {
                        map.ctrls.addOverlay(layer, GRID_LAYER_NAME);
                    }
                    if (typeof map.addLayer === "function") {
                        map.addLayer(layer);
                    }
                    updateGriddedLoss();
                    return layer;
                })
                .catch(function (error) {
                    handleError(error);
                    throw error;
                });
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

        var lossMetricCache = Object.create(null);
        var lossMetricInflight = Object.create(null);

        function fetchLossMetric(metricKey) {
            var expression = WEPP_LOSS_METRIC_EXPRESSIONS[metricKey];
            if (!expression) {
                return Promise.reject(new Error("Unknown WEPP loss metric: " + metricKey));
            }

            if (lossMetricCache[metricKey]) {
                return Promise.resolve(lossMetricCache[metricKey]);
            }
            if (lossMetricInflight[metricKey]) {
                return lossMetricInflight[metricKey];
            }

            var payload = {
                datasets: [
                    { path: "wepp/output/interchange/loss_pw0.hill.parquet", alias: "loss" }
                ],
                columns: [
                    'loss.wepp_id AS wepp_id',
                    expression + " AS value"
                ],
                order_by: ["wepp_id"]
            };

            var requestPromise = postQueryEngine(http, payload).then(function (response) {
                var records = Array.isArray(response && response.records) ? response.records : [];
                var map = Object.create(null);
                records.forEach(function (row) {
                    if (!row) {
                        return;
                    }
                    var weppId = row.wepp_id;
                    if (weppId === undefined || weppId === null) {
                        return;
                    }
                    map[String(weppId)] = {
                        wepp_id: weppId,
                        value: row.value
                    };
                });
                lossMetricCache[metricKey] = map;
                return map;
            });

            requestPromise = requestPromise.then(function (map) {
                delete lossMetricInflight[metricKey];
                return map;
            }, function (error) {
                delete lossMetricInflight[metricKey];
                throw error;
            });

            lossMetricInflight[metricKey] = requestPromise;
            return requestPromise;
        }

        function renderRunoff() {
            return fetchLossMetric("runoff").then(function (data) {
                state.dataRunoff = data;
                state.cmapMode = "runoff";
                updateGlLayerStyle();
                updateLegendLabels(state, "runoff");
            }).catch(handleError);
        }

        function renderSubrunoff() {
            return fetchLossMetric("subrunoff").then(function (data) {
                state.dataRunoff = state.dataRunoff || data;
                state.cmapMode = "runoff";
                updateGlLayerStyle();
                updateLegendLabels(state, "runoff");
            }).catch(handleError);
        }

        function renderBaseflow() {
            return fetchLossMetric("baseflow").then(function (data) {
                state.dataRunoff = state.dataRunoff || data;
                state.cmapMode = "runoff";
                updateGlLayerStyle();
                updateLegendLabels(state, "runoff");
            }).catch(handleError);
        }

        function renderLoss() {
            return fetchLossMetric("loss").then(function (data) {
                state.dataLoss = data;
                state.cmapMode = "loss";
                updateGlLayerStyle();
                updateLegendLabels(state, "loss");
            }).catch(handleError);
        }

        function renderPhosphorus() {
            return requestJson(resolveRunScopedUrl("query/wepp/phosphorus/subcatchments/"))
                .then(function (data) {
                    state.dataPhosphorus = data;
                    state.cmapMode = "phosphorus";
                    updateGlLayerStyle();
                    updateLegendLabels(state, "phosphorus");
                })
                .catch(handleError);
        }

        function getAshTransportMeasure() {
            var radio = document.querySelector("input[name='wepp_sub_cmap_radio']:checked");
            return radio ? radio.value : null;
        }

        function renderAshLoad() {
            return requestJson(resolveRunScopedUrl("query/ash/out/"))
                .then(function (data) {
                    state.dataAshLoad = data;
                    state.cmapMode = "ash_load";
                    state.ashMeasure = getAshTransportMeasure();
                    updateGlLayerStyle();
                    updateLegendLabels(state, "ash_load");
                })
                .catch(handleError);
        }

        function renderAshTransport() {
            return requestJson(resolveRunScopedUrl("query/ash_out/"))
                .then(function (data) {
                    state.dataAshTransport = data;
                    state.cmapMode = "ash_transport";
                    updateGlLayerStyle();
                    updateLegendLabels(state, "ash_transport");
                })
                .catch(handleError);
        }

        function renderRhemRunoff() {
            return requestJson(resolveRunScopedUrl("query/rhem/runoff/subcatchments/"))
                .then(function (data) {
                    state.dataRhemRunoff = data;
                    state.cmapMode = "rhem_runoff";
                    updateGlLayerStyle();
                    updateLegendLabels(state, "rhem_runoff");
                })
                .catch(handleError);
        }

        function renderRhemSedYield() {
            return requestJson(resolveRunScopedUrl("query/rhem/sed_yield/subcatchments/"))
                .then(function (data) {
                    state.dataRhemSedYield = data;
                    state.cmapMode = "rhem_sed_yield";
                    updateGlLayerStyle();
                    updateLegendLabels(state, "rhem_sed_yield");
                })
                .catch(handleError);
        }

        function renderRhemSoilLoss() {
            return requestJson(resolveRunScopedUrl("query/rhem/soil_loss/subcatchments/"))
                .then(function (data) {
                    state.dataRhemSoilLoss = data;
                    state.cmapMode = "rhem_soil_loss";
                    updateGlLayerStyle();
                    updateLegendLabels(state, "rhem_soil_loss");
                })
                .catch(handleError);
        }

        function handleRangeUpdate(mode) {
            if (!mode) {
                return;
            }
            updateLegendLabels(state, mode);
            if (mode === "grd_loss") {
                updateGriddedLoss();
                return;
            }
            updateGlLayerStyle();
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

            dom.delegate(document, "input", "[data-subcatchment-role='scale-range']", function () {
                var mode = this.getAttribute("data-subcatchment-scale");
                handleRangeUpdate(mode);
            });
        }

        function bindDirectFallbackListeners() {
            var gridded = state.rangeElements.griddedLoss;
            if (gridded && typeof gridded.addEventListener === "function") {
                gridded.addEventListener("input", function () {
                    handleRangeUpdate("grd_loss");
                });
            }
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
            if (!state.glLayer && resolvedMode !== "default" && resolvedMode !== "clear" && resolvedMode !== "grd_loss") {
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
            } else if (resolvedMode === "sub_runoff") {
                renderRunoff();
            } else if (resolvedMode === "sub_subrunoff") {
                renderSubrunoff();
            } else if (resolvedMode === "sub_baseflow") {
                renderBaseflow();
            } else if (resolvedMode === "sub_loss") {
                renderLoss();
            } else if (resolvedMode === "sub_phosphorus") {
                renderPhosphorus();
            } else if (resolvedMode === "sub_rhem_runoff") {
                renderRhemRunoff();
            } else if (resolvedMode === "sub_rhem_sed_yield") {
                renderRhemSedYield();
            } else if (resolvedMode === "sub_rhem_soil_loss") {
                renderRhemSoilLoss();
            } else if (resolvedMode === "ash_load") {
                renderAshLoad();
            } else if (resolvedMode === "wind_transport (kg/ha)" || resolvedMode === "water_transport (kg/ha" || resolvedMode === "ash_transport (kg/ha)" || resolvedMode === "ash_transport") {
                renderAshTransport();
            } else if (resolvedMode === "grd_loss") {
                state.cmapMode = "clear";
                updateGlLayerStyle();
                renderGriddedLoss();
            }

            if (resolvedMode !== "grd_loss") {
                removeGrid();
            }
        };

        sub.prefetchLossMetrics = function () {
            return Promise.all([
                fetchLossMetric("runoff").then(function (data) { state.dataRunoff = state.dataRunoff || data; }),
                fetchLossMetric("subrunoff"),
                fetchLossMetric("baseflow"),
                fetchLossMetric("loss").then(function (data) { state.dataLoss = data; })
            ]);
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
            renderLegendIfPresent("viridis", "wepp_sub_cmap_canvas_phosphorus");
            renderLegendIfPresent("winter", "wepp_sub_cmap_canvas_runoff");
            renderLegendIfPresent("jet2", "wepp_sub_cmap_canvas_loss");
            renderLegendIfPresent("jet2", "wepp_grd_cmap_canvas_loss");
            renderLegendIfPresent("winter", "rhem_sub_cmap_canvas_runoff");
            renderLegendIfPresent("viridis", "rhem_sub_cmap_canvas_sed_yield");
            renderLegendIfPresent("jet2", "rhem_sub_cmap_canvas_soil_loss");
            renderLegendIfPresent("jet2", "ash_sub_cmap_canvas_load");
            renderLegendIfPresent("jet2", "ash_sub_cmap_canvas_transport");
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
        bindDirectFallbackListeners();

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
