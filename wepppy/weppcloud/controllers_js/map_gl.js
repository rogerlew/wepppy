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

    function buildBounds(center, zoom) {
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
        var drilldownSuppressionTokens = typeof Set === "function" ? new Set() : null;
        var panes = {};
        var mapHandlers = {};

        function emit(eventName, payload) {
            if (mapEvents && typeof mapEvents.emit === "function") {
                mapEvents.emit(eventName, payload || {});
            }
        }

        function warnNotImplemented(action) {
            console.warn("Map GL stub: " + action + " not implemented.");
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

        function buildViewportPayload() {
            var center = state.center;
            var bounds = buildBounds(center, state.zoom);
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
                    overlayRegistry.set(layer, name);
                    overlayNameRegistry.set(name, layer);
                },
                removeLayer: function (layer) {
                    if (!layer || !overlayRegistry || !overlayNameRegistry) {
                        return;
                    }
                    var name = overlayRegistry.get(layer);
                    if (name) {
                        overlayRegistry.delete(layer);
                        overlayNameRegistry.delete(name);
                    }
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
                return buildBounds(state.center, state.zoom);
            },
            distance: function (a, b) {
                return calculateDistanceMeters(a, b);
            },
            setView: function (center, zoom) {
                var normalized = normalizeCenter(center);
                if (normalized) {
                    state.center = normalized;
                }
                if (Number.isFinite(zoom)) {
                    state.zoom = zoom;
                }
                map.onMapChange();
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
            invalidateSize: function () { return null; },
            addLayer: function () { return null; },
            removeLayer: function () { return null; },
            hasLayer: function () { return false; },
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
                emit("map:center:changed", buildViewportPayload());
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
