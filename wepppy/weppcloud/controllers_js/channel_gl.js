/* ----------------------------------------------------------------------------
 * ChannelDelineation (Deck.gl pass 1)
 * ----------------------------------------------------------------------------
 */
var ChannelDelineation = (function () {
    "use strict";

    var instance;

    var EVENT_NAMES = [
        "channel:build:started",
        "channel:build:completed",
        "channel:build:error",
        "channel:map:updated",
        "channel:extent:mode",
        "channel:report:loaded",
        "channel:layers:loaded"
    ];

    var CHANNEL_LAYER_NAME = "Channels";
    var CHANNEL_LAYER_ID = "wc-channels-netful";
    var NETFUL_ENDPOINT = "resources/netful.json";
    var CHANNEL_OPACITY = 0.9;
    var DEFAULT_ORDER = 4;
    var MAX_ORDER = 7;
    var EMPTY_GEOJSON = { type: "FeatureCollection", features: [] };
    var CHANNEL_PALETTE = [
        "#8AE5FE", "#65C8FE", "#479EFF", "#306EFE",
        "#2500F4", "#6600cc", "#50006b", "#6b006b"
    ].map(function (color) {
        return hexToRgba(color, CHANNEL_OPACITY);
    });

    function ensureEvents() {
        var events = window.WCEvents;
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("ChannelDelineation GL requires WCEvents helpers.");
        }
        return events;
    }

    function ensureHttp() {
        var http = window.WCHttp;
        if (!http || typeof http.getJson !== "function") {
            throw new Error("ChannelDelineation GL requires WCHttp.getJson.");
        }
        return http;
    }

    function ensureMap() {
        var map = window.MapController && typeof window.MapController.getInstance === "function"
            ? window.MapController.getInstance()
            : null;
        if (!map) {
            throw new Error("ChannelDelineation GL requires MapController.");
        }
        return map;
    }

    function ensureDeck() {
        var deckApi = window.deck;
        if (!deckApi || typeof deckApi.GeoJsonLayer !== "function") {
            throw new Error("ChannelDelineation GL requires deck.gl GeoJsonLayer.");
        }
        return deckApi;
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

    function resolveOrder(feature) {
        if (!feature || !feature.properties) {
            return DEFAULT_ORDER;
        }
        var value = parseInt(feature.properties.Order, 10);
        if (!Number.isFinite(value)) {
            return DEFAULT_ORDER;
        }
        return Math.max(0, Math.min(MAX_ORDER, value));
    }

    function getLineColor(feature) {
        var order = resolveOrder(feature);
        return CHANNEL_PALETTE[order] || CHANNEL_PALETTE[DEFAULT_ORDER];
    }

    function attachRebuild(layer, channel) {
        if (!layer) {
            return;
        }
        layer.__wcRebuild = function () {
            if (!channel || !channel.glData) {
                return layer;
            }
            var deckApi = ensureDeck();
            var nextLayer = buildLayer(deckApi, channel.glData);
            attachRebuild(nextLayer, channel);
            channel.glLayer = nextLayer;
            return nextLayer;
        };
    }

    function buildLayer(deckApi, data) {
        var layer = new deckApi.GeoJsonLayer({
            id: CHANNEL_LAYER_ID,
            data: data || EMPTY_GEOJSON,
            pickable: false,
            stroked: true,
            filled: false,
            lineWidthUnits: "pixels",
            lineWidthMinPixels: 1,
            getLineWidth: function () { return 1.5; },
            getLineColor: getLineColor
        });
        return layer;
    }

    function removeLayer(channel, map) {
        if (!channel.glLayer) {
            return;
        }
        if (typeof map.unregisterOverlay === "function") {
            map.unregisterOverlay(channel.glLayer);
        } else if (map.ctrls && typeof map.ctrls.removeLayer === "function") {
            map.ctrls.removeLayer(channel.glLayer);
        }
        if (typeof map.removeLayer === "function") {
            map.removeLayer(channel.glLayer);
        }
        channel.glLayer = null;
    }

    function buildNetfulUrl() {
        if (typeof window.url_for_run !== "function") {
            throw new Error("ChannelDelineation GL requires url_for_run.");
        }
        return window.url_for_run(NETFUL_ENDPOINT);
    }

    function createInstance() {
        var events = ensureEvents();
        var emitterBase = events.createEmitter();
        var emitter = typeof events.useEventMap === "function"
            ? events.useEventMap(EVENT_NAMES, emitterBase)
            : emitterBase;
        var bootstrapState = {
            shown: false
        };

        var channel = {
            events: emitter,
            glLayer: null,
            glData: null,
            bootstrap: function bootstrap(context) {
                var ctx = context || {};
                var helper = window.WCControllerBootstrap || null;
                var controllerContext = helper && typeof helper.getControllerContext === "function"
                    ? helper.getControllerContext(ctx, "channel")
                    : {};
                var watershed = (ctx.data && ctx.data.watershed) || {};
                var hasChannels = Boolean(watershed.hasChannels);

                if (controllerContext.zoomMin !== undefined && controllerContext.zoomMin !== null) {
                    channel.zoom_min = controllerContext.zoomMin;
                }
                if (typeof channel.onMapChange === "function") {
                    channel.onMapChange();
                }
                if (hasChannels && !bootstrapState.shown) {
                    bootstrapState.shown = true;
                    return channel.show();
                }

                return null;
            },
            onMapChange: function () {
                return null;
            },
            show: function () {
                var http = ensureHttp();
                var map = ensureMap();
                var deckApi = ensureDeck();
                var url = buildNetfulUrl();

                removeLayer(channel, map);

                return http.getJson(url, { params: { _: Date.now() } })
                    .then(function (data) {
                        channel.glData = data || EMPTY_GEOJSON;
                        channel.glLayer = buildLayer(deckApi, channel.glData);
                        attachRebuild(channel.glLayer, channel);
                        if (typeof map.registerOverlay === "function") {
                            map.registerOverlay(channel.glLayer, CHANNEL_LAYER_NAME);
                        } else if (map.ctrls && typeof map.ctrls.addOverlay === "function") {
                            map.ctrls.addOverlay(channel.glLayer, CHANNEL_LAYER_NAME);
                        }
                        if (typeof map.addLayer === "function") {
                            map.addLayer(channel.glLayer);
                        }
                        if (channel.events && typeof channel.events.emit === "function") {
                            channel.events.emit("channel:layers:loaded", { mode: 1, layer: channel.glLayer });
                        }
                        return channel.glLayer;
                    })
                    .catch(function (error) {
                        if (channel.events && typeof channel.events.emit === "function") {
                            channel.events.emit("channel:build:error", { mode: 1, error: error });
                        }
                        throw error;
                    });
            },
            refreshLayers: function () {
                return channel.show();
            }
        };

        return channel;
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

window.ChannelDelineation = ChannelDelineation;
