/* ----------------------------------------------------------------------------
 * Map (Deck.gl scaffolding)
 * Doc: controllers_js/README.md - Map Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var MapController = (function () {
    "use strict";

    var instance;

    var EVENT_NAMES = [
        "map:ready",
        "map:center:requested",
        "map:center:changed",
        "map:search:requested",
        "map:elevation:requested",
        "map:elevation:loaded",
        "map:elevation:error",
        "map:drilldown:requested",
        "map:drilldown:loaded",
        "map:drilldown:error",
        "map:layer:toggled",
        "map:layer:refreshed",
        "map:layer:error",
        "baer:map:opacity"
    ];

    var DEFAULT_VIEW = { lat: 44.0, lng: -116.0, zoom: 6 };
    var FLY_TO_DURATION_MS = 4000;
    var SENSOR_LAYER_MIN_ZOOM = 9;
    var USGS_LAYER_NAME = "USGS Gage Locations";
    var SNOTEL_LAYER_NAME = "SNOTEL Locations";
    var NHD_LAYER_NAME = "NHD Flowlines";
    var NHD_LAYER_MIN_ZOOM = 11;
    var NHD_LAYER_HR_MIN_ZOOM = 14;
    var NHD_SMALL_SCALE_QUERY_URL = "https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer/4/query";
    var NHD_HR_QUERY_URL = "https://hydro.nationalmap.gov/arcgis/rest/services/NHDPlus_HR/MapServer/3/query";
    var SBS_LAYER_NAME = "Burn Severity Map";
    var SBS_QUERY_ENDPOINT = "query/baer_wgs_map/";
    var SBS_LEGEND_ENDPOINT = "resources/legends/sbs/";
    var SBS_DEFAULT_OPACITY = 0.7;
    var LEGEND_OPACITY_CONTAINER_ID = "baer-opacity-controls";
    var LEGEND_OPACITY_INPUT_ID = "baer-opacity-slider";
    var DEFAULT_ELEVATION_COOLDOWN_MS = 200;
    var MOUSE_ELEVATION_HIDE_DELAY_MS = 2000;

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

    function createLegacyAdapter(element) {
        if (!element) {
            return {
                element: element,
                length: 0,
                show: function () { return this; },
                hide: function () { return this; },
                text: function () { return arguments.length === 0 ? "" : this; },
                html: function () { return arguments.length === 0 ? "" : this; },
                append: function () { return this; },
                empty: function () { return this; }
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
                return this;
            },
            hide: function () {
                element.hidden = true;
                if (element.style) {
                    element.style.display = "none";
                }
                return this;
            },
            text: function (value) {
                if (arguments.length === 0) {
                    return element.textContent;
                }
                element.textContent = value === undefined || value === null ? "" : String(value);
                return this;
            },
            html: function (value) {
                if (arguments.length === 0) {
                    return element.innerHTML;
                }
                element.innerHTML = value === undefined || value === null ? "" : String(value);
                return this;
            },
            append: function (content) {
                if (content === undefined || content === null) {
                    return this;
                }
                if (typeof content === "string") {
                    element.insertAdjacentHTML("beforeend", content);
                    return this;
                }
                if (content instanceof window.Node) {
                    element.appendChild(content);
                }
                return this;
            },
            empty: function () {
                element.textContent = "";
                return this;
            }
        };
    }

    function createTabset(root) {
        if (!root) {
            return null;
        }

        var tabs = Array.prototype.slice.call(root.querySelectorAll('[role="tab"]'));
        var panels = Array.prototype.slice.call(root.querySelectorAll('[role="tabpanel"]'));

        if (tabs.length === 0 || panels.length === 0) {
            return null;
        }

        function getTarget(tab) {
            return tab ? tab.getAttribute("data-tab-target") : null;
        }

        function setActive(panelId, focusTab) {
            tabs.forEach(function (tab) {
                var target = getTarget(tab);
                var isActive = target === panelId;
                tab.classList.toggle("is-active", isActive);
                tab.setAttribute("aria-selected", isActive ? "true" : "false");
                tab.setAttribute("tabindex", isActive ? "0" : "-1");
                if (isActive && focusTab) {
                    tab.focus();
                }
            });

            panels.forEach(function (panel) {
                var isActive = panel.id === panelId;
                panel.classList.toggle("is-active", isActive);
                if (isActive) {
                    panel.removeAttribute("hidden");
                } else {
                    panel.setAttribute("hidden", "");
                }
            });

            root.dispatchEvent(new CustomEvent("wc-tabset:change", {
                detail: { panelId: panelId },
                bubbles: true
            }));
        }

        var current = tabs.find(function (tab) {
            return tab.getAttribute("aria-selected") === "true" || tab.classList.contains("is-active");
        });
        var initialPanel = getTarget(current) || getTarget(tabs[0]);
        setActive(initialPanel, false);

        tabs.forEach(function (tab) {
            tab.addEventListener("click", function () {
                setActive(getTarget(tab), false);
            });

            tab.addEventListener("keydown", function (event) {
                var key = event.key;
                if (key !== "ArrowLeft" && key !== "ArrowRight" && key !== "Home" && key !== "End") {
                    return;
                }

                event.preventDefault();
                var currentIndex = tabs.indexOf(tab);
                if (key === "ArrowLeft" || key === "ArrowRight") {
                    var offset = key === "ArrowRight" ? 1 : -1;
                    var nextIndex = (currentIndex + offset + tabs.length) % tabs.length;
                    setActive(getTarget(tabs[nextIndex]), true);
                } else if (key === "Home") {
                    setActive(getTarget(tabs[0]), true);
                } else if (key === "End") {
                    setActive(getTarget(tabs[tabs.length - 1]), true);
                }
            });
        });

        return {
            activate: function (panelId, focusTab) {
                if (!panelId) {
                    return;
                }
                setActive(panelId, focusTab === true);
            }
        };
    }

    function sanitizeLocationInput(value) {
        if (!value) {
            return [];
        }
        var sanitized = String(value).replace(/[a-zA-Z{}\[\]\\|\/<>';:]/g, "");
        return sanitized.split(/[\s,]+/).filter(function (item) {
            return item !== "";
        });
    }

    function parseLocationInput(value) {
        var tokens = sanitizeLocationInput(value);
        if (tokens.length < 2) {
            return null;
        }
        var lng = Number(tokens[0]);
        var lat = Number(tokens[1]);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
            return null;
        }
        var zoom = null;
        if (tokens.length > 2) {
            var parsedZoom = Number(tokens[2]);
            if (Number.isFinite(parsedZoom)) {
                zoom = parsedZoom;
            }
        }
        return { lat: lat, lng: lng, zoom: zoom };
    }

    function normalizeUrlPayload(input) {
        if (!input) {
            return null;
        }
        if (Array.isArray(input)) {
            return input.length ? normalizeUrlPayload(input[0]) : null;
        }
        return String(input);
    }

    function isValidLatLng(lat, lng) {
        return lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180;
    }

    function buildNhdFlowlinesUrl(bbox, zoom) {
        if (!bbox) {
            return null;
        }
        var queryUrl = zoom >= NHD_LAYER_HR_MIN_ZOOM ? NHD_HR_QUERY_URL : NHD_SMALL_SCALE_QUERY_URL;
        return queryUrl
            + "?where=1%3D1"
            + "&outFields=OBJECTID"
            + "&geometry=" + encodeURIComponent(bbox)
            + "&geometryType=esriGeometryEnvelope"
            + "&inSR=4326&outSR=4326"
            + "&spatialRel=esriSpatialRelIntersects"
            + "&returnGeometry=true"
            + "&resultRecordCount=2000"
            + "&f=geojson";
    }

    function toOverlayId(name) {
        var base = String(name || "overlay").toLowerCase();
        var slug = base.replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
        return "map-gl-" + (slug || "overlay");
    }

    function hexToRgba(hex, alpha) {
        if (!hex) {
            return [0, 0, 0, Math.round((alpha === undefined ? 1 : alpha) * 255)];
        }
        var normalized = String(hex).trim().replace("#", "");
        if (normalized.length === 3) {
            normalized = normalized[0] + normalized[0] + normalized[1] + normalized[1] + normalized[2] + normalized[2];
        }
        var intVal = parseInt(normalized, 16);
        if (!Number.isFinite(intVal)) {
            return [0, 0, 0, Math.round((alpha === undefined ? 1 : alpha) * 255)];
        }
        var r = (intVal >> 16) & 255;
        var g = (intVal >> 8) & 255;
        var b = intVal & 255;
        var a = Math.round((alpha === undefined ? 1 : alpha) * 255);
        return [r, g, b, a];
    }

    function isAbsoluteUrl(url) {
        return /^([a-z][a-z\d+\-.]*:)?\/\//i.test(String(url || ""));
    }

    function clampOpacity(value) {
        var parsed = parseFloat(value);
        if (!Number.isFinite(parsed)) {
            return SBS_DEFAULT_OPACITY;
        }
        return Math.max(0, Math.min(1, parsed));
    }

    function normalizeSbsBounds(bounds) {
        if (!Array.isArray(bounds) || bounds.length < 2) {
            return null;
        }
        var sw = bounds[0];
        var ne = bounds[1];
        if (!Array.isArray(sw) || !Array.isArray(ne) || sw.length < 2 || ne.length < 2) {
            return null;
        }
        var south = Number(sw[0]);
        var west = Number(sw[1]);
        var north = Number(ne[0]);
        var east = Number(ne[1]);
        if (![south, west, north, east].every(Number.isFinite)) {
            return null;
        }
        return [west, south, east, north];
    }

    function normalizeCenter(center) {
        if (Array.isArray(center) && center.length >= 2) {
            var lat = Number(center[0]);
            var lng = Number(center[1]);
            if (Number.isFinite(lat) && Number.isFinite(lng)) {
                return { lat: lat, lng: lng };
            }
        }
        if (center && typeof center === "object") {
            var cLat = Number(center.lat);
            var cLng = Number(center.lng);
            if (Number.isFinite(cLat) && Number.isFinite(cLng)) {
                return { lat: cLat, lng: cLng };
            }
        }
        return null;
    }

    function buildBoundsFallback(center, zoom) {
        var lat = center.lat;
        var lng = center.lng;
        var zoomValue = Number.isFinite(zoom) ? zoom : DEFAULT_VIEW.zoom;
        var delta = Math.max(0.05, 1 / Math.max(zoomValue, 1));
        return {
            getSouthWest: function () { return { lat: lat - delta, lng: lng - delta }; },
            getNorthEast: function () { return { lat: lat + delta, lng: lng + delta }; },
            toBBoxString: function () {
                return [lng - delta, lat - delta, lng + delta, lat + delta].join(",");
            }
        };
    }

    function calculateDistanceMeters(a, b) {
        if (!a || !b) {
            return 0;
        }
        var lat1 = Number(a.lat);
        var lat2 = Number(b.lat);
        var lon1 = Number(a.lng);
        var lon2 = Number(b.lng);
        if (!Number.isFinite(lat1) || !Number.isFinite(lat2) || !Number.isFinite(lon1) || !Number.isFinite(lon2)) {
            return 0;
        }
        var toRad = Math.PI / 180;
        var dLat = (lat2 - lat1) * toRad;
        var dLon = (lon2 - lon1) * toRad;
        var sinLat = Math.sin(dLat / 2);
        var sinLon = Math.sin(dLon / 2);
        var aHarv = sinLat * sinLat + Math.cos(lat1 * toRad) * Math.cos(lat2 * toRad) * sinLon * sinLon;
        var cHarv = 2 * Math.atan2(Math.sqrt(aHarv), Math.sqrt(1 - aHarv));
        return 6371000 * cHarv;
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
        var mapStatusElement = dom.qs("#mapstatus");
        var mouseElevationElement = dom.qs("#mouseelev");
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
        var elevationCooldownTimer = null;
        var mouseElevationHideTimer = null;
        var isFetchingElevation = false;
        var lastElevationAbort = null;

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
            if (!mapStatusElement) {
                return;
            }
            var center = state.center;
            var zoom = state.zoom;
            var width = mapCanvasElement ? Math.round(mapCanvasElement.offsetWidth || 0) : 0;
            var lng = coordRound(center.lng);
            var lat = coordRound(center.lat);
            dom.setText(mapStatusElement, "Center: " + lng + ", " + lat + " | Zoom: " + zoom + " ( Map Width:" + width + "px )");
        }

        function showMouseElevation(text) {
            if (!mouseElevationElement) {
                return;
            }
            if (mouseElevationHideTimer) {
                clearTimeout(mouseElevationHideTimer);
                mouseElevationHideTimer = null;
            }
            dom.setText(mouseElevationElement, text);
            dom.show(mouseElevationElement);
        }

        function hideMouseElevation(delayMs) {
            if (!mouseElevationElement) {
                return;
            }
            if (mouseElevationHideTimer) {
                clearTimeout(mouseElevationHideTimer);
            }
            mouseElevationHideTimer = window.setTimeout(function () {
                dom.hide(mouseElevationElement);
            }, typeof delayMs === "number" ? delayMs : 0);
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

                if (!response || typeof response.Elevation !== "number" || !isFinite(response.Elevation)) {
                    var errorText = response && response.Error;
                    var suppressElevationMessage = typeof errorText === "string"
                        && errorText.toLowerCase().indexOf("dem not found under run directory") !== -1;

                    if (!suppressElevationMessage) {
                        var message = errorText || "Elevation unavailable";
                        showMouseElevation("| Elevation: " + message + " | Cursor: " + cursorLng + ", " + cursorLat);
                    } else {
                        hideMouseElevation(0);
                    }

                    emit("map:elevation:error", {
                        message: errorText || "Elevation unavailable",
                        lat: latlng.lat,
                        lng: latlng.lng
                    });
                    return;
                }

                var elev = response.Elevation.toFixed(1);
                showMouseElevation("| Elevation: " + elev + " m | Cursor: " + cursorLng + ", " + cursorLat);
                emit("map:elevation:loaded", {
                    elevation: response.Elevation,
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
            var bearing = Number.isFinite(viewState.bearing) ? Number(viewState.bearing) : 0;
            var pitch = Number.isFinite(viewState.pitch) ? Number(viewState.pitch) : 0;
            return {
                longitude: longitude,
                latitude: latitude,
                zoom: zoom,
                bearing: bearing,
                pitch: pitch
            };
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
            if (layerControl || !mapCanvasElement || typeof document === "undefined") {
                return layerControl;
            }
            var host = mapCanvasElement.closest ? mapCanvasElement.closest(".wc-map") : null;
            if (!host) {
                host = mapCanvasElement.parentElement;
            }
            if (!host) {
                return null;
            }

            var root = document.createElement("div");
            root.className = "wc-map-layer-control";
            root.setAttribute("data-map-layer-control", "true");

            var toggle = document.createElement("button");
            toggle.type = "button";
            toggle.className = "wc-map-layer-control__toggle";
            toggle.setAttribute("aria-expanded", "false");
            toggle.setAttribute("aria-label", "Layers");
            toggle.setAttribute("title", "Layers");
            toggle.innerHTML = '<svg class="wc-map-layer-control__icon" aria-hidden="true" viewBox="0 0 26 26" xmlns="http://www.w3.org/2000/svg" width="26" height="26"><path fill="#b9b9b9" d="m.032 17.056 13-8 13 8-13 8z"/><path fill="#737373" d="m.032 17.056-.032.93 13 8 13-8 .032-.93-13 8z"/><path fill="#cdcdcd" d="m0 13.076 13-8 13 8-13 8z"/><path fill="#737373" d="M0 13.076v.91l13 8 13-8v-.91l-13 8z"/><path fill="#e9e9e9" fill-opacity=".585" stroke="#797979" stroke-width=".1" d="m0 8.986 13-8 13 8-13 8-13-8"/><path fill="#737373" d="M0 8.986v1l13 8 13-8v-1l-13 8z"/></svg><span class="wc-sr-only">Layers</span>';

            var panel = document.createElement("div");
            panel.className = "wc-map-layer-control__panel";
            panel.hidden = true;

            var baseSection = document.createElement("div");
            baseSection.className = "wc-map-layer-control__section";
            var baseTitle = document.createElement("div");
            baseTitle.className = "wc-map-layer-control__title";
            baseTitle.textContent = "Base Layers";
            var baseList = document.createElement("div");
            baseList.className = "wc-map-layer-control__list";
            baseSection.appendChild(baseTitle);
            baseSection.appendChild(baseList);

            var overlaySection = document.createElement("div");
            overlaySection.className = "wc-map-layer-control__section";
            var overlayTitle = document.createElement("div");
            overlayTitle.className = "wc-map-layer-control__title";
            overlayTitle.textContent = "Overlays";
            var overlayList = document.createElement("div");
            overlayList.className = "wc-map-layer-control__list";
            overlaySection.appendChild(overlayTitle);
            overlaySection.appendChild(overlayList);

            panel.appendChild(baseSection);
            panel.appendChild(overlaySection);
            root.appendChild(toggle);
            root.appendChild(panel);
            host.appendChild(root);

            function setExpanded(expanded) {
                if (!layerControl) {
                    return;
                }
                layerControl.toggle.setAttribute("aria-expanded", expanded ? "true" : "false");
                layerControl.root.classList.toggle("is-expanded", expanded);
                layerControl.panel.hidden = !expanded;
            }

            function collapsePanel() {
                setExpanded(false);
            }

            toggle.addEventListener("click", function () {
                var expanded = toggle.getAttribute("aria-expanded") === "true";
                setExpanded(!expanded);
            });

            root.addEventListener("keydown", function (event) {
                if (event.key === "Escape") {
                    setExpanded(false);
                }
            });

            if (mapCanvasElement) {
                mapCanvasElement.addEventListener("pointerdown", collapsePanel);
                mapCanvasElement.addEventListener("wheel", collapsePanel);
            }

            layerControl = {
                root: root,
                toggle: toggle,
                panel: panel,
                baseSection: baseSection,
                baseList: baseList,
                overlaySection: overlaySection,
                overlayList: overlayList,
                overlayInputs: typeof Map === "function" ? new Map() : null,
                collapse: collapsePanel
            };

            return layerControl;
        }

        function renderBaseLayerControl() {
            var control = ensureLayerControl();
            if (!control) {
                return;
            }
            var baseMaps = map.baseMaps || {};
            var names = Object.keys(baseMaps);
            control.baseList.textContent = "";
            if (!names.length) {
                control.baseSection.hidden = true;
                return;
            }
            control.baseSection.hidden = false;
            names.forEach(function (name, index) {
                var def = baseMaps[name];
                var key = def && def.key ? def.key : name;
                var label = def && def.label ? def.label : name;
                var inputId = "wc-map-basemap-" + index;
                var wrapper = document.createElement("label");
                wrapper.className = "wc-map-layer-control__item";
                var input = document.createElement("input");
                input.type = "radio";
                input.name = "wc-map-basemap";
                input.value = key;
                input.id = inputId;
                input.checked = key === baseLayerKey;
                input.addEventListener("change", function () {
                    if (input.checked) {
                        map.setBaseLayer(key);
                    }
                });
                var text = document.createElement("span");
                text.className = "wc-map-layer-control__text";
                text.textContent = label;
                wrapper.appendChild(input);
                wrapper.appendChild(text);
                control.baseList.appendChild(wrapper);
            });
        }

        function syncBaseLayerControlSelection() {
            if (!layerControl) {
                return;
            }
            var inputs = layerControl.baseList.querySelectorAll('input[type="radio"][name="wc-map-basemap"]');
            Array.prototype.forEach.call(inputs, function (input) {
                input.checked = input.value === baseLayerKey;
            });
        }

        function overlaySortIndex(name) {
            if (!name) {
                return 99;
            }
            if (name.indexOf(USGS_LAYER_NAME) !== -1) {
            return 0;
        }
        if (name.indexOf(SNOTEL_LAYER_NAME) !== -1) {
            return 1;
        }
        if (name.indexOf("NHD") !== -1) {
            return 2;
        }
        if (name.indexOf(SBS_LAYER_NAME) !== -1) {
            return 3;
        }
        return 99;
    }

        function overlayRenderIndex(name) {
            if (!name) {
                return 99;
            }
            if (name.indexOf(SBS_LAYER_NAME) !== -1) {
            return -1;
        }
        if (name.indexOf("NHD") !== -1) {
            return 0;
        }
        if (name.indexOf(USGS_LAYER_NAME) !== -1) {
            return 1;
        }
        if (name.indexOf(SNOTEL_LAYER_NAME) !== -1) {
            return 2;
        }
            return 99;
        }

        function rebuildOverlayLayer(name, layer) {
            if (!layer || typeof layer.__wcRebuild !== "function") {
                return layer;
            }
            var nextLayer = layer.__wcRebuild();
            if (!nextLayer || nextLayer === layer) {
                return layer;
            }
            if (overlayRegistry) {
                overlayRegistry.delete(layer);
                overlayRegistry.set(nextLayer, name);
            }
            if (overlayNameRegistry) {
                overlayNameRegistry.set(name, nextLayer);
            }
            if (map.overlayMaps) {
                map.overlayMaps[name] = nextLayer;
            }
            return nextLayer;
        }

        function renderOverlayLayerControl() {
            var control = ensureLayerControl();
            if (!control || !overlayNameRegistry) {
                return;
            }
            control.overlayList.textContent = "";
            if (control.overlayInputs && typeof control.overlayInputs.clear === "function") {
                control.overlayInputs.clear();
            }
            var entries = Array.from(overlayNameRegistry.entries()).map(function (entry, index) {
                return {
                    entry: entry,
                    index: index,
                    order: overlaySortIndex(entry[0])
                };
            });
            if (!entries.length) {
                control.overlaySection.hidden = true;
                return;
            }
            control.overlaySection.hidden = false;
            entries.sort(function (a, b) {
                if (a.order !== b.order) {
                    return a.order - b.order;
                }
                return a.index - b.index;
            });
            entries.forEach(function (item, index) {
                var name = item.entry[0];
                var layer = item.entry[1];
                var inputId = "wc-map-overlay-" + index;
                var wrapper = document.createElement("label");
                wrapper.className = "wc-map-layer-control__item";
                var input = document.createElement("input");
                input.type = "checkbox";
                input.name = "wc-map-overlay";
                input.value = name;
                input.id = inputId;
                input.checked = map.hasLayer(layer);
                input.addEventListener("change", function () {
                    var activeLayer = overlayNameRegistry && overlayNameRegistry.get(name)
                        ? overlayNameRegistry.get(name)
                        : layer;
                    if (input.checked) {
                        activeLayer = rebuildOverlayLayer(name, activeLayer);
                        map.addLayer(activeLayer);
                    } else {
                        map.removeLayer(activeLayer);
                    }
                    emit("map:layer:toggled", {
                        name: name,
                        layer: activeLayer,
                        visible: input.checked,
                        type: "overlay"
                    });
                });
                var text = document.createElement("span");
                text.className = "wc-map-layer-control__text";
                text.textContent = name;
                wrapper.appendChild(input);
                wrapper.appendChild(text);
                control.overlayList.appendChild(wrapper);
                if (control.overlayInputs && typeof control.overlayInputs.set === "function") {
                    control.overlayInputs.set(name, input);
                }
            });
        }

        function syncOverlayLayerControlSelection() {
            if (!layerControl || !overlayNameRegistry || !layerControl.overlayInputs) {
                return;
            }
            layerControl.overlayInputs.forEach(function (input, name) {
                var layer = overlayNameRegistry.get(name);
                if (!layer) {
                    input.disabled = true;
                    return;
                }
                input.disabled = false;
                input.checked = map.hasLayer(layer);
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
            subQuery: function () {
                warnNotImplemented("subQuery");
            },
            chnQuery: function () {
                warnNotImplemented("chnQuery");
            },
            findByTopazId: function () {
                warnNotImplemented("findByTopazId");
            },
            findByWeppId: function () {
                warnNotImplemented("findByWeppId");
            },
            goToEnteredLocation: function (value) {
                var inputValue = value;
                if (!inputValue && map.centerInput) {
                    inputValue = map.centerInput.value;
                }
                var parsed = parseLocationInput(inputValue);
                if (!parsed) {
                    if (inputValue && String(inputValue).trim()) {
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

        function loadSbsLegend() {
            if (!sbsLegendElement) {
                return Promise.resolve(null);
            }
            var legendUrl = resolveRunScopedUrl(SBS_LEGEND_ENDPOINT);
            if (!legendUrl) {
                return Promise.resolve(null);
            }
            return http.request(legendUrl, { method: "GET" }).then(function (result) {
                var content = result.body;
                sbsLegendElement.innerHTML = content === null || content === undefined ? "" : String(content);
                attachSbsOpacitySlider(sbsLegendElement);
                dom.show(sbsLegendElement);
                return content;
            }).catch(function (error) {
                console.warn("Map GL: failed to load SBS legend", error);
                throw error;
            });
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
            var currentBounds = null;
            var currentImage = null;
            var currentLayer = buildBitmapLayer(layerId, null, null, currentOpacity);
            currentLayer.options = { opacity: currentOpacity };
            var controller = {
                layer: currentLayer,
                refresh: refresh,
                setOpacity: setOpacity,
                getOpacity: getOpacity
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

            function setOpacity(next) {
                currentOpacity = clampOpacity(next);
                var nextLayer = buildBitmapLayer(layerId, currentImage, currentBounds, currentOpacity);
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
                    if (!data || data.Success !== true || !data.Content) {
                        var message = data && data.Error ? data.Error : "No SBS map has been specified.";
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
                        currentImage = image;
                        var nextLayer = buildBitmapLayer(layerId, image, bounds, currentOpacity);
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

        function createHoverTooltip() {
            if (typeof document === "undefined") {
                return null;
            }
            var tooltip = document.createElement("div");
            tooltip.className = "wc-map-hover-info";
            tooltip.style.position = "fixed";
            tooltip.style.pointerEvents = "none";
            tooltip.style.zIndex = "1000";
            tooltip.style.padding = "6px 8px";
            tooltip.style.borderRadius = "6px";
            tooltip.style.background = "rgba(10, 10, 10, 0.85)";
            tooltip.style.color = "#f5f5f5";
            tooltip.style.fontSize = "14px";
            tooltip.style.lineHeight = "1.4";
            tooltip.style.maxWidth = "280px";
            tooltip.style.boxShadow = "0 8px 18px rgba(0, 0, 0, 0.25)";
            tooltip.style.display = "none";
            tooltip.style.transform = "translate(-50%, -120%)";
            document.body.appendChild(tooltip);

            return {
                show: function (text, x, y) {
                    tooltip.textContent = text;
                    tooltip.style.left = x + "px";
                    tooltip.style.top = y + "px";
                    tooltip.style.display = "block";
                },
                hide: function () {
                    tooltip.style.display = "none";
                }
            };
        }

        var hoverTooltip = createHoverTooltip();

        function sanitizeInfoHtml(html) {
            if (!html || typeof document === "undefined") {
                return "";
            }
            var container = document.createElement("div");
            container.innerHTML = String(html);

            var blocked = container.querySelectorAll("script, style, iframe, object, embed, link");
            Array.prototype.forEach.call(blocked, function (node) {
                node.remove();
            });

            var nodes = container.querySelectorAll("*");
            Array.prototype.forEach.call(nodes, function (node) {
                if (!node.attributes) {
                    return;
                }
                Array.prototype.slice.call(node.attributes).forEach(function (attr) {
                    var name = attr.name.toLowerCase();
                    var value = String(attr.value || "").toLowerCase();
                    if (name.indexOf("on") === 0) {
                        node.removeAttribute(attr.name);
                        return;
                    }
                    if ((name === "href" || name === "src") && value.indexOf("javascript:") === 0) {
                        node.removeAttribute(attr.name);
                    }
                });
            });

            return container.innerHTML;
        }

        function extractFeatureDescription(feature) {
            if (!feature || !feature.properties) {
                return null;
            }
            if (feature.properties.Description) {
                return String(feature.properties.Description);
            }
            if (feature.properties.description) {
                return String(feature.properties.description);
            }
            return null;
        }

        function extractFeatureName(feature) {
            if (!feature || !feature.properties) {
                return null;
            }
            var props = feature.properties;
            var candidates = [
                "Name",
                "name",
                "StationName",
                "station_name",
                "SiteName",
                "site_name",
                "LocationName",
                "location_name",
                "StationID",
                "station_id",
                "ID",
                "id"
            ];
            for (var i = 0; i < candidates.length; i += 1) {
                var value = props[candidates[i]];
                if (value !== undefined && value !== null) {
                    var text = String(value).trim();
                    if (text) {
                        return text;
                    }
                }
            }
            var description = extractFeatureDescription(feature);
            if (description) {
                var container = document.createElement("div");
                container.innerHTML = description;
                var content = container.textContent || "";
                var firstLine = content.split(/\n+/)[0] || "";
                var trimmed = firstLine.trim();
                if (trimmed) {
                    return trimmed;
                }
            }
            return null;
        }

        function updateHoverTooltip(info) {
            if (!hoverTooltip) {
                return;
            }
            if (!info || !info.object) {
                hoverTooltip.hide();
                return;
            }
            var name = extractFeatureName(info.object);
            if (!name) {
                hoverTooltip.hide();
                return;
            }
            var rect = mapCanvasElement ? mapCanvasElement.getBoundingClientRect() : { left: 0, top: 0 };
            var x = rect.left + (info.x || 0);
            var y = rect.top + (info.y || 0);
            hoverTooltip.show(name, x, y);
        }

        function createFeatureModal() {
            if (typeof document === "undefined") {
                return null;
            }
            var modal = document.createElement("div");
            modal.className = "wc-modal";
            modal.id = "wc-map-feature-modal";
            modal.setAttribute("data-modal", "");
            modal.setAttribute("hidden", "hidden");

            var overlay = document.createElement("div");
            overlay.className = "wc-modal__overlay";
            overlay.setAttribute("data-modal-dismiss", "");

            var dialog = document.createElement("div");
            dialog.className = "wc-modal__dialog";
            dialog.setAttribute("role", "dialog");
            dialog.setAttribute("aria-modal", "true");

            var header = document.createElement("div");
            header.className = "wc-modal__header";

            var title = document.createElement("h2");
            title.className = "wc-modal__title";
            title.textContent = "";

            var close = document.createElement("button");
            close.type = "button";
            close.className = "wc-modal__close";
            close.setAttribute("aria-label", "Close");
            close.setAttribute("data-modal-dismiss", "");
            close.textContent = "×";

            var body = document.createElement("div");
            body.className = "wc-modal__body";

            header.appendChild(title);
            header.appendChild(close);
            dialog.appendChild(header);
            dialog.appendChild(body);
            modal.appendChild(overlay);
            modal.appendChild(dialog);
            document.body.appendChild(modal);

            function openModal() {
                if (window.ModalManager && typeof window.ModalManager.open === "function") {
                    window.ModalManager.open(modal);
                    return;
                }
                modal.removeAttribute("hidden");
                modal.setAttribute("data-modal-open", "true");
                modal.classList.add("is-visible");
                document.body.classList.add("wc-modal-open");
            }

            function closeModal() {
                if (window.ModalManager && typeof window.ModalManager.close === "function") {
                    window.ModalManager.close(modal);
                    return;
                }
                modal.classList.remove("is-visible");
                modal.removeAttribute("data-modal-open");
                modal.setAttribute("hidden", "hidden");
                document.body.classList.remove("wc-modal-open");
            }

            overlay.addEventListener("click", function () {
                closeModal();
            });
            close.addEventListener("click", function () {
                closeModal();
            });

            return {
                show: function (name, html) {
                    title.textContent = name || "Location";
                    if (html) {
                        body.innerHTML = sanitizeInfoHtml(html);
                    } else {
                        body.textContent = "No additional details available.";
                    }
                    openModal();
                },
                hide: function () {
                    closeModal();
                }
            };
        }

        var featureModal = createFeatureModal();

        function openFeatureModal(feature) {
            if (!featureModal) {
                return;
            }
            var name = extractFeatureName(feature) || "Location";
            var description = extractFeatureDescription(feature);
            featureModal.show(name, description);
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
            opacity: SBS_DEFAULT_OPACITY
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
            controller: true,
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
