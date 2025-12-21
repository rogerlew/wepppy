/* ----------------------------------------------------------------------------
 * Outlet (Deck.gl)
 * Doc: controllers_js/README.md — Outlet Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var Outlet = (function () {
    "use strict";

    var instance;

    var EVENT_NAMES = [
        "outlet:mode:change",
        "outlet:cursor:toggle",
        "outlet:set:start",
        "outlet:set:queued",
        "outlet:set:success",
        "outlet:set:error",
        "outlet:display:refresh"
    ];

    var OUTLET_LAYER_NAME = "Outlet";
    var OUTLET_LAYER_ID = "wc-outlet-marker";
    var TEMP_LAYER_ID = "wc-outlet-temp-marker";
    var TEMP_DIALOG_LAYER_ID = "wc-outlet-temp-dialog";
    var TEMP_DIALOG_TEXT = "Setting outlet...";
    var TEMP_COLOR = "#1a73e8";

    function ensureHelpers() {
        var dom = window.WCDom;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function") {
            throw new Error("Outlet GL requires WCDom helpers.");
        }
        if (!http || typeof http.request !== "function" || typeof http.getJson !== "function") {
            throw new Error("Outlet GL requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Outlet GL requires WCEvents helpers.");
        }

        return { dom: dom, http: http, events: events };
    }

    function ensureDeck() {
        var deckApi = window.deck;
        if (!deckApi || typeof deckApi.GeoJsonLayer !== "function") {
            throw new Error("Outlet GL requires deck.gl GeoJsonLayer.");
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

    function parseMode(value, fallback) {
        if (value === undefined || value === null) {
            return fallback;
        }
        if (typeof value === "number" && !Number.isNaN(value)) {
            return value;
        }
        var parsed = parseInt(String(value), 10);
        return Number.isNaN(parsed) ? fallback : parsed;
    }

    function normaliseModeKey(mode) {
        return mode === 1 ? "entry" : "cursor";
    }

    function parseCoordinatesFromEntry(raw) {
        var input = (raw || "").trim();
        if (!input) {
            throw new Error('Enter coordinates as "lon, lat".');
        }

        var parts = input.split(",").map(function (token) {
            return token.trim();
        }).filter(Boolean);

        if (parts.length < 2) {
            parts = input.split(/\s+/).filter(Boolean);
        }
        if (parts.length < 2) {
            throw new Error('Enter coordinates as "lon, lat".');
        }

        var lng = parseFloat(parts[0]);
        var lat = parseFloat(parts[1]);
        if (!Number.isFinite(lng) || !Number.isFinite(lat)) {
            throw new Error("Invalid coordinates.");
        }
        return { lat: lat, lng: lng };
    }

    function ensureLatLng(lat, lng) {
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
            throw new Error("Latitude and longitude must be finite numbers.");
        }
        return { lat: lat, lng: lng };
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

    function buildPointLayer(deckApi, id, latlng, options) {
        var radius = options.radius || 6;
        var strokeWidth = options.strokeWidth || 2;
        var fillColor = options.fillColor || [0, 0, 0, 0];
        var lineColor = options.lineColor || [0, 0, 0, 255];
        return new deckApi.GeoJsonLayer({
            id: id,
            data: {
                type: "FeatureCollection",
                features: [
                    {
                        type: "Feature",
                        properties: options.properties || {},
                        geometry: {
                            type: "Point",
                            coordinates: [latlng.lng, latlng.lat]
                        }
                    }
                ]
            },
            pickable: false,
            pointType: "circle",
            pointRadiusUnits: "pixels",
            pointRadiusMinPixels: radius,
            pointRadiusMaxPixels: radius,
            getPointRadius: function () { return radius; },
            filled: true,
            stroked: true,
            lineWidthUnits: "pixels",
            lineWidthMinPixels: strokeWidth,
            getLineWidth: function () { return strokeWidth; },
            getFillColor: function () { return fillColor; },
            getLineColor: function () { return lineColor; }
        });
    }

    function buildOutletLayer(deckApi, outletData) {
        if (!outletData) {
            return null;
        }
        var fillColor = hexToRgba(TEMP_COLOR, 0.9);
        var strokeColor = hexToRgba(TEMP_COLOR, 1);
        return buildPointLayer(deckApi, OUTLET_LAYER_ID, {
            lat: outletData.lat,
            lng: outletData.lng
        }, {
            radius: 8,
            strokeWidth: 2,
            fillColor: fillColor,
            lineColor: strokeColor,
            properties: outletData.properties || {}
        });
    }

    function attachOutletRebuild(layer, outlet) {
        if (!layer) {
            return;
        }
        layer.__wcRebuild = function () {
            if (!outlet || !outlet.outletData) {
                return layer;
            }
            var deckApi = ensureDeck();
            var nextLayer = buildOutletLayer(deckApi, outlet.outletData);
            if (!nextLayer) {
                return layer;
            }
            attachOutletRebuild(nextLayer, outlet);
            outlet.outletLayer = nextLayer;
            return nextLayer;
        };
    }

    function buildDialogLayer(deckApi, latlng) {
        if (!deckApi || typeof deckApi.TextLayer !== "function") {
            return null;
        }
        return new deckApi.TextLayer({
            id: TEMP_DIALOG_LAYER_ID,
            data: [
                {
                    position: [latlng.lng, latlng.lat],
                    text: TEMP_DIALOG_TEXT
                }
            ],
            getPosition: function (d) { return d.position; },
            getText: function (d) { return d.text; },
            getSize: function () { return 14; },
            sizeUnits: "pixels",
            getColor: function () { return [20, 20, 20, 255]; },
            getPixelOffset: function () { return [0, -16]; },
            background: true,
            getBackgroundColor: function () { return [255, 255, 255, 235]; },
            backgroundPadding: [6, 4]
        });
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var http = helpers.http;
        var events = helpers.events;
        var deckApi = ensureDeck();

        var outlet = controlBase();
        var baseTriggerEvent = outlet.triggerEvent.bind(outlet);

        var outletEmitter = events.createEmitter();
        if (typeof events.useEventMap === "function") {
            outlet.events = events.useEventMap(EVENT_NAMES, outletEmitter);
        } else {
            outlet.events = outletEmitter;
        }

        var formElement = dom.ensureElement("#set_outlet_form", "Outlet form not found.");
        var infoElement = dom.qs("#set_outlet_form #info");
        var statusElement = dom.qs("#set_outlet_form #status");
        var stacktraceElement = dom.qs("#set_outlet_form #stacktrace");
        var rqJobElement = dom.qs("#set_outlet_form #rq_job");
        var hintElement = dom.qs("#hint_set_outlet_cursor");
        var cursorHintElement = dom.qs("#set_outlet_cursor_hint");
        var entryInputElement = dom.qs("[data-outlet-entry-field]", formElement);
        var cursorButtonElement = dom.qs("[data-outlet-action='cursor-toggle']", formElement);
        var entryButtonElement = dom.qs("[data-outlet-action='entry-submit']", formElement);
        var modeSections = dom.qsa("[data-outlet-mode-section]", formElement);
        var modeRadios = dom.qsa("input[name='set_outlet_mode']", formElement);
        var outletRoot = dom.qs("[data-outlet-root]", formElement) || formElement;
        var mapElement = dom.qs("#mapid");

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);
        var hintAdapter = createLegacyAdapter(hintElement);
        var cursorHintAdapter = null;
        if (cursorHintElement && cursorHintElement !== hintElement) {
            cursorHintAdapter = createLegacyAdapter(cursorHintElement);
        }

        outlet.form = formElement;
        outlet.info = infoAdapter;
        outlet.status = statusAdapter;
        outlet.stacktrace = stacktraceAdapter;
        outlet.rq_job = rqJobAdapter;
        outlet.command_btn_id = ["btn_set_outlet_cursor", "btn_set_outlet_entry"];
        outlet.hint = hintAdapter;
        outlet.cursorHint = cursorHintAdapter || hintAdapter;
        outlet.cursorButton = cursorButtonElement;
        outlet.entryInput = entryInputElement;
        outlet.entryButton = entryButtonElement;
        outlet.mode = 0;
        outlet.statusPanelEl = dom.qs("#set_outlet_status_panel");
        outlet.stacktracePanelEl = dom.qs("#set_outlet_stacktrace_panel");
        outlet.statusStream = null;
        var spinnerElement = outlet.statusPanelEl ? outlet.statusPanelEl.querySelector("#braille") : null;

        outlet.attach_status_stream(outlet, {
            element: outlet.statusPanelEl,
            channel: "outlet",
            stacktrace: outlet.stacktracePanelEl ? { element: outlet.stacktracePanelEl } : null,
            spinner: spinnerElement,
            logLimit: 200,
            autoConnect: true
        });
        outlet.poll_completion_event = "SET_OUTLET_TASK_COMPLETED";
        outlet._completion_seen = false;
        outlet.cursorSelectionOn = false;
        outlet.outletLayer = null;
        outlet.outletData = null;
        outlet.tempSelectionLayer = null;
        outlet.tempDialogLayer = null;
        outlet.tempDialogElement = null;
        outlet.tempDialogUpdate = null;
        var lastSubmission = null;

        function setStatusMessage(message) {
            outlet.clear_status_messages(outlet);
            if (message) {
                outlet.append_status_message(outlet, message);
            }
        }

        function setErrorStatus(message) {
            var text = message || "Unable to complete outlet request.";
            setStatusMessage('<span class="text-danger">' + text + "</span>");
        }

        function resetStatus(taskMsg) {
            if (infoAdapter && typeof infoAdapter.html === "function") {
                infoAdapter.html("");
            }
            if (taskMsg) {
                setStatusMessage(taskMsg + "...");
            } else {
                setStatusMessage("");
            }
            if (stacktraceAdapter && typeof stacktraceAdapter.text === "function") {
                stacktraceAdapter.text("");
            }
        }

        function updateModeUI(modeValue, options) {
            var emitEvent = !options || options.emit !== false;
            var nextMode = parseMode(modeValue, outlet.mode || 0);
            var modeKey = normaliseModeKey(nextMode);

            outlet.mode = nextMode;

            modeSections.forEach(function (section) {
                if (!section) {
                    return;
                }
                var sectionMode = section.getAttribute("data-mode") || "";
                var isActive = sectionMode === modeKey;
                dom.toggle(section, isActive);
                if (isActive) {
                    section.removeAttribute("aria-hidden");
                } else {
                    section.setAttribute("aria-hidden", "true");
                }
            });

            if (nextMode !== 0) {
                setCursorSelection(false);
            }

            if (outlet.events && typeof outlet.events.emit === "function" && emitEvent) {
                outlet.events.emit("outlet:mode:change", {
                    mode: modeKey,
                    value: nextMode
                });
            }
        }

        function updateCursorHint(state) {
            var message = state ? "Click on the map to define outlet." : "";
            var adapter = cursorHintAdapter;

            if (adapter && typeof adapter.text === "function") {
                adapter.text(message);
                if (adapter !== hintAdapter) {
                    if (state && typeof adapter.show === "function") {
                        adapter.show();
                    }
                    if (!state && typeof adapter.hide === "function") {
                        adapter.hide();
                    }
                }
                return;
            }

            if (hintElement) {
                dom.setText(hintElement, message);
            }
        }

        function setCursorSelection(state) {
            var enabled = Boolean(state);
            outlet.cursorSelectionOn = enabled;

            if (cursorButtonElement) {
                dom.setText(cursorButtonElement, enabled ? "Cancel" : "Use Cursor");
                cursorButtonElement.setAttribute("aria-pressed", enabled ? "true" : "false");
            }

            updateCursorHint(enabled);

            if (mapElement && mapElement.style) {
                mapElement.style.cursor = enabled ? "crosshair" : "";
            }
            if (mapElement) {
                var canvas = mapElement.querySelector("canvas");
                if (canvas && canvas.style) {
                    canvas.style.cursor = enabled ? "crosshair" : "";
                }
            }

            if (outlet.events && typeof outlet.events.emit === "function") {
                outlet.events.emit("outlet:cursor:toggle", {
                    enabled: enabled
                });
            }
        }

        function handleCursorToggle(event) {
            event.preventDefault();
            setCursorSelection(!outlet.cursorSelectionOn);
        }

        function handleEntrySubmit(event) {
            event.preventDefault();
            if (!entryInputElement) {
                return;
            }
            var coords;
            try {
                coords = parseCoordinatesFromEntry(entryInputElement.value);
            } catch (err) {
                setErrorStatus(err.message);
                return;
            }
            submitOutlet({ lat: coords.lat, lng: coords.lng }, "entry");
        }

        function addLayer(map, layer) {
            if (!layer || !map || typeof map.addLayer !== "function") {
                return;
            }
            map.addLayer(layer, { skipRefresh: true });
        }

        function removeLayer(map, layer) {
            if (!layer || !map || typeof map.removeLayer !== "function") {
                return;
            }
            map.removeLayer(layer, { skipOverlay: true });
        }

        function clearTemporarySelection(map) {
            if (outlet.tempSelectionLayer) {
                removeLayer(map, outlet.tempSelectionLayer);
                outlet.tempSelectionLayer = null;
            }
            if (outlet.tempDialogLayer) {
                removeLayer(map, outlet.tempDialogLayer);
                outlet.tempDialogLayer = null;
            }
            if (outlet.tempDialogElement && outlet.tempDialogElement.parentNode) {
                outlet.tempDialogElement.parentNode.removeChild(outlet.tempDialogElement);
                outlet.tempDialogElement = null;
            }
            if (outlet.tempDialogUpdate && map && typeof map.off === "function") {
                map.off("move", outlet.tempDialogUpdate);
                map.off("zoom", outlet.tempDialogUpdate);
                outlet.tempDialogUpdate = null;
            }
        }

        function updateDialogElement(map, latlng, element) {
            if (!map || !map._deck || typeof map._deck.project !== "function" || !mapElement) {
                return;
            }
            var projected = map._deck.project([latlng.lng, latlng.lat]);
            if (!projected || projected.length < 2) {
                return;
            }
            var rect = mapElement.getBoundingClientRect();
            var left = rect.left + projected[0];
            var top = rect.top + projected[1];
            element.style.left = left + "px";
            element.style.top = top + "px";
        }

        function buildDialogElement(map, latlng) {
            if (!mapElement || typeof document === "undefined") {
                return null;
            }
            var element = document.createElement("div");
            element.className = "wc-map-outlet-dialog";
            element.textContent = TEMP_DIALOG_TEXT;
            element.style.position = "fixed";
            element.style.zIndex = "5";
            element.style.pointerEvents = "none";
            element.style.padding = "4px 6px";
            element.style.borderRadius = "6px";
            element.style.background = "rgba(255, 255, 255, 0.92)";
            element.style.color = "#141414";
            element.style.fontSize = "12px";
            element.style.boxShadow = "0 2px 8px rgba(0,0,0,0.2)";
            element.style.transform = "translate(-50%, -120%)";
            document.body.appendChild(element);
            updateDialogElement(map, latlng, element);

            return element;
        }

        function createTempSelection(latlng) {
            var map = MapController.getInstance();
            if (!map) {
                return;
            }
            clearTemporarySelection(map);

            var fillColor = hexToRgba(TEMP_COLOR, 0.5);
            var strokeColor = hexToRgba(TEMP_COLOR, 1);
            outlet.tempSelectionLayer = buildPointLayer(deckApi, TEMP_LAYER_ID, latlng, {
                radius: 6,
                strokeWidth: 2,
                fillColor: fillColor,
                lineColor: strokeColor
            });
            addLayer(map, outlet.tempSelectionLayer);

            outlet.tempDialogLayer = buildDialogLayer(deckApi, latlng);
            if (outlet.tempDialogLayer) {
                addLayer(map, outlet.tempDialogLayer);
            } else {
                outlet.tempDialogElement = buildDialogElement(map, latlng);
                if (outlet.tempDialogElement) {
                    outlet.tempDialogUpdate = function () {
                        updateDialogElement(map, latlng, outlet.tempDialogElement);
                    };
                    if (typeof map.on === "function") {
                        map.on("move", outlet.tempDialogUpdate);
                        map.on("zoom", outlet.tempDialogUpdate);
                    }
                }
            }
        }

        function submitOutlet(latlng, source) {
            if (!latlng) {
                return Promise.reject(new Error("LatLng is required."));
            }

            var coordinates = ensureLatLng(latlng.lat, latlng.lng);

            resetStatus("Attempting to set outlet");

            outlet.connect_status_stream(outlet);
            createTempSelection(coordinates);

            setCursorSelection(false);
            outlet._completion_seen = false;

            if (outlet.events && typeof outlet.events.emit === "function") {
                outlet.events.emit("outlet:set:start", {
                    coordinates: coordinates,
                    source: source || "cursor"
                });
            }

            lastSubmission = {
                coordinates: coordinates,
                source: source || "cursor",
                enqueuedAt: Date.now(),
                jobId: null
            };

            return http.request(url_for_run("rq/api/set_outlet"), {
                method: "POST",
                json: {
                    latitude: coordinates.lat,
                    longitude: coordinates.lng
                },
                form: formElement
            })
                .then(function (result) {
                    var data = result.body || {};
                    var success = data.Success === true && data.job_id;
                    if (success) {
                        setStatusMessage("set_outlet job submitted: " + data.job_id);
                        outlet.set_rq_job_id(outlet, data.job_id);
                        if (outlet.events && typeof outlet.events.emit === "function") {
                            outlet.events.emit("outlet:set:queued", {
                                jobId: data.job_id,
                                coordinates: coordinates,
                                source: source || "cursor"
                            });
                        }
                        if (lastSubmission) {
                            lastSubmission.jobId = data.job_id;
                        }
                        outlet.triggerEvent("job:started", {
                            jobId: data.job_id,
                            task: "outlet:set",
                            coordinates: coordinates,
                            source: source || "cursor"
                        });
                        return data;
                    }
                    outlet.pushResponseStacktrace(outlet, data);
                    setErrorStatus("Failed to submit outlet job.");
                    if (outlet.events && typeof outlet.events.emit === "function") {
                        outlet.events.emit("outlet:set:error", {
                            reason: "server",
                            response: data,
                            coordinates: coordinates,
                            source: source || "cursor"
                        });
                    }
                    lastSubmission = null;
                    outlet.triggerEvent("job:error", {
                        reason: "server",
                        response: data,
                        task: "outlet:set",
                        coordinates: coordinates,
                        source: source || "cursor"
                    });
                    clearTemporarySelection(MapController.getInstance());
                    return data;
                })
                .catch(function (error) {
                    outlet.pushErrorStacktrace(outlet, error);
                    setErrorStatus("Unable to enqueue outlet job.");
                    if (outlet.events && typeof outlet.events.emit === "function") {
                        outlet.events.emit("outlet:set:error", {
                            reason: "http",
                            error: error,
                            coordinates: coordinates,
                            source: source || "cursor"
                        });
                    }
                    lastSubmission = null;
                    outlet.triggerEvent("job:error", {
                        reason: "http",
                        error: error,
                        task: "outlet:set",
                        coordinates: coordinates,
                        source: source || "cursor"
                    });
                    clearTemporarySelection(MapController.getInstance());
                    throw error;
                });
        }

        outlet.triggerEvent = function (eventName, payload) {
            var normalized = (eventName || "").toString().toUpperCase();
            if (normalized === "SET_OUTLET_TASK_COMPLETED") {
                if (!outlet._completion_seen) {
                    outlet._completion_seen = true;
                    outlet.disconnect_status_stream(outlet);
                    outlet.show();
                    if (outlet.events && typeof outlet.events.emit === "function") {
                        outlet.events.emit("outlet:set:success", {
                            jobId: outlet.rq_job_id || (lastSubmission && lastSubmission.jobId) || null,
                            submission: lastSubmission,
                            payload: payload || {}
                        });
                    }
                    baseTriggerEvent("job:completed", {
                        jobId: outlet.rq_job_id || null,
                        task: "outlet:set",
                        payload: payload || {}
                    });
                    lastSubmission = null;
                }
            }
            return baseTriggerEvent(eventName, payload);
        };

        outlet.hideStacktrace = function () {
            if (stacktraceAdapter && typeof stacktraceAdapter.hide === "function") {
                stacktraceAdapter.hide();
                return;
            }
            if (stacktraceElement) {
                stacktraceElement.hidden = true;
                stacktraceElement.style.display = "none";
            }
        };

        outlet.remove = function () {
            var map = MapController.getInstance();
            clearTemporarySelection(map);

            if (outlet.outletLayer) {
                if (map && typeof map.unregisterOverlay === "function") {
                    try {
                        map.unregisterOverlay(outlet.outletLayer);
                    } catch (err) {
                        console.warn("Failed to unregister outlet overlay.", err);
                    }
                } else if (map && map.ctrls && typeof map.ctrls.removeLayer === "function") {
                    try {
                        map.ctrls.removeLayer(outlet.outletLayer);
                    } catch (err) {
                        console.warn("Failed to remove outlet overlay.", err);
                    }
                }
                if (map && typeof map.removeLayer === "function") {
                    try {
                        map.removeLayer(outlet.outletLayer);
                    } catch (err) {
                        console.warn("Failed to remove outlet marker from map.", err);
                    }
                }
                outlet.outletLayer = null;
            }

            if (infoAdapter && typeof infoAdapter.html === "function") {
                infoAdapter.html("");
            }
            setStatusMessage("");
            if (stacktraceAdapter && typeof stacktraceAdapter.text === "function") {
                stacktraceAdapter.text("");
            }
        };

        outlet.show = function () {
            var taskMsg = "Displaying Outlet";
            resetStatus(taskMsg);
            outlet.remove();

            var map = MapController.getInstance();
            var bust = { _: Date.now() };

            var queryPromise = http.getJson(url_for_run("query/outlet/"), { params: bust })
                .then(function (response) {
                    if (!response || typeof response.lat !== "number" || typeof response.lng !== "number") {
                        setErrorStatus("Outlet location unavailable.");
                        clearTemporarySelection(map);
                        return;
                    }

                    var offset = typeof cellsize === "number" ? cellsize * 5e-6 : 0;
                    var lat = response.lat - offset;
                    var lng = response.lng + offset;

                    outlet.outletData = {
                        lat: lat,
                        lng: lng,
                        properties: response || {}
                    };
                    outlet.outletLayer = buildOutletLayer(deckApi, outlet.outletData);
                    attachOutletRebuild(outlet.outletLayer, outlet);

                    if (map && typeof map.addLayer === "function") {
                        map.addLayer(outlet.outletLayer);
                    }
                    if (map && typeof map.registerOverlay === "function") {
                        map.registerOverlay(outlet.outletLayer, OUTLET_LAYER_NAME);
                    } else if (map && map.ctrls && typeof map.ctrls.addOverlay === "function") {
                        map.ctrls.addOverlay(outlet.outletLayer, OUTLET_LAYER_NAME);
                    }
                    setStatusMessage(taskMsg + "... Success");
                    clearTemporarySelection(map);
                })
                .catch(function (error) {
                    outlet.pushErrorStacktrace(outlet, error);
                    setErrorStatus("Failed to display outlet.");
                    clearTemporarySelection(map);
                });

            var reportPromise = http.request(url_for_run("report/outlet/"), { params: bust })
                .then(function (result) {
                    var response = result.body;
                    if (infoAdapter && typeof infoAdapter.html === "function") {
                        infoAdapter.html(response || "");
                    }
                })
                .catch(function (error) {
                    outlet.pushErrorStacktrace(outlet, error);
                    setErrorStatus("Failed to load outlet report.");
                });

            Promise.all([queryPromise, reportPromise]).then(function () {
                if (outlet.events && typeof outlet.events.emit === "function") {
                    outlet.events.emit("outlet:display:refresh", {});
                }
            });
        };

        outlet.setCursorSelection = setCursorSelection;
        outlet.setMode = function (mode) {
            updateModeUI(mode);
        };
        outlet.handleModeChange = function (mode) {
            updateModeUI(mode);
        };
        outlet.handleCursorToggle = function () {
            setCursorSelection(!outlet.cursorSelectionOn);
        };
        outlet.handleEntrySubmit = function () {
            if (!entryInputElement) {
                return false;
            }
            var coords;
            try {
                coords = parseCoordinatesFromEntry(entryInputElement.value);
            } catch (err) {
                setErrorStatus(err.message);
                return false;
            }
            submitOutlet({ lat: coords.lat, lng: coords.lng }, "entry");
            return true;
        };

        outlet.set_outlet = function (ev, options) {
            if (!ev || !ev.latlng) {
                return Promise.reject(new Error("LatLng event required."));
            }
            var source = options && options.source ? options.source : "cursor";
            return submitOutlet(ev.latlng, source);
        };

        outlet.setClickHandler = function (ev) {
            if (outlet.cursorSelectionOn) {
                outlet.set_outlet(ev);
            }
        };

        if (modeRadios.length > 0) {
            modeRadios.forEach(function (radio) {
                radio.addEventListener("change", function (event) {
                    updateModeUI(event.target.value);
                });
            });
            var initial = modeRadios.find(function (radio) {
                return radio.checked;
            });
            if (initial) {
                updateModeUI(initial.value, { emit: false });
            }
        }

        dom.delegate(outletRoot, "click", "[data-outlet-action]", function (event, target) {
            var action = target.getAttribute("data-outlet-action");
            if (action === "cursor-toggle") {
                handleCursorToggle(event);
            }
            if (action === "entry-submit") {
                handleEntrySubmit(event);
            }
        });

        var bootstrapState = {
            mapClickBound: false,
            outletLoaded: false,
            initialModeApplied: false
        };

        outlet.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            var controllerContext = helper && typeof helper.getControllerContext === "function"
                ? helper.getControllerContext(ctx, "outlet")
                : {};

            var jobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "set_outlet_rq")
                : null;
            if (!jobId && controllerContext.jobId) {
                jobId = controllerContext.jobId;
            }
            if (!jobId) {
                var jobIds = ctx && (ctx.jobIds || ctx.jobs);
                if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "set_outlet_rq")) {
                    var value = jobIds.set_outlet_rq;
                    if (value !== undefined && value !== null) {
                        jobId = String(value);
                    }
                }
            }

            if (typeof outlet.set_rq_job_id === "function") {
                outlet.set_rq_job_id(outlet, jobId);
            }

            if (!bootstrapState.mapClickBound) {
                try {
                    var map = typeof MapController !== "undefined" ? MapController.getInstance() : null;
                    if (map && typeof map.on === "function") {
                        map.on("click", outlet.setClickHandler);
                        bootstrapState.mapClickBound = true;
                    }
                } catch (err) {
                    console.warn("[Outlet GL] Failed to register map click handler", err);
                }
            }

            if (!bootstrapState.initialModeApplied) {
                var initialMode = controllerContext.mode;
                if (initialMode === undefined || initialMode === null) {
                    var initialModeElement = document.querySelector("input[name='set_outlet_mode']:checked");
                    initialMode = initialModeElement ? initialModeElement.value : null;
                }
                if (initialMode !== undefined && initialMode !== null) {
                    try {
                        outlet.handleModeChange(initialMode);
                        bootstrapState.initialModeApplied = true;
                    } catch (err) {
                        console.warn("[Outlet GL] Failed to apply initial mode", err);
                    }
                }
            }

            var watershed = (ctx.data && ctx.data.watershed) || {};
            var hasOutlet = controllerContext.hasOutlet;
            if (hasOutlet === undefined) {
                hasOutlet = Boolean(watershed.hasOutlet);
            }
            if (hasOutlet && !bootstrapState.outletLoaded) {
                try {
                    outlet.triggerEvent("SET_OUTLET_TASK_COMPLETED");
                } catch (err) {
                    console.warn("[Outlet GL] Failed to trigger outlet display", err);
                }
                bootstrapState.outletLoaded = true;
            }

            return outlet;
        };

        return outlet;
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

window.Outlet = Outlet;
