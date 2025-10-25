/* ----------------------------------------------------------------------------
 * Baer
 * Doc: controllers_js/README.md — BAER Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var Baer = (function () {
    var instance;

    var MODE_PANELS = {
        0: "#sbs_mode0_controls",
        1: "#sbs_mode1_controls"
    };

    var EVENT_NAMES = [
        "baer:mode:changed",
        "baer:upload:started",
        "baer:upload:completed",
        "baer:upload:error",
        "baer:remove:started",
        "baer:remove:completed",
        "baer:remove:error",
        "baer:uniform:started",
        "baer:uniform:completed",
        "baer:uniform:error",
        "baer:firedate:updated",
        "baer:firedate:error",
        "baer:classes:updated",
        "baer:classes:error",
        "baer:color-map:updated",
        "baer:color-map:error",
        "baer:map:shown",
        "baer:map:error",
        "baer:map:opacity"
    ];

    var DEFAULT_OPACITY = 0.7;
    var LEGEND_OPACITY_CONTAINER_ID = "baer-opacity-controls";
    var LEGEND_OPACITY_INPUT_ID = "baer-opacity-slider";

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function") {
            throw new Error("Baer controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Baer controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("Baer controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Baer controller requires WCEvents helpers.");
        }

        return { dom: dom, forms: forms, http: http, events: events };
    }

    function normalizeElement(target) {
        if (!target) {
            return null;
        }
        if (typeof window.Node !== "undefined" && target instanceof window.Node) {
            return target;
        }
        if (typeof window.Element !== "undefined" && target instanceof window.Element) {
            return target;
        }
        if (target.jquery !== undefined && typeof target.get === "function") {
            return target.get(0);
        }
        if (Array.isArray(target) && target.length > 0) {
            var first = target[0];
            if (typeof window.Node !== "undefined" && first instanceof window.Node) {
                return first;
            }
        }
        return null;
    }

    function createLegacyAdapter(target) {
        var element = normalizeElement(target);
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

    function parseInteger(value, fallback) {
        if (value === undefined || value === null || value === "") {
            return fallback;
        }
        var parsed = parseInt(value, 10);
        if (Number.isNaN(parsed)) {
            return fallback;
        }
        return parsed;
    }

    function clampOpacity(value) {
        var parsed = parseFloat(value);
        if (Number.isNaN(parsed)) {
            return DEFAULT_OPACITY;
        }
        if (parsed < 0) {
            return 0;
        }
        if (parsed > 1) {
            return 1;
        }
        return parsed;
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var events = helpers.events;

        var baer = controlBase();
        var baerEvents = null;

        if (events && typeof events.createEmitter === "function") {
            var emitterBase = events.createEmitter();
            if (typeof events.useEventMap === "function") {
                baerEvents = events.useEventMap(EVENT_NAMES, emitterBase);
            } else {
                baerEvents = emitterBase;
            }
        }

        if (baerEvents) {
            baer.events = baerEvents;
        }

        var formElement = dom.qs("#sbs_upload_form");
        var infoElement = formElement ? dom.qs("#info", formElement) : null;
        var statusElement = formElement ? dom.qs("#status", formElement) : null;
        var stacktraceElement = formElement ? dom.qs("#stacktrace", formElement) : null;
        var rqJobElement = formElement ? dom.qs("#rq_job", formElement) : null;
        var spinnerElement = formElement ? dom.qs("#braille", formElement) : null;

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);

        var modePanelElements = {};
        Object.keys(MODE_PANELS).forEach(function (key) {
            modePanelElements[key] = dom.qs(MODE_PANELS[key]);
        });

        baer.form = formElement || null;
        baer.info = infoAdapter;
        baer.status = statusAdapter;
        baer.stacktrace = stacktraceAdapter;
        baer.rq_job = rqJobAdapter;
        baer.infoElement = infoElement;
        baer.baer_map = null;
        baer.statusSpinnerEl = spinnerElement;

        baer.attach_status_stream(baer, {
            form: formElement,
            channel: "sbs_upload",
            runId: window.runid || window.runId || null,
            spinner: spinnerElement
        });

        baer.hideStacktrace = function () {
            if (stacktraceAdapter && typeof stacktraceAdapter.hide === "function") {
                stacktraceAdapter.hide();
                return;
            }
            if (stacktraceElement) {
                stacktraceElement.hidden = true;
                stacktraceElement.style.display = "none";
            }
        };

        function emit(name, payload) {
            if (!baerEvents || typeof baerEvents.emit !== "function" || !name) {
                return;
            }
            baerEvents.emit(name, payload || {});
        }

        function startTask(message) {
            if (infoAdapter && typeof infoAdapter.html === "function") {
                infoAdapter.html("");
            }
            if (statusAdapter && typeof statusAdapter.text === "function") {
                statusAdapter.text(message + "...");
            }
            if (stacktraceAdapter && typeof stacktraceAdapter.text === "function") {
                stacktraceAdapter.text("");
            }
            baer.hideStacktrace();
        }

        function completeTask(message) {
            if (statusAdapter && typeof statusAdapter.text === "function") {
                statusAdapter.text(message + "... Success");
            }
        }

        function failTask(message) {
            if (statusAdapter && typeof statusAdapter.text === "function") {
                statusAdapter.text(message + "... Failed");
            }
        }

        function jobStarted(task, extra) {
            baer.triggerEvent("job:started", Object.assign({ task: task }, extra || {}));
        }

        function jobCompleted(task, extra) {
            baer.triggerEvent("job:completed", Object.assign({ task: task }, extra || {}));
        }

        function jobErrored(task, extra) {
            baer.triggerEvent("job:error", Object.assign({ task: task }, extra || {}));
        }

        function showHideControls(mode) {
            if (mode === -1) {
                Object.keys(modePanelElements).forEach(function (key) {
                    var panel = modePanelElements[key];
                    if (panel) {
                        dom.hide(panel);
                    }
                });
                emit("baer:mode:changed", { mode: mode });
                return;
            }
            var normalized = parseInteger(mode, 0);
            if (!Object.prototype.hasOwnProperty.call(modePanelElements, String(normalized))) {
                throw new Error("ValueError: BAER unknown mode");
            }
            Object.keys(modePanelElements).forEach(function (key) {
                var panel = modePanelElements[key];
                if (!panel) {
                    return;
                }
                if (String(key) === String(normalized)) {
                    dom.show(panel);
                } else {
                    dom.hide(panel);
                }
            });
            emit("baer:mode:changed", { mode: normalized });
        }

        function initializeMode() {
            if (!formElement) {
                showHideControls(-1);
                return;
            }
            var selected = formElement.querySelector("input[name='sbs_mode']:checked");
            if (!selected) {
                selected = formElement.querySelector("input[name='sbs_mode']");
                if (selected) {
                    selected.checked = true;
                }
            }
            var modeValue = selected ? parseInteger(selected.value, 0) : 0;
            showHideControls(modeValue);
        }

        function setFireDate(fireDate) {
            var taskMsg = "Setting Fire Date";
            startTask(taskMsg);

            var effectiveFireDate = fireDate;
            if (!effectiveFireDate && formElement && forms && typeof forms.serializeForm === "function") {
                var formValues = forms.serializeForm(formElement, { format: "object" }) || {};
                if (formValues && Object.prototype.hasOwnProperty.call(formValues, "firedate")) {
                    effectiveFireDate = formValues.firedate;
                }
            }

            return http.request(url_for_run("tasks/set_firedate/"), {
                method: "POST",
                json: { fire_date: effectiveFireDate || null },
                form: formElement
            })
                .then(function (result) {
                    var data = result.body || {};
                    if (data.Success === true) {
                        completeTask(taskMsg);
                        emit("baer:firedate:updated", { fireDate: effectiveFireDate || null });
                        return data;
                    }
                    baer.pushResponseStacktrace(baer, data);
                    failTask(taskMsg);
                    emit("baer:firedate:error", { response: data });
                    return data;
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    baer.pushResponseStacktrace(baer, payload);
                    failTask(taskMsg);
                    emit("baer:firedate:error", { error: payload });
                    return payload;
                });
        }

        function uploadSbs() {
            if (!formElement) {
                return Promise.resolve(null);
            }

            var taskMsg = "Uploading SBS";
            startTask(taskMsg);
            var formData = new window.FormData(formElement);

            emit("baer:upload:started", {});
            jobStarted("baer:upload", {});

            return http.request(url_for_run("tasks/upload_sbs/"), {
                method: "POST",
                body: formData,
                form: formElement
            })
                .then(function (result) {
                    var data = result.body || {};
                    if (data.Success === true) {
                        completeTask(taskMsg);
                        baer.triggerEvent("SBS_UPLOAD_TASK_COMPLETE", data);
                        emit("baer:upload:completed", { response: data });
                        jobCompleted("baer:upload", { response: data });
                        return data;
                    }
                    baer.pushResponseStacktrace(baer, data);
                    failTask(taskMsg);
                    emit("baer:upload:error", { response: data });
                    jobErrored("baer:upload", { response: data });
                    return data;
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    baer.pushResponseStacktrace(baer, payload);
                    failTask(taskMsg);
                    emit("baer:upload:error", { error: payload });
                    jobErrored("baer:upload", { error: payload });
                    return payload;
                });
        }

        function removeSbs() {
            var taskMsg = "Removing SBS";
            startTask(taskMsg);

            emit("baer:remove:started", {});
            jobStarted("baer:remove", {});

            return http.request(url_for_run("tasks/remove_sbs"), {
                method: "POST",
                form: formElement
            })
                .then(function (result) {
                    var data = result.body || {};
                    if (data.Success === true) {
                        completeTask(taskMsg);
                        baer.triggerEvent("SBS_REMOVE_TASK_COMPLETE", data);
                        emit("baer:remove:completed", { response: data });
                        jobCompleted("baer:remove", { response: data });

                        try {
                            var map = MapController.getInstance();
                            if (baer.baer_map) {
                                if (map && map.ctrls && typeof map.ctrls.removeLayer === "function") {
                                    map.ctrls.removeLayer(baer.baer_map);
                                }
                                if (map && typeof map.removeLayer === "function") {
                                    map.removeLayer(baer.baer_map);
                                }
                                baer.baer_map = null;
                            }
                        } catch (err) {
                            console.warn("[Baer] Failed to remove SBS layer from map", err);
                        }

                        if (infoAdapter && typeof infoAdapter.html === "function") {
                            infoAdapter.html("");
                        }

                        return data;
                    }
                    baer.pushResponseStacktrace(baer, data);
                    failTask(taskMsg);
                    emit("baer:remove:error", { response: data });
                    jobErrored("baer:remove", { response: data });
                    return data;
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    baer.pushResponseStacktrace(baer, payload);
                    failTask(taskMsg);
                    emit("baer:remove:error", { error: payload });
                    jobErrored("baer:remove", { error: payload });
                    return payload;
                });
        }

        function buildUniformSbs(value) {
            var severity = parseInteger(value, null);
            if (severity === null) {
                return Promise.resolve(null);
            }

            var taskMsg = "Setting Uniform SBS";
            startTask(taskMsg);

            emit("baer:uniform:started", { value: severity });
            jobStarted("baer:uniform", { value: severity });

            return http.request(url_for_run("tasks/build_uniform_sbs/") + severity, {
                method: "POST",
                form: formElement
            })
                .then(function (result) {
                    var data = result.body || {};
                    if (data.Success === true) {
                        completeTask(taskMsg);
                        baer.triggerEvent("SBS_UPLOAD_TASK_COMPLETE", data);
                        emit("baer:uniform:completed", { response: data, value: severity });
                        jobCompleted("baer:uniform", { response: data, value: severity });
                        return data;
                    }
                    baer.pushResponseStacktrace(baer, data);
                    failTask(taskMsg);
                    emit("baer:uniform:error", { response: data, value: severity });
                    jobErrored("baer:uniform", { response: data, value: severity });
                    return data;
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    baer.pushResponseStacktrace(baer, payload);
                    failTask(taskMsg);
                    emit("baer:uniform:error", { error: payload, value: severity });
                    jobErrored("baer:uniform", { error: payload, value: severity });
                    return payload;
                });
        }

        function loadModifyClass() {
            return http.request(url_for_run("view/modify_burn_class"), {
                method: "GET"
            })
                .then(function (result) {
                    var content = result.body;
                    if (infoAdapter && typeof infoAdapter.html === "function") {
                        infoAdapter.html(content);
                    } else if (infoElement) {
                        infoElement.innerHTML = content === null || content === undefined ? "" : String(content);
                    }
                    return content;
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    baer.pushResponseStacktrace(baer, payload);
                    return payload;
                });
        }

        function readClassBreaks(values) {
            var names = ["baer_brk0", "baer_brk1", "baer_brk2", "baer_brk3"];
            return names.map(function (name) {
                var raw = values && Object.prototype.hasOwnProperty.call(values, name) ? values[name] : null;
                if (raw === null || raw === undefined) {
                    var element = dom.qs("#" + name);
                    raw = element ? element.value : null;
                }
                return parseInteger(raw, null);
            });
        }

        function modifyClasses() {
            var taskMsg = "Modifying Class Breaks";
            startTask(taskMsg);

            var formValues = {};
            if (formElement && forms && typeof forms.serializeForm === "function") {
                formValues = forms.serializeForm(formElement, { format: "object" }) || {};
            }
            var classBreaks = readClassBreaks(formValues);
            var nodataVals;
            if (formValues && Object.prototype.hasOwnProperty.call(formValues, "baer_nodata")) {
                nodataVals = formValues.baer_nodata;
            } else {
                var nodataField = dom.qs("#baer_nodata");
                nodataVals = nodataField ? nodataField.value : null;
            }

            return http.request(url_for_run("tasks/modify_burn_class"), {
                method: "POST",
                json: { classes: classBreaks, nodata_vals: nodataVals },
                form: formElement
            })
                .then(function (result) {
                    var data = result.body || {};
                    if (data.Success === true) {
                        completeTask(taskMsg);
                        baer.triggerEvent("MODIFY_BURN_CLASS_TASK_COMPLETE", data);
                        emit("baer:classes:updated", { response: data });
                        return data;
                    }
                    baer.pushResponseStacktrace(baer, data);
                    failTask(taskMsg);
                    emit("baer:classes:error", { response: data });
                    return data;
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    baer.pushResponseStacktrace(baer, payload);
                    failTask(taskMsg);
                    emit("baer:classes:error", { error: payload });
                    return payload;
                });
        }

        function modifyColorMap() {
            var taskMsg = "Modifying Class Breaks";
            startTask(taskMsg);

            var selects = document.querySelectorAll("select[id^='baer_color_']");
            var colorMap = {};
            selects.forEach(function (select) {
                var id = select.id || "";
                if (!id) {
                    return;
                }
                var rgb = id.replace("baer_color_", "");
                colorMap[rgb] = select.value;
            });

            return http.request(url_for_run("tasks/modify_color_map"), {
                method: "POST",
                json: { color_map: colorMap },
                form: formElement
            })
                .then(function (result) {
                    var data = result.body || {};
                    if (data.Success === true) {
                        completeTask(taskMsg);
                        baer.triggerEvent("MODIFY_BURN_CLASS_TASK_COMPLETE", data);
                        emit("baer:color-map:updated", { response: data });
                        return data;
                    }
                    baer.pushResponseStacktrace(baer, data);
                    failTask(taskMsg);
                    emit("baer:color-map:error", { response: data });
                    return data;
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    baer.pushResponseStacktrace(baer, payload);
                    failTask(taskMsg);
                    emit("baer:color-map:error", { error: payload });
                    return payload;
                });
        }

        function attachOpacitySlider(legendElement) {
            if (!legendElement) {
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
            var initialOpacity = baer.baer_map && typeof baer.baer_map.options === "object"
                ? clampOpacity(baer.baer_map.options.opacity)
                : DEFAULT_OPACITY;
            slider.value = String(initialOpacity);

            function updateOpacity(event) {
                if (!baer.baer_map) {
                    return;
                }
                var next = clampOpacity(event.target.value);
                baer.baer_map.setOpacity(next);
                emit("baer:map:opacity", { opacity: next });
            }

            slider.addEventListener("input", updateOpacity);
            slider.addEventListener("change", updateOpacity);

            container.appendChild(label);
            container.appendChild(slider);

            legendElement.appendChild(container);
        }

        function loadLegend() {
            return http.request(url_for_run("resources/legends/sbs/"), {
                method: "GET"
            })
                .then(function (result) {
                    var content = result.body;
                    var legend = dom.qs("#sbs_legend");
                    if (legend) {
                        legend.innerHTML = content === null || content === undefined ? "" : String(content);
                        attachOpacitySlider(legend);
                    }
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    baer.pushResponseStacktrace(baer, payload);
                });
        }

        function showSbs() {
            var taskMsg = "Querying SBS map";
            startTask(taskMsg);

            try {
                SubcatchmentDelineation.getInstance();
            } catch (err) {
                console.warn("[Baer] Unable to initialize SubcatchmentDelineation controller", err);
            }

            try {
                var map = MapController.getInstance();
                if (baer.baer_map) {
                    if (map && map.ctrls && typeof map.ctrls.removeLayer === "function") {
                        map.ctrls.removeLayer(baer.baer_map);
                    }
                    if (map && typeof map.removeLayer === "function") {
                        map.removeLayer(baer.baer_map);
                    }
                    baer.baer_map = null;
                }
            } catch (err) {
                console.warn("[Baer] Failed to clear existing SBS map overlay", err);
            }

            return http.request(url_for_run("query/baer_wgs_map/"), {
                method: "GET"
            })
                .then(function (result) {
                    var data = result.body || {};
                    if (data.Success === true && data.Content) {
                        completeTask(taskMsg);
                        var map;
                        try {
                            map = MapController.getInstance();
                        } catch (err) {
                            baer.pushErrorStacktrace(baer, err);
                            throw err;
                        }
                        var bounds = data.Content.bounds;
                        var imgurl = data.Content.imgurl ? data.Content.imgurl + "?v=" + Date.now() : null;

                        if (map && bounds && imgurl) {
                            baer.baer_map = L.imageOverlay(imgurl, bounds, { opacity: DEFAULT_OPACITY });
                            baer.baer_map.addTo(map);
                            if (map.ctrls && typeof map.ctrls.addOverlay === "function") {
                                map.ctrls.addOverlay(baer.baer_map, "Burn Severity Map");
                            }
                            emit("baer:map:shown", { bounds: bounds, imgurl: imgurl });
                        }

                        return http.request(url_for_run("query/has_dem/"), { method: "GET" })
                            .then(function (demResult) {
                                var hasDem = demResult.body;
                                if (hasDem === false && map && baer.baer_map && typeof map.flyToBounds === "function") {
                                    map.flyToBounds(baer.baer_map._bounds);
                                }
                                return data;
                            })
                            .catch(function (error) {
                                var payload = toResponsePayload(http, error);
                                baer.pushResponseStacktrace(baer, payload);
                                return data;
                            });
                    }

                    baer.pushResponseStacktrace(baer, data);
                    failTask(taskMsg);
                    emit("baer:map:error", { response: data });
                    return data;
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    baer.pushResponseStacktrace(baer, payload);
                    failTask(taskMsg);
                    emit("baer:map:error", { error: payload });
                    return payload;
                })
                .finally(function () {
                    loadLegend();
                });
        }

        function bindHandlers() {
            if (!formElement) {
                return;
            }
            if (formElement.dataset && formElement.dataset.baerHandlersBound === "true") {
                return;
            }
            if (formElement.dataset) {
                formElement.dataset.baerHandlersBound = "true";
            }

            dom.delegate(formElement, "change", "input[name='sbs_mode']", function (event, target) {
                var nextMode = parseInteger(target.value, 0);
                showHideControls(nextMode);
            });

            dom.delegate(formElement, "click", "[data-baer-action]", function (event, target) {
                event.preventDefault();
                var action = target.getAttribute("data-baer-action");
                if (!action) {
                    return;
                }
                if (action === "upload") {
                    uploadSbs();
                    return;
                }
                if (action === "remove") {
                    removeSbs();
                    return;
                }
                if (action === "build-uniform") {
                    var uniformValue = target.getAttribute("data-baer-uniform");
                    buildUniformSbs(uniformValue);
                    return;
                }
                if (action === "set-firedate") {
                    var selector = target.getAttribute("data-baer-target") || "#firedate";
                    var input = selector ? dom.qs(selector) : null;
                    var value = input ? input.value : null;
                    setFireDate(value);
                    return;
                }
                if (action === "load-classes") {
                    loadModifyClass();
                    return;
                }
                if (action === "modify-classes") {
                    modifyClasses();
                    return;
                }
                if (action === "modify-color-map") {
                    modifyColorMap();
                    return;
                }
                if (action === "show-map") {
                    showSbs();
                }
            });
        }

        baer.showHideControls = showHideControls;
        baer.initializeMode = initializeMode;
        baer.set_firedate = setFireDate;
        baer.upload_sbs = uploadSbs;
        baer.remove_sbs = removeSbs;
        baer.build_uniform_sbs = buildUniformSbs;
        baer.load_modify_class = loadModifyClass;
        baer.modify_classes = modifyClasses;
        baer.modify_color_map = modifyColorMap;
        baer.show_sbs = showSbs;

        bindHandlers();
        initializeMode();

        var bootstrapState = {
            listenersBound: false,
            initialSbsLoaded: false
        };

        baer.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var flags = ctx.flags || {};
            var initialHasSbs = Boolean(flags.initialHasSbs);
            var controllerContext = (ctx.controllers && ctx.controllers.baer) || {};

            var form = baer.form;
            if (form && !bootstrapState.listenersBound && typeof form.addEventListener === "function") {
                var attach = function (eventName, handler) {
                    form.addEventListener(eventName, handler);
                };

                attach("SBS_UPLOAD_TASK_COMPLETE", function () {
                    setTimeout(function () { baer.show_sbs(); }, 100);
                    setTimeout(function () { baer.load_modify_class(); }, 100);
                    try {
                        var disturbed = typeof Disturbed !== "undefined" ? Disturbed.getInstance() : null;
                        if (disturbed && typeof disturbed.set_has_sbs_cached === "function") {
                            disturbed.set_has_sbs_cached(true);
                        }
                    } catch (err) {
                        console.warn("[Baer] Failed to sync Disturbed controller after SBS upload", err);
                    }
                    if (flags) {
                        flags.initialHasSbs = true;
                    }
                });

                attach("SBS_REMOVE_TASK_COMPLETE", function () {
                    try {
                        var disturbed = typeof Disturbed !== "undefined" ? Disturbed.getInstance() : null;
                        if (disturbed && typeof disturbed.set_has_sbs_cached === "function") {
                            disturbed.set_has_sbs_cached(false);
                        }
                    } catch (err) {
                        console.warn("[Baer] Failed to sync Disturbed controller after SBS removal", err);
                    }
                    if (flags) {
                        flags.initialHasSbs = false;
                    }
                });

                attach("MODIFY_BURN_CLASS_TASK_COMPLETE", function () {
                    setTimeout(function () { baer.show_sbs(); }, 100);
                    setTimeout(function () { baer.load_modify_class(); }, 100);
                });

                bootstrapState.listenersBound = true;
            }

            if (initialHasSbs && !bootstrapState.initialSbsLoaded) {
                setTimeout(function () { baer.show_sbs(); }, 0);
                setTimeout(function () { baer.load_modify_class(); }, 0);
                bootstrapState.initialSbsLoaded = true;
            }

            if (typeof baer.showHideControls === "function") {
                var nextMode = controllerContext.mode;
                if (nextMode === undefined || nextMode === null) {
                    nextMode = 0;
                }
                baer.showHideControls(nextMode);
            }

            return baer;
        };

        return baer;
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
    globalThis.Baer = Baer;
}
