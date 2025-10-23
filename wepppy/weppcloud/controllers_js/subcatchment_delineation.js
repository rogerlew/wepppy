/* ----------------------------------------------------------------------------
 * Subcatchment Delineation (Modernized)
 * Doc: controllers_js/README.md — Subcatchment Delineation Controller (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var SubcatchmentDelineation = (function () {
    var instance;

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function") {
            throw new Error("SubcatchmentDelineation controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("SubcatchmentDelineation controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("SubcatchmentDelineation controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("SubcatchmentDelineation controller requires WCEvents helpers.");
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

    function toResponsePayload(http, error) {
        if (http && typeof http.isHttpError === "function" && http.isHttpError(error)) {
            var detail = error.detail || error.body || error.message || "Request failed";
            return { Error: detail };
        }
        return { Error: (error && error.message) || "Request failed" };
    }

    function resolveById(id) {
        if (!id) {
            return null;
        }
        return document.getElementById(id);
    }

    function safeText(element, value) {
        if (!element) {
            return;
        }
        element.textContent = value === undefined || value === null ? "" : String(value);
    }

    function safeHtml(element, value) {
        if (!element) {
            return;
        }
        element.innerHTML = value === undefined || value === null ? "" : String(value);
    }

    function safeHide(element) {
        if (!element) {
            return;
        }
        element.hidden = true;
        element.style.display = "none";
    }

    function safeShow(element) {
        if (!element) {
            return;
        }
        element.hidden = false;
        if (element.style.display === "none") {
            element.style.removeProperty("display");
        }
    }

    function isFiniteNumber(value) {
        return typeof value === "number" && Number.isFinite(value);
    }

    function parseNumeric(value) {
        if (value === null || value === undefined || value === "") {
            return null;
        }
        if (Array.isArray(value)) {
            return parseNumeric(value[0]);
        }
        var num = Number(value);
        return Number.isFinite(num) ? num : null;
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var events = helpers.events;

        var sub = controlBase();

        var emitterBase = events.createEmitter();
        var subEvents = typeof events.useEventMap === "function"
            ? events.useEventMap([
                "subcatchment:build:started",
                "subcatchment:build:completed",
                "subcatchment:build:error",
                "subcatchment:map:mode",
                "subcatchment:report:loaded",
                "subcatchment:legend:updated"
            ], emitterBase)
            : emitterBase;
        sub.events = subEvents;

        var formElement = dom.ensureElement("#build_subcatchments_form", "Subcatchment form not found.");
        var infoElement = dom.qs("#build_subcatchments_form #info");
        var statusElement = dom.qs("#build_subcatchments_form #status");
        var stacktraceElement = dom.qs("#build_subcatchments_form #stacktrace");
        var rqJobElement = dom.qs("#build_subcatchments_form #rq_job");
        var hintElement = dom.qs("#hint_build_subcatchments");
        var spinnerElement = dom.qs("#build_subcatchments_form #braille");

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);
        var hintAdapter = createLegacyAdapter(hintElement);

        sub.form = formElement;
        sub.info = infoAdapter;
        sub.status = statusAdapter;
        sub.stacktrace = stacktraceAdapter;
        sub.rq_job = rqJobAdapter;
        sub.hint = hintAdapter;
        sub.command_btn_id = "btn_build_subcatchments";
        sub.statusSpinnerEl = spinnerElement;
        sub.attach_status_stream(sub, {
            form: formElement,
            channel: "subcatchment_delineation",
            runId: window.runid || window.runId || null,
            spinner: spinnerElement
        });

        sub.hideStacktrace = function () {
            if (stacktraceAdapter && typeof stacktraceAdapter.hide === "function") {
                stacktraceAdapter.hide();
                return;
            }
            safeHide(stacktraceElement);
        };

        var defaultStyle = {
            color: "#ff7800",
            weight: 2,
            opacity: 0.65,
            fillColor: "#ff7800",
            fillOpacity: 0.3
        };
        var clearStyle = {
            color: "#ff7800",
            weight: 2,
            opacity: 0.65,
            fillColor: "#ffffff",
            fillOpacity: 0.0
        };
        var COLOR_DEFAULT = fromHex(defaultStyle.fillColor);
        var COLOR_CLEAR = fromHex(clearStyle.fillColor);

        var state = {
            labelStyle: "color:orange; text-shadow: -1px -1px 0 #FFF, 1px -1px 0 #FFF, -1px 1px 0 #FFF, 1px 1px 0 #FFF;",
            defaultStyle: defaultStyle,
            clearStyle: clearStyle,
            data: null,
            glLayer: null,
            labels: L.layerGroup(),
            cmapMode: "default",
            topIds: [],
            dataCover: null,
            dataSlpAsp: null,
            dataLanduse: null,
            dataSoils: null,
            dataRunoff: null,
            dataLoss: null,
            dataPhosphorus: null,
            dataAshLoad: null,
            dataAshTransport: null,
            dataRhemRunoff: null,
            dataRhemSedYield: null,
            dataRhemSoilLoss: null,
            rangeElements: {
                phosphorus: resolveById("wepp_sub_cmap_range_phosphorus"),
                runoff: resolveById("wepp_sub_cmap_range_runoff"),
                loss: resolveById("wepp_sub_cmap_range_loss"),
                griddedLoss: resolveById("wepp_grd_cmap_range_loss"),
                ashLoad: resolveById("ash_sub_cmap_range_load"),
                ashTransport: resolveById("ash_sub_cmap_range_transport"),
                rhemRunoff: resolveById("rhem_sub_cmap_range_runoff"),
                rhemSedYield: resolveById("rhem_sub_cmap_range_sed_yield"),
                rhemSoilLoss: resolveById("rhem_sub_cmap_range_soil_loss")
            },
            labelElements: {
                phosphorusMin: resolveById("wepp_sub_cmap_canvas_phosphorus_min"),
                phosphorusMax: resolveById("wepp_sub_cmap_canvas_phosphorus_max"),
                phosphorusUnits: resolveById("wepp_sub_cmap_canvas_phosphorus_units"),
                runoffMin: resolveById("wepp_sub_cmap_canvas_runoff_min"),
                runoffMax: resolveById("wepp_sub_cmap_canvas_runoff_max"),
                lossMin: resolveById("wepp_sub_cmap_canvas_loss_min"),
                lossMax: resolveById("wepp_sub_cmap_canvas_loss_max"),
                griddedLossMin: resolveById("wepp_grd_cmap_range_loss_min"),
                griddedLossMax: resolveById("wepp_grd_cmap_range_loss_max"),
                griddedLossUnits: resolveById("wepp_grd_cmap_range_loss_units"),
                ashLoadMin: resolveById("ash_sub_cmap_canvas_load_min"),
                ashLoadMax: resolveById("ash_sub_cmap_canvas_load_max"),
                rhemRunoffMin: resolveById("rhem_sub_cmap_canvas_runoff_min"),
                rhemRunoffMax: resolveById("rhem_sub_cmap_canvas_runoff_max"),
                rhemRunoffUnits: resolveById("rhem_sub_cmap_canvas_runoff_units"),
                rhemSedYieldMin: resolveById("rhem_sub_cmap_canvas_sed_yield_min"),
                rhemSedYieldMax: resolveById("rhem_sub_cmap_canvas_sed_yield_max"),
                rhemSedYieldUnits: resolveById("rhem_sub_cmap_canvas_sed_yield_units"),
                ashTransportMin: resolveById("ash_sub_cmap_canvas_transport_min"),
                ashTransportMax: resolveById("ash_sub_cmap_canvas_transport_max"),
                ashTransportUnits: resolveById("ash_sub_cmap_canvas_transport_units"),
                rhemSoilLossMin: resolveById("rhem_sub_cmap_canvas_soil_loss_min"),
                rhemSoilLossMax: resolveById("rhem_sub_cmap_canvas_soil_loss_max"),
                rhemSoilLossUnits: resolveById("rhem_sub_cmap_canvas_soil_loss_units")
            },
            colorMappers: {
                runoff: createColormap({ colormap: "winter", nshades: 64 }),
                loss: createColormap({ colormap: "jet2", nshades: 64 }),
                phosphorus: createColormap({ colormap: "viridis", nshades: 64 }),
                ashLoad: createColormap({ colormap: "jet2", nshades: 64 }),
                ashTransport: createColormap({ colormap: "jet2", nshades: 64 }),
                rhemRunoff: createColormap({ colormap: "winter", nshades: 64 }),
                rhemSedYield: createColormap({ colormap: "viridis", nshades: 64 }),
                rhemSoilLoss: createColormap({ colormap: "jet2", nshades: 64 }),
                cover: createColormap({ colormap: "viridis", nshades: 64 })
            },
            ashMeasure: null,
            grid: null,
            gridLabel: "Soil Deposition/Loss"
        };

        sub.state = state;

        function emit(eventName, payload) {
            if (subEvents && typeof subEvents.emit === "function") {
                subEvents.emit(eventName, payload || {});
            }
        }

        var baseTriggerEvent = sub.triggerEvent.bind(sub);
        sub.triggerEvent = function (eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === "BUILD_SUBCATCHMENTS_TASK_COMPLETED") {
                sub.show();
                try {
                    ChannelDelineation.getInstance().show();
                } catch (err) {
                    console.warn("[Subcatchment] Unable to show channel delineation", err);
                }
                emit("subcatchment:build:completed", payload || {});
            } else if (normalized === "WATERSHED_ABSTRACTION_TASK_COMPLETED") {
                sub.report();
                sub.disconnect_status_stream(sub);
                sub.enableColorMap("slp_asp");
                try {
                    Wepp.getInstance().updatePhosphorus();
                } catch (err) {
                    console.warn("[Subcatchment] Unable to update WEPP phosphorus", err);
                }
            }

            baseTriggerEvent(eventName, payload);
        };

        function handleError(error) {
            var payload = toResponsePayload(http, error);
            sub.pushResponseStacktrace(sub, payload);
            return payload;
        }

        function resetStatus(taskMsg) {
            if (infoAdapter && typeof infoAdapter.text === "function") {
                infoAdapter.text("");
            } else {
                safeText(infoElement, "");
            }
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(taskMsg + "...");
            } else {
                safeHtml(statusElement, taskMsg + "...");
            }
            if (stacktraceAdapter && typeof stacktraceAdapter.text === "function") {
                stacktraceAdapter.text("");
            } else {
                safeText(stacktraceElement, "");
            }
        }

        function requestJson(url, options) {
            var opts = options || {};
            if (!opts.method) {
                opts.method = "GET";
            }
            if (!opts.headers) {
                opts.headers = { Accept: "application/json" };
            } else if (!opts.headers.Accept) {
                opts.headers.Accept = "application/json";
            }
            return http.request(url, opts).then(function (result) {
                if (!result) {
                    return null;
                }
                if (result.body !== undefined) {
                    return result.body;
                }
                return result.response || null;
            });
        }

        function setSubLegend(html) {
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
                console.warn("[Subcatchment] Failed to update legend", err);
            }
        }

        function loadLegend(name) {
            if (!name) {
                return Promise.resolve();
            }
            var legendUrl = url_for_run("resources/legends/" + name + "/");
            return http.request(legendUrl, {
                method: "GET",
                headers: { Accept: "text/html,application/xhtml+xml" }
            }).then(function (result) {
                var html = typeof result.body === "string" ? result.body : "";
                setSubLegend(html);
                emit("subcatchment:legend:updated", { name: name });
            }).catch(function (error) {
                // propagate through standard handler while keeping console noise minimal
                handleError(error);
            });
        }

        function renderLayer(options) {
            var type = options.type;
            var dataProp = options.dataProp;
            var mode = options.mode;
            var legend = options.legend;
            var label = options.label || type;

            if (statusAdapter && typeof statusAdapter.text === "function") {
                statusAdapter.text("Loading " + label + " …");
            } else {
                safeText(statusElement, "Loading " + label + " …");
            }

            var targetUrl = "query/" + type + "/subcatchments/";

            return requestJson(targetUrl)
                .then(function (data) {
                    state[dataProp] = data;
                    state.cmapMode = mode;
                    refreshGlLayer();
                    var message = label.charAt(0).toUpperCase() + label.slice(1) + " loaded.";
                    if (statusAdapter && typeof statusAdapter.text === "function") {
                        statusAdapter.text(message);
                    } else {
                        safeText(statusElement, message);
                    }
                })
                .catch(handleError)
                .then(function () {
                    if (legend) {
                        return loadLegend(legend);
                    }
                    return undefined;
                });
        }

        function renderLegendIfPresent(palette, canvasId) {
            if (typeof window.render_legend !== "function") {
                return;
            }
            var canvas = resolveById(canvasId);
            if (!canvas) {
                return;
            }
            window.render_legend(palette, canvasId);
        }

        function getCheckedValue(selector) {
            var element = document.querySelector(selector + ":checked");
            return element ? element.value : null;
        }

        function updateRangeLabel(setter, minValue, maxValue) {
            if (typeof setter !== "function") {
                return;
            }
            try {
                setter(minValue, maxValue);
            } catch (err) {
                console.warn("[Subcatchment] Failed to update range label", err);
            }
        }

        function resolveWeppKey(feature) {
            if (!feature || !feature.properties) {
                return null;
            }
            var props = feature.properties;
            var candidates = [
                props.WeppID,
                props.wepp_id,
                props.weppId,
                props.Hillslopes,
                props.hillslope
            ];
            for (var i = 0; i < candidates.length; i += 1) {
                var candidate = candidates[i];
                if (candidate !== undefined && candidate !== null && candidate !== "") {
                    return String(candidate);
                }
            }
            return null;
        }

        function disposeGlLayer() {
            var map = MapController.getInstance();
            if (state.glLayer) {
                try {
                    state.glLayer.remove();
                } catch (err) {
                    console.warn("[Subcatchment] Failed to remove GL layer", err);
                }
                try {
                    map.ctrls.removeLayer(state.glLayer);
                } catch (err) {
                    console.warn("[Subcatchment] Failed to update layer control", err);
                }
                state.glLayer = null;
            }
            if (state.labels) {
                try {
                    map.ctrls.removeLayer(state.labels);
                } catch (err) {
                    // ignore
                }
            }
        }

        function colorFnFactory() {
            switch (state.cmapMode) {
                case "default":
                    return function () { return COLOR_DEFAULT; };
                case "clear":
                    return function () { return COLOR_CLEAR; };
                case "slp_asp":
                    return function (feature) {
                        var id = feature.properties.TopazID;
                        var rgbHex = state.dataSlpAsp && state.dataSlpAsp[id] ? state.dataSlpAsp[id].color : null;
                        return rgbHex ? fromHex(rgbHex, 0.7) : COLOR_DEFAULT;
                    };
                case "landuse":
                    return function (feature) {
                        var id = feature.properties.TopazID;
                        var rgbHex = state.dataLanduse && state.dataLanduse[id] ? state.dataLanduse[id].color : null;
                        return rgbHex ? fromHex(rgbHex, 0.7) : COLOR_DEFAULT;
                    };
                case "soils":
                    return function (feature) {
                        var id = feature.properties.TopazID;
                        var rgbHex = state.dataSoils && state.dataSoils[id] ? state.dataSoils[id].color : null;
                        return rgbHex ? fromHex(rgbHex, 0.7) : COLOR_DEFAULT;
                    };
                case "cover":
                    return function (feature) {
                        if (!state.dataCover) {
                            return COLOR_DEFAULT;
                        }
                        var id = feature.properties.TopazID;
                        var value = state.dataCover[id];
                        if (value === undefined || value === null) {
                            return COLOR_DEFAULT;
                        }
                        var mapper = state.colorMappers.cover;
                        var hex = mapper ? mapper.map(value) : "#ffffff";
                        return fromHex(hex);
                    };
                case "phosphorus":
                    return function (feature) {
                        var id = feature.properties.TopazID;
                        var record = state.dataPhosphorus ? state.dataPhosphorus[id] : null;
                        if (!record) {
                            return COLOR_DEFAULT;
                        }
                        var v = parseFloat(record.value);
                        if (!Number.isFinite(v)) {
                            return COLOR_DEFAULT;
                        }
                        var range = state.rangeElements.phosphorus;
                        var sliderValue = range ? parseFloat(range.value) : NaN;
                        var linearValue = Number.isFinite(sliderValue) ? sliderValue : 50;
                        var minLog = 0.001;
                        var maxLog = 10.0;
                        var maxLinear = 100;
                        var r = linearToLog(linearValue, minLog, maxLog, maxLinear);
                        safeText(state.labelElements.phosphorusMin, "0.000");
                        updateRangeMaxLabel_kgha(r, state.labelElements.phosphorusMax);
                        var hex = state.colorMappers.phosphorus.map(v / r);
                        return fromHex(hex, 0.9);
                    };
                case "runoff":
                    return function (feature) {
                        var key = resolveWeppKey(feature);
                        var record = key && state.dataRunoff ? state.dataRunoff[key] : null;
                        var v = record ? parseFloat(record.value) : NaN;
                        if (!record || Number.isNaN(v)) {
                            return COLOR_DEFAULT;
                        }
                        var range = state.rangeElements.runoff;
                        var sliderValue = range ? parseFloat(range.value) : NaN;
                        var linearValue = Number.isFinite(sliderValue) ? sliderValue : 50;
                        var minLog = 0.1;
                        var maxLog = 1000;
                        var maxLinear = 100;
                        var r = linearToLog(linearValue, minLog, maxLog, maxLinear);
                        safeText(state.labelElements.runoffMin, "0.000");
                        updateRangeMaxLabel_mm(r, state.labelElements.runoffMax);
                        var hex = state.colorMappers.runoff.map(v / r);
                        return fromHex(hex, 0.9);
                    };
                case "loss":
                    return function (feature) {
                        var key = resolveWeppKey(feature);
                        var record = key && state.dataLoss ? state.dataLoss[key] : null;
                        var v = record ? parseFloat(record.value) : NaN;
                        if (!record || Number.isNaN(v)) {
                            return COLOR_DEFAULT;
                        }
                        var range = state.rangeElements.loss;
                        var sliderValue = range ? parseFloat(range.value) : NaN;
                        var linearValue = Number.isFinite(sliderValue) ? sliderValue : 50;
                        var minLog = 1;
                        var maxLog = 10000;
                        var maxLinear = 100;
                        var r = linearToLog(linearValue, minLog, maxLog, maxLinear);
                        safeText(state.labelElements.lossMin, "0.000");
                        updateRangeMaxLabel_kgha(r, state.labelElements.lossMax);
                        var hex = state.colorMappers.loss.map(v / r);
                        return fromHex(hex, 0.9);
                    };
                case "ash_load":
                    return function (feature) {
                        var id = feature.properties.TopazID;
                        var bucket = state.dataAshLoad && state.dataAshLoad[id] ? state.dataAshLoad[id] : null;
                        if (!bucket || !state.ashMeasure) {
                            return COLOR_DEFAULT;
                        }
                        var record = bucket[state.ashMeasure];
                        if (!record) {
                            return COLOR_DEFAULT;
                        }
                        var v = parseFloat(record.value);
                        if (!Number.isFinite(v)) {
                            return COLOR_DEFAULT;
                        }
                        var range = state.rangeElements.ashLoad;
                        var sliderValue = range ? parseFloat(range.value) : NaN;
                        var linearValue = Number.isFinite(sliderValue) ? sliderValue : 50;
                        var minLog = 0.001;
                        var maxLog = 100;
                        var maxLinear = 100;
                        var r = linearToLog(linearValue, minLog, maxLog, maxLinear);
                        safeText(state.labelElements.ashLoadMin, "0.000");
                        updateRangeMaxLabel_tonneha(r, state.labelElements.ashLoadMax);
                        var hex = state.colorMappers.ashLoad.map(v / r);
                        return fromHex(hex, 0.9);
                    };
                case "ash_transport":
                    return function (feature) {
                        var id = feature.properties.TopazID;
                        var record = state.dataAshTransport ? state.dataAshTransport[id] : null;
                        if (!record) {
                            return COLOR_DEFAULT;
                        }
                        var value = parseFloat(record.value);
                        if (!Number.isFinite(value)) {
                            return COLOR_DEFAULT;
                        }
                        var range = state.rangeElements.ashTransport;
                        var sliderValue = range ? parseFloat(range.value) : NaN;
                        var linearValue = Number.isFinite(sliderValue) ? sliderValue : 50;
                        var minLog = 0.001;
                        var maxLog = 20;
                        var maxLinear = 100;
                        var r = linearToLog(linearValue, minLog, maxLog, maxLinear);
                        safeText(state.labelElements.ashTransportMin, "0.000");
                        updateRangeMaxLabel_tonneha(r, state.labelElements.ashTransportMax);
                        var hex = state.colorMappers.ashTransport.map(value / r);
                        return fromHex(hex, 0.9);
                    };
                case "rhem_runoff":
                    return function (feature) {
                        var id = feature.properties.TopazID;
                        var record = state.dataRhemRunoff ? state.dataRhemRunoff[id] : null;
                        if (!record) {
                            return COLOR_DEFAULT;
                        }
                        var value = parseFloat(record.value);
                        if (!Number.isFinite(value)) {
                            return COLOR_DEFAULT;
                        }
                        var range = state.rangeElements.rhemRunoff;
                        var sliderValue = range ? parseFloat(range.value) : NaN;
                        var linearValue = Number.isFinite(sliderValue) ? sliderValue : 50;
                        var minLog = 0.1;
                        var maxLog = 1000;
                        var maxLinear = 100;
                        var r = linearToLog(linearValue, minLog, maxLog, maxLinear);
                        safeText(state.labelElements.rhemRunoffMin, "0.000");
                        updateRangeMaxLabel_mm(r, state.labelElements.rhemRunoffMax);
                        var hex = state.colorMappers.rhemRunoff.map(value / r);
                        return fromHex(hex, 0.9);
                    };
                case "rhem_sed_yield":
                    return function (feature) {
                        var id = feature.properties.TopazID;
                        var record = state.dataRhemSedYield ? state.dataRhemSedYield[id] : null;
                        if (!record) {
                            return COLOR_DEFAULT;
                        }
                        var value = parseFloat(record.value);
                        if (!Number.isFinite(value)) {
                            return COLOR_DEFAULT;
                        }
                        var range = state.rangeElements.rhemSedYield;
                        var sliderValue = range ? parseFloat(range.value) : NaN;
                        var linearValue = Number.isFinite(sliderValue) ? sliderValue : 50;
                        var minLog = 1;
                        var maxLog = 10000;
                        var maxLinear = 100;
                        var r = linearToLog(linearValue, minLog, maxLog, maxLinear);
                        safeText(state.labelElements.rhemSedYieldMin, "0.000");
                        updateRangeMaxLabel_mm(r, state.labelElements.rhemSedYieldMax);
                        var hex = state.colorMappers.rhemSedYield.map(value / r);
                        return fromHex(hex, 0.9);
                    };
                case "rhem_soil_loss":
                    return function (feature) {
                        var id = feature.properties.TopazID;
                        var record = state.dataRhemSoilLoss ? state.dataRhemSoilLoss[id] : null;
                        if (!record) {
                            return COLOR_DEFAULT;
                        }
                        var value = parseFloat(record.value);
                        if (!Number.isFinite(value)) {
                            return COLOR_DEFAULT;
                        }
                        var range = state.rangeElements.rhemSoilLoss;
                        var sliderValue = range ? parseFloat(range.value) : NaN;
                        var linearValue = Number.isFinite(sliderValue) ? sliderValue : 50;
                        var minLog = 0.001;
                        var maxLog = 10000;
                        var maxLinear = 100;
                        var r = linearToLog(linearValue, minLog, maxLog, maxLinear);
                        safeText(state.labelElements.rhemSoilLossMin, "0.000");
                        updateRangeMaxLabel_kgha(r, state.labelElements.rhemSoilLossMax);
                        var hex = state.colorMappers.rhemSoilLoss.map(value / r);
                        return fromHex(hex, 0.9);
                    };
                default:
                    return function () { return COLOR_DEFAULT; };
            }
        }

        function refreshGlLayer() {
            if (!state.data) {
                return;
            }
            var map = MapController.getInstance();

            if (state.glLayer) {
                try {
                    state.glLayer.remove();
                } catch (err) {
                    console.warn("[Subcatchment] Failed to remove previous GL layer", err);
                }
                try {
                    map.ctrls.removeLayer(state.glLayer);
                } catch (err) {
                    console.warn("[Subcatchment] Failed to sync layer control", err);
                }
            }

            var cmapFn = colorFnFactory();

            state.glLayer = L.glify.layer({
                geojson: state.data,
                paneName: "subcatchmentsGlPane",
                glifyOptions: {
                    opacity: 0.5,
                    border: true,
                    color: function (index, feature) {
                        return cmapFn(feature);
                    },
                    click: function (event, feature) {
                        MapController.getInstance().subQuery(feature.properties.TopazID);
                    }
                }
            }).addTo(map);

            map.ctrls.addOverlay(state.glLayer, "Subcatchments");
        }

        function updateGlLayerStyle() {
            if (!state.glLayer) {
                return;
            }
            var cmapFn = colorFnFactory();
            state.glLayer.setStyle({
                color: function (index, feature) {
                    return cmapFn(feature);
                }
            });
        }

        function buildLabels() {
            state.labels.clearLayers();
            if (!state.data || !state.data.features) {
                return;
            }
            var seen = new Set();
            state.data.features.forEach(function (feature) {
                var id = feature.properties.TopazID;
                if (seen.has(id)) {
                    return;
                }
                seen.add(id);
                var center = polylabel(feature.geometry.coordinates, 1.0);
                var marker = L.marker([center[1], center[0]], {
                    icon: L.divIcon({
                        className: "label",
                        html: '<div style="' + state.labelStyle + '">' + id + '</div>'
                    }),
                    pane: "markerCustomPane"
                });
                state.labels.addLayer(marker);
            });
        }

        function removeGrid() {
            if (!state.grid) {
                return;
            }
            var map = MapController.getInstance();
            try {
                map.ctrls.removeLayer(state.grid);
            } catch (err) {
                // ignore
            }
            try {
                map.removeLayer(state.grid);
            } catch (err) {
                console.warn("[Subcatchment] Failed to remove grid layer", err);
            }
            state.grid = null;
        }

        function renderGriddedLoss() {
            removeGrid();
            var map = MapController.getInstance();
            state.grid = L.leafletGeotiff("resources/flowpaths_loss.tif", {
                band: 0,
                displayMin: 0,
                displayMax: 1,
                name: state.gridLabel,
                colorScale: "jet2",
                opacity: 1.0,
                clampLow: true,
                clampHigh: true,
                arrowSize: 20
            }).addTo(map);
            updateGriddedLoss();
            map.ctrls.addOverlay(state.grid, "Gridded Output");
        }

        function updateGriddedLoss() {
            var range = state.rangeElements.griddedLoss;
            if (!range) {
                return;
            }
            var value = parseFloat(range.value);
            if (!Number.isFinite(value)) {
                return;
            }
            if (state.grid && typeof state.grid.setDisplayRange === "function") {
                state.grid.setDisplayRange(-1.0 * value, value);
            }

            UnitizerClient.ready()
                .then(function (client) {
                    var maxHtml = client.renderValue(value, "kg/m^2", { includeUnits: true });
                    var minHtml = client.renderValue(-1.0 * value, "kg/m^2", { includeUnits: true });
                    var unitsHtml = client.renderUnits("kg/m^2");

                    safeHtml(state.labelElements.griddedLossMax, maxHtml);
                    safeHtml(state.labelElements.griddedLossMin, minHtml);
                    safeHtml(state.labelElements.griddedLossUnits, unitsHtml);

                    var project = Project.getInstance();
                    if (project && typeof project.set_preferred_units === "function") {
                        project.set_preferred_units();
                    }
                })
                .catch(function (error) {
                    sub.pushErrorStacktrace(sub, error);
                });
        }

        function getAshTransportMeasure() {
            var radio = document.querySelector("input[name='wepp_sub_cmap_radio']:checked");
            return radio ? radio.value : null;
        }

        function handleColorMapChange(value) {
            if (!value) {
                return;
            }
            sub.setColorMap(value);
            emit("subcatchment:map:mode", { mode: value });
        }

        function handleRangeUpdate(mode) {
            if (!mode) {
                return;
            }
            if (mode === "grd_loss") {
                updateGriddedLoss();
                return;
            }
            updateGlLayerStyle();
        }

        function setupDelegatedEvents() {
            dom.delegate(document, "click", "[data-subcatchment-action='build']", function (event) {
                event.preventDefault();
                sub.build();
            });

            dom.delegate(document, "change", "[data-subcatchment-role='cmap-option']", function (event) {
                handleColorMapChange(this.value);
            });

            dom.delegate(document, "input", "[data-subcatchment-role='scale-range']", function () {
                var mode = this.getAttribute("data-subcatchment-scale");
                handleRangeUpdate(mode);
            });
        }

        function bindDirectFallbackListeners() {
            var gridded = state.rangeElements.griddedLoss;
            if (gridded && typeof gridded.addEventListener === "function") {
                gridded.addEventListener("input", function () {
                    handleRangeUpdate("grd_loss");
                });
            }
        }

        function disableRadio(id, disabled) {
            var radio = resolveById(id);
            if (!radio) {
                return;
            }
            radio.disabled = Boolean(disabled);
            if (disabled) {
                radio.setAttribute("aria-disabled", "true");
            } else {
                radio.removeAttribute("aria-disabled");
            }
        }

        sub.enableColorMap = function (cmapName) {
            switch (cmapName) {
                case "dom_lc":
                    disableRadio("sub_cmap_radio_dom_lc", false);
                    break;
                case "rangeland_cover":
                    disableRadio("sub_cmap_radio_rangeland_cover", false);
                    break;
                case "dom_soil":
                    disableRadio("sub_cmap_radio_dom_soil", false);
                    break;
                case "slp_asp":
                    disableRadio("sub_cmap_radio_slp_asp", false);
                    break;
                default:
                    throw new Error("Map.enableColorMap received unexpected parameter: " + cmapName);
            }
        };

        sub.getCmapMode = function () {
            if (resolveById("sub_cmap_radio_dom_lc")?.checked) {
                return "dom_lc";
            }
            if (resolveById("sub_cmap_radio_dom_soil")?.checked) {
                return "dom_soil";
            }
            if (resolveById("sub_cmap_radio_slp_asp")?.checked) {
                return "slp_asp";
            }
            if (resolveById("sub_cmap_radio_rangeland_cover")?.checked) {
                return "rangeland_cover";
            }
            return "default";
        };

        sub.setColorMap = function (mode) {
            if (!state.glLayer && mode !== "default" && mode !== "clear") {
                throw new Error("Subcatchments have not been drawn");
            }

            if (mode === "default") {
                state.cmapMode = "default";
                refreshGlLayer();
                setSubLegend("");
            } else if (mode === "slp_asp") {
                renderSlpAsp();
            } else if (mode === "dom_lc") {
                renderLanduse();
            } else if (mode === "rangeland_cover") {
                renderRangelandCover();
            } else if (mode === "dom_soil") {
                renderSoils();
            } else if (mode === "landuse_cover") {
                renderCover();
            } else if (mode === "sub_runoff") {
                renderRunoff();
            } else if (mode === "sub_subrunoff") {
                renderSubrunoff();
            } else if (mode === "sub_baseflow") {
                renderBaseflow();
            } else if (mode === "sub_loss") {
                renderLoss();
            } else if (mode === "sub_phosphorus") {
                renderPhosphorus();
            } else if (mode === "sub_rhem_runoff") {
                renderRhemRunoff();
            } else if (mode === "sub_rhem_sed_yield") {
                renderRhemSedYield();
            } else if (mode === "sub_rhem_soil_loss") {
                renderRhemSoilLoss();
            } else if (mode === "ash_load") {
                renderAshLoad();
            } else if (mode === "wind_transport (kg/ha)") {
                renderAshTransport();
            } else if (mode === "water_transport (kg/ha") {
                renderAshTransport();
            } else if (mode === "ash_transport (kg/ha)") {
                renderAshTransport();
            } else if (mode === "grd_loss") {
                state.cmapMode = "clear";
                refreshGlLayer();
                renderGriddedLoss();
            }

            if (mode !== "grd_loss") {
                removeGrid();
            }
        };

        sub.initializeColorMapControls = function () {
            renderLegendIfPresent("viridis", "landuse_sub_cmap_canvas_cover");
            renderLegendIfPresent("viridis", "wepp_sub_cmap_canvas_phosphorus");
            renderLegendIfPresent("winter", "wepp_sub_cmap_canvas_runoff");
            renderLegendIfPresent("jet2", "wepp_sub_cmap_canvas_loss");
            renderLegendIfPresent("jet2", "wepp_grd_cmap_canvas_loss");
            renderLegendIfPresent("winter", "rhem_sub_cmap_canvas_runoff");
            renderLegendIfPresent("viridis", "rhem_sub_cmap_canvas_sed_yield");
            renderLegendIfPresent("jet2", "rhem_sub_cmap_canvas_soil_loss");
            renderLegendIfPresent("jet2", "ash_sub_cmap_canvas_load");
            renderLegendIfPresent("jet2", "ash_sub_cmap_canvas_transport");
        };

        sub._refreshGlLayer = refreshGlLayer;
        sub.updateGlLayerStyle = updateGlLayerStyle;
        sub._buildLabels = buildLabels;
        sub.removeGrid = removeGrid;
        sub.updateGriddedLoss = updateGriddedLoss;

        function showSubcatchments() {
            state.cmapMode = "default";
            requestJson("resources/subcatchments.json", { params: { _: Date.now() } })
                .then(function (geojson) {
                    if (!geojson) {
                        return;
                    }
                    state.data = geojson;
                    buildLabels();
                    refreshGlLayer();
                    MapController.getInstance().ctrls.addOverlay(state.labels, "Subcatchment Labels");
                })
                .catch(handleError);
        }

        sub.show = showSubcatchments;

        sub.render = function () {
            state.cmapMode = "default";
            refreshGlLayer();
        };

        sub.renderClear = function () {
            state.cmapMode = "clear";
            refreshGlLayer();
        };

        function renderSlpAsp() {
            renderLayer({
                type: "watershed",
                dataProp: "dataSlpAsp",
                mode: "slp_asp",
                legend: "slope_aspect",
                label: "slope/aspect"
            });
        }

        function renderLanduse() {
            renderLayer({
                type: "landuse",
                dataProp: "dataLanduse",
                mode: "landuse",
                legend: "landuse",
                label: "landuse"
            });
        }

        function renderRangelandCover() {
            renderLayer({
                type: "rangeland_cover",
                dataProp: "dataLanduse",
                mode: "landuse",
                legend: "landuse",
                label: "rangeland cover"
            });
        }

        function renderSoils() {
            renderLayer({
                type: "soils",
                dataProp: "dataSoils",
                mode: "soils",
                legend: "soils",
                label: "soils"
            });
        }

        function renderCover() {
            requestJson("query/landuse/cover/subcatchments")
                .then(function (data) {
                    state.dataCover = data;
                    state.cmapMode = "cover";
                    state.colorMappers.cover = createColormap({ colormap: "viridis", nshades: 64 });
                    refreshGlLayer();
                })
                .catch(handleError);
        }

        var WEPP_LOSS_METRIC_EXPRESSIONS = Object.freeze({
            runoff: 'CAST(loss."Runoff Volume" / (NULLIF(loss."Hillslope Area", 0) * 10.0) AS DOUBLE)',
            subrunoff: 'CAST(loss."Subrunoff Volume" / (NULLIF(loss."Hillslope Area", 0) * 10.0) AS DOUBLE)',
            baseflow: 'CAST(loss."Baseflow Volume" / (NULLIF(loss."Hillslope Area", 0) * 10.0) AS DOUBLE)',
            loss: 'CAST(loss."Soil Loss" / NULLIF(loss."Hillslope Area", 0) AS DOUBLE)'
        });

        function resolveRunSlugForQuery() {
            var prefix = typeof window.site_prefix === "string" ? window.site_prefix : "";
            if (prefix && prefix !== "/" && prefix.charAt(0) !== "/") {
                prefix = "/" + prefix;
            }
            if (prefix === "/") {
                prefix = "";
            }

            var path = window.location && window.location.pathname ? window.location.pathname : "";
            if (prefix && path.indexOf(prefix) === 0) {
                path = path.slice(prefix.length);
            }

            var parts = path.split("/").filter(function (segment) {
                return segment.length > 0;
            });
            var runsIndex = parts.indexOf("runs");
            if (runsIndex === -1 || parts.length <= runsIndex + 1) {
                return null;
            }
            return decodeURIComponent(parts[runsIndex + 1]);
        }

        function postQueryEngine(payload) {
            var runSlug = resolveRunSlugForQuery();
            if (!runSlug) {
                return Promise.reject(new Error("Unable to resolve run identifier from the current URL."));
            }
            var path = "/query-engine/runs/" + encodeURIComponent(runSlug) + "/query";
            var targetUrl = url_for_run(path);
            return http.postJson(targetUrl, payload, {
                headers: { Accept: "application/json" }
            }).then(function (result) {
                return result && result.body ? result.body : null;
            });
        }

        var lossMetricCache = Object.create(null);
        var lossMetricInflight = Object.create(null);

        function fetchLossMetric(metricKey) {
            var expression = WEPP_LOSS_METRIC_EXPRESSIONS[metricKey];
            if (!expression) {
                return Promise.reject(new Error("Unknown WEPP loss metric: " + metricKey));
            }

            if (lossMetricCache[metricKey]) {
                return Promise.resolve(lossMetricCache[metricKey]);
            }
            if (lossMetricInflight[metricKey]) {
                return lossMetricInflight[metricKey];
            }

            var payload = {
                datasets: [
                    { path: "wepp/output/interchange/loss_pw0.hill.parquet", alias: "loss" }
                ],
                columns: [
                    'loss.wepp_id AS wepp_id',
                    expression + " AS value"
                ],
                order_by: ["wepp_id"]
            };

            var requestPromise = postQueryEngine(payload).then(function (response) {
                var records = Array.isArray(response && response.records) ? response.records : [];
                var map = Object.create(null);
                records.forEach(function (row) {
                    if (!row) {
                        return;
                    }
                    var weppId = row.wepp_id;
                    if (weppId === undefined || weppId === null) {
                        return;
                    }
                    map[String(weppId)] = {
                        wepp_id: weppId,
                        value: row.value
                    };
                });
                lossMetricCache[metricKey] = map;
                return map;
            });

            requestPromise = requestPromise.then(function (map) {
                delete lossMetricInflight[metricKey];
                return map;
            }, function (error) {
                delete lossMetricInflight[metricKey];
                throw error;
            });

            lossMetricInflight[metricKey] = requestPromise;
            return requestPromise;
        }

        function renderRunoff() {
            fetchLossMetric("runoff").then(function (data) {
                state.dataRunoff = data;
                state.cmapMode = "runoff";
                refreshGlLayer();
            }).catch(handleError);
        }

        function renderSubrunoff() {
            fetchLossMetric("subrunoff").then(function (data) {
                state.dataRunoff = state.dataRunoff || data;
                state.cmapMode = "runoff";
                refreshGlLayer();
            }).catch(handleError);
        }

        function renderBaseflow() {
            fetchLossMetric("baseflow").then(function (data) {
                state.dataRunoff = state.dataRunoff || data;
                state.cmapMode = "runoff";
                refreshGlLayer();
            }).catch(handleError);
        }

        function renderLoss() {
            fetchLossMetric("loss").then(function (data) {
                state.dataLoss = data;
                state.cmapMode = "loss";
                refreshGlLayer();
            }).catch(handleError);
        }

        sub.prefetchLossMetrics = function () {
            return Promise.all([
                fetchLossMetric("runoff").then(function (data) { state.dataRunoff = state.dataRunoff || data; }),
                fetchLossMetric("subrunoff"),
                fetchLossMetric("baseflow"),
                fetchLossMetric("loss").then(function (data) { state.dataLoss = data; })
            ]);
        };

        function renderPhosphorus() {
            requestJson("query/wepp/phosphorus/subcatchments/")
                .then(function (data) {
                    state.dataPhosphorus = data;
                    state.cmapMode = "phosphorus";
                    refreshGlLayer();
                })
                .catch(handleError);
        }

        function renderAshLoad() {
            requestJson("query/ash/out/")
                .then(function (data) {
                    state.dataAshLoad = data;
                    state.cmapMode = "ash_load";
                    state.ashMeasure = getAshTransportMeasure();
                    refreshGlLayer();
                })
                .catch(handleError);
        }

        function renderAshTransport() {
            requestJson("query/ash_out/")
                .then(function (data) {
                    state.dataAshTransport = data;
                    state.cmapMode = "ash_transport";
                    refreshGlLayer();
                })
                .catch(handleError);
        }
        function renderAshTransportWater() {
            renderAshTransport();
        }

        function renderRhemRunoff() {
            requestJson("query/rhem/runoff/subcatchments/")
                .then(function (data) {
                    state.dataRhemRunoff = data;
                    state.cmapMode = "rhem_runoff";
                    refreshGlLayer();
                })
                .catch(handleError);
        }

        function renderRhemSedYield() {
            requestJson("query/rhem/sed_yield/subcatchments/")
                .then(function (data) {
                    state.dataRhemSedYield = data;
                    state.cmapMode = "rhem_sed_yield";
                    refreshGlLayer();
                })
                .catch(handleError);
        }

        function renderRhemSoilLoss() {
            requestJson("query/rhem/soil_loss/subcatchments/")
                .then(function (data) {
                    state.dataRhemSoilLoss = data;
                    state.cmapMode = "rhem_soil_loss";
                    refreshGlLayer();
                })
                .catch(handleError);
        }

        sub.build = function () {
            var map = MapController.getInstance();
            var taskMsg = "Building Subcatchments";

            resetStatus(taskMsg);
            sub.connect_status_stream(sub);

            disposeGlLayer();
            removeGrid();

            if (map && typeof map.ctrls === "object" && map.ctrls.removeLayer) {
                try {
                    map.ctrls.removeLayer(state.labels);
                } catch (err) {
                    console.warn("[Subcatchment] Failed to remove labels", err);
                }
            }

            emit("subcatchment:build:started", {});

            var payload = forms.serializeForm(formElement, { format: "json" }) || {};

            http.postJson("rq/api/build_subcatchments_and_abstract_watershed", payload, { form: formElement })
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && response.Success === true) {
                        if (statusAdapter && typeof statusAdapter.html === "function") {
                            statusAdapter.html("build_subcatchments_and_abstract_watershed_rq job submitted: " + response.job_id);
                        } else {
                            safeHtml(statusElement, "build_subcatchments_and_abstract_watershed_rq job submitted: " + response.job_id);
                        }
                        sub.set_rq_job_id(sub, response.job_id);
                    } else if (response) {
                        sub.pushResponseStacktrace(sub, response);
                    }
                })
                .catch(function (error) {
                    var payload = handleError(error);
                    emit("subcatchment:build:error", { error: payload });
                });
        };

        sub.report = function () {
            var project = Project.getInstance();
            var taskMsg = "Fetching Summary";

            if (infoAdapter && typeof infoAdapter.text === "function") {
                infoAdapter.text("");
            } else {
                safeText(infoElement, "");
            }
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(taskMsg + "...");
            } else {
                safeHtml(statusElement, taskMsg + "...");
            }
            if (stacktraceAdapter && typeof stacktraceAdapter.text === "function") {
                stacktraceAdapter.text("");
            } else {
                safeText(stacktraceElement, "");
            }

            http.request(url_for_run("report/watershed/"), {
                method: "GET",
                headers: { Accept: "text/html,application/xhtml+xml" }
            }).then(function (result) {
                var html = typeof result.body === "string" ? result.body : "";
                if (infoAdapter && typeof infoAdapter.html === "function") {
                    infoAdapter.html(html);
                } else {
                    safeHtml(infoElement, html);
                }
                if (statusAdapter && typeof statusAdapter.html === "function") {
                    statusAdapter.html(taskMsg + "... Success");
                } else {
                    safeHtml(statusElement, taskMsg + "... Success");
                }
                emit("subcatchment:report:loaded", {});
                if (project && typeof project.set_preferred_units === "function") {
                    project.set_preferred_units();
                }
            }).catch(handleError);
        };

        setupDelegatedEvents();
        bindDirectFallbackListeners();

        sub.renderSlpAsp = renderSlpAsp;
        sub.renderLanduse = renderLanduse;
        sub.renderRangelandCover = renderRangelandCover;
        sub.renderSoils = renderSoils;
        sub.renderCover = renderCover;
        sub.renderRunoff = renderRunoff;
        sub.renderSubrunoff = renderSubrunoff;
        sub.renderBaseflow = renderBaseflow;
        sub.renderLoss = renderLoss;
        sub.renderPhosphorus = renderPhosphorus;
        sub.renderAshLoad = renderAshLoad;
        sub.renderAshTransport = renderAshTransport;
        sub.renderAshTransportWater = renderAshTransportWater;
        sub.renderRhemRunoff = renderRhemRunoff;
        sub.renderRhemSedYield = renderRhemSedYield;
        sub.renderRhemSoilLoss = renderRhemSoilLoss;

        return sub;
    }

    return {
        getInstance: function () {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        }
    };
})();

if (typeof globalThis !== "undefined") {
    globalThis.SubcatchmentDelineation = SubcatchmentDelineation;
}
