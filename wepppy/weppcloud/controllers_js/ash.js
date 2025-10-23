/* ----------------------------------------------------------------------------
 * Ash
 * ----------------------------------------------------------------------------
 */
var Ash = (function () {
    var instance;

    var DEPTH_MODE_IDS = {
        0: "ash_depth_mode0_controls",
        1: "ash_depth_mode1_controls",
        2: "ash_depth_mode2_controls"
    };

    var EVENT_NAMES = [
        "ash:mode:changed",
        "ash:model:changed",
        "ash:transport:mode",
        "ash:run:started",
        "ash:run:completed",
        "ash:model:values:capture"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function") {
            throw new Error("Ash controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Ash controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("Ash controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Ash controller requires WCEvents helpers.");
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

    function parseDepthMode(value, fallback) {
        if (value === undefined || value === null || value === "") {
            return fallback;
        }
        var parsed = parseInt(value, 10);
        if (Number.isNaN(parsed)) {
            return fallback;
        }
        return parsed;
    }

    function readModelParams(dom) {
        var scriptNode = dom.qs("#ash-model-params-data");
        if (scriptNode && scriptNode.textContent) {
            try {
                return JSON.parse(scriptNode.textContent);
            } catch (err) {
                console.warn("Unable to parse ash model params payload", err);
            }
        }
        if (typeof window.modelParams !== "undefined") {
            return window.modelParams;
        }
        return {};
    }

    function applyReadonlyMarkers(formElement) {
        if (!formElement) {
            return;
        }
        var nodes = formElement.querySelectorAll("[data-disable-readonly]");
        nodes.forEach(function (node) {
            node.classList.add("disable-readonly");
            node.removeAttribute("data-disable-readonly");
        });
    }

    function ensureModelCache(cache, model) {
        if (!cache[model]) {
            cache[model] = {
                white: {},
                black: {}
            };
        }
        return cache[model];
    }

    function mergeModelValues(base, overrides) {
        var result = {};
        Object.keys(base || {}).forEach(function (key) {
            result[key] = base[key];
        });
        Object.keys(overrides || {}).forEach(function (key) {
            if (overrides[key] !== undefined) {
                result[key] = overrides[key];
            }
        });
        return result;
    }

    function storeModelValue(cache, input) {
        if (!input || !input.id) {
            return;
        }
        var separator = input.id.indexOf("_");
        if (separator <= 0) {
            return;
        }
        var color = input.id.slice(0, separator);
        if (color !== "white" && color !== "black") {
            return;
        }
        var key = input.id.slice(separator + 1);
        cache[color][key] = input.value;
    }

    function captureModelValues(formElement, cache, model, transportModeEl) {
        if (!model) {
            return;
        }
        var store = ensureModelCache(cache, model);
        if (transportModeEl && model === "alex") {
            store.transport_mode = transportModeEl.value || "dynamic";
        }
        var inputs = formElement.querySelectorAll("input");
        inputs.forEach(function (input) {
            storeModelValue(store, input);
        });
    }

    function toggleNodes(dom, nodes, shouldShow) {
        nodes.forEach(function (node) {
            if (!node) {
                return;
            }
            if (shouldShow) {
                dom.show(node);
            } else {
                dom.hide(node);
            }
        });
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var eventsApi = helpers.events;

        var ash = controlBase();
        var emitter = eventsApi.useEventMap(EVENT_NAMES, eventsApi.createEmitter());

        var formElement = dom.ensureElement("#ash_form", "Ash form not found.");
        var infoElement = dom.qs("#ash_form #info");
        var statusElement = dom.qs("#ash_form #status");
        var stacktraceElement = dom.qs("#ash_form #stacktrace");
        var rqJobElement = dom.qs("#ash_form #rq_job");
        var hintElement = dom.qs("#hint_run_ash");
        var spinnerElement = dom.qs("#ash_form #braille");

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);
        var hintAdapter = createLegacyAdapter(hintElement);

        ash.form = formElement;
        ash.info = infoAdapter;
        ash.status = statusAdapter;
        ash.stacktrace = stacktraceAdapter;
        ash.rq_job = rqJobAdapter;
        ash.command_btn_id = "btn_run_ash";
        ash.hint = hintAdapter;
        ash.events = emitter;
        ash.statusSpinnerEl = spinnerElement;

        ash.attach_status_stream(ash, {
            form: formElement,
            channel: "ash",
            runId: window.runid || window.runId || null,
            spinner: spinnerElement
        });
        ash.rq_job_id = null;

        var depthModeInputs = dom.qsa('input[name="ash_depth_mode"]', formElement);
        var modelSelectEl = dom.qs('[data-ash-action="model-select"]', formElement) || dom.qs("#ash_model_select", formElement);
        var transportModeEl = dom.qs('[data-ash-action="transport-select"]', formElement) || dom.qs("#ash_transport_mode_select", formElement);
        var windCheckboxEl = dom.qs('[data-ash-action="toggle-wind"]', formElement) || dom.qs("#checkbox_run_wind_transport", formElement);

        var alexOnlyNodes = dom.qsa(".alex-only-param", formElement);
        var anuOnlyNodes = dom.qsa(".anu-only-param", formElement);
        var alexDynamicNodes = dom.qsa(".alex-dynamic-param", formElement);
        var alexStaticNodes = dom.qsa(".alex-static-param", formElement);
        var dynamicDescription = dom.qs("#dynamic_description", formElement);
        var staticDescription = dom.qs("#static_description", formElement);

        var depthModeContainers = {};
        Object.keys(DEPTH_MODE_IDS).forEach(function (key) {
            depthModeContainers[key] = dom.qs("#" + DEPTH_MODE_IDS[key], formElement);
        });

        var modelParams = readModelParams(dom);
        var modelValuesCache = {};

        var initialDepthMode = (function () {
            var checked = depthModeInputs.find(function (input) {
                return input && input.checked;
            });
            return checked ? checked.value : undefined;
        })();

        var state = {
            depthMode: parseDepthMode(initialDepthMode, 0),
            currentModel: modelSelectEl ? modelSelectEl.value || "multi" : "multi"
        };

        ash.ash_depth_mode = state.depthMode;
        ensureModelCache(modelValuesCache, state.currentModel);

        applyReadonlyMarkers(formElement);

        function resetStatus(taskMsg) {
            if (infoAdapter && typeof infoAdapter.text === "function") {
                infoAdapter.text("");
            }
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(taskMsg + "...");
            }
            if (stacktraceAdapter && typeof stacktraceAdapter.text === "function") {
                stacktraceAdapter.text("");
            }
        }

        function handleError(error, context) {
            var payload = toResponsePayload(http, error);
            ash.pushResponseStacktrace(ash, payload);
            var eventPayload = { jobId: null, error: payload };
            if (context && context.snapshot) {
                eventPayload.payload = context.snapshot;
            }
            emitter.emit("ash:run:completed", eventPayload);
        }

        function updateDepthModeUI(shouldEmit) {
            depthModeInputs.forEach(function (input) {
                if (!input) {
                    return;
                }
                input.checked = parseInt(input.value, 10) === state.depthMode;
            });

            var activeMode = Object.prototype.hasOwnProperty.call(DEPTH_MODE_IDS, state.depthMode)
                ? state.depthMode
                : 0;

            Object.keys(depthModeContainers).forEach(function (key) {
                var container = depthModeContainers[key];
                if (!container) {
                    return;
                }
                if (parseInt(key, 10) === activeMode) {
                    dom.show(container);
                } else {
                    dom.hide(container);
                }
            });

            if (shouldEmit) {
                emitter.emit("ash:mode:changed", { mode: state.depthMode });
            }
        }

        function toggleModelPanels(isAlex) {
            toggleNodes(dom, alexOnlyNodes, isAlex);
            toggleNodes(dom, anuOnlyNodes, !isAlex);
            if (!isAlex) {
                toggleNodes(dom, alexDynamicNodes, false);
                toggleNodes(dom, alexStaticNodes, false);
                if (dynamicDescription) {
                    dom.hide(dynamicDescription);
                }
                if (staticDescription) {
                    dom.hide(staticDescription);
                }
            }
        }

        function updateTransportModeUI(mode, shouldEmit) {
            if (!transportModeEl) {
                return;
            }
            transportModeEl.value = mode;
            if (state.currentModel !== "alex") {
                return;
            }
            var isDynamic = mode === "dynamic";
            toggleNodes(dom, alexDynamicNodes, isDynamic);
            toggleNodes(dom, alexStaticNodes, !isDynamic);
            if (dynamicDescription) {
                if (isDynamic) {
                    dom.show(dynamicDescription);
                } else {
                    dom.hide(dynamicDescription);
                }
            }
            if (staticDescription) {
                if (isDynamic) {
                    dom.hide(staticDescription);
                } else {
                    dom.show(staticDescription);
                }
            }
            if (shouldEmit) {
                emitter.emit("ash:transport:mode", {
                    model: state.currentModel,
                    transportMode: mode
                });
            }
        }

        function storeCurrentModelValue(input) {
            if (!state.currentModel) {
                return;
            }
            var cache = ensureModelCache(modelValuesCache, state.currentModel);
            storeModelValue(cache, input);
        }

        function setDepthMode(mode, emit) {
            var parsed = parseDepthMode(mode, state.depthMode || 0);
            if (state.depthMode === parsed) {
                updateDepthModeUI(false);
                return;
            }
            state.depthMode = parsed;
            ash.ash_depth_mode = parsed;
            ash.clearHint();
            updateDepthModeUI(emit);
        }

        function updateModelFormImpl(options) {
            options = options || {};
            if (!modelSelectEl) {
                return;
            }

            var selectedModel = modelSelectEl.value || "multi";
            var previousModel = state.currentModel;
            var capturePrevious = options.capturePrevious !== false;
            var shouldEmit = options.emit !== false;

            if (capturePrevious && previousModel && previousModel !== selectedModel) {
                captureModelValues(formElement, modelValuesCache, previousModel, transportModeEl);
                emitter.emit("ash:model:values:capture", { model: previousModel });
            }

            state.currentModel = selectedModel;
            ash.currentModel = selectedModel;

            var cache = ensureModelCache(modelValuesCache, selectedModel);
            var paramsForModel = modelParams[selectedModel] || {};
            var isAlex = selectedModel === "alex";

            toggleModelPanels(isAlex);

            if (transportModeEl) {
                if (isAlex) {
                    var mode = cache.transport_mode || transportModeEl.value || "dynamic";
                    transportModeEl.value = mode;
                    updateTransportModeUI(mode, shouldEmit);
                } else {
                    updateTransportModeUI(transportModeEl.value || "dynamic", false);
                }
            }

            ["white", "black"].forEach(function (color) {
                var mergedValues = mergeModelValues(paramsForModel[color] || {}, cache[color] || {});
                Object.keys(mergedValues).forEach(function (key) {
                    var inputId = "#" + color + "_" + key;
                    var input = dom.qs(inputId, formElement);
                    if (input) {
                        input.value = mergedValues[key];
                    }
                });
            });

            if (shouldEmit && previousModel !== selectedModel) {
                emitter.emit("ash:model:changed", {
                    model: selectedModel,
                    previousModel: previousModel
                });
            }
        }

        ash.hideStacktrace = function () {
            if (stacktraceAdapter && typeof stacktraceAdapter.hide === "function") {
                stacktraceAdapter.hide();
                return;
            }
            if (stacktraceElement) {
                stacktraceElement.hidden = true;
                stacktraceElement.style.display = "none";
            }
        };

        ash.clearHint = function () {
            if (hintAdapter && typeof hintAdapter.text === "function") {
                hintAdapter.text("");
            }
        };

        ash.showHint = function (message) {
            if (hintAdapter && typeof hintAdapter.text === "function") {
                hintAdapter.text(message || "");
            }
        };

        ash.setAshDepthMode = function (mode) {
            setDepthMode(mode, true);
        };

        ash.handleDepthModeChange = function (mode) {
            ash.setAshDepthMode(mode);
        };

        ash.showHideControls = function () {
            updateDepthModeUI(false);
        };

        ash.updateModelForm = function (options) {
            updateModelFormImpl(options || {});
        };

        ash.validateBeforeRun = function () {
            ash.clearHint();

            if (state.depthMode === undefined) {
                var checked = depthModeInputs.find(function (input) {
                    return input && input.checked;
                });
                state.depthMode = parseDepthMode(checked ? checked.value : undefined, 0);
                ash.ash_depth_mode = state.depthMode;
            }

            if (state.depthMode === 2) {
                var errors = [];
                var allowedExtensions = [".tif", ".tiff", ".img"];
                var maxBytes = 100 * 1024 * 1024;
                var loadInput = dom.qs("#input_upload_ash_load", formElement);
                var typeInput = dom.qs("#input_upload_ash_type_map", formElement);
                [loadInput, typeInput].forEach(function (input) {
                    if (!input || !input.files || !input.files.length) {
                        return;
                    }
                    var file = input.files[0];
                    var name = (file.name || "").toLowerCase();
                    var hasAllowedExt = allowedExtensions.some(function (ext) {
                        return name.endsWith(ext);
                    });
                    if (!hasAllowedExt) {
                        errors.push(file.name + " must be a .tif, .tiff, or .img file.");
                    }
                    if (file.size > maxBytes) {
                        errors.push(file.name + " exceeds the 100 MB upload limit.");
                    }
                });
                if (errors.length) {
                    ash.showHint(errors.join(" "));
                    return false;
                }
            }

            return true;
        };

        ash.run = function () {
            var taskMsg = "Running ash model";
            resetStatus(taskMsg);

            if (!ash.validateBeforeRun()) {
                return;
            }

            ash.connect_status_stream(ash);

            var formData;
            var payloadSnapshot = null;
            try {
                formData = new FormData(formElement);
            } catch (err) {
                handleError(err, { snapshot: payloadSnapshot });
                return;
            }

            if (forms && typeof forms.formToJSON === "function") {
                try {
                    payloadSnapshot = forms.formToJSON(formElement);
                } catch (_err) {
                    payloadSnapshot = null;
                }
            }

            http.request("rq/api/run_ash", {
                method: "POST",
                body: formData,
                form: formElement
            }).then(function (response) {
                var payload = response.body || {};
                if (payload.Success === true) {
                    statusAdapter.html("run_ash job submitted: " + payload.job_id);
                    ash.set_rq_job_id(ash, payload.job_id);
                    ash.rq_job_id = payload.job_id;
                    emitter.emit("ash:run:started", {
                        jobId: payload.job_id,
                        payload: payloadSnapshot
                    });
                } else {
                    ash.pushResponseStacktrace(ash, payload);
                    var failureEvent = { jobId: null, error: payload };
                    if (payloadSnapshot) {
                        failureEvent.payload = payloadSnapshot;
                    }
                    emitter.emit("ash:run:completed", failureEvent);
                }
            }).catch(function (error) {
                handleError(error, { snapshot: payloadSnapshot });
            });
        };

        ash.set_wind_transport = function (state) {
            var taskMsg = "Setting wind_transport(" + state + ")";
            resetStatus(taskMsg);

            http.postJson("tasks/set_ash_wind_transport/", {
                run_wind_transport: Boolean(state)
            }, {
                form: formElement
            }).then(function (response) {
                var payload = response.body || {};
                if (payload.Success === true || payload.success === true) {
                    statusAdapter.html(taskMsg + "... Success");
                } else {
                    ash.pushResponseStacktrace(ash, payload);
                }
            }).catch(function (error) {
                var payload = toResponsePayload(http, error);
                ash.pushResponseStacktrace(ash, payload);
            });
        };

        ash.report = function () {
            var taskMsg = "Fetching Summary";
            resetStatus(taskMsg);

            var project = null;
            try {
                if (window.Project && typeof window.Project.getInstance === "function") {
                    project = window.Project.getInstance();
                }
            } catch (err) {
                console.warn("Ash controller unable to load Project instance", err);
            }

            var url = typeof window.url_for_run === "function"
                ? window.url_for_run("report/run_ash/")
                : "report/run_ash/";

            http.request(url, { method: "GET" }).then(function (response) {
                infoAdapter.html(response.body || "");
                statusAdapter.html(taskMsg + "... Success");
                if (project && typeof project.set_preferred_units === "function") {
                    project.set_preferred_units();
                }
            }).catch(function (error) {
                var payload = toResponsePayload(http, error);
                ash.pushResponseStacktrace(ash, payload);
            });
        };

        var baseTriggerEvent = ash.triggerEvent.bind(ash);
        ash.triggerEvent = function (eventName, payload) {
            if (eventName === "ASH_RUN_TASK_COMPLETED") {
                ash.disconnect_status_stream(ash);
                ash.report();
                emitter.emit("ash:run:completed", {
                    jobId: ash.rq_job_id || null,
                    payload: payload || null
                });
            }
            baseTriggerEvent(eventName, payload);
        };

        dom.delegate(formElement, "change", 'input[name="ash_depth_mode"]', function (event, matched) {
            setDepthMode(matched.value, true);
        });

        dom.delegate(formElement, "click", '[data-ash-action="run"]', function (event) {
            event.preventDefault();
            ash.run();
        });

        dom.delegate(formElement, "change", '[data-ash-action="toggle-wind"]', function (event, checkbox) {
            ash.set_wind_transport(checkbox.checked);
        });

        if (modelSelectEl) {
            dom.delegate(formElement, "change", '[data-ash-action="model-select"]', function () {
                updateModelFormImpl({ capturePrevious: true, emit: true });
            });
        }

        if (transportModeEl) {
            dom.delegate(formElement, "change", '[data-ash-action="transport-select"]', function (event, select) {
                var cache = ensureModelCache(modelValuesCache, state.currentModel);
                cache.transport_mode = select.value || "dynamic";
                updateTransportModeUI(select.value || "dynamic", true);
            });
        }

        dom.delegate(formElement, "change", "input", function (event, input) {
            storeCurrentModelValue(input);
        });

        dom.delegate(formElement, "change", 'input[type="file"][data-ash-upload]', function () {
            ash.clearHint();
        });

        setDepthMode(state.depthMode, false);
        updateModelFormImpl({ capturePrevious: false, emit: false });
        if (transportModeEl && state.currentModel === "alex") {
            updateTransportModeUI(transportModeEl.value || "dynamic", false);
        }

        return ash;
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

if (typeof window !== "undefined") {
    window.Ash = Ash;
} else if (typeof globalThis !== "undefined") {
    globalThis.Ash = Ash;
}
