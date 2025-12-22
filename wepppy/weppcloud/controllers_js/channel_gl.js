/* ----------------------------------------------------------------------------
 * ChannelDelineation (Deck.gl parity + pass 1/2)
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
    var CHANNEL_PASS2_LAYER_ID = "wc-channels-subwta";
    var CHANNEL_LABEL_LAYER_NAME = "Channel Labels";
    var CHANNEL_LABEL_LAYER_ID = "wc-channel-labels";
    var CHANNEL_HOVER_LABEL_LAYER_ID = "wc-channel-hover-label";
    var NETFUL_ENDPOINT = "resources/netful.json";
    var CHANNELS_ENDPOINT = "resources/channels.json";
    var CHANNEL_OPACITY = 0.9;
    var CHANNEL_PASS1_FILL_OPACITY = 0.9;
    var CHANNEL_PASS2_OPACITY = 0.6;
    var CHANNEL_PASS2_FILL_OPACITY = 0.9;
    var CHANNEL_LABEL_COLOR = [26, 115, 232, 255];
    var CHANNEL_LABEL_OUTLINE_COLOR = [255, 255, 255, 255];
    var CHANNEL_LABEL_OUTLINE_WIDTH = 3;
    var CHANNEL_LABEL_FONT_SIZE = 14;
    var CHANNEL_HOVER_OFFSET_PX = [14, -18];
    var DEFAULT_ORDER = 4;
    var MAX_ORDER = 7;
    var EMPTY_GEOJSON = { type: "FeatureCollection", features: [] };
    var CHANNEL_PALETTE = [
        "#8AE5FE", "#65C8FE", "#479EFF", "#306EFE",
        "#2500F4", "#6600cc", "#50006b", "#6b006b"
    ].map(function (color) {
        return hexToRgba(color, CHANNEL_OPACITY);
    });
    var CHANNEL_PASS1_FILL_PALETTE = [
        "#8AE5FE", "#65C8FE", "#479EFF", "#306EFE",
        "#2500F4", "#6600cc", "#50006b", "#6b006b"
    ].map(function (color) {
        return hexToRgba(color, CHANNEL_PASS1_FILL_OPACITY);
    });
    var CHANNEL_PASS2_PALETTE = [
        "#8AE5FE", "#65C8FE", "#479EFF", "#306EFE",
        "#2500F4", "#6600cc", "#50006b", "#6b006b"
    ].map(function (color) {
        return hexToRgba(color, CHANNEL_PASS2_OPACITY);
    });
    var CHANNEL_PASS2_FILL_PALETTE = [
        "#8AE5FE", "#65C8FE", "#479EFF", "#306EFE",
        "#2500F4", "#6600cc", "#50006b", "#6b006b"
    ].map(function (color) {
        return hexToRgba(color, CHANNEL_PASS2_FILL_OPACITY);
    });

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function" || typeof dom.qs !== "function" ||
            typeof dom.qsa !== "function" || typeof dom.delegate !== "function" ||
            typeof dom.show !== "function" || typeof dom.hide !== "function") {
            throw new Error("ChannelDelineation GL requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("ChannelDelineation GL requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function" || typeof http.getJson !== "function") {
            throw new Error("ChannelDelineation GL requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("ChannelDelineation GL requires WCEvents helpers.");
        }

        return { dom: dom, forms: forms, http: http, events: events };
    }

    function ensureControlBase() {
        if (typeof window.controlBase !== "function") {
            throw new Error("ChannelDelineation GL requires controlBase.");
        }
        return window.controlBase;
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

    function toFloat(value) {
        if (value === null || value === undefined || value === "") {
            return null;
        }
        if (Array.isArray(value)) {
            return toFloat(value[0]);
        }
        var parsed = Number(value);
        if (!Number.isFinite(parsed)) {
            return null;
        }
        return parsed;
    }

    function toInteger(value) {
        var parsed = toFloat(value);
        if (parsed === null) {
            return null;
        }
        return Math.trunc(parsed);
    }

    function coalesceNumeric(raw, keys) {
        if (!raw) {
            return null;
        }
        for (var i = 0; i < keys.length; i += 1) {
            var key = keys[i];
            if (!Object.prototype.hasOwnProperty.call(raw, key)) {
                continue;
            }
            var value = toFloat(raw[key]);
            if (value !== null) {
                return value;
            }
        }
        return null;
    }

    function parseNumericList(value, expectedLength) {
        if (value === null || value === undefined) {
            return null;
        }
        var parts = [];
        if (Array.isArray(value)) {
            parts = value;
        } else if (typeof value === "string") {
            parts = value.split(",").map(function (part) {
                return part.trim();
            });
        } else {
            parts = [value];
        }
        var numbers = parts
            .map(function (part) {
                return toFloat(part);
            })
            .filter(function (part) {
                return part !== null && !Number.isNaN(part);
            });
        if (expectedLength && numbers.length !== expectedLength) {
            return null;
        }
        return numbers.length ? numbers : null;
    }

    function unwrapPyTuple(value) {
        if (value && typeof value === "object" && !Array.isArray(value) && Object.prototype.hasOwnProperty.call(value, "py/tuple")) {
            return value["py/tuple"];
        }
        return value;
    }

    function normalizeUtmTuple(value) {
        var tuple = unwrapPyTuple(value);
        if (tuple === null || tuple === undefined || tuple === "") {
            return null;
        }
        if (!Array.isArray(tuple) || tuple.length !== 4) {
            throw new Error("UTM tuple must include 4 values (ul_x, ul_y, zone, letter).");
        }
        var zoneLetter = String(tuple[3]).trim();
        var east = toFloat(tuple[0]);
        var north = toFloat(tuple[1]);
        var zone = toInteger(tuple[2]);
        if (east === null || north === null || zone === null || !zoneLetter) {
            throw new Error("UTM tuple is missing required values.");
        }
        return [east, north, zone, zoneLetter];
    }

    function normalizeMapObject(rawValue) {
        if (rawValue === null || rawValue === undefined || rawValue === "") {
            throw new Error("Map object JSON is required when using Set Map Object.");
        }

        var parsed = rawValue;
        if (typeof rawValue === "string") {
            try {
                parsed = JSON.parse(rawValue);
            } catch (err) {
                throw new Error("Map object must be valid JSON.");
            }
        }

        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
            throw new Error("Map object must be a JSON object.");
        }

        var extent = parseNumericList(unwrapPyTuple(parsed.extent), 4);
        var center = parseNumericList(unwrapPyTuple(parsed.center), 2);
        var zoom = toInteger(parsed.zoom);
        var cellsize = toFloat(parsed.cellsize);

        if (!extent || extent.length !== 4) {
            throw new Error("Map object must include an extent array with four numeric values.");
        }
        if (!center || center.length !== 2) {
            throw new Error("Map object must include a center array with two numeric values.");
        }
        if (zoom === null) {
            throw new Error("Map object must include a numeric zoom.");
        }
        if (cellsize !== null && cellsize <= 0) {
            throw new Error("Map object cellsize must be positive when provided.");
        }

        var mapPayload = {
            "py/object": parsed["py/object"] || "wepppy.nodb.ron.Map",
            extent: extent,
            center: center,
            zoom: zoom
        };
        if (cellsize !== null) {
            mapPayload.cellsize = cellsize;
        }

        var utm = normalizeUtmTuple(parsed.utm);
        if (utm) {
            mapPayload.utm = utm;
        }

        var ulx = toFloat(parsed._ul_x);
        var uly = toFloat(parsed._ul_y);
        var lrx = toFloat(parsed._lr_x);
        var lry = toFloat(parsed._lr_y);
        var numCols = toInteger(parsed._num_cols);
        var numRows = toInteger(parsed._num_rows);

        if (ulx !== null) { mapPayload._ul_x = ulx; }
        if (uly !== null) { mapPayload._ul_y = uly; }
        if (lrx !== null) { mapPayload._lr_x = lrx; }
        if (lry !== null) { mapPayload._lr_y = lry; }
        if (numCols !== null) { mapPayload._num_cols = numCols; }
        if (numRows !== null) { mapPayload._num_rows = numRows; }

        return {
            payload: mapPayload,
            extent: extent,
            center: center,
            zoom: zoom
        };
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

    function getLineColorPass1(feature) {
        var order = resolveOrder(feature);
        return CHANNEL_PALETTE[order] || CHANNEL_PALETTE[DEFAULT_ORDER];
    }

    function getLineColorPass2(feature) {
        var order = resolveOrder(feature);
        return CHANNEL_PASS2_PALETTE[order] || CHANNEL_PASS2_PALETTE[DEFAULT_ORDER];
    }

    function getFillColorPass1(feature) {
        var order = resolveOrder(feature);
        return CHANNEL_PASS1_FILL_PALETTE[order] || CHANNEL_PASS1_FILL_PALETTE[DEFAULT_ORDER];
    }

    function getFillColorPass2(feature) {
        var order = resolveOrder(feature);
        return CHANNEL_PASS2_FILL_PALETTE[order] || CHANNEL_PASS2_FILL_PALETTE[DEFAULT_ORDER];
    }

    function attachChannelRebuild(layer, channel, options) {
        if (!layer) {
            return;
        }
        layer.__wcRebuild = function () {
            if (!channel || !channel.glData) {
                return layer;
            }
            var deckApi = ensureDeck();
            var nextLayer = buildChannelLayer(deckApi, channel.glData, options || {});
            attachChannelRebuild(nextLayer, channel, options || {});
            channel.glLayer = nextLayer;
            return nextLayer;
        };
    }

    function attachLabelRebuild(layer, channel) {
        if (!layer) {
            return;
        }
        layer.__wcRebuild = function () {
            if (!channel || !channel.labelData) {
                return layer;
            }
            var deckApi = ensureDeck();
            var nextLayer = buildLabelLayer(deckApi, channel.labelData);
            if (!nextLayer) {
                return layer;
            }
            attachLabelRebuild(nextLayer, channel);
            channel.labelLayer = nextLayer;
            return nextLayer;
        };
    }

    function buildChannelLayer(deckApi, data, options) {
        var opts = options || {};
        return new deckApi.GeoJsonLayer({
            id: opts.layerId || CHANNEL_LAYER_ID,
            data: data || EMPTY_GEOJSON,
            pickable: Boolean(opts.pickable),
            stroked: true,
            filled: Boolean(opts.filled),
            lineWidthUnits: "pixels",
            lineWidthMinPixels: 1,
            getLineWidth: function () { return 1.5; },
            getLineColor: opts.getLineColor || getLineColorPass1,
            getFillColor: opts.getFillColor || null,
            onHover: typeof opts.onHover === "function" ? opts.onHover : null,
            onClick: typeof opts.onClick === "function" ? opts.onClick : null
        });
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

    function resolveHoverLabelPosition(info, map) {
        if (!info || !map || !map._deck) {
            return null;
        }
        var x = Number(info.x);
        var y = Number(info.y);
        if (!Number.isFinite(x) || !Number.isFinite(y)) {
            return null;
        }
        var offsetX = x + CHANNEL_HOVER_OFFSET_PX[0];
        var offsetY = y + CHANNEL_HOVER_OFFSET_PX[1];
        var deckInstance = map._deck;
        if (typeof deckInstance.getViewports === "function") {
            var viewports = deckInstance.getViewports();
            var viewport = viewports && viewports.length ? viewports[0] : null;
            if (viewport && typeof viewport.unproject === "function") {
                var coords = viewport.unproject([offsetX, offsetY]);
                if (coords && coords.length >= 2) {
                    return [coords[0], coords[1]];
                }
            }
        }
        return null;
    }

    function buildHoverLabelData(feature, positionOverride) {
        if (!feature || !feature.properties) {
            return null;
        }
        var topId = feature.properties.TopazID;
        if (topId === null || topId === undefined) {
            return null;
        }
        var position = positionOverride || resolveLabelPosition(feature);
        if (!position) {
            return null;
        }
        return [{
            text: String(topId),
            position: position
        }];
    }

    function buildLabelLayer(deckApi, labelData) {
        if (!deckApi || typeof deckApi.TextLayer !== "function") {
            return null;
        }
        return new deckApi.TextLayer({
            id: CHANNEL_LABEL_LAYER_ID,
            data: labelData || [],
            pickable: false,
            getPosition: function (d) { return d.position; },
            getText: function (d) { return d.text; },
            getSize: function () { return CHANNEL_LABEL_FONT_SIZE; },
            sizeUnits: "pixels",
            getColor: function () { return CHANNEL_LABEL_COLOR; },
            outlineColor: CHANNEL_LABEL_OUTLINE_COLOR,
            outlineWidth: CHANNEL_LABEL_OUTLINE_WIDTH,
            fontSettings: { sdf: true }
        });
    }

    function buildHoverLabelLayer(deckApi, labelData) {
        if (!deckApi || typeof deckApi.TextLayer !== "function") {
            return null;
        }
        return new deckApi.TextLayer({
            id: CHANNEL_HOVER_LABEL_LAYER_ID,
            data: labelData || [],
            pickable: false,
            getPosition: function (d) { return d.position; },
            getText: function (d) { return d.text; },
            getSize: function () { return CHANNEL_LABEL_FONT_SIZE; },
            sizeUnits: "pixels",
            getColor: function () { return CHANNEL_LABEL_COLOR; },
            outlineColor: CHANNEL_LABEL_OUTLINE_COLOR,
            outlineWidth: CHANNEL_LABEL_OUTLINE_WIDTH,
            fontSettings: { sdf: true }
        });
    }

    function clearHoverLabel(channel, map) {
        if (!channel) {
            return;
        }
        if (!channel.hoverLabelLayer) {
            channel.hoverLabelKey = null;
            return;
        }
        if (map && typeof map.removeLayer === "function") {
            map.removeLayer(channel.hoverLabelLayer, { skipOverlay: true });
        }
        channel.hoverLabelLayer = null;
        channel.hoverLabelKey = null;
    }

    function updateHoverLabel(channel, map, deckApi, info) {
        if (!channel || !map || !deckApi) {
            return;
        }
        if (channel.labelLayer && typeof map.hasLayer === "function" && map.hasLayer(channel.labelLayer)) {
            clearHoverLabel(channel, map);
            return;
        }
        var feature = info && info.object ? info.object : null;
        if (!feature) {
            clearHoverLabel(channel, map);
            return;
        }
        var topId = feature && feature.properties ? feature.properties.TopazID : null;
        if (topId === null || topId === undefined) {
            clearHoverLabel(channel, map);
            return;
        }
        var key = String(topId);
        if (channel.hoverLabelKey === key && channel.hoverLabelLayer) {
            return;
        }
        var position = resolveHoverLabelPosition(info, map);
        var data = buildHoverLabelData(feature, position);
        if (!data || !data.length) {
            clearHoverLabel(channel, map);
            return;
        }
        var nextLayer = buildHoverLabelLayer(deckApi, data);
        if (!nextLayer) {
            return;
        }
        if (channel.hoverLabelLayer && typeof map.removeLayer === "function") {
            map.removeLayer(channel.hoverLabelLayer, { skipOverlay: true });
        }
        channel.hoverLabelLayer = nextLayer;
        channel.hoverLabelKey = key;
        if (typeof map.addLayer === "function") {
            map.addLayer(nextLayer, { skipRefresh: true });
        }
    }

    function buildChannelLegendHtml() {
        var items = [
            "#8AE5FE", "#65C8FE", "#479EFF", "#306EFE",
            "#2500F4", "#6600cc", "#50006b", "#6b006b"
        ];
        var html = '<div class="wc-map-legend__header">Channel Order</div>';
        for (var i = 0; i < items.length; i += 1) {
            html += '<div class="wc-legend-item">'
                + '<span class="wc-legend-item__swatch" style="--legend-color: ' + items[i] + ';"></span>'
                + '<span class="wc-legend-item__label">Order ' + i + "</span>"
                + "</div>";
        }
        return html;
    }

    function setChannelLegend(html) {
        try {
            var map = MapController.getInstance();
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
            console.warn("[Channel GL] Failed to update legend", err);
        }
    }

    function removeLayer(channel, map) {
        clearHoverLabel(channel, map);
        if (channel.glLayer) {
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
        if (channel.labelLayer) {
            if (typeof map.unregisterOverlay === "function") {
                map.unregisterOverlay(channel.labelLayer);
            } else if (map.ctrls && typeof map.ctrls.removeLayer === "function") {
                map.ctrls.removeLayer(channel.labelLayer);
            }
            if (typeof map.removeLayer === "function") {
                map.removeLayer(channel.labelLayer);
            }
            channel.labelLayer = null;
        }
    }

    function buildNetfulUrl() {
        if (typeof window.url_for_run !== "function") {
            throw new Error("ChannelDelineation GL requires url_for_run.");
        }
        return window.url_for_run(NETFUL_ENDPOINT);
    }

    function buildChannelsUrl() {
        if (typeof window.url_for_run !== "function") {
            throw new Error("ChannelDelineation GL requires url_for_run.");
        }
        return window.url_for_run(CHANNELS_ENDPOINT);
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var events = helpers.events;
        var baseFactory = ensureControlBase();

        var channel = baseFactory();

        var emitterBase = events.createEmitter();
        var channelEvents = typeof events.useEventMap === "function"
            ? events.useEventMap(EVENT_NAMES, emitterBase)
            : emitterBase;

        channel.events = channelEvents;

        var formElement = dom.ensureElement("#build_channels_form", "Channel delineation form not found.");
        var infoElement = dom.qs("#build_channels_form #info");
        var statusElement = dom.qs("#build_channels_form #status");
        var stacktraceElement = dom.qs("#build_channels_form #stacktrace");
        var rqJobElement = dom.qs("#build_channels_form #rq_job");
        var hintElement = dom.qs("#hint_build_channels_en");
        var spinnerElement = dom.qs("#build_channels_form #braille");
        var manualExtentGroup = dom.qs("#map_bounds_text_group");
        var manualExtentInput = dom.qs("#map_bounds_text");
        var mapObjectGroup = dom.qs("#map_object_group");
        var mapObjectInput = dom.qs("#map_object");
        var mapBoundsInput = dom.qs("#map_bounds");
        var mapCenterInput = dom.qs("#map_center");
        var mapZoomInput = dom.qs("#map_zoom");
        var mapDistanceInput = dom.qs("#map_distance");
        var wbtFillSelect = dom.qs("#input_wbt_fill_or_breach");
        var wbtBreachContainer = dom.qs("#wbt_blc_dist_container");
        var wbtBreachInput = dom.qs("#wbt_blc_dist");
        var buildButton = document.getElementById("btn_build_channels_en");

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);
        var hintAdapter = createLegacyAdapter(hintElement);

        channel.form = formElement;
        channel.info = infoAdapter;
        channel.status = statusAdapter;
        channel.stacktrace = stacktraceAdapter;
        channel.rq_job = rqJobAdapter;
        channel.hint = hintAdapter;
        channel.command_btn_id = "btn_build_channels_en";
        channel.statusSpinnerEl = spinnerElement;
        channel.attach_status_stream(channel, {
            form: formElement,
            channel: "channel_delineation",
            runId: window.runid || window.runId || null,
            spinner: spinnerElement,
            autoConnect: true
        });
        channel.poll_completion_event = "BUILD_CHANNELS_TASK_COMPLETED";

        channel.zoom_min = 12;
        channel.glLayer = null;
        channel.glData = null;
        channel.labelLayer = null;
        channel.labelData = null;
        channel.hoverLabelLayer = null;
        channel.hoverLabelKey = null;
        channel._completion_seen = false;

        var bootstrapState = {
            reported: false,
            shownWithoutSubcatchments: false
        };

        function emit(eventName, payload) {
            if (channelEvents && typeof channelEvents.emit === "function") {
                channelEvents.emit(eventName, payload || {});
            }
        }

        function setHint(message) {
            if (hintAdapter && typeof hintAdapter.text === "function") {
                hintAdapter.text(message || "");
            }
        }

        function resetStatus(message) {
            if (infoAdapter && typeof infoAdapter.text === "function") {
                infoAdapter.text("");
            }
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(message + "...");
            }
            if (stacktraceAdapter && typeof stacktraceAdapter.empty === "function") {
                stacktraceAdapter.empty();
            }
            channel.hideStacktrace();
        }

        function showErrorStatus(message) {
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html('<span class="text-danger">' + message + "</span>");
            }
        }

        function getExtentMode() {
            var radios = dom.qsa('[data-channel-role="extent-mode"]', formElement);
            for (var i = 0; i < radios.length; i += 1) {
                if (radios[i].checked) {
                    var parsed = parseInt(radios[i].value, 10);
                    return Number.isNaN(parsed) ? 0 : parsed;
                }
            }
            return 0;
        }

        function updateManualExtentVisibility(mode) {
            if (!manualExtentGroup) {
                return;
            }
            if (mode === 1) {
                dom.show(manualExtentGroup);
            } else {
                dom.hide(manualExtentGroup);
            }
        }

        function updateMapObjectVisibility(mode) {
            if (!mapObjectGroup) {
                return;
            }
            if (mode === 2) {
                dom.show(mapObjectGroup);
            } else {
                dom.hide(mapObjectGroup);
            }
        }

        function updateExtentInputVisibility(mode) {
            updateManualExtentVisibility(mode);
            updateMapObjectVisibility(mode);
            if (mode === 2) {
                setBuildButtonEnabled(true, "");
                channel.update_command_button_state(channel);
            } else if (typeof channel.onMapChange === "function") {
                channel.onMapChange();
            }
        }

        function updateBreachDistanceVisibility(selection) {
            if (!wbtBreachContainer) {
                return;
            }
            if (selection === "breach_least_cost") {
                dom.show(wbtBreachContainer);
            } else {
                dom.hide(wbtBreachContainer);
            }
        }

        function setBuildButtonEnabled(enabled, reason) {
            if (!buildButton) {
                return;
            }
            buildButton.dataset.mapDisabled = enabled ? "false" : "true";
            if (buildButton.dataset.jobDisabled === "true") {
                buildButton.disabled = true;
            } else {
                buildButton.disabled = !enabled;
            }
            setHint(enabled ? "" : reason);
        }

        var baseShouldDisable = channel.should_disable_command_button.bind(channel);
        channel.should_disable_command_button = function (self) {
            if (baseShouldDisable(self)) {
                return true;
            }
            if (buildButton && buildButton.dataset.mapDisabled === "true") {
                return true;
            }
            return false;
        };

        function prepareExtentFields() {
            if (getExtentMode() !== 1) {
                return;
            }
            if (!manualExtentInput || !mapBoundsInput) {
                return;
            }
            if (typeof window.parseBboxText !== "function") {
                throw new Error("parseBboxText helper is required for manual extents.");
            }
            var raw = manualExtentInput.value || "";
            var bbox = window.parseBboxText(raw);
            manualExtentInput.value = bbox.join(", ");
            mapBoundsInput.value = bbox.join(",");
        }

        function buildPayload() {
            var raw = forms.serializeForm(formElement, { format: "object" });
            var setExtentMode = toInteger(raw.set_extent_mode);
            if (setExtentMode === null) {
                setExtentMode = 0;
            }
            var mapObject = null;
            var center = null;
            var bounds = null;
            var zoom = null;
            var distance = toFloat(raw.map_distance);
            var mcl = coalesceNumeric(raw, ["mcl", "input_mcl"]);
            var csa = coalesceNumeric(raw, ["csa", "input_csa"]);
            var wbtFill = raw.wbt_fill_or_breach || null;
            var wbtBreachDistance = toInteger(raw.wbt_blc_dist);
            var mapBoundsText = raw.map_bounds_text || "";

            if (setExtentMode === 2) {
                mapObject = normalizeMapObject(raw.map_object);
                center = mapObject.center;
                bounds = mapObject.extent;
                zoom = mapObject.zoom;

                if (bounds) {
                    mapBoundsText = bounds.join(", ");
                }
                if (mapCenterInput) {
                    mapCenterInput.value = center.join(",");
                }
                if (mapBoundsInput) {
                    mapBoundsInput.value = bounds.join(",");
                }
                if (mapZoomInput) {
                    mapZoomInput.value = zoom;
                }
            } else {
                if (setExtentMode === 1) {
                    prepareExtentFields();
                }
                center = parseNumericList(raw.map_center, 2);
                bounds = parseNumericList(raw.map_bounds, 4);
                zoom = toFloat(raw.map_zoom);
            }

            if (!center || center.length !== 2) {
                throw new Error("Map center is not available yet. Move the map to establish bounds.");
            }
            if (!bounds || bounds.length !== 4) {
                throw new Error("Map extent is missing. Navigate the map or specify a manual extent.");
            }
            if (mcl === null || csa === null) {
                throw new Error("Minimum channel length and critical source area must be numeric.");
            }

            return {
                map_center: center,
                map_zoom: zoom,
                map_bounds: bounds,
                map_distance: distance,
                mcl: mcl,
                csa: csa,
                wbt_fill_or_breach: wbtFill,
                wbt_blc_dist: wbtBreachDistance,
                set_extent_mode: setExtentMode,
                map_bounds_text: mapBoundsText,
                map_object: mapObject ? mapObject.payload : null
            };
        }

        var delegates = [];

        delegates.push(dom.delegate(formElement, "change", "[data-channel-role=\"extent-mode\"]", function () {
            var mode = parseInt(this.value, 10);
            if (Number.isNaN(mode)) {
                mode = 0;
            }
            updateExtentInputVisibility(mode);
            emit("channel:extent:mode", { mode: mode });
            try {
                channel.onMapChange();
            } catch (err) {
                // Map may not be ready yet; safe to ignore.
            }
        }));

        delegates.push(dom.delegate(formElement, "change", "[data-channel-role=\"wbt-fill\"]", function () {
            updateBreachDistanceVisibility(this.value);
        }));

        delegates.push(dom.delegate(formElement, "click", "[data-channel-action=\"build\"]", function (event) {
            event.preventDefault();
            channel.build();
        }));

        function initializeUI() {
            updateExtentInputVisibility(getExtentMode());
            if (wbtFillSelect) {
                updateBreachDistanceVisibility(wbtFillSelect.value);
            }
            if (buildButton) {
                buildButton.dataset.mapDisabled = "false";
            }
        }

        initializeUI();

        var baseTriggerEvent = channel.triggerEvent.bind(channel);
        channel.triggerEvent = function (eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === "BUILD_CHANNELS_TASK_COMPLETED") {
                if (!channel._completion_seen) {
                    channel._completion_seen = true;
                    channel.disconnect_status_stream(channel);
                    channel.show();
                    channel.report();
                    emit("channel:build:completed", payload || {});
                    baseTriggerEvent("job:completed", {
                        jobId: channel.rq_job_id,
                        task: "channel:build",
                        payload: payload || {}
                    });
                }
            } else if (normalized === "BUILD_CHANNELS_TASK_FAILED" || normalized === "BUILD_CHANNELS_TASK_ERROR") {
                emit("channel:build:error", {
                    reason: "job_failure",
                    payload: payload || {}
                });
                baseTriggerEvent("job:error", {
                    jobId: channel.rq_job_id,
                    task: "channel:build",
                    payload: payload || {}
                });
            }

            baseTriggerEvent(eventName, payload);
        };

        channel.hideStacktrace = function () {
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

        channel.remove = function () {
            var map;
            try {
                map = ensureMap();
            } catch (err) {
                return;
            }
            removeLayer(channel, map);
        };

        channel.onMapChange = function () {
            var map;
            try {
                map = ensureMap();
            } catch (error) {
                return;
            }
            try {
                var center = map.getCenter();
                var zoom = map.getZoom();
                var bounds = map.getBounds();
                var sw = bounds.getSouthWest();
                var ne = bounds.getNorthEast();
                var extent = [sw.lng, sw.lat, ne.lng, ne.lat];
                var distance = map.distance(ne, sw);

                if (mapCenterInput) {
                    mapCenterInput.value = [center.lng, center.lat].join(",");
                }
                if (mapZoomInput) {
                    mapZoomInput.value = zoom;
                }
                if (mapDistanceInput) {
                    mapDistanceInput.value = distance;
                }
                if (mapBoundsInput) {
                    mapBoundsInput.value = extent.join(",");
                }

                var extentMode = getExtentMode();
                if (extentMode === 2) {
                    setBuildButtonEnabled(true, "");
                } else {
                    var zoomOk = zoom >= channel.zoom_min;
                    var powerOverride = typeof window.ispoweruser !== "undefined" && window.ispoweruser;
                    var enabled = zoomOk || powerOverride;

                    if (!enabled) {
                        setBuildButtonEnabled(false, "Area is too large, zoom must be " + channel.zoom_min + ", current zoom is " + zoom + ".");
                    } else {
                        setBuildButtonEnabled(true, "");
                    }
                }

                channel.update_command_button_state(channel);

                emit("channel:map:updated", {
                    center: [center.lng, center.lat],
                    zoom: zoom,
                    distance: distance,
                    extent: extent
                });
            } catch (error) {
                // Map not initialized yet - this is normal during bootstrap.
            }
        };

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
            if (map && typeof map.on === "function") {
                map.on("move", channel.onMapChange);
                map.on("zoom", channel.onMapChange);
            }
            if (map && map.events && typeof map.events.on === "function") {
                map.events.on("map:ready", function () {
                    channel.onMapChange();
                });
                map.events.on("map:layer:toggled", function (payload) {
                    if (!payload || !payload.name) {
                        return;
                    }
                    if (payload.name === CHANNEL_LABEL_LAYER_NAME && payload.visible) {
                        clearHoverLabel(channel, map);
                    }
                    if (payload.name === CHANNEL_LAYER_NAME && !payload.visible) {
                        clearHoverLabel(channel, map);
                    }
                });
            }
            mapEventsBound = true;
        }

        bindMapEvents();

        channel.has_dem = function (onSuccessCallback) {
            return http.getJson(window.url_for_run("query/has_dem/"), { params: { _: Date.now() } })
                .then(function (response) {
                    if (typeof onSuccessCallback === "function") {
                        onSuccessCallback(response);
                    }
                    return response;
                })
                .catch(function (error) {
                    channel.pushErrorStacktrace(channel, error);
                    throw error;
                });
        };

        channel.build = function () {
            var taskMsg = "Delineating channels";
            resetStatus(taskMsg);

            channel.remove();
            channel._completion_seen = false;
            try {
                if (window.Outlet && typeof window.Outlet.getInstance === "function") {
                    window.Outlet.getInstance().remove();
                }
            } catch (err) {
                console.warn("Failed to remove outlet before channel build", err);
            }

            channel.connect_status_stream(channel);

            var payload;
            try {
                payload = buildPayload();
            } catch (err) {
                showErrorStatus(err.message);
                emit("channel:build:error", { reason: "validation", error: err });
                channel.triggerEvent("job:error", {
                    reason: "validation",
                    message: err.message
                });
                return Promise.reject(err);
            }

            if (payload.set_extent_mode === 2 && payload.map_center && payload.map_center.length === 2) {
                try {
                    var map = ensureMap();
                    if (map && typeof map.flyTo === "function") {
                        var flyZoom = payload.map_zoom || map.getZoom();
                        map.flyTo([payload.map_center[1], payload.map_center[0]], flyZoom);
                    }
                } catch (err) {
                    // Best-effort.
                }
            }

            emit("channel:build:started", {
                payload: payload
            });

            return http.request(window.url_for_run("rq/api/fetch_dem_and_build_channels"), {
                method: "POST",
                json: payload,
                form: formElement
            })
                .then(function (result) {
                    var data = result.body || {};
                    if (data.Success === true && data.job_id) {
                        if (statusAdapter && typeof statusAdapter.html === "function") {
                            statusAdapter.html("fetch_dem_and_build_channels_rq job submitted: " + data.job_id);
                        }
                        channel.set_rq_job_id(channel, data.job_id);
                        channel.triggerEvent("job:started", {
                            jobId: data.job_id,
                            task: "channel:build",
                            payload: payload
                        });
                        return data;
                    }
                    channel.pushResponseStacktrace(channel, data);
                    showErrorStatus("Failed to submit channel delineation job.");
                    emit("channel:build:error", {
                        reason: "server",
                        response: data
                    });
                    channel.triggerEvent("job:error", {
                        reason: "server",
                        response: data
                    });
                    return data;
                })
                .catch(function (error) {
                    channel.pushErrorStacktrace(channel, error);
                    showErrorStatus("Unable to enqueue channel delineation job.");
                    emit("channel:build:error", {
                        reason: "http",
                        error: error
                    });
                    channel.triggerEvent("job:error", {
                        reason: "http",
                        error: error
                    });
                    throw error;
                });
        };

        channel.show_1 = function () {
            var map = ensureMap();
            var deckApi = ensureDeck();
            var url = buildNetfulUrl();
            var taskMsg = "Displaying Channel Map (WebGL)";

            if (!bootstrapState.reported) {
                resetStatus(taskMsg);
            }
            if (statusAdapter && typeof statusAdapter.text === "function") {
                statusAdapter.text(taskMsg + "...");
            }

            removeLayer(channel, map);
            setChannelLegend("");

            return http.getJson(url, { params: { _: Date.now() } })
                .then(function (data) {
                    channel.glData = data || EMPTY_GEOJSON;
                    if (map && typeof map.clearFindFlashCache === "function") {
                        map.clearFindFlashCache("channels");
                    }
                    channel.labelData = null;
                    channel.glLayer = buildChannelLayer(deckApi, channel.glData, {
                        layerId: CHANNEL_LAYER_ID,
                        getLineColor: getLineColorPass1,
                        getFillColor: getFillColorPass1,
                        pickable: false,
                        filled: true
                    });
                    attachChannelRebuild(channel.glLayer, channel, {
                        layerId: CHANNEL_LAYER_ID,
                        getLineColor: getLineColorPass1,
                        getFillColor: getFillColorPass1,
                        pickable: false,
                        filled: true
                    });
                    if (typeof map.registerOverlay === "function") {
                        map.registerOverlay(channel.glLayer, CHANNEL_LAYER_NAME);
                    } else if (map.ctrls && typeof map.ctrls.addOverlay === "function") {
                        map.ctrls.addOverlay(channel.glLayer, CHANNEL_LAYER_NAME);
                    }
                    if (typeof map.addLayer === "function") {
                        map.addLayer(channel.glLayer);
                    }
                    if (statusAdapter && typeof statusAdapter.text === "function") {
                        statusAdapter.text(taskMsg + " - done");
                    }
                    emit("channel:layers:loaded", { mode: 1, layer: channel.glLayer });
                    return channel.glLayer;
                })
                .catch(function (error) {
                    channel.pushErrorStacktrace(channel, error);
                    showErrorStatus("Unable to load channel map.");
                    emit("channel:build:error", { reason: "load", error: error });
                    throw error;
                });
        };

        channel.show_2 = function () {
            var map = ensureMap();
            var deckApi = ensureDeck();
            var url = buildChannelsUrl();
            var taskMsg = "Displaying SUBWTA channels";

            if (!bootstrapState.reported) {
                resetStatus(taskMsg);
            }
            if (statusAdapter && typeof statusAdapter.text === "function") {
                statusAdapter.text(taskMsg + "...");
            }

            removeLayer(channel, map);
            setChannelLegend("");

            return http.getJson(url, { params: { _: Date.now() } })
                .then(function (data) {
                    var features = data && data.features ? data.features : [];
                    var onHoverHandler = function (info) {
                        updateHoverLabel(channel, map, deckApi, info);
                    };
                    var onClickHandler = function (info) {
                        var feature = info && info.object ? info.object : null;
                        var topId = feature && feature.properties ? feature.properties.TopazID : null;
                        if (!topId) {
                            return;
                        }
                        if (map && typeof map.chnQuery === "function") {
                            map.chnQuery(topId);
                        }
                    };
                    channel.glData = data || EMPTY_GEOJSON;
                    if (map && typeof map.clearFindFlashCache === "function") {
                        map.clearFindFlashCache("channels");
                    }
                    channel.glLayer = buildChannelLayer(deckApi, channel.glData, {
                        layerId: CHANNEL_PASS2_LAYER_ID,
                        getLineColor: getLineColorPass2,
                        getFillColor: getFillColorPass2,
                        pickable: true,
                        filled: true,
                        onHover: onHoverHandler,
                        onClick: onClickHandler
                    });
                    attachChannelRebuild(channel.glLayer, channel, {
                        layerId: CHANNEL_PASS2_LAYER_ID,
                        getLineColor: getLineColorPass2,
                        getFillColor: getFillColorPass2,
                        pickable: true,
                        filled: true,
                        onHover: onHoverHandler,
                        onClick: onClickHandler
                    });

                    channel.labelData = buildLabelData(features);
                    channel.labelLayer = buildLabelLayer(deckApi, channel.labelData);
                    if (channel.labelLayer) {
                        attachLabelRebuild(channel.labelLayer, channel);
                    }

                    if (typeof map.registerOverlay === "function") {
                        map.registerOverlay(channel.glLayer, CHANNEL_LAYER_NAME);
                    } else if (map.ctrls && typeof map.ctrls.addOverlay === "function") {
                        map.ctrls.addOverlay(channel.glLayer, CHANNEL_LAYER_NAME);
                    }
                    if (typeof map.addLayer === "function") {
                        map.addLayer(channel.glLayer);
                    }

                    if (channel.labelLayer) {
                        if (typeof map.registerOverlay === "function") {
                            map.registerOverlay(channel.labelLayer, CHANNEL_LABEL_LAYER_NAME);
                        } else if (map.ctrls && typeof map.ctrls.addOverlay === "function") {
                            map.ctrls.addOverlay(channel.labelLayer, CHANNEL_LABEL_LAYER_NAME);
                        }
                    }

                    if (statusAdapter && typeof statusAdapter.text === "function") {
                        statusAdapter.text(taskMsg + " - done");
                    }
                    setChannelLegend(buildChannelLegendHtml());
                    emit("channel:layers:loaded", { mode: 2, layer: channel.glLayer });
                    return channel.glLayer;
                })
                .catch(function (error) {
                    channel.pushErrorStacktrace(channel, error);
                    showErrorStatus("Unable to load channel map.");
                    emit("channel:build:error", { reason: "load", error: error });
                    throw error;
                });
        };

        channel.show = function () {
            var taskMsg = "Identifying topaz_pass";
            if (!bootstrapState.reported) {
                resetStatus(taskMsg);
            }

            return http.request(window.url_for_run("query/delineation_pass/"), { params: { _: Date.now() } })
                .then(function (result) {
                    var response = result && Object.prototype.hasOwnProperty.call(result, "body") ? result.body : result;
                    var pass = parseInt(response, 10);
                    if ([0, 1, 2].indexOf(pass) === -1) {
                        channel.pushResponseStacktrace(channel, { Error: "Error Determining Delineation Pass" });
                        showErrorStatus("Error determining delineation pass.");
                        setChannelLegend("");
                        return null;
                    }
                    if (pass === 0) {
                        channel.pushResponseStacktrace(channel, { Error: "Channels not delineated" });
                        showErrorStatus("Channels have not been delineated yet.");
                        setChannelLegend("");
                        return null;
                    }

                    if (pass === 1) {
                        return channel.show_1();
                    }
                    return channel.show_2();
                })
                .then(function (layer) {
                    if (layer && statusAdapter && typeof statusAdapter.html === "function") {
                        statusAdapter.html(taskMsg + "... Success");
                    }
                    return layer;
                })
                .catch(function (error) {
                    channel.pushErrorStacktrace(channel, error);
                });
        };

        channel.refreshLayers = function () {
            return channel.show();
        };

        channel.report = function () {
            return http.request(window.url_for_run("report/channel"), {
                headers: { Accept: "text/html, */*;q=0.8" }
            })
                .then(function (result) {
                    if (infoAdapter && typeof infoAdapter.html === "function") {
                        infoAdapter.html(result.body || "");
                    }
                    bootstrapState.reported = true;
                    emit("channel:report:loaded", {});
                })
                .catch(function (error) {
                    channel.pushErrorStacktrace(channel, error);
                });
        };

        channel.bootstrap = function bootstrap(context) {
            bindMapEvents();
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            var controllerContext = helper && typeof helper.getControllerContext === "function"
                ? helper.getControllerContext(ctx, "channel")
                : {};

            var jobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "fetch_dem_and_build_channels_rq")
                : null;
            if (!jobId && controllerContext.jobId) {
                jobId = controllerContext.jobId;
            }
            if (!jobId) {
                var jobIds = ctx && (ctx.jobIds || ctx.jobs);
                if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "fetch_dem_and_build_channels_rq")) {
                    var value = jobIds.fetch_dem_and_build_channels_rq;
                    if (value !== undefined && value !== null) {
                        jobId = String(value);
                    }
                }
            }

            if (typeof channel.set_rq_job_id === "function") {
                channel.set_rq_job_id(channel, jobId);
            }

            if (controllerContext.zoomMin !== undefined && controllerContext.zoomMin !== null) {
                channel.zoom_min = controllerContext.zoomMin;
            }

            if (typeof channel.onMapChange === "function") {
                channel.onMapChange();
            }

            var watershed = (ctx.data && ctx.data.watershed) || {};
            var hasChannels = Boolean(watershed.hasChannels);
            if (hasChannels && !bootstrapState.reported && typeof channel.report === "function") {
                channel.report();
                bootstrapState.reported = true;
            }

            if (hasChannels && !bootstrapState.shownWithoutSubcatchments && typeof channel.show === "function") {
                channel.show();
                bootstrapState.shownWithoutSubcatchments = true;
            }

            return channel;
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
