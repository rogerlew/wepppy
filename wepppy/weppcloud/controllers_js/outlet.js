/* ----------------------------------------------------------------------------
 * Outlet
 * Doc: controllers_js/README.md — Outlet Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var Outlet = (function () {
    var instance;

    function ensureHelpers() {
        var dom = window.WCDom;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function") {
            throw new Error("Outlet controller requires WCDom helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("Outlet controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Outlet controller requires WCEvents helpers.");
        }

        return { dom: dom, http: http, events: events };
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

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var http = helpers.http;
        var events = helpers.events;

        var outlet = controlBase();
        var baseTriggerEvent = outlet.triggerEvent.bind(outlet);

        var outletEmitter = events.createEmitter();
        if (typeof events.useEventMap === "function") {
            outlet.events = events.useEventMap([
                "outlet:mode:change",
                "outlet:cursor:toggle",
                "outlet:set:start",
                "outlet:set:queued",
                "outlet:set:success",
                "outlet:set:error",
                "outlet:display:refresh"
            ], outletEmitter);
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

        outlet.popup = L.popup();
        outlet.cursorSelectionOn = false;
        outlet.outletMarker = L.marker(undefined, {
            pane: "markerCustomPane"
        });
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
                setStatusMessage(taskMsg + "…");
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

            var containers = dom.qsa(".leaflet-container");
            containers.forEach(function (container) {
                if (!container || !container.style) {
                    return;
                }
                container.style.cursor = enabled ? "crosshair" : "";
            });

            if (outlet.events && typeof outlet.events.emit === "function") {
                outlet.events.emit("outlet:cursor:toggle", {
                    enabled: enabled
                });
            }
        }

        function handleModeChange(event) {
            if (!event || !event.target) {
                return;
            }
            updateModeUI(event.target.value);
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
            var latlng = L.latLng(coords.lat, coords.lng);
            submitOutlet(latlng, "entry");
        }

        function submitOutlet(latlng, source) {
            if (!latlng) {
                return Promise.reject(new Error("LatLng is required."));
            }

            var coordinates = ensureLatLng(latlng.lat, latlng.lng);

            resetStatus("Attempting to set outlet");

            outlet.connect_status_stream(outlet);

            // Brief visual feedback: flash a temporary marker with a popup
            try {
                var map = MapController.getInstance();
                var flashMarker = L.circleMarker(latlng, {
                    radius: 6,
                    color: '#1a73e8',
                    weight: 2,
                    fillColor: '#1a73e8',
                    fillOpacity: 0.5,
                    pane: 'markerCustomPane',
                    interactive: false
                }).addTo(map);
                flashMarker.bindPopup('Setting outlet…', {
                    closeButton: false,
                    autoClose: true,
                    closeOnClick: false,
                    offset: [0, -6]
                }).openPopup();
                window.setTimeout(function () {
                    try { map.removeLayer(flashMarker); } catch (e) { /* no-op */ }
                }, 1500);
            } catch (err) {
                console.warn("Failed to display outlet feedback marker.", err);
            }

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
                    throw error;
                });
        }

        outlet.triggerEvent = function (eventName, payload) {
            var normalized = (eventName || "").toString().toUpperCase();
            if (normalized === "SET_OUTLET_TASK_COMPLETED") {
                if (!outlet._completion_seen) {
                    outlet._completion_seen = true;
                    outlet.disconnect_status_stream(outlet);
                    if (outlet.popup && typeof outlet.popup.remove === "function") {
                        try {
                            outlet.popup.remove();
                        } catch (err) {
                            console.warn("Failed to remove outlet popup.", err);
                        }
                    }
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
            if (map && typeof map.unregisterOverlay === "function") {
                try {
                    map.unregisterOverlay(outlet.outletMarker);
                } catch (err) {
                    console.warn("Failed to unregister outlet overlay.", err);
                }
            } else if (map && map.ctrls && typeof map.ctrls.removeLayer === "function") {
                try {
                    map.ctrls.removeLayer(outlet.outletMarker);
                } catch (err) {
                    console.warn("Failed to remove outlet overlay.", err);
                }
            }
            if (map && typeof map.removeLayer === "function") {
                try {
                    map.removeLayer(outlet.outletMarker);
                } catch (err) {
                    console.warn("Failed to remove outlet marker from map.", err);
                }
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
                        return;
                    }

                    var offset = typeof cellsize === "number" ? cellsize * 5e-6 : 0;
                    var lat = response.lat - offset;
                    var lng = response.lng + offset;
                    outlet.outletMarker.setLatLng([lat, lng]).addTo(map);
                    if (map && typeof map.registerOverlay === "function") {
                        map.registerOverlay(outlet.outletMarker, "Outlet");
                    } else if (map && map.ctrls && typeof map.ctrls.addOverlay === "function") {
                        map.ctrls.addOverlay(outlet.outletMarker, "Outlet");
                    }
                    setStatusMessage(taskMsg + "... Success");
                })
                .catch(function (error) {
                    outlet.pushErrorStacktrace(outlet, error);
                    setErrorStatus("Failed to display outlet.");
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
            var latlng = L.latLng(coords.lat, coords.lng);
            submitOutlet(latlng, "entry");
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
                radio.addEventListener("change", handleModeChange);
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
                    console.warn("[Outlet] Failed to register map click handler", err);
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
                        console.warn("[Outlet] Failed to apply initial mode", err);
                    }
                }
            }

            var watershed = (ctx.data && ctx.data.watershed) || {};
            var hasOutlet = controllerContext.hasOutlet;
            if (hasOutlet === undefined) {
                hasOutlet = watershed.hasOutlet;
            }
            if (hasOutlet && !bootstrapState.outletLoaded) {
                try {
                    outlet.triggerEvent("SET_OUTLET_TASK_COMPLETED");
                } catch (err) {
                    console.warn("[Outlet] Failed to trigger outlet display", err);
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
})();

if (typeof globalThis !== "undefined") {
    globalThis.Outlet = Outlet;
}

function render_legend(cmap, canvasID) {
    var element = document.getElementById(canvasID);
    if (!element) {
        return;
    }

    var rect = element.getBoundingClientRect();
    var width = Math.round(rect.width || element.offsetWidth || element.clientWidth || element.width || 0);
    var height = Math.round(rect.height || element.offsetHeight || element.clientHeight || element.height || 0);

    if (width <= 0 || height <= 0) {
        return;
    }

    if (element.width !== width) {
        element.width = width;
    }
    if (element.height !== height) {
        element.height = height;
    }

    var data = new Float32Array(width * height);
    var denom = width > 1 ? width - 1 : 1;

    for (var y = 0; y < height; y++) {
        var rowOffset = y * width;
        for (var x = 0; x < width; x++) {
            data[rowOffset + x] = x / denom;
        }
    }

    var plot = new plotty.plot({
        canvas: element,
        data: data,
        width: width,
        height: height,
        domain: [0, 1],
        colorScale: cmap
    });
    plot.render();
}
