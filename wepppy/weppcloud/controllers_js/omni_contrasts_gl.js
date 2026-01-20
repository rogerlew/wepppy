/* ----------------------------------------------------------------------------
 * Omni Contrast Overlays (Deck.gl)
 * ----------------------------------------------------------------------------
 */
var OmniContrastOverlays = (function () {
    "use strict";

    var instance;

    var CONTRAST_LAYER_NAME = "Contrast IDs";
    var CONTRAST_LABEL_LAYER_NAME = "Contrast ID Labels";
    var CONTRAST_LAYER_ID = "wc-omni-contrast-ids";
    var CONTRAST_LABEL_LAYER_ID = "wc-omni-contrast-labels";
    var CONTRAST_HOVER_LABEL_LAYER_ID = "wc-omni-contrast-hover-label";
    var CONTRAST_ENDPOINT = "download/omni/contrasts/contrast_ids.wgs.geojson";

    var DEFAULT_STYLE = {
        color: "#1f9d55",
        weight: 2,
        opacity: 0.65,
        fillColor: "#1f9d55",
        fillOpacity: 0.2
    };
    var HOVER_STYLE = {
        color: "#2bbf78",
        opacity: 0.9,
        fillColor: "#6fe3ad",
        fillOpacity: 0.4
    };

    var LABEL_COLOR = [11, 93, 51, 255];
    var LABEL_OUTLINE_COLOR = [255, 255, 255, 255];
    var LABEL_OUTLINE_WIDTH = 2;
    var LABEL_FONT_SIZE = 16;

    function ensureHelpers() {
        var http = window.WCHttp;
        if (!http || typeof http.getJson !== "function") {
            throw new Error("OmniContrastOverlays requires WCHttp.getJson.");
        }
        return { http: http };
    }

    function ensureControlBase() {
        if (typeof window.controlBase !== "function") {
            throw new Error("OmniContrastOverlays requires controlBase.");
        }
        return window.controlBase;
    }

    function ensureMap() {
        var map = window.MapController && typeof window.MapController.getInstance === "function"
            ? window.MapController.getInstance()
            : null;
        if (!map) {
            throw new Error("OmniContrastOverlays requires MapController.");
        }
        return map;
    }

    function ensureDeck() {
        var deckApi = window.deck;
        if (!deckApi || typeof deckApi.GeoJsonLayer !== "function" ||
            typeof deckApi.TextLayer !== "function") {
            throw new Error("OmniContrastOverlays requires deck.gl GeoJsonLayer/TextLayer.");
        }
        return deckApi;
    }

    function ensureUrlForRun() {
        if (typeof window.url_for_run !== "function") {
            throw new Error("OmniContrastOverlays requires url_for_run.");
        }
        return window.url_for_run;
    }

    function hexToRgba(hex, alpha) {
        if (!hex) {
            return [0, 0, 0, 0];
        }
        var cleaned = hex.replace("#", "").trim();
        if (cleaned.length === 3) {
            cleaned = cleaned[0] + cleaned[0] + cleaned[1] + cleaned[1] + cleaned[2] + cleaned[2];
        }
        var r = parseInt(cleaned.substring(0, 2), 16);
        var g = parseInt(cleaned.substring(2, 4), 16);
        var b = parseInt(cleaned.substring(4, 6), 16);
        var a = Math.round((alpha === undefined ? 1 : alpha) * 255);
        if (Number.isNaN(r) || Number.isNaN(g) || Number.isNaN(b)) {
            return [0, 0, 0, 0];
        }
        return [r, g, b, a];
    }

    function resolveGeometryRing(geometry) {
        if (!geometry || !geometry.type || !geometry.coordinates) {
            return null;
        }
        if (geometry.type === "Polygon") {
            return geometry.coordinates[0] || null;
        }
        if (geometry.type === "MultiPolygon") {
            return geometry.coordinates[0] && geometry.coordinates[0][0]
                ? geometry.coordinates[0][0]
                : null;
        }
        return null;
    }

    function resolveGeometryCenter(geometry) {
        var ring = resolveGeometryRing(geometry);
        if (!ring || !ring.length) {
            return null;
        }
        var count = ring.length;
        if (count > 1) {
            var last = ring[count - 1];
            var first = ring[0];
            if (last && first && last[0] === first[0] && last[1] === first[1]) {
                count -= 1;
            }
        }
        if (count <= 0) {
            return null;
        }
        var sumX = 0;
        var sumY = 0;
        for (var i = 0; i < count; i += 1) {
            sumX += ring[i][0];
            sumY += ring[i][1];
        }
        return [sumX / count, sumY / count];
    }

    function resolveLabelPosition(feature) {
        if (!feature) {
            return null;
        }
        if (feature.__wcContrastLabelPosition) {
            return feature.__wcContrastLabelPosition;
        }
        var geometry = feature.geometry;
        var position = null;
        if (typeof window.polylabel === "function" &&
            geometry &&
            (geometry.type === "Polygon" || geometry.type === "MultiPolygon")) {
            var coords = geometry.type === "Polygon" ? geometry.coordinates : geometry.coordinates[0];
            if (coords && coords.length) {
                position = window.polylabel(coords, 1.0);
            }
        }
        if (!position) {
            position = resolveGeometryCenter(geometry);
        }
        if (position) {
            feature.__wcContrastLabelPosition = position;
        }
        return position;
    }

    function resolveFeatureLabel(feature) {
        if (!feature || !feature.properties) {
            return null;
        }
        var props = feature.properties;
        if (props.contrast_label !== undefined && props.contrast_label !== null && props.contrast_label !== "") {
            return props.contrast_label;
        }
        if (props.label !== undefined && props.label !== null && props.label !== "") {
            return props.label;
        }
        return null;
    }

    function resolveFeatureKey(feature) {
        return resolveFeatureLabel(feature);
    }

    function buildContrastLayer(deckApi, data, hoverKey, onHover) {
        var lineColor = hexToRgba(DEFAULT_STYLE.color, DEFAULT_STYLE.opacity);
        var fillColor = hexToRgba(DEFAULT_STYLE.fillColor, DEFAULT_STYLE.fillOpacity);
        var hoverLineColor = hexToRgba(HOVER_STYLE.color, HOVER_STYLE.opacity);
        var hoverFillColor = hexToRgba(HOVER_STYLE.fillColor, HOVER_STYLE.fillOpacity);
        return new deckApi.GeoJsonLayer({
            id: CONTRAST_LAYER_ID,
            data: data || { type: "FeatureCollection", features: [] },
            pickable: true,
            stroked: true,
            filled: true,
            lineWidthUnits: "pixels",
            lineWidthMinPixels: 1,
            getLineWidth: function () { return DEFAULT_STYLE.weight; },
            getLineColor: function (feature) {
                return resolveFeatureKey(feature) === hoverKey ? hoverLineColor : lineColor;
            },
            getFillColor: function (feature) {
                return resolveFeatureKey(feature) === hoverKey ? hoverFillColor : fillColor;
            },
            updateTriggers: {
                getLineColor: [DEFAULT_STYLE.color, DEFAULT_STYLE.opacity, HOVER_STYLE.color, HOVER_STYLE.opacity, hoverKey],
                getFillColor: [DEFAULT_STYLE.fillColor, DEFAULT_STYLE.fillOpacity, HOVER_STYLE.fillColor, HOVER_STYLE.fillOpacity, hoverKey]
            },
            onHover: onHover
        });
    }

    function buildLabelLayer(deckApi, labelData) {
        return new deckApi.TextLayer({
            id: CONTRAST_LABEL_LAYER_ID,
            data: labelData || [],
            pickable: false,
            getPosition: function (d) { return d.position; },
            getText: function (d) { return d.text; },
            getSize: function () { return LABEL_FONT_SIZE; },
            sizeUnits: "pixels",
            getColor: function () { return LABEL_COLOR; },
            outlineColor: LABEL_OUTLINE_COLOR,
            outlineWidth: LABEL_OUTLINE_WIDTH,
            fontSettings: { sdf: true }
        });
    }

    function buildHoverLabelLayer(deckApi, labelData) {
        return new deckApi.TextLayer({
            id: CONTRAST_HOVER_LABEL_LAYER_ID,
            data: labelData || [],
            pickable: false,
            getPosition: function (d) { return d.position; },
            getText: function (d) { return d.text; },
            getSize: function () { return LABEL_FONT_SIZE; },
            sizeUnits: "pixels",
            getColor: function () { return LABEL_COLOR; },
            outlineColor: LABEL_OUTLINE_COLOR,
            outlineWidth: LABEL_OUTLINE_WIDTH,
            fontSettings: { sdf: true }
        });
    }

    function buildHoverLabelData(feature) {
        var label = resolveFeatureLabel(feature);
        if (!label) {
            return null;
        }
        var position = resolveLabelPosition(feature);
        if (!position) {
            return null;
        }
        return [{
            text: String(label),
            position: position
        }];
    }

    function buildAllLabelData(data) {
        if (!data || !Array.isArray(data.features)) {
            return [];
        }
        var labels = [];
        data.features.forEach(function (feature) {
            var label = resolveFeatureLabel(feature);
            if (!label) {
                return;
            }
            var position = resolveLabelPosition(feature);
            if (!position) {
                return;
            }
            labels.push({
                text: String(label),
                position: position
            });
        });
        return labels;
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

    function createController() {
        var helpers = ensureHelpers();
        var http = helpers.http;
        var baseFactory = ensureControlBase();
        var overlay = baseFactory();

        var state = {
            data: null,
            layer: null,
            labelLayer: null,
            hoverLabelLayer: null,
            hoverLabelKey: null,
            allLabelData: [],
            hoveredKey: null,
            loading: null,
            mapEventsBound: false,
            omniEventsBound: false
        };

        overlay.state = state;

        function attachContrastRebuild(layer) {
            if (!layer) {
                return;
            }
            layer.__wcRebuild = function () {
                if (!state.data) {
                    return layer;
                }
                var deckApi = ensureDeck();
                var map = ensureMap();
                var onHover = function (info) {
                    updateHoverLabel(info);
                };
                var nextLayer = buildContrastLayer(deckApi, state.data, state.hoveredKey, onHover);
                attachContrastRebuild(nextLayer);
                state.layer = nextLayer;
                return nextLayer;
            };
        }

        function attachLabelRebuild(layer) {
            if (!layer) {
                return;
            }
            layer.__wcRebuild = function () {
                var deckApi = ensureDeck();
                var nextLayer = buildLabelLayer(deckApi, state.allLabelData || []);
                attachLabelRebuild(nextLayer);
                state.labelLayer = nextLayer;
                return nextLayer;
            };
        }

        function applyContrastData(data) {
            var map = ensureMap();
            var deckApi = ensureDeck();
            state.data = data || { type: "FeatureCollection", features: [] };
            state.allLabelData = buildAllLabelData(state.data);
            state.hoveredKey = null;
            clearHoverLabel();

            var onHover = function (info) {
                updateHoverLabel(info);
            };
            var wasVisible = state.layer ? map.hasLayer(state.layer) : false;
            var nextLayer = buildContrastLayer(deckApi, state.data, state.hoveredKey, onHover);
            attachContrastRebuild(nextLayer);
            replaceOverlayLayer(map, CONTRAST_LAYER_NAME, state.layer, nextLayer, wasVisible);
            state.layer = nextLayer;

            var labelVisible = state.labelLayer ? map.hasLayer(state.labelLayer) : false;
            var nextLabelLayer = buildLabelLayer(deckApi, state.allLabelData || []);
            attachLabelRebuild(nextLabelLayer);
            replaceOverlayLayer(map, CONTRAST_LABEL_LAYER_NAME, state.labelLayer, nextLabelLayer, labelVisible);
            state.labelLayer = nextLabelLayer;
        }

        function clearHoverLabel() {
            if (!state.hoverLabelLayer) {
                state.hoverLabelKey = null;
                return;
            }
            var map = ensureMap();
            if (map && typeof map.removeLayer === "function") {
                map.removeLayer(state.hoverLabelLayer, { skipOverlay: true });
            }
            state.hoverLabelLayer = null;
            state.hoverLabelKey = null;
        }

        function updateHoverLabel(info) {
            var feature = info && info.object ? info.object : null;
            updateHoverState(feature);
            if (!feature) {
                clearHoverLabel();
                return;
            }
            var label = resolveFeatureLabel(feature);
            if (!label) {
                clearHoverLabel();
                return;
            }
            var key = String(label);
            if (state.hoverLabelKey === key && state.hoverLabelLayer) {
                return;
            }
            var labelData = buildHoverLabelData(feature);
            if (!labelData) {
                clearHoverLabel();
                return;
            }
            var map = ensureMap();
            var deckApi = ensureDeck();
            var nextLayer = buildHoverLabelLayer(deckApi, labelData);
            if (state.hoverLabelLayer && typeof map.removeLayer === "function") {
                map.removeLayer(state.hoverLabelLayer, { skipOverlay: true });
            }
            state.hoverLabelLayer = nextLayer;
            state.hoverLabelKey = key;
            if (typeof map.addLayer === "function") {
                map.addLayer(nextLayer, { skipRefresh: true });
            }
        }

        function updateHoverState(feature) {
            var nextKey = feature ? resolveFeatureKey(feature) : null;
            if (nextKey === state.hoveredKey) {
                return;
            }
            state.hoveredKey = nextKey;
            refreshContrastLayer();
        }

        function refreshContrastLayer() {
            if (!state.data) {
                return;
            }
            var map = ensureMap();
            var deckApi = ensureDeck();
            var onHover = function (info) {
                updateHoverLabel(info);
            };
            var wasVisible = state.layer ? map.hasLayer(state.layer) : false;
            var nextLayer = buildContrastLayer(deckApi, state.data, state.hoveredKey, onHover);
            attachContrastRebuild(nextLayer);
            replaceOverlayLayer(map, CONTRAST_LAYER_NAME, state.layer, nextLayer, wasVisible);
            state.layer = nextLayer;
        }

        function refreshOverlays() {
            if (state.loading) {
                return state.loading;
            }
            var urlForRun = ensureUrlForRun();
            var endpoint = urlForRun(CONTRAST_ENDPOINT);
            var bust = { _: Date.now() };
            state.loading = http.getJson(endpoint, { params: bust })
                .then(function (result) {
                    var data = result && result.body !== undefined ? result.body : result;
                    if (!data || typeof data !== "object") {
                        throw new Error("Contrast overlay response missing GeoJSON data.");
                    }
                    applyContrastData(data);
                    return data;
                })
                .catch(function (error) {
                    console.warn("[Omni Contrast GL] Failed to load contrast IDs", error);
                    applyContrastData({ type: "FeatureCollection", features: [] });
                })
                .finally(function () {
                    state.loading = null;
                });
            return state.loading;
        }

        function bindMapEvents() {
            if (state.mapEventsBound) {
                return;
            }
            var map = ensureMap();
            if (map && map.events && typeof map.events.on === "function") {
                map.events.on("map:layer:toggled", function (payload) {
                    if (!payload || !payload.name) {
                        return;
                    }
                    if (payload.name === CONTRAST_LAYER_NAME && !payload.visible) {
                        clearHoverLabel();
                        state.hoveredKey = null;
                    }
                });
            }
            state.mapEventsBound = true;
        }

        function bindOmniEvents() {
            if (state.omniEventsBound) {
                return;
            }
            var omni = window.Omni && typeof window.Omni.getInstance === "function"
                ? window.Omni.getInstance()
                : null;
            if (omni && omni.events && typeof omni.events.on === "function") {
                omni.events.on("omni:contrast:run:completed", function () {
                    refreshOverlays();
                });
                omni.events.on("omni:contrast:dry-run:completed", function () {
                    refreshOverlays();
                });
            }
            state.omniEventsBound = true;
        }

        overlay.refresh = refreshOverlays;
        overlay.bootstrap = function (context) {
            bindMapEvents();
            bindOmniEvents();
            var hasContrasts = context && context.data && context.data.omni
                ? context.data.omni.hasRanContrasts
                : null;
            if (hasContrasts || hasContrasts === null) {
                refreshOverlays();
            } else {
                applyContrastData({ type: "FeatureCollection", features: [] });
            }
        };

        return overlay;
    }

    return {
        getInstance: function () {
            if (!instance) {
                instance = createController();
            }
            return instance;
        }
    };
}());

window.OmniContrastOverlays = OmniContrastOverlays;
