/* ----------------------------------------------------------------------------
 * Roads Map Overlay (Deck.gl parity)
 * ----------------------------------------------------------------------------
 */
var RoadsMapOverlay = (function () {
    "use strict";

    var instance;

    var EVENT_NAMES = [
        "roads:map:loaded",
        "roads:map:error",
        "roads:map:hover",
        "roads:map:selected"
    ];

    var ROADS_LAYER_NAME = "Roads";
    var ROADS_LAYER_ID = "wc-roads";
    var ROADS_HOVER_LAYER_ID = "wc-roads-hover";
    var ROADS_LABEL_LAYER_NAME = "Road Labels";
    var ROADS_LABEL_LAYER_ID = "wc-road-labels";
    var ROADS_HOVER_LABEL_LAYER_ID = "wc-road-hover-label";
    var ROADS_ENDPOINT = "resources/roads.json";
    var ROADS_PREPARE_COMPLETION_EVENT = "ROADS_PREPARE_TASK_COMPLETED";
    var ROADS_RUN_COMPLETION_EVENT = "ROADS_RUN_TASK_COMPLETED";
    var ROAD_BASE_WIDTH_PX = 3;
    var ROAD_HOVER_WIDTH_PX = 6;
    var ROAD_LABEL_FONT_SIZE = 14;
    var ROAD_HOVER_OFFSET_PX = [18, -18];
    var ROAD_COLOR_VAR = "--wc-map-roads-color";
    var ROAD_HOVER_COLOR_VAR = "--wc-map-roads-hover-color";
    var ROAD_LABEL_COLOR_VAR = "--wc-map-road-label-color";
    var ROAD_DEFAULT_COLOR = "#ff00c8";
    var ROAD_DEFAULT_HOVER_COLOR = "#ff7be5";
    var ROAD_DEFAULT_LABEL_COLOR = "#b1008d";
    var LABEL_OUTLINE_COLOR = [255, 255, 255, 255];
    var LABEL_OUTLINE_WIDTH = 3;
    var EMPTY_GEOJSON = { type: "FeatureCollection", features: [] };

    function ensureHelpers() {
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!http || typeof http.getJson !== "function" || typeof http.request !== "function") {
            throw new Error("Roads map overlay requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Roads map overlay requires WCEvents helpers.");
        }

        return { http: http, events: events };
    }

    function ensureMap() {
        var map = window.MapController && typeof window.MapController.getInstance === "function"
            ? window.MapController.getInstance()
            : null;
        if (!map) {
            throw new Error("Roads map overlay requires MapController.");
        }
        return map;
    }

    function ensureDeck() {
        var deckApi = window.deck;
        if (!deckApi || typeof deckApi.GeoJsonLayer !== "function" || typeof deckApi.TextLayer !== "function") {
            throw new Error("Roads map overlay requires deck.gl GeoJsonLayer/TextLayer.");
        }
        return deckApi;
    }

    function ensureMapShared() {
        if (!window.WCMapGlShared || typeof window.WCMapGlShared.hexToRgba !== "function") {
            throw new Error("Roads map overlay requires WCMapGlShared helpers.");
        }
        return window.WCMapGlShared;
    }

    function resolveRunScopedUrl(path) {
        if (typeof window.url_for_run !== "function") {
            throw new Error("Roads map overlay requires url_for_run.");
        }
        return window.url_for_run(path);
    }

    function asString(value) {
        if (value === null || value === undefined) {
            return "";
        }
        return String(value).trim();
    }

    function normalizeGeoJson(payload) {
        if (!payload || typeof payload !== "object") {
            return EMPTY_GEOJSON;
        }
        if (payload.type !== "FeatureCollection" || !Array.isArray(payload.features)) {
            return EMPTY_GEOJSON;
        }
        return payload;
    }

    function resolveSegmentId(feature) {
        if (!feature || !feature.properties) {
            return "";
        }
        var properties = feature.properties;
        var value = properties.segment_id;
        if (value === undefined || value === null || value === "") {
            value = properties.segmentId;
        }
        return asString(value);
    }

    function resolveRoadLabelPosition(feature) {
        var geometry = feature && feature.geometry ? feature.geometry : null;
        if (!geometry) {
            return null;
        }
        if (geometry.type === "LineString" && Array.isArray(geometry.coordinates) && geometry.coordinates.length > 0) {
            var mid = Math.floor(geometry.coordinates.length / 2);
            var coords = geometry.coordinates[mid] || geometry.coordinates[0];
            if (Array.isArray(coords) && coords.length >= 2) {
                return [coords[0], coords[1]];
            }
        }
        if (geometry.type === "MultiLineString" && Array.isArray(geometry.coordinates) && geometry.coordinates.length > 0) {
            var firstLine = geometry.coordinates[0];
            if (Array.isArray(firstLine) && firstLine.length > 0) {
                var midIdx = Math.floor(firstLine.length / 2);
                var midCoords = firstLine[midIdx] || firstLine[0];
                if (Array.isArray(midCoords) && midCoords.length >= 2) {
                    return [midCoords[0], midCoords[1]];
                }
            }
        }
        if (geometry.type === "Point" && Array.isArray(geometry.coordinates) && geometry.coordinates.length >= 2) {
            return [geometry.coordinates[0], geometry.coordinates[1]];
        }
        return null;
    }

    function buildLabelData(features) {
        var labels = [];
        var seen = typeof Set === "function" ? new Set() : null;
        (features || []).forEach(function (feature) {
            var segmentId = resolveSegmentId(feature);
            if (!segmentId) {
                return;
            }
            if (seen) {
                if (seen.has(segmentId)) {
                    return;
                }
                seen.add(segmentId);
            }
            var position = resolveRoadLabelPosition(feature);
            if (!position) {
                return;
            }
            labels.push({
                text: segmentId,
                position: position
            });
        });
        return labels;
    }

    function resolveHoverLabelPosition(info, map) {
        if (!info || !map || !map._deck) {
            return null;
        }
        var x = Number(info.x);
        var y = Number(info.y);
        if (!Number.isFinite(x) || !Number.isFinite(y)) {
            return null;
        }
        var offsetX = x + ROAD_HOVER_OFFSET_PX[0];
        var offsetY = y + ROAD_HOVER_OFFSET_PX[1];
        var deckInstance = map._deck;
        if (typeof deckInstance.getViewports !== "function") {
            return null;
        }
        var viewports = deckInstance.getViewports();
        var viewport = viewports && viewports.length ? viewports[0] : null;
        if (!viewport || typeof viewport.unproject !== "function") {
            return null;
        }
        var coords = viewport.unproject([offsetX, offsetY]);
        if (!coords || coords.length < 2) {
            return null;
        }
        return [coords[0], coords[1]];
    }

    function compactHoverText(feature) {
        var segmentId = resolveSegmentId(feature);
        return segmentId || "road-segment";
    }

    function buildRoadLayer(deckApi, data, options) {
        var opts = options || {};
        var lineColor = opts.lineColor || [255, 0, 200, 255];
        return new deckApi.GeoJsonLayer({
            id: ROADS_LAYER_ID,
            data: data || EMPTY_GEOJSON,
            pickable: true,
            stroked: true,
            filled: false,
            lineWidthUnits: "pixels",
            lineWidthMinPixels: 1,
            getLineWidth: function () { return ROAD_BASE_WIDTH_PX; },
            getLineColor: function () { return lineColor; },
            onHover: typeof opts.onHover === "function" ? opts.onHover : null,
            onClick: typeof opts.onClick === "function" ? opts.onClick : null
        });
    }

    function buildHoverLayer(deckApi, feature, options) {
        if (!feature) {
            return null;
        }
        var opts = options || {};
        var lineColor = opts.lineColor || [255, 123, 229, 255];
        return new deckApi.GeoJsonLayer({
            id: ROADS_HOVER_LAYER_ID,
            data: {
                type: "FeatureCollection",
                features: [feature]
            },
            pickable: false,
            stroked: true,
            filled: false,
            lineWidthUnits: "pixels",
            lineWidthMinPixels: 1,
            getLineWidth: function () { return ROAD_HOVER_WIDTH_PX; },
            getLineColor: function () { return lineColor; }
        });
    }

    function buildLabelLayer(deckApi, id, labelData, color) {
        return new deckApi.TextLayer({
            id: id,
            data: labelData || [],
            pickable: false,
            getPosition: function (d) { return d.position; },
            getText: function (d) { return d.text; },
            getSize: function () { return ROAD_LABEL_FONT_SIZE; },
            sizeUnits: "pixels",
            getColor: function () { return color; },
            outlineColor: LABEL_OUTLINE_COLOR,
            outlineWidth: LABEL_OUTLINE_WIDTH,
            fontSettings: { sdf: true }
        });
    }

    function resolveThemeColors(shared) {
        function cssColor(varName, fallback) {
            if (typeof window.getComputedStyle !== "function" || !document || !document.documentElement) {
                return fallback;
            }
            var value = window.getComputedStyle(document.documentElement).getPropertyValue(varName);
            var normalized = asString(value);
            return normalized || fallback;
        }

        return {
            road: shared.hexToRgba(cssColor(ROAD_COLOR_VAR, ROAD_DEFAULT_COLOR), 0.95),
            roadHover: shared.hexToRgba(cssColor(ROAD_HOVER_COLOR_VAR, ROAD_DEFAULT_HOVER_COLOR), 1.0),
            label: shared.hexToRgba(cssColor(ROAD_LABEL_COLOR_VAR, ROAD_DEFAULT_LABEL_COLOR), 1.0)
        };
    }

    function isRoadsUnavailableError(http, error) {
        if (error && error.roadsUnavailable) {
            return true;
        }
        if (http && typeof http.isHttpError === "function" && http.isHttpError(error)) {
            if (error.status === 404) {
                return true;
            }
            var detail = error.detail || error.body || {};
            var message = asString((detail.error && detail.error.message) || detail.message || error.message).toLowerCase();
            if (message.indexOf("prepare_segments") !== -1 || message.indexOf("not enabled") !== -1) {
                return true;
            }
        }
        return false;
    }

    function replaceOverlayLayer(map, name, currentLayer, nextLayer, wasVisible) {
        if (!map || !nextLayer) {
            return;
        }
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

    function clearHoverArtifacts(state, map) {
        if (!state || !map) {
            return;
        }
        if (state.hoverLayer && typeof map.removeLayer === "function") {
            map.removeLayer(state.hoverLayer, { skipOverlay: true });
        }
        if (state.hoverLabelLayer && typeof map.removeLayer === "function") {
            map.removeLayer(state.hoverLabelLayer, { skipOverlay: true });
        }
        state.hoverLayer = null;
        state.hoverLabelLayer = null;
        state.hoverSegmentId = null;
    }

    function clearHoverLabel(state, map) {
        if (!state || !map) {
            return;
        }
        if (state.hoverLabelLayer && typeof map.removeLayer === "function") {
            map.removeLayer(state.hoverLabelLayer, { skipOverlay: true });
        }
        state.hoverLabelLayer = null;
    }

    function unregisterOverlay(map, layer) {
        if (!map || !layer) {
            return;
        }
        if (typeof map.unregisterOverlay === "function") {
            map.unregisterOverlay(layer);
        } else if (map.ctrls && typeof map.ctrls.removeLayer === "function") {
            map.ctrls.removeLayer(layer);
        }
        if (typeof map.removeLayer === "function") {
            map.removeLayer(layer, { skipOverlay: true });
        }
    }

    function attachLayerRebuild(state, layerFactory) {
        if (!state || !state.glLayer || typeof layerFactory !== "function") {
            return;
        }
        state.glLayer.__wcRebuild = function () {
            var rebuilt = layerFactory();
            if (rebuilt) {
                state.glLayer = rebuilt;
            }
            return rebuilt || state.glLayer;
        };
    }

    function attachLabelLayerRebuild(state, layerFactory) {
        if (!state || !state.labelLayer || typeof layerFactory !== "function") {
            return;
        }
        state.labelLayer.__wcRebuild = function () {
            var rebuilt = layerFactory();
            if (rebuilt) {
                state.labelLayer = rebuilt;
            }
            return rebuilt || state.labelLayer;
        };
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var http = helpers.http;
        var events = helpers.events;
        var map = ensureMap();
        var deckApi = ensureDeck();
        var shared = ensureMapShared();

        var emitterBase = events.createEmitter();
        var roadsEvents = typeof events.useEventMap === "function"
            ? events.useEventMap(EVENT_NAMES, emitterBase)
            : emitterBase;

        var state = {
            glData: EMPTY_GEOJSON,
            glLayer: null,
            labelLayer: null,
            hoverLayer: null,
            hoverLabelLayer: null,
            labelData: [],
            hoverSegmentId: null,
            mapEventsBound: false,
            completionEventsBound: false
        };

        function emit(eventName, payload) {
            if (roadsEvents && typeof roadsEvents.emit === "function") {
                roadsEvents.emit(eventName, payload || {});
            }
        }

        function removeAllLayers() {
            clearHoverArtifacts(state, map);
            if (state.glLayer) {
                unregisterOverlay(map, state.glLayer);
                state.glLayer = null;
            }
            if (state.labelLayer) {
                unregisterOverlay(map, state.labelLayer);
                state.labelLayer = null;
            }
        }

        function onHover(info) {
            var feature = info && info.object ? info.object : null;
            if (!feature) {
                clearHoverArtifacts(state, map);
                emit("roads:map:hover", { segment_id: null });
                return;
            }
            var segmentId = resolveSegmentId(feature);
            if (!segmentId) {
                clearHoverArtifacts(state, map);
                emit("roads:map:hover", { segment_id: null });
                return;
            }

            var roadLabelsVisible = Boolean(
                state.labelLayer && typeof map.hasLayer === "function" && map.hasLayer(state.labelLayer)
            );
            var hasActiveHoverVisuals = Boolean(state.hoverLayer) && (roadLabelsVisible || Boolean(state.hoverLabelLayer));
            if (segmentId === state.hoverSegmentId && hasActiveHoverVisuals) {
                return;
            }

            clearHoverArtifacts(state, map);
            state.hoverSegmentId = segmentId;

            var colors = resolveThemeColors(shared);
            state.hoverLayer = buildHoverLayer(deckApi, feature, { lineColor: colors.roadHover });
            if (state.hoverLayer && state.glLayer && typeof map.hasLayer === "function" && map.hasLayer(state.glLayer)) {
                map.addLayer(state.hoverLayer, { skipRefresh: true });
            }

            if (!roadLabelsVisible) {
                var position = resolveHoverLabelPosition(info, map) || resolveRoadLabelPosition(feature);
                if (position) {
                    state.hoverLabelLayer = buildLabelLayer(
                        deckApi,
                        ROADS_HOVER_LABEL_LAYER_ID,
                        [{ text: compactHoverText(feature), position: position }],
                        colors.label
                    );
                    if (state.hoverLabelLayer) {
                        map.addLayer(state.hoverLabelLayer, { skipRefresh: true });
                    }
                }
            }

            emit("roads:map:hover", { segment_id: segmentId });
        }

        function onClick(info) {
            var feature = info && info.object ? info.object : null;
            var segmentId = resolveSegmentId(feature);
            if (!segmentId) {
                return;
            }
            if (map && typeof map.roadQuery === "function") {
                map.roadQuery(segmentId);
            }
            emit("roads:map:selected", { segment_id: segmentId });
        }

        function rebuildLayers(data) {
            clearHoverArtifacts(state, map);

            var colors = resolveThemeColors(shared);
            var nextData = normalizeGeoJson(data);
            var nextFeatures = Array.isArray(nextData.features) ? nextData.features : [];
            var nextLabelData = buildLabelData(nextFeatures);

            var wasRoadVisible = state.glLayer ? map.hasLayer(state.glLayer) : true;
            var wasLabelVisible = state.labelLayer ? map.hasLayer(state.labelLayer) : false;

            var nextRoadLayer = buildRoadLayer(deckApi, nextData, {
                lineColor: colors.road,
                onHover: onHover,
                onClick: onClick
            });
            var nextLabelLayer = buildLabelLayer(deckApi, ROADS_LABEL_LAYER_ID, nextLabelData, colors.label);

            replaceOverlayLayer(map, ROADS_LAYER_NAME, state.glLayer, nextRoadLayer, wasRoadVisible);
            replaceOverlayLayer(map, ROADS_LABEL_LAYER_NAME, state.labelLayer, nextLabelLayer, wasLabelVisible);

            state.glData = nextData;
            state.glLayer = nextRoadLayer;
            state.labelLayer = nextLabelLayer;
            state.labelData = nextLabelData;

            attachLayerRebuild(state, function () {
                return buildRoadLayer(deckApi, state.glData, {
                    lineColor: resolveThemeColors(shared).road,
                    onHover: onHover,
                    onClick: onClick
                });
            });
            attachLabelLayerRebuild(state, function () {
                return buildLabelLayer(
                    deckApi,
                    ROADS_LABEL_LAYER_ID,
                    state.labelData,
                    resolveThemeColors(shared).label
                );
            });
        }

        function fetchRoads() {
            var url = resolveRunScopedUrl(ROADS_ENDPOINT);
            return http.getJson(url, { params: { _: Date.now() } }).then(function (payload) {
                if (payload && (payload.error || payload.errors)) {
                    var message = asString(
                        (payload.error && payload.error.message)
                        || payload.message
                        || payload.detail
                        || "Roads data unavailable"
                    );
                    var error = new Error(message);
                    var lowered = message.toLowerCase();
                    if (lowered.indexOf("prepare_segments") !== -1 || lowered.indexOf("not enabled") !== -1) {
                        error.roadsUnavailable = true;
                    }
                    throw error;
                }
                return normalizeGeoJson(payload);
            });
        }

        function bindMapEvents() {
            if (state.mapEventsBound) {
                return;
            }
            if (map && map.events && typeof map.events.on === "function") {
                map.events.on("map:layer:toggled", function (payload) {
                    if (!payload || !payload.name) {
                        return;
                    }
                    if (payload.name === ROADS_LABEL_LAYER_NAME && payload.visible) {
                        clearHoverLabel(state, map);
                    }
                    if (payload.name === ROADS_LAYER_NAME && !payload.visible) {
                        clearHoverArtifacts(state, map);
                    }
                });
            }
            state.mapEventsBound = true;
        }

        function bindCompletionEvents(controller) {
            if (state.completionEventsBound || typeof document === "undefined") {
                return;
            }
            document.addEventListener(ROADS_PREPARE_COMPLETION_EVENT, function () {
                controller.show();
            });
            document.addEventListener(ROADS_RUN_COMPLETION_EVENT, function () {
                controller.show();
            });
            state.completionEventsBound = true;
        }

        var controller = {
            events: roadsEvents,
            state: state,
            show: function () {
                bindMapEvents();
                return fetchRoads().then(function (payload) {
                    rebuildLayers(payload);
                    emit("roads:map:loaded", {
                        feature_count: Array.isArray(payload.features) ? payload.features.length : 0
                    });
                    return state.glLayer;
                }).catch(function (error) {
                    if (isRoadsUnavailableError(http, error)) {
                        removeAllLayers();
                        return null;
                    }
                    emit("roads:map:error", { error: error });
                    return null;
                });
            },
            refreshLayers: function () {
                return this.show();
            },
            bootstrap: function (context) {
                var ctx = context || {};
                var modFlags = ctx && ctx.mods && ctx.mods.flags ? ctx.mods.flags : {};
                bindMapEvents();
                bindCompletionEvents(this);
                if (!modFlags.roads) {
                    removeAllLayers();
                    return this;
                }
                this.show();
                return this;
            }
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

window.RoadsMapOverlay = RoadsMapOverlay;
