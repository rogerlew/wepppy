/* ----------------------------------------------------------------------------
 * Map (Deck.gl scaffolding)
 * Doc: controllers_js/README.md - Map Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var MapController = (function () {
    "use strict";

    var instance;

    function getMapGlShared() {
        if (!window.WCMapGlShared) {
            throw new Error("Map GL controller requires WCMapGlShared helpers.");
        }
        return window.WCMapGlShared;
    }

    function getMapGlLayerControlHelpers() {
        if (!window.WCMapGlLayerControl) {
            throw new Error("Map GL controller requires WCMapGlLayerControl helpers.");
        }
        return window.WCMapGlLayerControl;
    }

    function getMapGlFeatureUiHelpers() {
        if (!window.WCMapGlFeatureUi) {
            throw new Error("Map GL controller requires WCMapGlFeatureUi helpers.");
        }
        return window.WCMapGlFeatureUi;
    }

    function ensureHelpers() {
        var dom = window.WCDom;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.qs !== "function" || typeof dom.delegate !== "function" ||
            typeof dom.show !== "function" || typeof dom.hide !== "function" || typeof dom.setText !== "function") {
            throw new Error("Map GL controller requires WCDom helpers.");
        }
        if (!http || typeof http.postJson !== "function" || typeof http.getJson !== "function" || typeof http.request !== "function") {
            throw new Error("Map GL controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Map GL controller requires WCEvents helpers.");
        }

        return { dom: dom, http: http, events: events };
    }

    function ensureDeck() {
        if (typeof window === "undefined" || !window.deck || !window.deck.Deck) {
            throw new Error("Map GL controller requires deck.gl (window.deck.Deck).");
        }
    }

    function createInstance() {

        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var http = helpers.http;
        var events = helpers.events;
        var deckApi = window.deck;
        var coordRound = (typeof window.coordRound === "function")
            ? window.coordRound
            : function (value) { return Math.round(value * 1000) / 1000; };

        var shared = getMapGlShared();
        var layerControlHelpers = getMapGlLayerControlHelpers();
        var featureUiHelpers = getMapGlFeatureUiHelpers();

        var EVENT_NAMES = shared.EVENT_NAMES;
        var DEFAULT_VIEW = shared.DEFAULT_VIEW;
        var FLY_TO_DURATION_MS = shared.FLY_TO_DURATION_MS;
        var FLY_TO_BOUNDS_PADDING_PX = shared.FLY_TO_BOUNDS_PADDING_PX;
        var SENSOR_LAYER_MIN_ZOOM = shared.SENSOR_LAYER_MIN_ZOOM;
        var MAP_MIN_ZOOM = shared.MAP_MIN_ZOOM;
        var MAP_MAX_ZOOM = shared.MAP_MAX_ZOOM;
        var USGS_LAYER_NAME = shared.USGS_LAYER_NAME;
        var SNOTEL_LAYER_NAME = shared.SNOTEL_LAYER_NAME;
        var NHD_LAYER_NAME = shared.NHD_LAYER_NAME;
        var NHD_LAYER_MIN_ZOOM = shared.NHD_LAYER_MIN_ZOOM;
        var NHD_LAYER_HR_MIN_ZOOM = shared.NHD_LAYER_HR_MIN_ZOOM;
        var SUBCATCHMENT_LAYER_ENDPOINT = shared.SUBCATCHMENT_LAYER_ENDPOINT;
        var CHANNEL_LAYER_ENDPOINT = shared.CHANNEL_LAYER_ENDPOINT;
        var SBS_LAYER_NAME = shared.SBS_LAYER_NAME;
        var SBS_QUERY_ENDPOINT = shared.SBS_QUERY_ENDPOINT;
        var SBS_DEFAULT_OPACITY = shared.SBS_DEFAULT_OPACITY;
        var SBS_COLOR_MODES = shared.SBS_COLOR_MODES;
        var LEGEND_OPACITY_CONTAINER_ID = shared.LEGEND_OPACITY_CONTAINER_ID;
        var LEGEND_OPACITY_INPUT_ID = shared.LEGEND_OPACITY_INPUT_ID;
        var DEFAULT_ELEVATION_COOLDOWN_MS = shared.DEFAULT_ELEVATION_COOLDOWN_MS;
        var MOUSE_ELEVATION_HIDE_DELAY_MS = shared.MOUSE_ELEVATION_HIDE_DELAY_MS;
        var FIND_FLASH_LAYER_PREFIX = shared.FIND_FLASH_LAYER_PREFIX;
        var FIND_FLASH_DURATION_MS = shared.FIND_FLASH_DURATION_MS;
        var FIND_FLASH_PULSE_INTERVAL_MS = shared.FIND_FLASH_PULSE_INTERVAL_MS;

        var createLegacyAdapter = shared.createLegacyAdapter;
        var createTabset = shared.createTabset;
        var parseLocationInput = shared.parseLocationInput;
        var normalizeUrlPayload = shared.normalizeUrlPayload;
        var resolveErrorMessage = shared.resolveErrorMessage;
        var isValidLatLng = shared.isValidLatLng;
        var buildNhdFlowlinesUrl = shared.buildNhdFlowlinesUrl;
        var toOverlayId = shared.toOverlayId;
        var hexToRgba = shared.hexToRgba;
        var isAbsoluteUrl = shared.isAbsoluteUrl;
        var clampOpacity = shared.clampOpacity;
        var normalizeSbsColorMode = shared.normalizeSbsColorMode;
        var getSbsLegendItemsForMode = shared.getSbsLegendItemsForMode;
        var drawSbsImageToCanvas = shared.drawSbsImageToCanvas;
        var buildShiftedSbsImage = shared.buildShiftedSbsImage;
        var normalizeSbsBounds = shared.normalizeSbsBounds;
        var normalizeCenter = shared.normalizeCenter;
        var buildBoundsFallback = shared.buildBoundsFallback;
        var calculateDistanceMeters = shared.calculateDistanceMeters;

        ensureDeck();

        function ensureGeoJsonLayer() {
            if (!deckApi || typeof deckApi.GeoJsonLayer !== "function") {
                throw new Error("Map GL controller requires deck.gl GeoJsonLayer (window.deck.GeoJsonLayer).");
            }
        }

        function ensureBitmapLayer() {
            if (!deckApi || typeof deckApi.BitmapLayer !== "function") {
                throw new Error("Map GL controller requires deck.gl BitmapLayer (window.deck.BitmapLayer).");
            }
        }

        var state = {
            center: { lat: DEFAULT_VIEW.lat, lng: DEFAULT_VIEW.lng },
            zoom: DEFAULT_VIEW.zoom,
            readyEmitted: false
        };

        var emitterBase = events.createEmitter();
        var mapEvents = typeof events.useEventMap === "function"
            ? events.useEventMap(EVENT_NAMES, emitterBase)
            : emitterBase;

        var basemapDefs = {
            googleTerrain: {
                key: "googleTerrain",
                label: "Terrain",
                template: "https://{s}.google.com/vt/lyrs=p&x={x}&y={y}&z={z}",
                subdomains: ["mt0", "mt1", "mt2", "mt3"]
            },
            googleSatellite: {
                key: "googleSatellite",
                label: "Satellite",
                template: "https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
                subdomains: ["mt0", "mt1", "mt2", "mt3"]
            }
        };

        var formElement = dom.qs("#setloc_form");
        var centerInput = dom.qs("#input_centerloc", formElement);
        var mapCanvasElement = dom.qs("#mapid");
        var drilldownElement = dom.qs("#drilldown");
        var subLegendElement = dom.qs("#sub_legend");
        var sbsLegendElement = dom.qs("#sbs_legend");
        var sbsColorShiftToggleElement = dom.qs("#sbs_color_shift_toggle");
        var mapStatusElement = dom.qs("#mapstatus");
        var mapStatusCenterElement = dom.qs("#mapstatus-center");
        var mapStatusZoomElement = dom.qs("#mapstatus-zoom");
        var mapStatusWidthElement = dom.qs("#mapstatus-width");
        var mapStatusCursorElement = dom.qs("#mapstatus-cursor");
        var mouseElevationElement = dom.qs("#mouseelev");
        var mapStatusCursorItem = mapStatusCursorElement
            ? mapStatusCursorElement.closest(".wc-summary-pane__item")
            : null;
        var mouseElevationItem = mouseElevationElement
            ? mouseElevationElement.closest(".wc-summary-pane__item")
            : null;
        var tabsetRoot = dom.qs("#setloc_form [data-tabset]");

        var overlayRegistry = typeof Map === "function" ? new Map() : null;
        var overlayNameRegistry = typeof Map === "function" ? new Map() : null;
        var layerRegistry = typeof Set === "function" ? new Set() : null;
        var drilldownSuppressionTokens = typeof Set === "function" ? new Set() : null;
        var panes = {};
        var mapHandlers = {};
        var deckgl = null;
        var isApplyingViewState = false;
        var baseLayer = null;
        var baseLayerKey = basemapDefs.googleTerrain.key;
        var layerControl = null;
        var sbsLayerController = null;
        var sbsOverlayAvailable = null;
        var elevationCooldownTimer = null;
        var mouseElevationHideTimer = null;
        var isFetchingElevation = false;
        var lastElevationAbort = null;
        var flashState = {
            layer: null,
            timer: null,
            pulseTimer: null,
            cache: {
                subcatchments: null,
                channels: null
            }
        };

        function getSbsColorModeFromToggle() {
            if (sbsColorShiftToggleElement && sbsColorShiftToggleElement.checked) {
                return SBS_COLOR_MODES.SHIFTED;
            }
            return SBS_COLOR_MODES.STANDARD;
        }

        function emit(eventName, payload) {
            if (mapEvents && typeof mapEvents.emit === "function") {
                mapEvents.emit(eventName, payload || {});
            }
        }

        function resolveRunScopedUrl(path) {
            if (!path) {
                return null;
            }
            var raw = String(path);
            if (isAbsoluteUrl(raw)) {
                return raw;
            }
            if (raw.indexOf("/runs/") !== -1 || raw.indexOf("runs/") === 0) {
                return raw;
            }
            if (typeof url_for_run !== "function") {
                throw new Error("Map GL controller requires url_for_run helper for run-scoped URLs.");
            }
            return url_for_run(raw);
        }

        function warnNotImplemented(action) {
            console.warn("Map GL stub: " + action + " not implemented.");
        }

        function normalizeSbsAvailability(value) {
            if (value === undefined || value === null) {
                return null;
            }
            return Boolean(value);
        }

        function resolveInitialHasSbs(context) {
            var ctx = context || null;
            var flags = ctx && ctx.flags ? ctx.flags : null;
            if (flags && flags.initialHasSbs !== undefined && flags.initialHasSbs !== null) {
                return normalizeSbsAvailability(flags.initialHasSbs);
            }
            if (typeof window !== "undefined") {
                var runContext = window.runContext || null;
                var runFlags = runContext && runContext.flags ? runContext.flags : null;
                if (runFlags && runFlags.initialHasSbs !== undefined && runFlags.initialHasSbs !== null) {
                    return normalizeSbsAvailability(runFlags.initialHasSbs);
                }
            }
            return null;
        }

        function setSbsOverlayAvailability(value) {
            var normalized = normalizeSbsAvailability(value);
            if (normalized === null) {
                return;
            }
            if (sbsOverlayAvailable === normalized) {
                return;
            }
            sbsOverlayAvailable = normalized;
            if (layerControl) {
                renderOverlayLayerControl();
            }
        }

        function shouldRenderOverlay(name) {
            if (!name) {
                return false;
            }
            if (sbsOverlayAvailable === false && name.indexOf(SBS_LAYER_NAME) !== -1) {
                return false;
            }
            return true;
        }

        function normalizeFeatureCollection(data) {
            if (!data || !data.features) {
                return { type: "FeatureCollection", features: [] };
            }
            if (data.type !== "FeatureCollection") {
                return { type: "FeatureCollection", features: data.features };
            }
            return data;
        }

        function featureMatches(feature, idType, value) {
            if (!feature || !feature.properties || !idType) {
                return false;
            }
            var propValue = feature.properties[idType];
            if (propValue === undefined || propValue === null) {
                if (idType === "WeppID") {
                    if (feature.properties.wepp_id !== undefined && feature.properties.wepp_id !== null) {
                        propValue = feature.properties.wepp_id;
                    } else if (feature.properties.weppId !== undefined && feature.properties.weppId !== null) {
                        propValue = feature.properties.weppId;
                    }
                }
            }
            if (propValue === undefined || propValue === null) {
                var lowerKey = idType.replace(/([A-Z])/g, function (match, p1) {
                    return "_" + p1.toLowerCase();
                }).replace(/^_/, "");
                propValue = feature.properties[lowerKey];
            }
            return String(propValue) === String(value);
        }

        function extractFeatureCollection(ctrl) {
            if (!ctrl) {
                return null;
            }
            if (ctrl.state && ctrl.state.data && ctrl.state.data.features) {
                return ctrl.state.data;
            }
            if (ctrl.glData && ctrl.glData.features) {
                return ctrl.glData;
            }
            if (ctrl.glLayer && ctrl.glLayer.props && ctrl.glLayer.props.data) {
                return normalizeFeatureCollection(ctrl.glLayer.props.data);
            }
            return null;
        }

        function resolveLayerData(layer) {
            if (!layer) {
                return Promise.resolve(null);
            }
            var ctrl = layer.ctrl || null;
            var type = layer.type || null;
            var fromCtrl = extractFeatureCollection(ctrl);
            if (fromCtrl) {
                return Promise.resolve(fromCtrl);
            }
            var cacheKey = type === "channel" ? "channels" : "subcatchments";
            var cached = flashState.cache[cacheKey];
            if (cached) {
                return Promise.resolve(cached);
            }
            var endpoint = type === "channel" ? CHANNEL_LAYER_ENDPOINT : SUBCATCHMENT_LAYER_ENDPOINT;
            var url = resolveRunScopedUrl(endpoint);
            if (!url) {
                return Promise.resolve(null);
            }
            return http.getJson(url, { params: { _: Date.now() } })
                .then(function (data) {
                    var normalized = normalizeFeatureCollection(data);
                    flashState.cache[cacheKey] = normalized;
                    return normalized;
                })
                .catch(function (error) {
                    console.warn("Map GL: failed to load layer data for find/flash", error);
                    return null;
                });
        }

        function clearFlashLayer() {
            if (flashState.timer) {
                clearTimeout(flashState.timer);
                flashState.timer = null;
            }
            if (flashState.pulseTimer) {
                clearInterval(flashState.pulseTimer);
                flashState.pulseTimer = null;
            }
            if (flashState.layer) {
                try {
                    map.removeLayer(flashState.layer, { skipOverlay: true });
                } catch (err) {
                    // ignore cleanup errors
                }
                flashState.layer = null;
            }
        }

        function buildFlashLayer(features, opacity, layerId) {
            ensureGeoJsonLayer();
            var alpha = Math.max(0, Math.min(1, opacity));
            var lineAlpha = Math.round(255 * alpha);
            var fillAlpha = Math.round(200 * alpha);
            var data = { type: "FeatureCollection", features: features };
            return new deckApi.GeoJsonLayer({
                id: layerId,
                data: data,
                pickable: false,
                stroked: true,
                filled: true,
                lineWidthUnits: "pixels",
                lineWidthMinPixels: 2,
                getLineWidth: function () { return 2; },
                getLineColor: function () { return [255, 255, 255, lineAlpha]; },
                getFillColor: function () { return [255, 255, 255, fillAlpha]; }
            });
        }

        function flashFeatures(mapInstance, features, options) {
            if (!mapInstance || !features || !features.length) {
                return;
            }
            var config = options || {};
            var duration = Number.isFinite(config.duration) ? config.duration : FIND_FLASH_DURATION_MS;
            var layerId = FIND_FLASH_LAYER_PREFIX + "-" + Date.now();

            clearFlashLayer();

            var start = Date.now();
            var ticks = 0;
            var maxTick = Math.max(1, Math.floor(duration / FIND_FLASH_PULSE_INTERVAL_MS));

            function applyFlashLayer() {
                var progress = ticks / maxTick;
                var pulse = Math.abs(Math.sin(progress * Math.PI * 3));
                var opacity = 0.35 + 0.65 * pulse;
                var layer = buildFlashLayer(features, opacity, layerId);
                if (flashState.layer) {
                    mapInstance.removeLayer(flashState.layer, { skipOverlay: true });
                }
                mapInstance.addLayer(layer, { skipRefresh: true });
                flashState.layer = layer;
                ticks += 1;
            }

            applyFlashLayer();

            flashState.pulseTimer = setInterval(function () {
                var elapsed = Date.now() - start;
                if (elapsed >= duration) {
                    return;
                }
                applyFlashLayer();
            }, FIND_FLASH_PULSE_INTERVAL_MS);

            flashState.timer = setTimeout(function () {
                clearFlashLayer();
            }, duration);
        }

        function ensureFindAndFlashHelper() {
            if (window.WEPP_FIND_AND_FLASH && typeof window.WEPP_FIND_AND_FLASH.findAndFlashById === "function") {
                return window.WEPP_FIND_AND_FLASH;
            }

            var helper = {
                ID_TYPE: {
                    TOPAZ: "TopazID",
                    WEPP: "WeppID"
                },
                FEATURE_TYPE: {
                    SUBCATCHMENT: "subcatchment",
                    CHANNEL: "channel"
                },
                findAndFlashById: function (options) {
                    options = options || {};
                    var idType = options.idType;
                    var value = options.value;
                    var mapInstance = options.map || map;
                    var layers = Array.isArray(options.layers) ? options.layers : [];
                    var onFlash = options.onFlash;

                    if (!idType || value === undefined || value === null) {
                        return Promise.resolve(null);
                    }
                    if (!mapInstance) {
                        console.warn("Map GL: findAndFlashById map instance unavailable");
                        return Promise.resolve(null);
                    }

                    var targetValue = String(value);

                    function searchLayer(index) {
                        if (index >= layers.length) {
                            console.warn("Map GL: findAndFlashById no feature matched", idType, targetValue);
                            return Promise.resolve(null);
                        }
                        var layer = layers[index];
                        return resolveLayerData(layer).then(function (collection) {
                            if (!collection || !collection.features || !collection.features.length) {
                                return searchLayer(index + 1);
                            }
                            var hits = collection.features.filter(function (feature) {
                                return featureMatches(feature, idType, targetValue);
                            });
                            if (!hits.length) {
                                return searchLayer(index + 1);
                            }

                            flashFeatures(mapInstance, hits, { duration: FIND_FLASH_DURATION_MS });

                            var result = {
                                hits: hits,
                                featureType: layer.type,
                                idType: idType,
                                value: targetValue
                            };

                            if (typeof onFlash === "function") {
                                try {
                                    onFlash(result);
                                } catch (err) {
                                    console.error("Map GL: findAndFlashById onFlash error", err);
                                }
                            }

                            return result;
                        });
                    }

                    return searchLayer(0);
                },
                flashFeatures: function (mapInstance, features, options) {
                    flashFeatures(mapInstance || map, features, options);
                }
            };

            window.WEPP_FIND_AND_FLASH = helper;
            return helper;
        }

        function getCanvasSize() {
            if (!mapCanvasElement) {
                return { width: 0, height: 0 };
            }
            var rect = mapCanvasElement.getBoundingClientRect();
            var width = Math.round(rect.width || mapCanvasElement.offsetWidth || mapCanvasElement.clientWidth || 0);
            var height = Math.round(rect.height || mapCanvasElement.offsetHeight || mapCanvasElement.clientHeight || 0);
            return { width: width, height: height };
        }

        function updateMapStatus() {
            if (!mapStatusElement && !mapStatusCenterElement && !mapStatusZoomElement && !mapStatusWidthElement) {
                return;
            }
            var center = state.center;
            var zoom = state.zoom;
            var width = mapCanvasElement ? Math.round(mapCanvasElement.offsetWidth || 0) : 0;
            var lng = coordRound(center.lng);
            var lat = coordRound(center.lat);
            if (mapStatusCenterElement) {
                dom.setText(mapStatusCenterElement, lng + ", " + lat);
            }
            if (mapStatusZoomElement) {
                dom.setText(mapStatusZoomElement, zoom);
            }
            if (mapStatusWidthElement) {
                dom.setText(mapStatusWidthElement, width + "px");
            }
        }

        function showMouseElevation(payload) {
            if (!mouseElevationElement && !mapStatusCursorElement) {
                return;
            }
            if (mouseElevationHideTimer) {
                clearTimeout(mouseElevationHideTimer);
                mouseElevationHideTimer = null;
            }
            var elevationText = payload && payload.elevation ? payload.elevation : "-";
            var cursorText = payload && payload.cursor ? payload.cursor : "-";
            if (mouseElevationElement) {
                dom.setText(mouseElevationElement, elevationText);
            }
            if (mapStatusCursorElement) {
                dom.setText(mapStatusCursorElement, cursorText);
            }
            if (mouseElevationItem) {
                dom.show(mouseElevationItem);
            }
            if (mapStatusCursorItem) {
                dom.show(mapStatusCursorItem);
            }
        }

        function hideMouseElevation(delayMs) {
            if (!mouseElevationElement && !mapStatusCursorElement) {
                return;
            }
            if (mouseElevationHideTimer) {
                clearTimeout(mouseElevationHideTimer);
            }
            mouseElevationHideTimer = window.setTimeout(function () {
                if (mouseElevationElement) {
                    dom.setText(mouseElevationElement, "-");
                }
                if (mapStatusCursorElement) {
                    dom.setText(mapStatusCursorElement, "-");
                }
            }, typeof delayMs === "number" ? delayMs : 0);
        }

        function updateCursorStatus(latlng) {
            if (!mapStatusCursorElement || !latlng) {
                return;
            }
            var cursorLng = coordRound(latlng.lng);
            var cursorLat = coordRound(latlng.lat);
            dom.setText(mapStatusCursorElement, cursorLng + ", " + cursorLat);
            if (mapStatusCursorItem) {
                dom.show(mapStatusCursorItem);
            }
        }

        function scheduleElevationCooldown() {
            if (elevationCooldownTimer) {
                clearTimeout(elevationCooldownTimer);
            }
            elevationCooldownTimer = window.setTimeout(function () {
                isFetchingElevation = false;
            }, DEFAULT_ELEVATION_COOLDOWN_MS);
            map.fetchTimer = elevationCooldownTimer;
        }

        function resolveElevationEndpoint() {
            if (typeof url_for_run === "function") {
                try {
                    return url_for_run("elevationquery/");
                } catch (error) {
                    // Fallback to manual path construction below.
                }
            }
            var encodedRunId = (typeof runid !== "undefined" && runid !== null) ? encodeURIComponent(runid) : null;
            var encodedConfig = (typeof config !== "undefined" && config !== null) ? encodeURIComponent(config) : null;
            if (encodedRunId && encodedConfig) {
                return "/runs/" + encodedRunId + "/" + encodedConfig + "/elevationquery/";
            }
            return null;
        }

        function handleDeckHover(info) {
            if (!info || !info.coordinate || info.coordinate.length < 2) {
                return;
            }
            var lng = Number(info.coordinate[0]);
            var lat = Number(info.coordinate[1]);
            if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
                return;
            }
            updateCursorStatus({ lat: lat, lng: lng });
            if (!isFetchingElevation) {
                fetchElevation({ lat: lat, lng: lng });
            }
        }

        function fetchElevation(latlng) {
            var endpoint = resolveElevationEndpoint();
            if (!endpoint) {
                return Promise.resolve();
            }
            if (isFetchingElevation) {
                return Promise.resolve();
            }
            isFetchingElevation = true;

            if (lastElevationAbort && typeof lastElevationAbort.abort === "function") {
                lastElevationAbort.abort();
            }
            var abortController = typeof AbortController === "function" ? new AbortController() : null;
            lastElevationAbort = abortController;

            emit("map:elevation:requested", { lat: latlng.lat, lng: latlng.lng });

            return http.postJson(endpoint, { lat: latlng.lat, lng: latlng.lng }, {
                signal: abortController ? abortController.signal : undefined
            }).then(function (result) {
                var response = result ? result.body : null;
                var cursorLng = coordRound(latlng.lng);
                var cursorLat = coordRound(latlng.lat);

                var elevationValue = response && typeof response.elevation === "number"
                    ? response.elevation
                    : response ? response.Elevation : undefined;
                if (!response || typeof elevationValue !== "number" || !isFinite(elevationValue)) {
                    var errorText = resolveErrorMessage(response, "Elevation unavailable");
                    var suppressElevationMessage = typeof errorText === "string"
                        && errorText.toLowerCase().indexOf("dem not found under run directory") !== -1;

                    if (suppressElevationMessage) {
                        showMouseElevation({
                            elevation: "-",
                            cursor: cursorLng + ", " + cursorLat
                        });
                    } else {
                        var message = errorText || "Elevation unavailable";
                        showMouseElevation({
                            elevation: message,
                            cursor: cursorLng + ", " + cursorLat
                        });
                    }

                    emit("map:elevation:error", {
                        message: errorText || "Elevation unavailable",
                        lat: latlng.lat,
                        lng: latlng.lng
                    });
                    return;
                }

                var elev = elevationValue.toFixed(1);
                showMouseElevation({
                    elevation: elev + " m",
                    cursor: cursorLng + ", " + cursorLat
                });
                emit("map:elevation:loaded", {
                    elevation: elevationValue,
                    lat: latlng.lat,
                    lng: latlng.lng
                });
            }).catch(function (error) {
                if (http.isHttpError && http.isHttpError(error) && error.cause && error.cause.name === "AbortError") {
                    return;
                }
                console.warn("[Map GL] Elevation request failed", error);
                emit("map:elevation:error", {
                    error: error,
                    lat: latlng.lat,
                    lng: latlng.lng
                });
            }).then(function () {
                scheduleElevationCooldown();
            });
        }

        function buildBounds() {
            var center = state.center;
            var zoom = state.zoom;
            if (deckApi && typeof deckApi.WebMercatorViewport === "function") {
                var size = getCanvasSize();
                if (size.width > 0 && size.height > 0) {
                    var viewport = new deckApi.WebMercatorViewport({
                        width: size.width,
                        height: size.height,
                        longitude: center.lng,
                        latitude: center.lat,
                        zoom: zoom,
                        pitch: 0,
                        bearing: 0
                    });
                    var bounds = viewport.getBounds();
                    if (bounds && bounds.length === 4) {
                        return {
                            getSouthWest: function () { return { lat: bounds[1], lng: bounds[0] }; },
                            getNorthEast: function () { return { lat: bounds[3], lng: bounds[2] }; },
                            toBBoxString: function () {
                                return [bounds[0], bounds[1], bounds[2], bounds[3]].join(",");
                            }
                        };
                    }
                }
            }
            return buildBoundsFallback(center, zoom);
        }

        function buildViewportPayload() {
            var center = state.center;
            var bounds = buildBounds();
            return {
                center: { lat: center.lat, lng: center.lng },
                zoom: state.zoom,
                bounds: bounds,
                bbox: bounds.toBBoxString()
            };
        }

        function addDrilldownSuppression(token) {
            if (!drilldownSuppressionTokens) {
                return;
            }
            drilldownSuppressionTokens.add(token || "default");
        }

        function removeDrilldownSuppression(token) {
            if (!drilldownSuppressionTokens) {
                return;
            }
            drilldownSuppressionTokens.delete(token || "default");
        }

        function isDrilldownSuppressed() {
            return drilldownSuppressionTokens ? drilldownSuppressionTokens.size > 0 : false;
        }

        function lockViewState(viewState) {
            if (!viewState || typeof viewState !== "object") {
                return viewState;
            }
            viewState.bearing = 0;
            viewState.pitch = 0;
            return viewState;
        }

        function normalizeViewState(viewState) {
            if (!viewState || typeof viewState !== "object") {
                return null;
            }
            var longitude = Number(viewState.longitude);
            var latitude = Number(viewState.latitude);
            var zoom = Number.isFinite(viewState.zoom) ? Number(viewState.zoom) : state.zoom;
            if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
                return null;
            }
            return lockViewState({
                longitude: longitude,
                latitude: latitude,
                zoom: zoom,
                bearing: 0,
                pitch: 0
            });
        }

        function clampZoom(value) {
            if (!Number.isFinite(value)) {
                return state.zoom;
            }
            return Math.max(MAP_MIN_ZOOM, Math.min(MAP_MAX_ZOOM, value));
        }

        function fitBoundsToViewState(bounds, options) {
            if (!bounds || !deckApi || typeof deckApi.WebMercatorViewport !== "function") {
                return null;
            }
            var sw = bounds.getSouthWest ? bounds.getSouthWest() : null;
            var ne = bounds.getNorthEast ? bounds.getNorthEast() : null;
            if (!sw || !ne) {
                return null;
            }
            var size = getCanvasSize();
            if (!(size.width > 0 && size.height > 0)) {
                return null;
            }
            var padding = options && Number.isFinite(options.padding)
                ? options.padding
                : FLY_TO_BOUNDS_PADDING_PX;
            var viewport = new deckApi.WebMercatorViewport({
                width: size.width,
                height: size.height,
                longitude: state.center.lng,
                latitude: state.center.lat,
                zoom: state.zoom,
                pitch: 0,
                bearing: 0
            });
            if (typeof viewport.fitBounds !== "function") {
                return null;
            }
            var boundsArray = [ [sw.lng, sw.lat], [ne.lng, ne.lat] ];
            var fit = viewport.fitBounds(
                boundsArray,
                { padding: padding }
            );
            var normalized = normalizeViewState(fit);
            if (!normalized) {
                return null;
            }
            normalized.zoom = clampZoom(normalized.zoom);
            return normalized;
        }

        function toViewState(center, zoom) {
            return normalizeViewState({
                longitude: center.lng,
                latitude: center.lat,
                zoom: Number.isFinite(zoom) ? zoom : state.zoom
            });
        }

        function updateStateFromViewState(viewState) {
            state.center = { lat: viewState.latitude, lng: viewState.longitude };
            state.zoom = viewState.zoom;
        }

        function fireMapHandlers(eventName) {
            if (!eventName || !mapHandlers[eventName]) {
                return;
            }
            mapHandlers[eventName].forEach(function (handler) {
                try {
                    handler({ target: map });
                } catch (err) {
                    console.warn("Map GL handler failed for " + eventName, err);
                }
            });
        }

        function fireClickHandlers(latlng, info) {
            if (!latlng || !mapHandlers.click) {
                return;
            }
            mapHandlers.click.forEach(function (handler) {
                try {
                    handler({
                        target: map,
                        latlng: latlng,
                        info: info || null,
                        originalEvent: info && info.srcEvent ? info.srcEvent : null
                    });
                } catch (err) {
                    console.warn("Map GL handler failed for click", err);
                }
            });
        }

        function notifyViewChange(isFinal) {
            updateMapStatus();
            fireMapHandlers("move");
            fireMapHandlers("zoom");
            if (isFinal) {
                fireMapHandlers("moveend");
                fireMapHandlers("zoomend");
                emit("map:center:changed", buildViewportPayload());
            }
        }

        function applyViewState(nextViewState, options) {
            var normalized = normalizeViewState(nextViewState);
            if (!normalized) {
                return;
            }
            var viewState = normalized;
            var transition = options && options.transition ? options.transition : null;
            if (transition) {
                viewState = Object.assign({}, normalized);
                if (Number.isFinite(transition.duration)) {
                    viewState.transitionDuration = transition.duration;
                }
                if (transition.interpolator) {
                    viewState.transitionInterpolator = transition.interpolator;
                }
                if (transition.easing) {
                    viewState.transitionEasing = transition.easing;
                }
            }
            lockViewState(viewState);
            updateStateFromViewState(normalized);
            if (deckgl && !(options && options.skipDeck)) {
                var size = getCanvasSize();
                if (!isApplyingViewState) {
                    isApplyingViewState = true;
                    deckgl.setProps({
                        viewState: viewState,
                        width: size.width || undefined,
                        height: size.height || undefined
                    });
                    isApplyingViewState = false;
                }
            }
            notifyViewChange(Boolean(options && options.final));
        }

        function resolveBasemap(key) {
            if (!key) {
                return basemapDefs.googleTerrain;
            }
            if (basemapDefs[key]) {
                return basemapDefs[key];
            }
            var lower = String(key).toLowerCase();
            if (lower.indexOf("sat") !== -1) {
                return basemapDefs.googleSatellite;
            }
            if (lower.indexOf("terrain") !== -1) {
                return basemapDefs.googleTerrain;
            }
            return basemapDefs.googleTerrain;
        }

        function buildBasemapUrl(def, x, y, z) {
            var template = def.template;
            var subdomains = def.subdomains || [];
            var subdomain = subdomains.length
                ? subdomains[(x + y + z) % subdomains.length]
                : "";
            return template
                .replace("{s}", subdomain)
                .replace("{x}", x)
                .replace("{y}", y)
                .replace("{z}", z);
        }

        function createBaseLayer(definition) {
            var def = definition || basemapDefs.googleTerrain;
            if (!deckApi || typeof deckApi.TileLayer !== "function" || typeof deckApi.BitmapLayer !== "function") {
                warnNotImplemented("TileLayer/BitmapLayer unavailable");
                return null;
            }
            return new deckApi.TileLayer({
                id: "map-gl-base-" + def.key,
                data: def.template,
                minZoom: 0,
                maxZoom: 19,
                tileSize: 256,
                maxRequests: 8,
                getTileData: async function (params) {
                    var index = params && params.index ? params.index : {};
                    var x = index.x;
                    var y = index.y;
                    var z = index.z;
                    if (![x, y, z].every(Number.isFinite)) {
                        throw new Error("Tile coords missing: x=" + x + " y=" + y + " z=" + z);
                    }
                    var url = buildBasemapUrl(def, x, y, z);
                    var response = await fetch(url, { signal: params.signal, mode: "cors" });
                    if (!response.ok) {
                        throw new Error("Tile fetch failed " + response.status + ": " + url);
                    }
                    var blob = await response.blob();
                    return await createImageBitmap(blob);
                },
                onTileError: function (error) {
                    console.warn("Map GL tile error", error);
                },
                renderSubLayers: function (props) {
                    var tile = props.tile;
                    if (!tile || !props.data || !tile.bbox) {
                        return null;
                    }
                    var west = tile.bbox.west;
                    var south = tile.bbox.south;
                    var east = tile.bbox.east;
                    var north = tile.bbox.north;
                    return new deckApi.BitmapLayer(props, {
                        id: props.id + "-" + tile.id,
                        data: null,
                        image: props.data,
                        bounds: [west, south, east, north],
                        pickable: false,
                        opacity: 1.0
                    });
                }
            });
        }

        function applyLayers() {
            if (!deckgl) {
                return;
            }
            var nextLayers = [];
            if (baseLayer) {
                nextLayers.push(baseLayer);
            }
            if (layerRegistry) {
                var overlayLayers = Array.from(layerRegistry);
                overlayLayers.sort(function (left, right) {
                    var leftName = overlayRegistry ? overlayRegistry.get(left) : null;
                    var rightName = overlayRegistry ? overlayRegistry.get(right) : null;
                    var leftOrder = overlayRenderIndex(leftName);
                    var rightOrder = overlayRenderIndex(rightName);
                    if (leftOrder !== rightOrder) {
                        return leftOrder - rightOrder;
                    }
                    return 0;
                });
                overlayLayers.forEach(function (layer) {
                    nextLayers.push(layer);
                });
            }
            deckgl.setProps({ layers: nextLayers });
        }

        function ensureLayerControl() {
            layerControl = layerControlHelpers.ensureLayerControl({
                layerControl: layerControl,
                mapCanvasElement: mapCanvasElement
            });
            return layerControl;
        }

        function renderBaseLayerControl() {
            var control = ensureLayerControl();
            layerControlHelpers.renderBaseLayerControl({
                control: control,
                map: map,
                baseLayerKey: baseLayerKey
            });
        }

        function syncBaseLayerControlSelection() {
            layerControlHelpers.syncBaseLayerControlSelection({
                control: layerControl,
                baseLayerKey: baseLayerKey
            });
        }

        function overlaySortIndex(name) {
            return layerControlHelpers.overlaySortIndex(name, {
                usgsLayerName: USGS_LAYER_NAME,
                snotelLayerName: SNOTEL_LAYER_NAME,
                sbsLayerName: SBS_LAYER_NAME
            });
        }

        function overlayRenderIndex(name) {
            return layerControlHelpers.overlayRenderIndex(name, {
                usgsLayerName: USGS_LAYER_NAME,
                snotelLayerName: SNOTEL_LAYER_NAME,
                sbsLayerName: SBS_LAYER_NAME
            });
        }

        function rebuildOverlayLayer(name, layer) {
            return layerControlHelpers.rebuildOverlayLayer({
                name: name,
                layer: layer,
                overlayRegistry: overlayRegistry,
                overlayNameRegistry: overlayNameRegistry,
                overlayMaps: map.overlayMaps
            });
        }

        function renderOverlayLayerControl() {
            var control = ensureLayerControl();
            layerControlHelpers.renderOverlayLayerControl({
                control: control,
                map: map,
                overlayNameRegistry: overlayNameRegistry,
                shouldRenderOverlay: shouldRenderOverlay,
                overlaySortIndex: overlaySortIndex,
                rebuildOverlayLayer: rebuildOverlayLayer,
                emit: emit
            });
        }

        function syncOverlayLayerControlSelection() {
            layerControlHelpers.syncOverlayLayerControlSelection({
                control: layerControl,
                overlayNameRegistry: overlayNameRegistry,
                map: map
            });
        }

        var map = {

            events: mapEvents,
            drilldown: createLegacyAdapter(drilldownElement),
            sub_legend: createLegacyAdapter(subLegendElement),
            sbs_legend: createLegacyAdapter(sbsLegendElement),
            mouseelev: createLegacyAdapter(mouseElevationElement),
            centerInput: centerInput || null,
            tabset: createTabset(tabsetRoot),
            ctrls: {
                addOverlay: function (layer, name) {
                    if (!layer || !name || !overlayRegistry || !overlayNameRegistry) {
                        return;
                    }
                    var existing = overlayNameRegistry.get(name);
                    if (existing && existing !== layer) {
                        map.removeLayer(existing);
                        overlayRegistry.delete(existing);
                        overlayNameRegistry.delete(name);
                        if (map.overlayMaps) {
                            delete map.overlayMaps[name];
                        }
                    }
                    overlayRegistry.set(layer, name);
                    overlayNameRegistry.set(name, layer);
                    if (map.overlayMaps) {
                        map.overlayMaps[name] = layer;
                    }
                    renderOverlayLayerControl();
                },
                removeLayer: function (layer) {
                    if (!layer || !overlayRegistry || !overlayNameRegistry) {
                        return;
                    }
                    var name = overlayRegistry.get(layer);
                    if (name) {
                        overlayRegistry.delete(layer);
                        overlayNameRegistry.delete(name);
                        if (map.overlayMaps) {
                            delete map.overlayMaps[name];
                        }
                    }
                    renderOverlayLayerControl();
                }
            },
            boxZoom: {
                disable: function () { return null; },
                enable: function () { return null; }
            },
            on: function (eventName, handler) {
                if (!eventName || typeof handler !== "function") {
                    return;
                }
                mapHandlers[eventName] = mapHandlers[eventName] || [];
                mapHandlers[eventName].push(handler);
            },
            off: function (eventName, handler) {
                if (!eventName || !mapHandlers[eventName]) {
                    return;
                }
                if (!handler) {
                    delete mapHandlers[eventName];
                    return;
                }
                mapHandlers[eventName] = mapHandlers[eventName].filter(function (item) {
                    return item !== handler;
                });
            },
            createPane: function (name) {
                panes[name] = panes[name] || { style: {} };
                return panes[name];
            },
            getPane: function (name) {
                return panes[name] || null;
            },
            getCenter: function () {
                return { lat: state.center.lat, lng: state.center.lng };
            },
            getZoom: function () {
                return state.zoom;
            },
            getBounds: function () {
                return buildBounds();
            },
            distance: function (a, b) {
                return calculateDistanceMeters(a, b);
            },
            setView: function (center, zoom) {
                var normalized = normalizeCenter(center);
                if (!normalized) {
                    return;
                }
                var nextViewState = toViewState(normalized, Number.isFinite(zoom) ? zoom : state.zoom);
                applyViewState(nextViewState, { final: true });
            },
            flyTo: function (center, zoom) {
                var normalized = normalizeCenter(center);
                if (!normalized) {
                    return;
                }
                var targetZoom = Number.isFinite(zoom) ? zoom : state.zoom;
                if (!deckApi || typeof deckApi.FlyToInterpolator !== "function") {
                    map.setView([normalized.lat, normalized.lng], targetZoom);
                    return;
                }
                var nextViewState = toViewState(normalized, targetZoom);
                applyViewState(nextViewState, {
                    final: true,
                    transition: {
                        duration: FLY_TO_DURATION_MS,
                        interpolator: new deckApi.FlyToInterpolator()
                    }
                });
            },
            flyToBounds: function (bounds) {
                if (!bounds) {
                    return;
                }
                var sw = bounds.getSouthWest ? bounds.getSouthWest() : null;
                var ne = bounds.getNorthEast ? bounds.getNorthEast() : null;
                if (!sw || !ne) {
                    return;
                }
                var fitViewState = fitBoundsToViewState(bounds, {
                    padding: FLY_TO_BOUNDS_PADDING_PX
                });
                if (fitViewState) {
                    if (!deckApi || typeof deckApi.FlyToInterpolator !== "function") {
                        applyViewState(fitViewState, { final: true });
                    } else {
                        applyViewState(fitViewState, {
                            final: true,
                            transition: {
                                duration: FLY_TO_DURATION_MS,
                                interpolator: new deckApi.FlyToInterpolator()
                            }
                        });
                    }
                    return;
                }
                var center = {
                    lat: (sw.lat + ne.lat) / 2,
                    lng: (sw.lng + ne.lng) / 2
                };
                map.setView([center.lat, center.lng], state.zoom);
            },
            invalidateSize: function () {
                if (!deckgl) {
                    return null;
                }
                var size = getCanvasSize();
                deckgl.setProps({
                    width: size.width || undefined,
                    height: size.height || undefined
                });
                updateMapStatus();
                return null;
            },
            addLayer: function (layer, options) {
                if (layerRegistry && layer) {
                    layerRegistry.add(layer);
                    applyLayers();
                }
                if (!(options && options.skipRefresh)) {
                    handleOverlayAdded(layer);
                }
                syncOverlayLayerControlSelection();
                return layer;
            },
            removeLayer: function (layer, options) {
                if (layerRegistry && layer) {
                    layerRegistry.delete(layer);
                    applyLayers();
                }
                if (!(options && options.skipOverlay)) {
                    handleOverlayRemoved(layer);
                }
                syncOverlayLayerControlSelection();
                return null;
            },
            hasLayer: function (layer) {
                if (!layerRegistry || !layer) {
                    return false;
                }
                return layerRegistry.has(layer);
            },
            registerOverlay: function (layer, name) {
                map.ctrls.addOverlay(layer, name);
                return layer;
            },
            unregisterOverlay: function (layer) {
                map.ctrls.removeLayer(layer);
            },
            suppressDrilldown: function (token) {
                addDrilldownSuppression(token);
            },
            releaseDrilldown: function (token) {
                removeDrilldownSuppression(token);
            },
            isDrilldownSuppressed: function () {
                return isDrilldownSuppressed();
            },
            addGeoJsonOverlay: function () {
                var options = arguments.length > 0 && arguments[0] ? arguments[0] : {};
                var url = options.url || null;
                if (!url) {
                    console.warn("Map GL: addGeoJsonOverlay called without url");
                    return map;
                }
                var layerName = options.layerName || "Overlay";
                var controller = createRemoteGeoJsonLayer({
                    layerName: layerName,
                    url: url,
                    layerProps: options.layerProps || {},
                    mapKey: options.mapKey || null
                });
                attachLayerRefresh(layerName, controller);
                map.registerOverlay(controller.layer, layerName);
                map.addLayer(controller.layer);
                controller.refresh(url).catch(function (error) {
                    console.warn("Map GL: failed to load overlay", layerName, error);
                });
                return map;
            },
            loadUSGSGageLocations: function () {
                if (!requireMinZoom(SENSOR_LAYER_MIN_ZOOM, USGS_LAYER_NAME)) {
                    return null;
                }
                if (!map.hasLayer(map.usgs_gage) || typeof map.usgs_gage.refresh !== "function") {
                    return null;
                }
                var bbox = map.getBounds().toBBoxString();
                return map.usgs_gage.refresh("/resources/usgs/gage_locations/?&bbox=" + bbox).catch(function (error) {
                    console.warn("Map GL: failed to refresh USGS gage locations", error);
                });
            },
            loadSnotelLocations: function () {
                if (!requireMinZoom(SENSOR_LAYER_MIN_ZOOM, SNOTEL_LAYER_NAME)) {
                    return null;
                }
                if (!map.hasLayer(map.snotel_locations) || typeof map.snotel_locations.refresh !== "function") {
                    return null;
                }
                var bbox = map.getBounds().toBBoxString();
                return map.snotel_locations.refresh("/resources/snotel/snotel_locations/?&bbox=" + bbox).catch(function (error) {
                    console.warn("Map GL: failed to refresh SNOTEL locations", error);
                });
            },
            loadNhdFlowlines: function () {
                if (!requireMinZoom(NHD_LAYER_MIN_ZOOM, NHD_LAYER_NAME)) {
                    return null;
                }
                if (!map.hasLayer(map.nhd_flowlines) || typeof map.nhd_flowlines.refresh !== "function") {
                    return null;
                }
                var bbox = map.getBounds().toBBoxString();
                var url = buildNhdFlowlinesUrl(bbox, map.getZoom());
                if (!url) {
                    return null;
                }
                return map.nhd_flowlines.refresh(url).catch(function (error) {
                    console.warn("Map GL: failed to refresh NHD flowlines", error);
                });
            },
            loadSbsMap: function () {
                if (!map.sbs_layer || !map.hasLayer(map.sbs_layer) || typeof map.sbs_layer.refresh !== "function") {
                    return null;
                }
                var url = resolveRunScopedUrl(SBS_QUERY_ENDPOINT);
                if (!url) {
                    return null;
                }
                return map.sbs_layer.refresh(url).then(function (data) {
                    if (data === undefined) {
                        return data;
                    }
                    return loadSbsLegend().catch(function (error) {
                        console.warn("Map GL: failed to update SBS legend", error);
                    }).then(function () {
                        return data;
                    });
                }).catch(function (error) {
                    clearSbsLegend();
                    console.warn("Map GL: failed to refresh SBS map", error);
                });
            },
            hillQuery: function (queryUrl) {
                if (!queryUrl) {
                    return;
                }
                if (map.isDrilldownSuppressed && map.isDrilldownSuppressed()) {
                    return;
                }
                if (map.tabset && typeof map.tabset.activate === "function") {
                    map.tabset.activate("drilldown", true);
                }
                emit("map:drilldown:requested", { url: queryUrl });
                http.request(queryUrl, {
                    method: "GET",
                    headers: { Accept: "text/html,application/xhtml+xml" }
                }).then(function (result) {
                    var html = typeof result.body === "string" ? result.body : "";
                    if (map.drilldown && typeof map.drilldown.html === "function") {
                        map.drilldown.html(html);
                    } else if (drilldownElement) {
                        drilldownElement.innerHTML = html;
                    }
                    try {
                        if (window.Project && typeof window.Project.getInstance === "function") {
                            window.Project.getInstance().set_preferred_units();
                        }
                    } catch (err) {
                        console.warn("Map GL: failed to set preferred units", err);
                    }
                    emit("map:drilldown:loaded", { url: queryUrl });
                }).catch(function (error) {
                    console.error("Map GL: drilldown request failed", error);
                    emit("map:drilldown:error", { url: queryUrl, error: error });
                });
            },
            subQuery: function () {
                if (arguments.length === 0) {
                    return;
                }
                var topazId = arguments[0];
                if (topazId === undefined || topazId === null) {
                    return;
                }
                var queryUrl = window.url_for_run("report/sub_summary/" + topazId + "/");
                map.hillQuery(queryUrl);
            },
            chnQuery: function (topazId) {
                if (topazId === undefined || topazId === null) {
                    return;
                }
                var queryUrl = window.url_for_run("report/chn_summary/" + topazId + "/");
                map.hillQuery(queryUrl);
            },
            findByTopazId: function () {
                var helper = ensureFindAndFlashHelper();
                if (!helper) {
                    console.warn("Map GL: WEPP_FIND_AND_FLASH helper not available");
                    return null;
                }
                return map.findById(helper.ID_TYPE.TOPAZ, arguments.length ? arguments[0] : undefined);
            },
            findByWeppId: function () {
                var helper = ensureFindAndFlashHelper();
                if (!helper) {
                    console.warn("Map GL: WEPP_FIND_AND_FLASH helper not available");
                    return null;
                }
                return map.findById(helper.ID_TYPE.WEPP, arguments.length ? arguments[0] : undefined);
            },
            clearFindFlashCache: function (type) {
                if (!flashState || !flashState.cache) {
                    return;
                }
                if (!type) {
                    flashState.cache.subcatchments = null;
                    flashState.cache.channels = null;
                    return;
                }
                var normalized = String(type).toLowerCase();
                if (normalized.indexOf("sub") !== -1) {
                    flashState.cache.subcatchments = null;
                }
                if (normalized.indexOf("chn") !== -1 || normalized.indexOf("channel") !== -1) {
                    flashState.cache.channels = null;
                }
            },
            findById: function (idType, value) {
                var helper = ensureFindAndFlashHelper();
                if (!helper || typeof helper.findAndFlashById !== "function") {
                    console.warn("Map GL: WEPP_FIND_AND_FLASH helper not available");
                    return Promise.resolve(null);
                }
                var inputValue = value !== undefined && value !== null
                    ? String(value).trim()
                    : (map.centerInput && map.centerInput.value ? map.centerInput.value.trim() : "");
                if (!inputValue) {
                    return Promise.resolve(null);
                }
                var subCtrl = typeof window.SubcatchmentDelineation !== "undefined"
                    ? window.SubcatchmentDelineation.getInstance()
                    : null;
                var channelCtrl = typeof window.ChannelDelineation !== "undefined"
                    ? window.ChannelDelineation.getInstance()
                    : null;
                return Promise.resolve(helper.findAndFlashById({
                    idType: idType,
                    value: inputValue,
                    map: map,
                    layers: [
                        { ctrl: subCtrl, type: helper.FEATURE_TYPE.SUBCATCHMENT },
                        { ctrl: channelCtrl, type: helper.FEATURE_TYPE.CHANNEL }
                    ],
                    onFlash: function (result) {
                        var topazId = inputValue;
                        if (idType !== helper.ID_TYPE.TOPAZ) {
                            var hit = result.hits && result.hits[0];
                            if (hit && hit.properties && hit.properties.TopazID !== undefined && hit.properties.TopazID !== null) {
                                topazId = hit.properties.TopazID;
                            }
                        }
                        if (result.featureType === helper.FEATURE_TYPE.SUBCATCHMENT) {
                            map.subQuery(topazId);
                        } else if (result.featureType === helper.FEATURE_TYPE.CHANNEL) {
                            map.chnQuery(topazId);
                        }
                    }
                }));
            },
            goToEnteredLocation: function (value) {
                var inputValue = value;
                if (!inputValue && map.centerInput) {
                    inputValue = map.centerInput.value;
                }
                var parsed = parseLocationInput(inputValue);
                if (!parsed) {
                    if (inputValue && String(inputValue).trim()) {
                        var trimmed = String(inputValue).trim();
                        var helper = ensureFindAndFlashHelper();
                        if (helper && typeof map.findByTopazId === "function") {
                            return Promise.resolve(map.findByTopazId(trimmed)).then(function (result) {
                                if (result) {
                                    return result;
                                }
                                if (typeof map.findByWeppId === "function") {
                                    return map.findByWeppId(trimmed);
                                }
                                return null;
                            });
                        }
                        console.warn("Map GL: invalid location input. Expected 'lon, lat[, zoom]'.", inputValue);
                    }
                    return;
                }
                if (!isValidLatLng(parsed.lat, parsed.lng)) {
                    console.warn("Map GL: location out of range. Longitude must be between -180 and 180; latitude between -90 and 90.", {
                        lat: parsed.lat,
                        lng: parsed.lng
                    });
                    return;
                }
                if (parsed.zoom === null) {
                    map.flyTo([parsed.lat, parsed.lng]);
                } else {
                    map.flyTo([parsed.lat, parsed.lng], parsed.zoom);
                }
            },
            onMapChange: function () {
                updateMapStatus();
            },
            fetchElevation: function (ev) {
                if (!ev || !ev.latlng) {
                    return;
                }
                fetchElevation(ev.latlng);
            },
            bootstrap: function (context) {
                var mapContext = context && context.map ? context.map : context || {};
                var center = Array.isArray(mapContext.center) ? mapContext.center : null;
                var zoom = Number.isFinite(mapContext.zoom) ? mapContext.zoom : null;

                if (center && zoom !== null) {
                    map.setView(center, zoom);
                } else if (center) {
                    map.setView(center, state.zoom);
                } else {
                    map.setView([DEFAULT_VIEW.lat, DEFAULT_VIEW.lng], zoom !== null ? zoom : state.zoom);
                }

                if (mapContext && mapContext.boundary) {
                    warnNotImplemented("boundary overlay");
                }

                if (!state.readyEmitted) {
                    emit("map:ready", buildViewportPayload());
                    state.readyEmitted = true;
                }

                var flags = context && context.flags ? context.flags : null;
                if (flags && flags.initialHasSbs !== undefined) {
                    setSbsOverlayAvailability(flags.initialHasSbs);
                }
                if (flags && flags.initialHasSbs === true && map.sbs_layer && !map.hasLayer(map.sbs_layer)) {
                    map.addLayer(map.sbs_layer);
                }

                updateMapStatus();
            }
        };

        var EMPTY_GEOJSON = { type: "FeatureCollection", features: [] };

        function buildGeoJsonLayer(layerId, data, layerProps) {
            ensureGeoJsonLayer();
            var props = Object.assign({}, layerProps || {});
            props.id = layerId;
            props.data = data || EMPTY_GEOJSON;
            return new deckApi.GeoJsonLayer(props);
        }

        function buildBitmapLayer(layerId, image, bounds, opacity) {
            ensureBitmapLayer();
            var hasData = Boolean(image && bounds);
            return new deckApi.BitmapLayer({
                id: layerId,
                image: image || null,
                bounds: bounds || [0, 0, 0, 0],
                opacity: Number.isFinite(opacity) ? opacity : SBS_DEFAULT_OPACITY,
                pickable: false,
                visible: hasData
            });
        }

        function loadImageFromBlob(blob) {
            if (!blob) {
                return Promise.reject(new Error("SBS image payload missing."));
            }
            if (typeof window.Blob === "function" && !(blob instanceof window.Blob)) {
                return Promise.reject(new Error("SBS image response was not a Blob."));
            }
            if (typeof window.createImageBitmap === "function") {
                return window.createImageBitmap(blob);
            }
            if (typeof window.Image !== "function") {
                return Promise.reject(new Error("SBS image loader unavailable."));
            }
            return new Promise(function (resolve, reject) {
                var urlBuilder = window.URL || window.webkitURL;
                if (!urlBuilder || typeof urlBuilder.createObjectURL !== "function") {
                    reject(new Error("SBS image loader unavailable."));
                    return;
                }
                var objectUrl = urlBuilder.createObjectURL(blob);
                var image = new window.Image();
                image.onload = function () {
                    urlBuilder.revokeObjectURL(objectUrl);
                    resolve(image);
                };
                image.onerror = function () {
                    urlBuilder.revokeObjectURL(objectUrl);
                    reject(new Error("Failed to decode SBS image."));
                };
                image.src = objectUrl;
            });
        }

        function fetchSbsImage(url, signal) {
            return http.request(url, { method: "GET", signal: signal }).then(function (result) {
                return loadImageFromBlob(result.body);
            });
        }

        function escapeHtml(value) {
            if (value === null || value === undefined) {
                return "";
            }
            return String(value)
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#39;");
        }

        function buildSbsLegendHtml(items) {
            if (!items || items.length === 0) {
                return "";
            }
            var html = "<div class=\"wc-map-legend__header\">SBS Legend</div>";
            html += "<div class=\"wc-legend\">";
            items.forEach(function (item) {
                html += ""
                    + "<div class=\"wc-legend-item\">"
                    + "<span class=\"wc-legend-item__swatch\" style=\"--legend-color: " + escapeHtml(item.color) + ";\" aria-label=\"Color swatch for " + escapeHtml(item.label) + "\"></span>"
                    + "<span class=\"wc-legend-item__label\">" + escapeHtml(item.label) + " (" + escapeHtml(item.key) + ")</span>"
                    + "</div>";
            });
            html += "</div>";
            return html;
        }

        function loadSbsLegend() {
            if (!sbsLegendElement) {
                return Promise.resolve(null);
            }
            var mode = getSbsColorModeFromToggle();
            if (sbsLayerController && typeof sbsLayerController.getColorMode === "function") {
                mode = sbsLayerController.getColorMode();
            }
            var html = buildSbsLegendHtml(getSbsLegendItemsForMode(mode));
            sbsLegendElement.innerHTML = html;
            attachSbsOpacitySlider(sbsLegendElement);
            dom.show(sbsLegendElement);
            return Promise.resolve(html);
        }

        function clearSbsLegend() {
            if (!sbsLegendElement) {
                return;
            }
            sbsLegendElement.innerHTML = "";
            dom.hide(sbsLegendElement);
        }

        function attachSbsOpacitySlider(legendElement) {
            if (!legendElement || !sbsLayerController) {
                return;
            }
            var existing = legendElement.querySelector("#" + LEGEND_OPACITY_CONTAINER_ID);
            if (existing && existing.parentNode) {
                existing.parentNode.removeChild(existing);
            }

            var container = document.createElement("div");
            container.id = LEGEND_OPACITY_CONTAINER_ID;

            var label = document.createElement("p");
            label.textContent = "SBS Map Opacity";

            var slider = document.createElement("input");
            slider.type = "range";
            slider.id = LEGEND_OPACITY_INPUT_ID;
            slider.min = "0";
            slider.max = "1";
            slider.step = "0.1";
            slider.value = String(sbsLayerController.getOpacity());

            function updateOpacity(event) {
                if (!sbsLayerController) {
                    return;
                }
                var next = clampOpacity(event.target.value);
                sbsLayerController.setOpacity(next);
                emit("baer:map:opacity", { opacity: next });
            }

            slider.addEventListener("input", updateOpacity);
            slider.addEventListener("change", updateOpacity);

            container.appendChild(label);
            container.appendChild(slider);
            legendElement.appendChild(container);
        }

        function createRemoteGeoJsonLayer(options) {
            options = options || {};
            var layerName = options.layerName || "Overlay";
            var layerId = options.layerId || toOverlayId(layerName);
            var layerProps = options.layerProps || {};
            var activeAbort = null;
            var requestToken = 0;
            var currentLayer = buildGeoJsonLayer(layerId, EMPTY_GEOJSON, layerProps);
            var controller = {
                layer: currentLayer,
                refresh: refresh
            };

            function replaceLayer(nextLayer) {
                var label = overlayRegistry && overlayRegistry.get(currentLayer)
                    ? overlayRegistry.get(currentLayer)
                    : layerName;
                var wasVisible = map.hasLayer(currentLayer);
                if (overlayRegistry) {
                    overlayRegistry.delete(currentLayer);
                }
                if (overlayNameRegistry && label) {
                    overlayNameRegistry.delete(label);
                }
                if (map.overlayMaps && label) {
                    delete map.overlayMaps[label];
                }
                if (wasVisible) {
                    map.removeLayer(currentLayer);
                }
                currentLayer = nextLayer;
                controller.layer = currentLayer;
                currentLayer.refresh = controller.refresh;
                if (options.mapKey) {
                    map[options.mapKey] = currentLayer;
                }
                if (label) {
                    if (overlayRegistry) {
                        overlayRegistry.set(currentLayer, label);
                    }
                    if (overlayNameRegistry) {
                        overlayNameRegistry.set(label, currentLayer);
                    }
                    if (map.overlayMaps) {
                        map.overlayMaps[label] = currentLayer;
                    }
                }
                if (wasVisible) {
                    map.addLayer(currentLayer, { skipRefresh: true });
                }
                renderOverlayLayerControl();
            }

            function refresh(urlInput) {
                var url = normalizeUrlPayload(urlInput || options.url);
                if (!url) {
                    return Promise.resolve();
                }
                if (activeAbort && typeof activeAbort.abort === "function") {
                    activeAbort.abort();
                }
                var abortController = typeof AbortController === "function" ? new AbortController() : null;
                activeAbort = abortController;
                requestToken += 1;
                var token = requestToken;

                return http.getJson(url, {
                    signal: abortController ? abortController.signal : undefined
                }).then(function (data) {
                    if (token !== requestToken) {
                        return data;
                    }
                    activeAbort = null;
                    var nextLayer = buildGeoJsonLayer(layerId, data || EMPTY_GEOJSON, layerProps);
                    replaceLayer(nextLayer);
                    return data;
                }).catch(function (error) {
                    activeAbort = null;
                    if (http.isHttpError && http.isHttpError(error) && error.cause && error.cause.name === "AbortError") {
                        return;
                    }
                    throw error;
                });
            }

            currentLayer.refresh = refresh;

            return controller;
        }

        function createSbsLayerController(options) {
            options = options || {};
            var layerName = options.layerName || SBS_LAYER_NAME;
            var layerId = options.layerId || toOverlayId(layerName);
            var activeAbort = null;
            var activeImageAbort = null;
            var requestToken = 0;
            var currentOpacity = clampOpacity(options.opacity);
            var currentColorMode = normalizeSbsColorMode(options.colorMode);
            var currentBounds = null;
            var currentImageStandard = null;
            var currentImageShifted = null;
            var currentLayer = buildBitmapLayer(layerId, null, null, currentOpacity);
            currentLayer.options = { opacity: currentOpacity };
            var controller = {
                layer: currentLayer,
                refresh: refresh,
                setOpacity: setOpacity,
                getOpacity: getOpacity,
                setColorMode: setColorMode,
                getColorMode: getColorMode
            };

            function replaceLayer(nextLayer) {
                var label = overlayRegistry && overlayRegistry.get(currentLayer)
                    ? overlayRegistry.get(currentLayer)
                    : layerName;
                var wasVisible = map.hasLayer(currentLayer);
                if (overlayRegistry) {
                    overlayRegistry.delete(currentLayer);
                }
                if (overlayNameRegistry && label) {
                    overlayNameRegistry.delete(label);
                }
                if (map.overlayMaps && label) {
                    delete map.overlayMaps[label];
                }
                if (wasVisible) {
                    map.removeLayer(currentLayer, { skipOverlay: true });
                }
                currentLayer = nextLayer;
                controller.layer = currentLayer;
                currentLayer.refresh = controller.refresh;
                currentLayer.setOpacity = controller.setOpacity;
                currentLayer.setColorMode = controller.setColorMode;
                currentLayer.getColorMode = controller.getColorMode;
                currentLayer.options = { opacity: currentOpacity };
                if (options.mapKey) {
                    map[options.mapKey] = currentLayer;
                }
                if (label) {
                    if (overlayRegistry) {
                        overlayRegistry.set(currentLayer, label);
                    }
                    if (overlayNameRegistry) {
                        overlayNameRegistry.set(label, currentLayer);
                    }
                    if (map.overlayMaps) {
                        map.overlayMaps[label] = currentLayer;
                    }
                }
                if (wasVisible) {
                    map.addLayer(currentLayer, { skipRefresh: true });
                }
                renderOverlayLayerControl();
            }

            function getOpacity() {
                return currentOpacity;
            }

            function getColorMode() {
                return currentColorMode;
            }

            function resolveDisplayImage() {
                if (currentColorMode !== SBS_COLOR_MODES.SHIFTED) {
                    return currentImageStandard;
                }
                if (currentImageShifted === null && currentImageStandard !== null) {
                    currentImageShifted = buildShiftedSbsImage(currentImageStandard);
                }
                return currentImageShifted || currentImageStandard;
            }

            function setOpacity(next) {
                currentOpacity = clampOpacity(next);
                var nextLayer = buildBitmapLayer(layerId, resolveDisplayImage(), currentBounds, currentOpacity);
                replaceLayer(nextLayer);
            }

            function setColorMode(nextMode) {
                currentColorMode = normalizeSbsColorMode(nextMode);
                var nextLayer = buildBitmapLayer(layerId, resolveDisplayImage(), currentBounds, currentOpacity);
                replaceLayer(nextLayer);
            }

            function refresh(urlInput) {
                var rawUrl = normalizeUrlPayload(urlInput || options.url || SBS_QUERY_ENDPOINT);
                if (!rawUrl) {
                    return Promise.resolve();
                }
                var url = resolveRunScopedUrl(rawUrl);
                if (!url) {
                    return Promise.resolve();
                }
                if (activeAbort && typeof activeAbort.abort === "function") {
                    activeAbort.abort();
                }
                if (activeImageAbort && typeof activeImageAbort.abort === "function") {
                    activeImageAbort.abort();
                }
                var abortController = typeof AbortController === "function" ? new AbortController() : null;
                activeAbort = abortController;
                requestToken += 1;
                var token = requestToken;

                return http.getJson(url, {
                    signal: abortController ? abortController.signal : undefined
                }).then(function (data) {
                    if (token !== requestToken) {
                        return data;
                    }
                    activeAbort = null;
                    if (!data || data.error || data.errors || !data.Content) {
                        var message = resolveErrorMessage(data, "No SBS map has been specified.");
                        var error = new Error(message);
                        error.payload = data;
                        throw error;
                    }
                    var content = data.Content || {};
                    var bounds = normalizeSbsBounds(content.bounds);
                    var imgPath = normalizeUrlPayload(content.imgurl);
                    if (!bounds || !imgPath) {
                        throw new Error("SBS map metadata missing bounds or image URL.");
                    }
                    var imgUrl = isAbsoluteUrl(imgPath) ? imgPath : resolveRunScopedUrl(imgPath);
                    if (!imgUrl) {
                        throw new Error("SBS map image URL unavailable.");
                    }
                    imgUrl = imgUrl + (imgUrl.indexOf("?") === -1 ? "?v=" : "&v=") + Date.now();
                    var imageAbort = typeof AbortController === "function" ? new AbortController() : null;
                    activeImageAbort = imageAbort;
                    return fetchSbsImage(imgUrl, imageAbort ? imageAbort.signal : undefined).then(function (image) {
                        if (token !== requestToken) {
                            return data;
                        }
                        activeImageAbort = null;
                        currentBounds = bounds;
                        currentImageStandard = drawSbsImageToCanvas(image) || image;
                        currentImageShifted = null;
                        var nextLayer = buildBitmapLayer(layerId, resolveDisplayImage(), bounds, currentOpacity);
                        replaceLayer(nextLayer);
                        return data;
                    });
                }).catch(function (error) {
                    activeAbort = null;
                    activeImageAbort = null;
                    if (http.isHttpError && http.isHttpError(error) && error.cause && error.cause.name === "AbortError") {
                        return;
                    }
                    throw error;
                });
            }

            currentLayer.refresh = refresh;
            currentLayer.setOpacity = setOpacity;
            currentLayer.setColorMode = setColorMode;
            currentLayer.getColorMode = getColorMode;

            return controller;
        }

        function attachLayerRefresh(layerName, controller) {
            var baseRefresh = controller.refresh;
            function wrapped(url) {
                return baseRefresh(url).then(function (data) {
                    var layer = controller.layer;
                    emit("map:layer:refreshed", {
                        name: layerName,
                        layer: layer,
                        url: normalizeUrlPayload(url)
                    });
                    return data;
                }).catch(function (error) {
                    var layer = controller.layer;
                    emit("map:layer:error", {
                        name: layerName,
                        layer: layer,
                        url: normalizeUrlPayload(url),
                        error: error
                    });
                    throw error;
                });
            }
            controller.refresh = wrapped;
            if (controller.layer) {
                controller.layer.refresh = wrapped;
            }
            return controller;
        }

        function relabelOverlay(layer, newName) {
            if (!layer || !overlayRegistry || !overlayNameRegistry) {
                return;
            }
            var currentName = overlayRegistry.get(layer);
            if (currentName === newName) {
                return;
            }
            if (currentName) {
                overlayRegistry.delete(layer);
                overlayNameRegistry.delete(currentName);
                if (map.overlayMaps) {
                    delete map.overlayMaps[currentName];
                }
            }
            overlayRegistry.set(layer, newName);
            overlayNameRegistry.set(newName, layer);
            if (map.overlayMaps) {
                map.overlayMaps[newName] = layer;
            }
            renderOverlayLayerControl();
        }

        function updateSnotelOverlayLabel() {
            if (!map.snotel_locations) {
                return;
            }
            var zoom = map.getZoom();
            var label = zoom >= SENSOR_LAYER_MIN_ZOOM
                ? SNOTEL_LAYER_NAME
                : SNOTEL_LAYER_NAME + " (zoom >= " + SENSOR_LAYER_MIN_ZOOM + ")";
            relabelOverlay(map.snotel_locations, label);
        }

        function resolveNhdLabel(zoom) {
            return zoom >= NHD_LAYER_HR_MIN_ZOOM ? "NHDPlus HR Flowlines" : NHD_LAYER_NAME;
        }

        function updateNhdOverlayLabel() {
            if (!map.nhd_flowlines) {
                return;
            }
            var zoom = map.getZoom();
            var baseLabel = resolveNhdLabel(zoom);
            var label = zoom >= NHD_LAYER_MIN_ZOOM
                ? baseLabel
                : baseLabel + " (zoom >= " + NHD_LAYER_MIN_ZOOM + ")";
            relabelOverlay(map.nhd_flowlines, label);
        }

        function updateUSGSOverlayLabel() {
            if (!map.usgs_gage) {
                return;
            }
            var zoom = map.getZoom();
            var label = zoom >= SENSOR_LAYER_MIN_ZOOM
                ? USGS_LAYER_NAME
                : USGS_LAYER_NAME + " (zoom >= " + SENSOR_LAYER_MIN_ZOOM + ")";
            relabelOverlay(map.usgs_gage, label);
        }

        function requireMinZoom(minZoom, label) {
            var zoom = map.getZoom();
            if (zoom < minZoom) {
                console.info("Map GL: " + label + " requires zoom " + minZoom + "+ (current " + zoom + ").");
                return false;
            }
            return true;
        }

        function handleViewportChange() {
            map.onMapChange();
            updateSnotelOverlayLabel();
            updateUSGSOverlayLabel();
            updateNhdOverlayLabel();
            scheduleOverlayRefresh();
            if (layerControl && typeof layerControl.collapse === "function") {
                layerControl.collapse();
            }
        }

        function handleViewportSettled() {
            if (overlayRefreshTimer) {
                clearTimeout(overlayRefreshTimer);
                overlayRefreshTimer = null;
            }
            map.loadUSGSGageLocations();
            map.loadSnotelLocations();
            map.loadNhdFlowlines();
        }

        function handleOverlayAdded(layer) {
            if (layer === map.usgs_gage) {
                map.loadUSGSGageLocations();
            } else if (layer === map.snotel_locations) {
                map.loadSnotelLocations();
            } else if (layer === map.nhd_flowlines) {
                map.loadNhdFlowlines();
            } else if (layer === map.sbs_layer) {
                map.loadSbsMap();
            }
        }

        function handleOverlayRemoved(layer) {
            if (layer === map.sbs_layer) {
                clearSbsLegend();
            }
        }

        var featureUi = featureUiHelpers.create({
            mapCanvasElement: mapCanvasElement
        });

        function updateHoverTooltip(info) {
            if (!featureUi || typeof featureUi.updateHoverTooltip !== "function") {
                return;
            }
            featureUi.updateHoverTooltip(info);
        }

        function openFeatureModal(feature) {
            if (!featureUi || typeof featureUi.openFeatureModal !== "function") {
                return;
            }
            featureUi.openFeatureModal(feature);
        }

        var overlayRefreshTimer = null;

        function scheduleOverlayRefresh() {
            if (overlayRefreshTimer) {
                clearTimeout(overlayRefreshTimer);
            }
            overlayRefreshTimer = setTimeout(function () {
                overlayRefreshTimer = null;
                handleViewportSettled();
            }, 200);
        }

        map.baseMaps = {
            Terrain: basemapDefs.googleTerrain,
            Satellite: basemapDefs.googleSatellite
        };
        map.overlayMaps = {};

        function createPointLayerProps(strokeHex) {
            var fillColor = hexToRgba(strokeHex, 0.4);
            var strokeColor = hexToRgba(strokeHex, 1);
            return {
                pickable: true,
                stroked: true,
                filled: true,
                pointType: "circle",
                pointRadiusUnits: "pixels",
                pointRadiusMinPixels: 2,
                pointRadiusMaxPixels: 10,
                getPointRadius: function () { return 8; },
                lineWidthUnits: "pixels",
                lineWidthMinPixels: 1,
                getFillColor: function () { return fillColor; },
                getLineColor: function () { return strokeColor; },
                getLineWidth: function () { return 1.5; },
                onHover: updateHoverTooltip,
                onClick: function (info) {
                    if (info && info.object) {
                        openFeatureModal(info.object);
                    }
                }
            };
        }

        var usgsLayerController = createRemoteGeoJsonLayer({
            layerName: USGS_LAYER_NAME,
            layerProps: createPointLayerProps("#ff7800"),
            mapKey: "usgs_gage"
        });
        var snotelLayerController = createRemoteGeoJsonLayer({
            layerName: SNOTEL_LAYER_NAME,
            layerProps: createPointLayerProps("#d6336c"),
            mapKey: "snotel_locations"
        });
        var nhdLayerController = createRemoteGeoJsonLayer({
            layerName: NHD_LAYER_NAME,
            layerProps: {
                pickable: false,
                stroked: true,
                filled: false,
                lineWidthUnits: "pixels",
                lineWidthMinPixels: 1,
                getLineColor: function () { return hexToRgba("#7b2cbf", 0.7); },
                getLineWidth: function () { return 1.5; }
            },
            mapKey: "nhd_flowlines"
        });
        sbsLayerController = createSbsLayerController({
            layerName: SBS_LAYER_NAME,
            mapKey: "sbs_layer",
            opacity: SBS_DEFAULT_OPACITY,
            colorMode: getSbsColorModeFromToggle()
        });

        attachLayerRefresh(USGS_LAYER_NAME, usgsLayerController);
        attachLayerRefresh(SNOTEL_LAYER_NAME, snotelLayerController);
        attachLayerRefresh(NHD_LAYER_NAME, nhdLayerController);
        attachLayerRefresh(SBS_LAYER_NAME, sbsLayerController);

        map.usgs_gage = usgsLayerController.layer;
        map.snotel_locations = snotelLayerController.layer;
        map.nhd_flowlines = nhdLayerController.layer;
        map.sbs_layer = sbsLayerController.layer;

        map.overlayMaps[USGS_LAYER_NAME] = map.usgs_gage;
        map.overlayMaps[SNOTEL_LAYER_NAME] = map.snotel_locations;
        map.overlayMaps[NHD_LAYER_NAME] = map.nhd_flowlines;
        map.overlayMaps[SBS_LAYER_NAME] = map.sbs_layer;

        map.registerOverlay(map.usgs_gage, USGS_LAYER_NAME);
        map.registerOverlay(map.snotel_locations, SNOTEL_LAYER_NAME);
        map.registerOverlay(map.nhd_flowlines, NHD_LAYER_NAME);
        map.registerOverlay(map.sbs_layer, SBS_LAYER_NAME);

        clearSbsLegend();

        map.addLayer(map.nhd_flowlines);
        updateUSGSOverlayLabel();
        updateSnotelOverlayLabel();
        updateNhdOverlayLabel();

        map.on("move", handleViewportChange);
        map.on("zoom", handleViewportChange);
        map.on("moveend", handleViewportSettled);
        map.on("zoomend", handleViewportSettled);

        if (typeof document !== "undefined" && document.addEventListener) {
            document.addEventListener("disturbed:has_sbs_changed", function (event) {
                var detail = event && event.detail ? event.detail : {};
                var hasSbs = detail.hasSbs === true;
                setSbsOverlayAvailability(hasSbs);
                if (hasSbs) {
                    if (map.sbs_layer && !map.hasLayer(map.sbs_layer)) {
                        map.addLayer(map.sbs_layer);
                        return;
                    }
                    map.loadSbsMap();
                } else if (map.sbs_layer && map.hasLayer(map.sbs_layer)) {
                    map.removeLayer(map.sbs_layer);
                } else {
                    clearSbsLegend();
                }
            });
        }

        function bindSbsColorShiftToggle() {
            if (!sbsColorShiftToggleElement || sbsColorShiftToggleElement.dataset.sbsColorShiftBound === "true") {
                return;
            }
            sbsColorShiftToggleElement.dataset.sbsColorShiftBound = "true";
            sbsColorShiftToggleElement.checked = getSbsColorModeFromToggle() === SBS_COLOR_MODES.SHIFTED;
            sbsColorShiftToggleElement.addEventListener("change", function () {
                var mode = getSbsColorModeFromToggle();
                if (sbsLayerController && typeof sbsLayerController.setColorMode === "function") {
                    sbsLayerController.setColorMode(mode);
                }
                if (map.sbs_layer && map.hasLayer(map.sbs_layer)) {
                    loadSbsLegend().catch(function (error) {
                        console.warn("Map GL: failed to update SBS legend after color shift", error);
                    });
                }
            });
        }
        bindSbsColorShiftToggle();

        map.setBaseLayer = function (key) {
            var def = resolveBasemap(key);
            baseLayerKey = def.key;
            baseLayer = createBaseLayer(def);
            applyLayers();
            syncBaseLayerControlSelection();
            emit("map:layer:toggled", {
                name: def.label,
                layer: baseLayer,
                visible: true,
                type: "base"
            });
        };
        setSbsOverlayAvailability(resolveInitialHasSbs());
        renderBaseLayerControl();
        renderOverlayLayerControl();

        if (centerInput && typeof centerInput.addEventListener === "function") {
            centerInput.addEventListener("keydown", function (event) {
                var key = event.key || event.keyCode;
                if (key === "Enter" || key === 13) {
                    event.preventDefault();
                    emit("map:center:requested", {
                        source: "input",
                        query: centerInput.value || ""
                    });
                    map.goToEnteredLocation();
                }
            });
        }

        if (formElement) {
            dom.delegate(formElement, "click", "[data-map-action]", function (event) {
                var action = this.getAttribute("data-map-action");
                if (!action) {
                    return;
                }
                event.preventDefault();
                switch (action) {
                    case "go":
                        emit("map:center:requested", {
                            source: "button",
                            query: centerInput ? centerInput.value : ""
                        });
                        map.goToEnteredLocation();
                        break;
                    case "find-topaz":
                        emit("map:search:requested", {
                            type: "topaz",
                            query: centerInput ? centerInput.value : ""
                        });
                        map.findByTopazId();
                        break;
                    case "find-wepp":
                        emit("map:search:requested", {
                            type: "wepp",
                            query: centerInput ? centerInput.value : ""
                        });
                        map.findByWeppId();
                        break;
                    default:
                        break;
                }
            });
        }

        if (mapCanvasElement && typeof mapCanvasElement.addEventListener === "function") {
            mapCanvasElement.addEventListener("mouseleave", function (event) {
                var related = event ? event.relatedTarget : null;
                if (related && mapCanvasElement.contains && mapCanvasElement.contains(related)) {
                    return;
                }
                hideMouseElevation(MOUSE_ELEVATION_HIDE_DELAY_MS);
                if (lastElevationAbort && typeof lastElevationAbort.abort === "function") {
                    lastElevationAbort.abort();
                }
                lastElevationAbort = null;
                isFetchingElevation = false;
            });
        }

        var initialViewState = normalizeViewState({
            longitude: state.center.lng,
            latitude: state.center.lat,
            zoom: state.zoom
        });

        var size = getCanvasSize();
        baseLayer = createBaseLayer(resolveBasemap(baseLayerKey));
        var widgets = [];
        if (deckApi && typeof deckApi.ZoomWidget === "function") {
            widgets.push(new deckApi.ZoomWidget({
                placement: "top-left",
                orientation: "vertical",
                transitionDuration: 200
            }));
        }
        deckgl = new deckApi.Deck({
            parent: mapCanvasElement,
            controller: {
                dragRotate: false,
                touchRotate: false,
                keyboard: true
            },
            views: deckApi.MapView ? [new deckApi.MapView({ repeat: true })] : undefined,
            initialViewState: initialViewState,
            width: size.width || undefined,
            height: size.height || undefined,
            layers: baseLayer ? [baseLayer] : [],
            widgets: widgets,
            onHover: function (info) {
                handleDeckHover(info);
            },
            onClick: function (info) {
                if (!info || !info.coordinate || info.coordinate.length < 2) {
                    return;
                }
                var lng = Number(info.coordinate[0]);
                var lat = Number(info.coordinate[1]);
                if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
                    return;
                }
                fireClickHandlers({ lat: lat, lng: lng }, info);
            },
            onViewStateChange: function (params) {
                var viewState = params && params.viewState ? params.viewState : null;
                if (!viewState) {
                    return;
                }
                if (isApplyingViewState) {
                    return;
                }
                var interaction = params && params.interactionState ? params.interactionState : null;
                var isFinal = !interaction || (!interaction.isDragging && !interaction.isZooming && !interaction.isPanning && !interaction.inTransition);
                applyViewState(viewState, { final: isFinal });
            },
            onError: function (error) {
                console.warn("Map GL deck error", error);
            }
        });
        map._deck = deckgl;

        if (typeof ResizeObserver !== "undefined" && mapCanvasElement) {
            var resizeObserver = new ResizeObserver(function () {
                if (deckgl) {
                    var size = getCanvasSize();
                    deckgl.setProps({
                        width: size.width || undefined,
                        height: size.height || undefined
                    });
                    updateMapStatus();
                }
            });
            resizeObserver.observe(mapCanvasElement);
        }

        updateMapStatus();
        return map;
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

window.MapController = MapController;
window.WeppMap = MapController;
