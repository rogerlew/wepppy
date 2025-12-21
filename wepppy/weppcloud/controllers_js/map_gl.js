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
        "map:layer:error"
    ];

    var DEFAULT_VIEW = { lat: 44.0, lng: -116.0, zoom: 6 };

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
        var events = helpers.events;
        var deckApi = window.deck;
        var coordRound = (typeof window.coordRound === "function")
            ? window.coordRound
            : function (value) { return Math.round(value * 1000) / 1000; };

        ensureDeck();

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

        function emit(eventName, payload) {
            if (mapEvents && typeof mapEvents.emit === "function") {
                mapEvents.emit(eventName, payload || {});
            }
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
            updateStateFromViewState(normalized);
            if (deckgl && !(options && options.skipDeck)) {
                var size = getCanvasSize();
                if (!isApplyingViewState) {
                    isApplyingViewState = true;
                    deckgl.setProps({
                        viewState: normalized,
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
                layerRegistry.forEach(function (layer) {
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

            toggle.addEventListener("click", function () {
                var expanded = toggle.getAttribute("aria-expanded") === "true";
                setExpanded(!expanded);
            });

            root.addEventListener("keydown", function (event) {
                if (event.key === "Escape") {
                    setExpanded(false);
                }
            });

            layerControl = {
                root: root,
                toggle: toggle,
                panel: panel,
                baseSection: baseSection,
                baseList: baseList,
                overlaySection: overlaySection,
                overlayList: overlayList,
                overlayInputs: typeof Map === "function" ? new Map() : null
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

        function renderOverlayLayerControl() {
            var control = ensureLayerControl();
            if (!control || !overlayNameRegistry) {
                return;
            }
            control.overlayList.textContent = "";
            if (control.overlayInputs && typeof control.overlayInputs.clear === "function") {
                control.overlayInputs.clear();
            }
            var entries = Array.from(overlayNameRegistry.entries());
            if (!entries.length) {
                control.overlaySection.hidden = true;
                return;
            }
            control.overlaySection.hidden = false;
            entries.forEach(function (entry, index) {
                var name = entry[0];
                var layer = entry[1];
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
                    if (input.checked) {
                        map.addLayer(layer);
                    } else {
                        map.removeLayer(layer);
                    }
                    emit("map:layer:toggled", {
                        name: name,
                        layer: layer,
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
                map.setView(center, zoom);
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
            addLayer: function (layer) {
                if (layerRegistry && layer) {
                    layerRegistry.add(layer);
                    applyLayers();
                }
                syncOverlayLayerControlSelection();
                return layer;
            },
            removeLayer: function (layer) {
                if (layerRegistry && layer) {
                    layerRegistry.delete(layer);
                    applyLayers();
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
                warnNotImplemented("addGeoJsonOverlay");
                return null;
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
                    warnNotImplemented("goToEnteredLocation: unable to parse input");
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

                updateMapStatus();
            }
        };

        map.baseMaps = {
            Terrain: basemapDefs.googleTerrain,
            Satellite: basemapDefs.googleSatellite
        };
        map.overlayMaps = {};
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
