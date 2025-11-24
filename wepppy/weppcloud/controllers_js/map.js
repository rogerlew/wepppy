/* ----------------------------------------------------------------------------
 * Map
 * Doc: controllers_js/README.md — Map Controller Reference (2025 helper migration)
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
        "map:layer:error"
    ];

    var DEFAULT_ELEVATION_COOLDOWN_MS = 400;

    function ensureHelpers() {
        var dom = window.WCDom;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.qs !== "function" || typeof dom.delegate !== "function" ||
            typeof dom.show !== "function" || typeof dom.hide !== "function" || typeof dom.setText !== "function") {
            throw new Error("Map controller requires WCDom helpers.");
        }
        if (!http || typeof http.postJson !== "function" || typeof http.getJson !== "function" || typeof http.request !== "function") {
            throw new Error("Map controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Map controller requires WCEvents helpers.");
        }

        return { dom: dom, http: http, events: events };
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
        var sanitized = String(value).replace(/[a-zA-Z{}\[\]\\|\/<>;:]/g, "");
        return sanitized.split(/[\s,]+/).filter(function (item) {
            return item !== "";
        });
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

    function createRemoteGeoJsonLayer(http, options) {
        options = options || {};
        var layer = L.geoJSON(null, {
            style: options.style || null,
            onEachFeature: options.onEachFeature,
            pointToLayer: options.pointToLayer
        });

        var activeAbort = null;

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

            return http.getJson(url, {
                signal: abortController ? abortController.signal : undefined
            }).then(function (data) {
                layer.clearLayers();
                if (data) {
                    layer.addData(data);
                }
                activeAbort = null;
                return data;
            }).catch(function (error) {
                activeAbort = null;
                if (http.isHttpError && http.isHttpError(error) && error.cause && error.cause.name === "AbortError") {
                    return;
                }
                throw error;
            });
        }

        layer.refresh = refresh;

        return {
            layer: layer,
            refresh: refresh
        };
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var http = helpers.http;
        var events = helpers.events;

        var map = L.map("mapid", {
            zoomSnap: 0.5,
            zoomDelta: 0.5
        });

        map.scrollWheelZoom.disable();

        map.createPane("subcatchmentsGlPane");
        map.getPane("subcatchmentsGlPane").style.zIndex = 600;

        map.createPane("channelGlPane");
        map.getPane("channelGlPane").style.zIndex = 650;

        map.createPane("markerCustomPane");
        map.getPane("markerCustomPane").style.zIndex = 700;

        var emitterBase = events.createEmitter();
        var mapEvents = typeof events.useEventMap === "function"
            ? events.useEventMap(EVENT_NAMES, emitterBase)
            : emitterBase;
        map.events = mapEvents;

        var formElement = dom.qs("#setloc_form");
        var centerInput = dom.qs("#input_centerloc", formElement);
        var mapCanvasElement = dom.qs("#mapid");
        var drilldownElement = dom.qs("#drilldown");
        var subLegendElement = dom.qs("#sub_legend");
        var sbsLegendElement = dom.qs("#sbs_legend");
        var mapStatusElement = dom.qs("#mapstatus");
        var mouseElevationElement = dom.qs("#mouseelev");
        var tabsetRoot = dom.qs("#setloc_form [data-tabset]");

        map.drilldown = createLegacyAdapter(drilldownElement);
        map.sub_legend = createLegacyAdapter(subLegendElement);
        map.sbs_legend = createLegacyAdapter(sbsLegendElement);
        map.mouseelev = createLegacyAdapter(mouseElevationElement);
        map.centerInput = centerInput || null;
        map.tabset = createTabset(tabsetRoot);

    var overlayRegistry = typeof Map === "function" ? new Map() : null;
    var overlayNameRegistry = typeof Map === "function" ? new Map() : null;
        var elevationCooldownTimer = null;
        var mouseElevationHideTimer = null;
        var isFetchingElevation = false;
        var lastElevationAbort = null;
        var drilldownSuppressionTokens = typeof Set === "function" ? new Set() : null;

        function addDrilldownSuppression(token) {
            if (!drilldownSuppressionTokens) {
                return;
            }
            var key = token || "default";
            drilldownSuppressionTokens.add(key);
        }

        function removeDrilldownSuppression(token) {
            if (!drilldownSuppressionTokens) {
                return;
            }
            var key = token || "default";
            drilldownSuppressionTokens.delete(key);
        }

        function isDrilldownSuppressed() {
            return drilldownSuppressionTokens ? drilldownSuppressionTokens.size > 0 : false;
        }

        var encodedRunId = (typeof runid !== "undefined" && runid !== null) ? encodeURIComponent(runid) : null;
        var encodedConfig = (typeof config !== "undefined" && config !== null) ? encodeURIComponent(config) : null;
        var elevationEndpoint = (encodedRunId && encodedConfig) ? "/runs/" + encodedRunId + "/" + encodedConfig + "/elevationquery/" : null;

        function emit(eventName, payload) {
            if (mapEvents && typeof mapEvents.emit === "function") {
                mapEvents.emit(eventName, payload || {});
            }
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

        function updateMapStatus() {
            if (!mapStatusElement) {
                return;
            }
            try {
                var center = map.getCenter();
                var lng = coordRound(center.lng);
                var lat = coordRound(center.lat);
                var zoom = map.getZoom();
                var width = mapCanvasElement ? Math.round(mapCanvasElement.offsetWidth || 0) : 0;
                dom.setText(mapStatusElement, "Center: " + lng + ", " + lat + " | Zoom: " + zoom + " ( Map Width:" + width + "px )");
            } catch (error) {
                // Map not initialized yet - skip status update
                dom.setText(mapStatusElement, "Map initializing...");
            }
        }

        function buildViewportPayload() {
            try {
                var center = map.getCenter();
                var bounds = map.getBounds();
                return {
                    center: { lat: center.lat, lng: center.lng },
                    zoom: map.getZoom(),
                    bounds: bounds,
                    bbox: bounds ? bounds.toBBoxString() : null
                };
            } catch (error) {
                return {
                    center: { lat: 0, lng: 0 },
                    zoom: 0,
                    bounds: null,
                    bbox: null
                };
            }
        }

        function handleCenterInputKey(event) {
            if (!event) {
                return;
            }
            var key = event.key || event.keyCode;
            if (key === "Enter" || key === 13) {
                event.preventDefault();
                emit("map:center:requested", {
                    source: "input",
                    query: centerInput ? centerInput.value : ""
                });
                map.goToEnteredLocation();
            }
        }

        if (centerInput && typeof centerInput.addEventListener === "function") {
            centerInput.addEventListener("keydown", handleCenterInputKey);
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

        function scheduleElevationCooldown() {
            if (elevationCooldownTimer) {
                clearTimeout(elevationCooldownTimer);
            }
            elevationCooldownTimer = window.setTimeout(function () {
                isFetchingElevation = false;
            }, DEFAULT_ELEVATION_COOLDOWN_MS);
            map.fetchTimer = elevationCooldownTimer;
        }

        function fetchElevation(latlng) {
            if (!elevationEndpoint) {
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

            return http.postJson(elevationEndpoint, { lat: latlng.lat, lng: latlng.lng }, {
                signal: abortController ? abortController.signal : undefined
            }).then(function (result) {
                var response = result ? result.body : null;
                var cursorLng = coordRound(latlng.lng);
                var cursorLat = coordRound(latlng.lat);

                if (!response || typeof response.Elevation !== "number" || !isFinite(response.Elevation)) {
                    var message = response && response.Error ? response.Error : "Elevation unavailable";
                    showMouseElevation("| Elevation: " + message + " | Cursor: " + cursorLng + ", " + cursorLat);
                    emit("map:elevation:error", {
                        message: message,
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
                console.warn("[Map] Elevation request failed", error);
                emit("map:elevation:error", {
                    error: error,
                    lat: latlng.lat,
                    lng: latlng.lng
                });
            }).then(function () {
                scheduleElevationCooldown();
            });
        }

        map.fetchElevation = function (ev) {
            if (!ev || !ev.latlng) {
                return;
            }
            fetchElevation(ev.latlng);
        };

        map.on("mousemove", function (ev) {
            if (!ev || !ev.latlng) {
                return;
            }
            if (!isFetchingElevation) {
                fetchElevation(ev.latlng);
            }
        });

        map.on("mouseout", function () {
            hideMouseElevation(2000);
            if (lastElevationAbort && typeof lastElevationAbort.abort === "function") {
                lastElevationAbort.abort();
            }
            lastElevationAbort = null;
            isFetchingElevation = false;
        });

        function createCircleLayerOptions(fillColor) {
            return function (feature, latlng) {
                return L.circleMarker(latlng, {
                    radius: 8,
                    fillColor: fillColor,
                    color: "#000",
                    weight: 1,
                    opacity: 1,
                    fillOpacity: 0.8
                });
            };
        }

        function bindDescription(feature, layer) {
            if (feature.properties && feature.properties.Description) {
                layer.bindPopup(feature.properties.Description, { autoPan: false });
            }
        }

        var usgsLayerController = createRemoteGeoJsonLayer(http, {
            layerName: "USGS Gage Locations",
            onEachFeature: bindDescription,
            pointToLayer: createCircleLayerOptions("#ff7800")
        });

        var snotelLayerController = createRemoteGeoJsonLayer(http, {
            layerName: "SNOTEL Locations",
            onEachFeature: bindDescription,
            pointToLayer: createCircleLayerOptions("#000078")
        });

        function attachLayerRefresh(layerName, controller) {
            var baseRefresh = controller.refresh;
            var layer = controller.layer;
            function wrapped(url) {
                return baseRefresh(url).then(function (data) {
                    emit("map:layer:refreshed", {
                        name: layerName,
                        layer: layer,
                        url: normalizeUrlPayload(url)
                    });
                    return data;
                }).catch(function (error) {
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
            if (layer) {
                layer.refresh = wrapped;
            }
            return controller;
        }

        attachLayerRefresh("USGS Gage Locations", usgsLayerController);
        attachLayerRefresh("SNOTEL Locations", snotelLayerController);

        map.usgs_gage = usgsLayerController.layer;
        map.snotel_locations = snotelLayerController.layer;

        map.googleTerrain = L.tileLayer("https://{s}.google.com/vt/lyrs=p&x={x}&y={y}&z={z}", {
            maxZoom: 20,
            subdomains: ["mt0", "mt1", "mt2", "mt3"]
        });

        map.googleSat = L.tileLayer("https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}", {
            maxZoom: 20,
            subdomains: ["mt0", "mt1", "mt2", "mt3"]
        });

        var DARK_THEME_SLUGS = new Set([
            "onedark",
            "ayu-dark",
            "ayu-dark-bordered",
            "ayu-mirage",
            "ayu-mirage-bordered",
            "cursor-dark-anysphere",
            "cursor-dark-midnight",
            "cursor-dark-high-contrast"
        ]);

        function isDarkTheme(theme) {
            if (!theme || theme === "default") {
                return false;
            }
            if (DARK_THEME_SLUGS.has(theme)) {
                return true;
            }
            var lower = theme.toLowerCase();
            return lower.indexOf("dark") !== -1 || lower.indexOf("midnight") !== -1 || lower.indexOf("mirage") !== -1;
        }

        function getCurrentTheme() {
            var root = window.document && window.document.documentElement;
            if (!root) {
                return "default";
            }
            return root.getAttribute("data-theme") || "default";
        }

        function syncMapTheme(theme) {
            var container = map.getContainer();
            if (!container) {
                return;
            }
            var dark = isDarkTheme(theme);
            container.classList.toggle("wc-map--invert-base", dark);
        }

        map.baseMaps = {
            "Satellite": map.googleSat,
            "Terrain": map.googleTerrain
        };

        map.overlayMaps = {
            "USGS Gage Locations": map.usgs_gage,
            "SNOTEL Locations": map.snotel_locations
        };

        // Default to Terrain base layer instead of Satellite
        map.googleTerrain.addTo(map);
        syncMapTheme(getCurrentTheme());

        map.ctrls = L.control.layers(map.baseMaps, map.overlayMaps);
        map.ctrls.addTo(map);

        function clearOverlayName(layer) {
            if (!overlayNameRegistry) {
                return;
            }
            overlayNameRegistry.forEach(function (value, key) {
                if (value === layer) {
                    overlayNameRegistry.delete(key);
                }
            });
        }

        function registerOverlay(layer, name) {
            if (!layer || !name || !map.ctrls || typeof map.ctrls.addOverlay !== "function") {
                return;
            }
            var existing = overlayNameRegistry && overlayNameRegistry.get ? overlayNameRegistry.get(name) : null;
            if (existing && existing !== layer) {
                try {
                    map.ctrls.removeLayer(existing);
                } catch (err) {
                    console.warn("[Map] Failed to remove existing overlay control entry", name, err);
                }
                try {
                    map.removeLayer(existing);
                } catch (err) {
                    console.warn("[Map] Failed to remove existing overlay from map", name, err);
                }
                if (existing && typeof existing.remove === "function") {
                    try {
                        existing.remove();
                    } catch (err) {
                        // ignore
                    }
                }
                if (overlayRegistry && overlayRegistry.delete) {
                    overlayRegistry.delete(existing);
                }
                clearOverlayName(existing);
            }
            map.ctrls.addOverlay(layer, name);
            if (overlayRegistry) {
                overlayRegistry.set(layer, name);
            }
            if (overlayNameRegistry) {
                overlayNameRegistry.set(name, layer);
            }
        }

        function unregisterOverlay(layer) {
            if (!layer || !map.ctrls || typeof map.ctrls.removeLayer !== "function") {
                return;
            }
            try {
                map.ctrls.removeLayer(layer);
            } catch (err) {
                console.warn("[Map] Failed to remove overlay from control", err);
            }
            if (overlayRegistry) {
                overlayRegistry.delete(layer);
            }
            clearOverlayName(layer);
        }

        map.registerOverlay = registerOverlay;
        map.unregisterOverlay = unregisterOverlay;

        window.document.addEventListener("wc-theme:change", function (event) {
            var theme = event && event.detail && event.detail.theme ? event.detail.theme : "default";
            syncMapTheme(theme);
        });

        if (overlayRegistry) {
            overlayRegistry.set(map.usgs_gage, "USGS Gage Locations");
            overlayRegistry.set(map.snotel_locations, "SNOTEL Locations");
        }
        if (overlayNameRegistry) {
            overlayNameRegistry.set("USGS Gage Locations", map.usgs_gage);
            overlayNameRegistry.set("SNOTEL Locations", map.snotel_locations);
        }

        map.addGeoJsonOverlay = function (options) {
            options = options || {};
            var url = options.url || null;
            if (!url) {
                console.warn("[Map] addGeoJsonOverlay called without url");
                return map;
            }
            var layerName = options.layerName || "Overlay";
            var controller = createRemoteGeoJsonLayer(http, options);
            attachLayerRefresh(layerName, controller);
            controller.layer.addTo(map);
            registerOverlay(controller.layer, layerName);
            controller.refresh(url).catch(function (error) {
                console.warn("[Map] Failed to load overlay", layerName, error);
            });
            return map;
        };

        function handleViewportChange() {
            map.onMapChange();
            if (typeof ChannelDelineation !== "undefined" && ChannelDelineation !== null) {
                try {
                    ChannelDelineation.getInstance().onMapChange();
                } catch (err) {
                    console.warn("ChannelDelineation.onMapChange failed", err);
                }
            }
        }

        function handleViewportSettled() {
            emit("map:center:changed", buildViewportPayload());
            map.loadUSGSGageLocations();
            map.loadSnotelLocations();
        }

        map.on("zoom", handleViewportChange);
        map.on("move", handleViewportChange);
        map.on("zoomend", handleViewportSettled);
        map.on("moveend", handleViewportSettled);

        map.onMapChange = function () {
            updateMapStatus();
        };

        map.hillQuery = function (queryUrl) {
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
                    Project.getInstance().set_preferred_units();
                } catch (err) {
                    console.warn("[Map] Failed to set preferred units", err);
                }
                emit("map:drilldown:loaded", { url: queryUrl });
            }).catch(function (error) {
                console.error("[Map] Drilldown request failed", error);
                emit("map:drilldown:error", { url: queryUrl, error: error });
            });
        };

        map.chnQuery = function (topazId) {
            var queryUrl = url_for_run("report/chn_summary/" + topazId + "/");
            map.hillQuery(queryUrl);
        };

        map.subQuery = function (topazId) {
            var queryUrl = url_for_run("report/sub_summary/" + topazId + "/");
            map.hillQuery(queryUrl);
        };

        map.goToEnteredLocation = function () {
            var value = centerInput ? centerInput.value : "";
            var parts = sanitizeLocationInput(value);
            if (parts.length < 2) {
                return;
            }

            var lon = parseFloat(parts[0]);
            var lat = parseFloat(parts[1]);
            if (!Number.isFinite(lon) || !Number.isFinite(lat)) {
                console.warn("[Map] Invalid location values", parts);
                return;
            }

            var zoom = map.getZoom();
            if (parts.length >= 3) {
                var parsedZoom = parseInt(parts[2], 10);
                if (Number.isFinite(parsedZoom)) {
                    zoom = parsedZoom;
                }
            }

            map.flyTo([lat, lon], zoom);
        };

        map.handleCenterInputKey = function (event) {
            handleCenterInputKey(event);
        };

        map.findById = function (idType) {
            if (!window.WEPP_FIND_AND_FLASH) {
                console.warn("WEPP_FIND_AND_FLASH helper not available");
                return;
            }
            var value = centerInput && centerInput.value ? centerInput.value.trim() : "";
            if (!value) {
                return;
            }
            var subCtrl = typeof SubcatchmentDelineation !== "undefined" ? SubcatchmentDelineation.getInstance() : null;
            var channelCtrl = typeof ChannelDelineation !== "undefined" ? ChannelDelineation.getInstance() : null;

            window.WEPP_FIND_AND_FLASH.findAndFlashById({
                idType: idType,
                value: value,
                map: map,
                layers: [
                    { ctrl: subCtrl, type: window.WEPP_FIND_AND_FLASH.FEATURE_TYPE.SUBCATCHMENT },
                    { ctrl: channelCtrl, type: window.WEPP_FIND_AND_FLASH.FEATURE_TYPE.CHANNEL }
                ],
                onFlash: function (result) {
                    var topazId = value;
                    if (idType !== window.WEPP_FIND_AND_FLASH.ID_TYPE.TOPAZ) {
                        var hit = result.hits && result.hits[0];
                        if (hit && hit.properties && hit.properties.TopazID !== undefined && hit.properties.TopazID !== null) {
                            topazId = hit.properties.TopazID;
                        }
                    }

                    if (result.featureType === window.WEPP_FIND_AND_FLASH.FEATURE_TYPE.SUBCATCHMENT) {
                        map.subQuery(topazId);
                    } else if (result.featureType === window.WEPP_FIND_AND_FLASH.FEATURE_TYPE.CHANNEL) {
                        map.chnQuery(topazId);
                    }
                }
            });
        };

        map.suppressDrilldown = function (token) {
            addDrilldownSuppression(token);
        };

        map.releaseDrilldown = function (token) {
            removeDrilldownSuppression(token);
        };

        map.isDrilldownSuppressed = function () {
            return isDrilldownSuppressed();
        };

        map.findByTopazId = function () {
            map.findById(window.WEPP_FIND_AND_FLASH.ID_TYPE.TOPAZ);
        };

        map.findByWeppId = function () {
            map.findById(window.WEPP_FIND_AND_FLASH.ID_TYPE.WEPP);
        };

        map.loadUSGSGageLocations = function () {
            if (map.getZoom() < 9) {
                return;
            }
            if (!map.hasLayer(map.usgs_gage) || typeof map.usgs_gage.refresh !== "function") {
                return;
            }
            var bbox = map.getBounds().toBBoxString();
            map.usgs_gage.refresh("/resources/usgs/gage_locations/?&bbox=" + bbox).catch(function (error) {
                console.warn("[Map] Failed to refresh USGS gage locations", error);
            });
        };

        map.loadSnotelLocations = function () {
            if (map.getZoom() < 9) {
                return;
            }
            if (!map.hasLayer(map.snotel_locations) || typeof map.snotel_locations.refresh !== "function") {
                return;
            }
            var bbox = map.getBounds().toBBoxString();
            map.snotel_locations.refresh("/resources/snotel/snotel_locations/?&bbox=" + bbox).catch(function (error) {
                console.warn("[Map] Failed to refresh SNOTEL locations", error);
            });
        };

        map.on("overlayadd", function (event) {
            var name = event && event.name ? event.name : (overlayRegistry && overlayRegistry.get ? overlayRegistry.get(event.layer) : null);
            if (overlayRegistry && name && event && event.layer) {
                overlayRegistry.set(event.layer, name);
            }
            if (overlayNameRegistry && name && event && event.layer) {
                overlayNameRegistry.set(name, event.layer);
            }
            emit("map:layer:toggled", {
                name: name,
                layer: event.layer,
                visible: true,
                type: "overlay"
            });
        });

        map.on("overlayremove", function (event) {
            var name = event && event.name ? event.name : (overlayRegistry && overlayRegistry.get ? overlayRegistry.get(event.layer) : null);
            if (overlayRegistry && event && event.layer) {
                overlayRegistry.delete(event.layer);
            }
            if (overlayNameRegistry && event && event.layer) {
                clearOverlayName(event.layer);
            }
            emit("map:layer:toggled", {
                name: name,
                layer: event.layer,
                visible: false,
                type: "overlay"
            });
        });

        map.on("baselayerchange", function (event) {
            emit("map:layer:toggled", {
                name: event && event.name ? event.name : null,
                layer: event && event.layer ? event.layer : null,
                visible: true,
                type: "base"
            });
        });

        setTimeout(function () {
            if (typeof map.invalidateSize === "function") {
                map.invalidateSize();
            }
        }, 0);

        var bootstrapState = {
            resizeObserver: null,
            windowResizeHandler: null,
            boundarySignature: null,
            readyEmitted: false
        };

        map.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var controllerContext = (ctx.controllers && ctx.controllers.map) || {};
            var mapContext = ctx.map && typeof ctx.map === "object" ? ctx.map : controllerContext;

            var center = mapContext && Array.isArray(mapContext.center) ? mapContext.center : null;
            var zoom = mapContext && typeof mapContext.zoom === "number" ? mapContext.zoom : null;

            // Always set a view - Leaflet requires both center and zoom to be initialized
            if (center && zoom !== null) {
                // Both provided - use them
                map.setView(center, zoom);
            } else if (center) {
                // Only center provided - use default zoom
                map.setView(center, 13);
            } else {
                // No center (zoom-only or nothing) - use fallback
                console.warn("Map bootstrap: No center provided in context, using default view [44.0, -116.0], zoom " + (zoom !== null ? zoom : 6));
                map.setView([44.0, -116.0], zoom !== null ? zoom : 6);
            }

            if (typeof map.onMapChange === "function") {
                map.onMapChange();
            }

            if (typeof window.ResizeObserver === "function" && !bootstrapState.resizeObserver) {
                var selector = mapContext && mapContext.containerSelector ? mapContext.containerSelector : ".wc-map";
                var container = selector ? document.querySelector(selector) : null;
                if (container) {
                    var observer = new ResizeObserver(function () {
                        if (typeof map.invalidateSize === "function") {
                            map.invalidateSize();
                        }
                    });
                    observer.observe(container);
                    bootstrapState.resizeObserver = observer;
                }
            }

            if (!bootstrapState.windowResizeHandler) {
                var handler = function () {
                    if (typeof map.invalidateSize === "function") {
                        map.invalidateSize();
                    }
                };
                window.addEventListener("resize", handler);
                bootstrapState.windowResizeHandler = handler;
                setTimeout(handler, 100);
            }

            var boundary = mapContext && mapContext.boundary ? mapContext.boundary : null;
            if (boundary && boundary.url) {
                var style = boundary.style || {};
                var signature = boundary.url + "|" + (boundary.layerName || "") + "|" + JSON.stringify(style);
                if (bootstrapState.boundarySignature !== signature) {
                    map.addGeoJsonOverlay({
                        url: boundary.url,
                        layerName: boundary.layerName,
                        style: style
                    });
                    bootstrapState.boundarySignature = signature;
                }
            }

            if (!bootstrapState.readyEmitted) {
                emit("map:ready", buildViewportPayload());
                bootstrapState.readyEmitted = true;
            }
            updateMapStatus();

            return map;
        };

        // Note: Do NOT emit map:ready here - the bootstrap() method will emit it
        // after properly setting center and zoom. Early emission causes
        // "Set map center and zoom first" errors.
        updateMapStatus();

        return map;
    }

    return {
        getInstance: function getInstance() {
            if (!instance) {
                // Double-check container isn't already initialized before creating
                var mapContainer = document.getElementById("mapid");
                if (mapContainer && mapContainer._leaflet_id) {
                    console.error("MapController.getInstance: Container already initialized but singleton instance is null. This indicates a previous initialization failed partway through.");
                    throw new Error("Map container #mapid is already initialized but instance is missing. Cannot recover - page reload required.");
                }
                instance = createInstance();
            }
            return instance;
        }
    };
}());

window.MapController = MapController;
window.WeppMap = MapController;
