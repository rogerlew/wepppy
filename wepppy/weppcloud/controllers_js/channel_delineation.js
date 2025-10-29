/* ----------------------------------------------------------------------------
 * Channel Delineation
 * ----------------------------------------------------------------------------
 */
var ChannelDelineation = (function () {
    var instance;

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function") {
            throw new Error("ChannelDelineation controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("ChannelDelineation controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("ChannelDelineation controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("ChannelDelineation controller requires WCEvents helpers.");
        }

        return { dom: dom, forms: forms, http: http, events: events };
    }

    function createLegacyAdapter(element) {
        if (!element) {
            return {
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

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var events = helpers.events;

        var channel = controlBase();

        var emitterBase = events.createEmitter();
        var channelEvents = typeof events.useEventMap === "function"
            ? events.useEventMap([
                "channel:build:started",
                "channel:build:completed",
                "channel:build:error",
                "channel:map:updated",
                "channel:extent:mode",
                "channel:report:loaded",
                "channel:layers:loaded"
            ], emitterBase)
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
            spinner: spinnerElement
        });

        channel.zoom_min = 12;
        channel.data = null;
        channel.polys = null;
        channel.topIds = [];
        channel.glLayer = null;
        channel.labels = L.layerGroup();

        channel.style = function (feature) {
            var order = parseInt(feature && feature.properties ? feature.properties.Order : 0, 6);

            if (Number.isNaN(order)) {
                order = 0;
            }

            if (order > 7) {
                order = 7;
            }

            var colors = {
                0: "#8AE5FE",
                1: "#65C8FE",
                2: "#479EFF",
                3: "#306EFE",
                4: "#2500F4",
                5: "#6600cc",
                6: "#50006b",
                7: "#6b006b"
            };
            var stroke = colors[order] || "#1F00CF";
            var fill = colors[order - 1] || "#2838FE";
            return {
                color: stroke,
                weight: 1,
                opacity: 1,
                fillColor: fill,
                fillOpacity: 0.9
            };
        };

        channel.labelStyle = "color:blue; text-shadow: -1px -1px 0 #FFF, 1px -1px 0 #FFF, -1px 1px 0 #FFF, 1px 1px 0 #FFF;";

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
            var raw = manualExtentInput.value || "";
            var bbox = parseBboxText(raw);
            manualExtentInput.value = bbox.join(", ");
            mapBoundsInput.value = bbox.join(",");
        }

        function buildPayload() {
            prepareExtentFields();

            var raw = forms.serializeForm(formElement, { format: "object" });
            var center = parseNumericList(raw.map_center, 2);
            var bounds = parseNumericList(raw.map_bounds, 4);
            var zoom = toFloat(raw.map_zoom);
            var distance = toFloat(raw.map_distance);
            var mcl = coalesceNumeric(raw, ["mcl", "input_mcl"]);
            var csa = coalesceNumeric(raw, ["csa", "input_csa"]);
            var setExtentMode = toInteger(raw.set_extent_mode);
            var wbtFill = raw.wbt_fill_or_breach || null;
            var wbtBreachDistance = toInteger(raw.wbt_blc_dist);
            var mapBoundsText = raw.map_bounds_text || "";

            if (!center || center.length !== 2) {
                throw new Error("Map center is not available yet. Move the map to establish bounds.");
            }
            if (!bounds || bounds.length !== 4) {
                throw new Error("Map extent is missing. Navigate the map or specify a manual extent.");
            }
            if (mcl === null || csa === null) {
                throw new Error("Minimum channel length and critical source area must be numeric.");
            }
            if (setExtentMode === null) {
                setExtentMode = 0;
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
                map_bounds_text: mapBoundsText
            };
        }

        var delegates = [];

        delegates.push(dom.delegate(formElement, "change", "[data-channel-role=\"extent-mode\"]", function () {
            var mode = parseInt(this.value, 10);
            if (Number.isNaN(mode)) {
                mode = 0;
            }
            updateManualExtentVisibility(mode);
            emit("channel:extent:mode", { mode: mode });
        }));

        delegates.push(dom.delegate(formElement, "change", "[data-channel-role=\"wbt-fill\"]", function () {
            updateBreachDistanceVisibility(this.value);
        }));

        delegates.push(dom.delegate(formElement, "click", "[data-channel-action=\"build\"]", function (event) {
            event.preventDefault();
            channel.build();
        }));

        function initializeUI() {
            updateManualExtentVisibility(getExtentMode());
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
                channel.disconnect_status_stream(channel);
                channel.show();
                channel.report();
                emit("channel:build:completed", payload || {});
                baseTriggerEvent("job:completed", {
                    jobId: channel.rq_job_id,
                    task: "channel:build",
                    payload: payload || {}
                });
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
            var map = MapController.getInstance();

            if (channel.glLayer !== null) {
                map.ctrls.removeLayer(channel.glLayer);
                map.removeLayer(channel.glLayer);
                channel.glLayer = null;
            }

            if (channel.labels !== null) {
                map.ctrls.removeLayer(channel.labels);
                map.removeLayer(channel.labels);
                channel.labels = L.layerGroup();
            }
        };

        channel.has_dem = function (onSuccessCallback) {
            return http.getJson(url_for_run("query/has_dem/"), { params: { _: Date.now() } })
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
            try {
                Outlet.getInstance().remove();
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

            emit("channel:build:started", {
                payload: payload
            });

            return http.request(url_for_run("rq/api/fetch_dem_and_build_channels"), {
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

        channel.onMapChange = function () {
            var map = MapController.getInstance();

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

                var zoomOk = zoom >= channel.zoom_min;
                var powerOverride = typeof window.ispoweruser !== "undefined" && window.ispoweruser;
                var enabled = zoomOk || powerOverride;

                if (!enabled) {
                    setBuildButtonEnabled(false, "Area is too large, zoom must be " + channel.zoom_min + ", current zoom is " + zoom + ".");
                } else {
                    setBuildButtonEnabled(true, "");
                }

                channel.update_command_button_state(channel);

                emit("channel:map:updated", {
                    center: [center.lng, center.lat],
                    zoom: zoom,
                    distance: distance,
                    extent: extent
                });
            } catch (error) {
                // Map not initialized yet - this is normal during bootstrap
                // Skip updating channel controls until map is ready
                // (Map will call onMapChange again once it emits 'map:ready')
            }
        };

        var palette = [
            "#8AE5FE", "#65C8FE", "#479EFF", "#306EFE",
            "#2500F4", "#6600cc", "#50006b", "#6b006b"
        ].map(function (color) {
            return fromHex(color, 0.9);
        });

        channel.show = function () {
            var taskMsg = "Identifying topaz_pass";
            // Only reset status (which clears info) if we haven't shown a report yet
            // This prevents clearing the channel report when subcatchment bootstrap calls show()
            if (!bootstrapState.reported) {
                resetStatus(taskMsg);
            }

            return http.request(url_for_run("query/delineation_pass/"), { params: { _: Date.now() } })
                .then(function (result) {
                    var response = result.body;
                    var pass = parseInt(response, 10);
                    if ([0, 1, 2].indexOf(pass) === -1) {
                        channel.pushResponseStacktrace(channel, { Error: "Error Determining Delineation Pass" });
                        showErrorStatus("Error determining delineation pass.");
                        return;
                    }
                    if (pass === 0) {
                        channel.pushResponseStacktrace(channel, { Error: "Channels not delineated" });
                        showErrorStatus("Channels have not been delineated yet.");
                        return;
                    }

                    if (pass === 1) {
                        channel.show_1();
                    } else {
                        channel.show_2();
                    }

                    if (statusAdapter && typeof statusAdapter.html === "function") {
                        statusAdapter.html(taskMsg + "... Success");
                    }
                })
                .catch(function (error) {
                    channel.pushErrorStacktrace(channel, error);
                });
        };

        channel.show_1 = function () {
            channel.remove();

            var taskMsg = "Displaying Channel Map (WebGL)";
            if (statusAdapter && typeof statusAdapter.text === "function") {
                statusAdapter.text(taskMsg + "…");
            }

            http.getJson(url_for_run("resources/netful.json"), { params: { _: Date.now() } })
                .then(function (fc) {
                    var map = MapController.getInstance();
                    channel.glLayer = L.glify.layer({
                        geojson: fc,
                        paneName: "channelGlPane",
                        glifyOptions: {
                            opacity: 0.9,
                            border: false,
                            color: function (i, feat) {
                                var order = parseInt(feat.properties.Order, 10) || 4;
                                order = Math.min(order, 7);
                                return palette[order];
                            }
                        }
                    }).addTo(map);

                    map.ctrls.addOverlay(channel.glLayer, "Channels");

                    if (statusAdapter && typeof statusAdapter.text === "function") {
                        statusAdapter.text(taskMsg + " – done");
                    }

                    emit("channel:layers:loaded", { mode: 1 });
                })
                .catch(function (error) {
                    channel.pushErrorStacktrace(channel, error);
                });
        };

        channel.show_2 = function () {
            channel.remove();
            if (statusAdapter && typeof statusAdapter.text === "function") {
                statusAdapter.text("Displaying SUBWTA channels…");
            }

            http.getJson(url_for_run("resources/channels.json"), { params: { _: Date.now() } })
                .then(function (fc) {
                    var map = MapController.getInstance();

                    channel.glLayer = L.glify.layer({
                        geojson: fc,
                        paneName: "channelGlPane",
                        glifyOptions: {
                            opacity: 0.6,
                            border: true,
                            color: function (i, feat) {
                                var order = parseInt(feat.properties.Order, 10) || 4;
                                order = Math.min(order, 7);
                                return palette[order];
                            },
                            click: function (e, feat) {
                                var ctrl = MapController.getInstance();
                                ctrl.chnQuery(feat.properties.TopazID);
                            }
                        }
                    }).addTo(map);

                    map.ctrls.addOverlay(channel.glLayer, "Channels");

                    channel.labels = L.layerGroup();
                    var seen = new Set();

                    fc.features.forEach(function (feature) {
                        var topId = feature && feature.properties ? feature.properties.TopazID : null;
                        if (!topId || seen.has(topId)) {
                            return;
                        }
                        seen.add(topId);

                        var ring = feature.geometry.coordinates[0][0];
                        var center = [ring[1], ring[0]];

                        var marker = L.marker(center, {
                            icon: L.divIcon({
                                className: "label",
                                html: '<div style="' + channel.labelStyle + '">' + topId + "</div>"
                            }),
                            pane: "markerCustomPane"
                        });
                        channel.labels.addLayer(marker);
                    });

                    map.ctrls.addOverlay(channel.labels, "Channel Labels");

                    if (statusAdapter && typeof statusAdapter.text === "function") {
                        statusAdapter.text("Displaying SUBWTA channels – done");
                    }

                    emit("channel:layers:loaded", { mode: 2 });
                })
                .catch(function (error) {
                    channel.pushErrorStacktrace(channel, error);
                });
        };

        channel.report = function () {
            return http.request(url_for_run("report/channel"), {
                headers: { Accept: "text/html, */*;q=0.8" }
            })
                .then(function (result) {
                    if (infoAdapter && typeof infoAdapter.html === "function") {
                        infoAdapter.html(result.body || "");
                    }
                    emit("channel:report:loaded", {});
                })
                .catch(function (error) {
                    channel.pushErrorStacktrace(channel, error);
                });
        };

        var bootstrapState = {
            reported: false,
            shownWithoutSubcatchments: false
        };

        channel.bootstrap = function bootstrap(context) {
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
            var hasSubcatchments = Boolean(watershed.hasSubcatchments);

            // Always show channel report when channels exist, regardless of subcatchment state
            if (hasChannels && !bootstrapState.reported && typeof channel.report === "function") {
                channel.report();
                bootstrapState.reported = true;
            }

            // Always show appropriate map visualization when channels exist
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

if (typeof globalThis !== "undefined") {
    globalThis.ChannelDelineation = ChannelDelineation;
}
