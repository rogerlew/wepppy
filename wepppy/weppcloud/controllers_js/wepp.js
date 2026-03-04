/* ----------------------------------------------------------------------------
 * Wepp
 * ----------------------------------------------------------------------------
 */
var Wepp = (function () {
    var instance;

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.qs !== "function" || typeof dom.ensureElement !== "function" || typeof dom.delegate !== "function") {
            throw new Error("Wepp controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Wepp controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("Wepp controller requires WCHttp helpers.");
        }
        if (typeof http.postJsonWithSessionToken !== "function") {
            throw new Error("Wepp controller requires WCHttp.postJsonWithSessionToken.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Wepp controller requires WCEvents helpers.");
        }

        return { dom: dom, forms: forms, http: http, events: events };
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
                } else if (content instanceof window.Node) {
                    element.appendChild(content);
                }
            },
            empty: function () {
                element.textContent = "";
            }
        };
    }

    function toResponsePayload(http, error) {
        function coerceBody(raw) {
            if (!raw) {
                return null;
            }
            if (typeof raw === "string") {
                try {
                    return JSON.parse(raw);
                } catch (err) {
                    return raw;
                }
            }
            return raw;
        }

        function normalizeErrorValue(value) {
            if (value === undefined || value === null) {
                return null;
            }
            if (typeof value === "string") {
                return value;
            }
            if (Array.isArray(value)) {
                return value.map(function (item) { return item === undefined || item === null ? "" : String(item); }).join("\n");
            }
            if (typeof value === "object") {
                if (typeof value.message === "string") {
                    return value.message;
                }
                if (typeof value.detail === "string") {
                    return value.detail;
                }
                if (typeof value.details === "string") {
                    return value.details;
                }
                if (value.details !== undefined) {
                    return normalizeErrorValue(value.details);
                }
                try {
                    return JSON.stringify(value);
                } catch (err) {
                    return String(value);
                }
            }
            return String(value);
        }

        function formatErrorList(errors) {
            if (!Array.isArray(errors)) {
                return null;
            }
            var parts = [];
            errors.forEach(function (entry) {
                if (entry === undefined || entry === null) {
                    return;
                }
                if (typeof entry === "string") {
                    parts.push(entry);
                    return;
                }
                if (typeof entry.message === "string") {
                    parts.push(entry.message);
                    return;
                }
                if (typeof entry.detail === "string") {
                    parts.push(entry.detail);
                    return;
                }
                if (typeof entry.code === "string") {
                    parts.push(entry.code);
                    return;
                }
                try {
                    parts.push(JSON.stringify(entry));
                } catch (err) {
                    parts.push(String(entry));
                }
            });
            return parts.length ? parts.join("\n") : null;
        }

        var body = coerceBody(error && error.body ? error.body : null);

        if (body && typeof body === "object") {
            if (body.error !== undefined || body.errors !== undefined) {
                return body;
            }
            var fallbackMessage = normalizeErrorValue(body.message || body.detail);
            var errorList = formatErrorList(body.errors);
            if (fallbackMessage || errorList) {
                return {
                    error: {
                        message: fallbackMessage || errorList || "Request failed",
                        details: body.details !== undefined ? body.details : undefined
                    },
                    errors: body.errors
                };
            }
        } else if (typeof body === "string" && body) {
            return { error: { message: body } };
        }

        if (error && typeof error === "object" && (error.error !== undefined || error.errors !== undefined)) {
            return error;
        }

        if (http && typeof http.isHttpError === "function" && http.isHttpError(error)) {
            var detail = error && (error.detail || error.message);
            if (detail && typeof detail === "object" && (detail.error !== undefined || detail.errors !== undefined)) {
                return detail;
            }
            return { error: { message: normalizeErrorValue(detail) || "Request failed" } };
        }

        return { error: { message: (error && error.message) || "Request failed" } };
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var events = helpers.events;

        var wepp = controlBase();
        var weppEvents = null;

        if (events && typeof events.createEmitter === "function") {
            var emitterBase = events.createEmitter();
            if (typeof events.useEventMap === "function") {
                weppEvents = events.useEventMap([
                    "wepp:run:started",
                    "wepp:run:queued",
                    "wepp:run:completed",
                    "wepp:run:error",
                    "wepp:run_watershed:started",
                    "wepp:run_watershed:queued",
                    "wepp:run_watershed:completed",
                    "wepp:run_watershed:error",
                    "wepp:prep_only:started",
                    "wepp:prep_only:queued",
                    "wepp:prep_only:completed",
                    "wepp:prep_only:error",
                    "wepp:report:loaded"
                ], emitterBase);
            } else {
                weppEvents = emitterBase;
            }
        }

        var formElement = dom.ensureElement("#wepp_form", "WEPP form not found.");
        var infoElement = dom.qs("#wepp_form #info");
        var statusElement = dom.qs("#wepp_form #status");
        var stacktraceElement = dom.qs("#wepp_form #stacktrace");
        var rqJobElement = dom.qs("#wepp_form #rq_job");
        var hintElement = dom.qs("#hint_run_wepp");
        var swatHintElement = dom.qs("#hint_run_swat");
        var swatExecButton = formElement ? formElement.querySelector('[data-wepp-action="run-swat"]') : null;
        var hasSwatControls = Boolean(swatHintElement || swatExecButton);
        var resultsContainer = dom.qs("#wepp-results");
        var revegSelect = dom.qs("#reveg_scenario");
        var coverTransformContainer = dom.qs("#user_defined_cover_transform_container");

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);
        var hintAdapter = createLegacyAdapter(hintElement);
        var swatHintAdapter = createLegacyAdapter(swatHintElement);

        wepp.form = formElement;
        wepp.info = infoAdapter;
        wepp.status = statusAdapter;
        wepp.stacktrace = stacktraceAdapter;
        wepp.rq_job = rqJobAdapter;
        wepp.hint = hintAdapter;
        wepp.command_btn_id = "btn_run_wepp";
        wepp.resultsContainer = resultsContainer;
        wepp.hasSwatControls = hasSwatControls;

        wepp.statusPanelEl = dom.qs("#wepp_status_panel");
        wepp.stacktracePanelEl = dom.qs("#wepp_stacktrace_panel");
        wepp.statusSpinnerEl = wepp.statusPanelEl ? wepp.statusPanelEl.querySelector("#braille") : null;
        wepp.statusStream = null;
        wepp._swatStatusStream = null;
        wepp._swatStatusPanelEl = null;
        wepp._delegates = [];

        if (weppEvents) {
            wepp.events = weppEvents;
        }

        wepp.appendStatus = function (message, meta) {
            if (!message) {
                return;
            }
            if (wepp.statusStream && typeof wepp.statusStream.append === "function") {
                wepp.statusStream.append(message, meta || null);
            } else if (statusAdapter && typeof statusAdapter.text === "function") {
                statusAdapter.text(message);
            } else if (statusElement) {
                statusElement.textContent = message;
            }
        };

        var statusStreamConfig = {
            element: wepp.statusPanelEl,
            runId: window.runid || window.runId || null,
            stacktrace: wepp.stacktracePanelEl ? { element: wepp.stacktracePanelEl } : null,
            spinner: wepp.statusSpinnerEl,
            logLimit: 400
        };

        function ensureWeppStatusStream() {
            if (!wepp.statusStream) {
                wepp.attach_status_stream(wepp, Object.assign({}, statusStreamConfig, { channel: "wepp" }));
            }
        }

        function ensureSwatStatusStream() {
            if (wepp._swatStatusStream) {
                return wepp._swatStatusStream;
            }
            if (typeof window === "undefined" || typeof window.StatusStream === "undefined") {
                return null;
            }

            var hostElement = wepp.statusPanelEl || formElement;
            if (!hostElement || typeof document === "undefined") {
                return null;
            }

            var panel = document.createElement("div");
            panel.setAttribute("data-status-panel", "");
            panel.style.display = "none";

            var logNode = document.createElement("div");
            logNode.setAttribute("data-status-log", "");
            panel.appendChild(logNode);
            hostElement.appendChild(panel);

            var swatStream = window.StatusStream.attach({
                element: panel,
                logElement: logNode,
                channel: "swat",
                runId: statusStreamConfig.runId,
                logLimit: statusStreamConfig.logLimit,
                stacktrace: statusStreamConfig.stacktrace,
                autoConnect: false,
                onAppend: function (detail) {
                    var message = detail && detail.raw !== undefined ? detail.raw : detail ? detail.message : "";
                    if (message) {
                        wepp.appendStatus(message, detail && detail.meta ? detail.meta : null);
                    }
                },
                onTrigger: function (detail) {
                    if (detail && detail.event) {
                        wepp.triggerEvent(detail.event, detail);
                    }
                }
            });

            wepp._swatStatusStream = swatStream;
            wepp._swatStatusPanelEl = panel;
            return swatStream;
        }

        function connectSwatStatusStream() {
            if (wepp._swatStatusStream && typeof wepp._swatStatusStream.connect === "function") {
                wepp._swatStatusStream.connect();
            }
        }

        function disconnectSwatStatusStream() {
            if (wepp._swatStatusStream && typeof wepp._swatStatusStream.disconnect === "function") {
                wepp._swatStatusStream.disconnect();
            }
        }

        ensureWeppStatusStream();

        wepp._completion_seen = false;
        wepp._prep_completion_seen = false;
        wepp._swat_completion_seen = false;
        wepp._active_wepp_run_event = "run";

        function setActiveWeppRunEvent(eventName) {
            if (eventName === "run_watershed") {
                wepp._active_wepp_run_event = "run_watershed";
                return;
            }
            if (eventName === "prep_only") {
                wepp._active_wepp_run_event = "prep_only";
                return;
            }
            wepp._active_wepp_run_event = "run";
        }

        function emitActiveWeppCompletion(payload) {
            if (!weppEvents || typeof weppEvents.emit !== "function") {
                return;
            }
            var completionPayload = payload || {};
            if (wepp._active_wepp_run_event === "run_watershed") {
                weppEvents.emit("wepp:run_watershed:completed", completionPayload);
                return;
            }
            if (wepp._active_wepp_run_event === "prep_only") {
                weppEvents.emit("wepp:prep_only:completed", completionPayload);
                return;
            }
            weppEvents.emit("wepp:run:completed", completionPayload);
        }

        function resetCompletionSeen() {
            wepp._completion_seen = false;
        }

        function resetPrepCompletionSeen() {
            wepp._prep_completion_seen = false;
        }

        function resetSwatCompletionSeen() {
            wepp._swat_completion_seen = false;
        }

        var baseTriggerEvent = wepp.triggerEvent.bind(wepp);
        wepp.triggerEvent = function (eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === "WEPP_RUN_TASK_COMPLETED") {
                if (wepp._completion_seen) {
                    return baseTriggerEvent(eventName, payload);
                }
                wepp._completion_seen = true;
                wepp.disconnect_status_stream(wepp);
                wepp.report();
                try {
                    Observed.getInstance().onWeppRunCompleted();
                } catch (err) {
                    console.warn("[WEPP] Observed controller notification failed", err);
                }
                emitActiveWeppCompletion(payload || {});
            }
            if (normalized === "WEPP_PREP_TASK_COMPLETED") {
                if (wepp._prep_completion_seen) {
                    return baseTriggerEvent(eventName, payload);
                }
                wepp._prep_completion_seen = true;
                wepp.disconnect_status_stream(wepp);
                if (statusAdapter && typeof statusAdapter.html === "function") {
                    statusAdapter.html("WEPP prep-only input generation completed.");
                }
                wepp.appendStatus("WEPP prep-only input generation completed.");
                emitActiveWeppCompletion(payload || {});
            }
            if (normalized === "SWAT_RUN_TASK_COMPLETED") {
                if (wepp._swat_completion_seen) {
                    return baseTriggerEvent(eventName, payload);
                }
                wepp._swat_completion_seen = true;
                disconnectSwatStatusStream();
                if (statusAdapter && typeof statusAdapter.html === "function") {
                    statusAdapter.html("SWAT run completed.");
                }
                wepp.appendStatus("SWAT run completed.");
                ensureWeppStatusStream();
            }

            return baseTriggerEvent(eventName, payload);
        };

        wepp.hideStacktrace = function () {
            if (stacktraceAdapter && typeof stacktraceAdapter.hide === "function") {
                stacktraceAdapter.hide();
            } else if (stacktraceElement) {
                stacktraceElement.hidden = true;
                stacktraceElement.style.display = "none";
            }
        };

        wepp.surf_runoff = dom.qs("#wepp_form #surf_runoff");
        wepp.lateral_flow = dom.qs("#wepp_form #lateral_flow");
        wepp.baseflow = dom.qs("#wepp_form #baseflow");
        wepp.sediment = dom.qs("#wepp_form #sediment");
        wepp.channel_critical_shear = dom.qs("#wepp_form #channel_critical_shear");

        wepp.addChannelCriticalShear = function (value) {
            if (!wepp.channel_critical_shear) {
                return;
            }
            var option = new Option("User Defined: CS = " + value, value, true, true);
            wepp.channel_critical_shear.appendChild(option);
        };

        wepp.updatePhosphorus = function () {
            http.getJson(url_for_run("query/wepp/phosphorus_opts/"))
                .then(function (response) {
                    if (!response) {
                        return;
                    }
                    if (response.surf_runoff !== null && wepp.surf_runoff) {
                        wepp.surf_runoff.value = Number(response.surf_runoff).toFixed(4);
                    }
                    if (response.lateral_flow !== null && wepp.lateral_flow) {
                        wepp.lateral_flow.value = Number(response.lateral_flow).toFixed(4);
                    }
                    if (response.baseflow !== null && wepp.baseflow) {
                        wepp.baseflow.value = Number(response.baseflow).toFixed(4);
                    }
                    if (response.sediment !== null && wepp.sediment) {
                        wepp.sediment.value = Number(response.sediment).toFixed(0);
                    }
                    wepp.appendStatus("Phosphorus defaults loaded from configuration.");
                })
                .catch(function (error) {
                    wepp.pushResponseStacktrace(wepp, toResponsePayload(http, error));
                });
        };

        wepp.set_run_wepp_routine = function (routine, state) {
            var taskMsg = "Setting " + routine + " (" + state + ")";
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(taskMsg + "...");
            }
            if (stacktraceAdapter && typeof stacktraceAdapter.text === "function") {
                stacktraceAdapter.text("");
            }
            wepp.appendStatus(taskMsg + "...");

            return http.postJson(url_for_run("tasks/set_run_wepp_routine/"), { routine: routine, state: state }, { form: formElement })
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && (response.error || response.errors)) {
                        wepp.pushResponseStacktrace(wepp, response);
                        return;
                    }
                    var message = taskMsg + "... Success";
                    if (statusAdapter && typeof statusAdapter.html === "function") {
                        statusAdapter.html(message);
                    }
                    wepp.appendStatus(message);
                })
                .catch(function (error) {
                    wepp.pushResponseStacktrace(wepp, toResponsePayload(http, error));
                });
        };

        wepp.handleCoverTransformUpload = function (input) {
            if (!input || !input.files || input.files.length === 0) {
                return false;
            }

            var file = input.files[0];
            var formData = new FormData();
            formData.append("input_upload_cover_transform", file);

            http.requestWithSessionToken(url_for_run("tasks/upload-cover-transform", { prefix: "/rq-engine/api" }), {
                method: "POST",
                body: formData,
                form: formElement
            }).then(function () {
                console.log("[WEPP] Cover transform uploaded");
            }).catch(function (error) {
                wepp.pushResponseStacktrace(wepp, toResponsePayload(http, error));
            });

            return true;
        };

        wepp.handleRevegetationScenarioChange = function (value) {
            if (!coverTransformContainer) {
                return;
            }
            if (value === "user_cover_transform") {
                if (dom.show) {
                    dom.show(coverTransformContainer);
                } else {
                    coverTransformContainer.hidden = false;
                    coverTransformContainer.style.removeProperty("display");
                }
            } else {
                if (dom.hide) {
                    dom.hide(coverTransformContainer);
                } else {
                    coverTransformContainer.hidden = true;
                    coverTransformContainer.style.display = "none";
                }
            }
        };

        function buildSwatPrintPrtPayload(element) {
            if (!element || typeof element.closest !== "function") {
                return null;
            }
            var row = element.closest("[data-swat-print-prt-row]");
            if (!row) {
                return null;
            }
            var objectName = row.getAttribute("data-swat-object");
            if (!objectName) {
                return null;
            }
            var payload = { object: objectName };
            var fields = row.querySelectorAll("[data-swat-print-prt-field]");
            fields.forEach(function (field) {
                var key = field.getAttribute("data-swat-print-prt-field");
                if (!key) {
                    return;
                }
                payload[key] = Boolean(field.checked);
            });
            return payload;
        }

        function buildSwatPrintPrtMetaPayload() {
            var payload = {};
            var fields = formElement ? formElement.querySelectorAll("[data-swat-print-prt-meta]") : [];
            fields.forEach(function (field) {
                if (!field || !field.name) {
                    return;
                }
                var key = field.name.replace("swat_print_prt_", "");
                if (!key) {
                    return;
                }
                payload[key] = field.value;
            });
            return payload;
        }

        wepp.updateSwatPrintPrt = function (payload) {
            if (!payload || !payload.object) {
                return;
            }
            var taskMsg = "Updating SWAT print.prt (" + payload.object + ")";
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(taskMsg + "...");
            }
            wepp.appendStatus(taskMsg + "...");

            return http.postJsonWithSessionToken(
                url_for_run("swat/print-prt", { prefix: "/rq-engine/api" }),
                payload,
                { form: formElement }
            )
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && (response.error || response.errors)) {
                        wepp.pushResponseStacktrace(wepp, response);
                        return;
                    }
                    var message = taskMsg + "... Success";
                    if (statusAdapter && typeof statusAdapter.html === "function") {
                        statusAdapter.html(message);
                    }
                    wepp.appendStatus(message);
                })
                .catch(function (error) {
                    wepp.pushResponseStacktrace(wepp, toResponsePayload(http, error));
                });
        };

        wepp.updateSwatPrintPrtMeta = function (payload) {
            if (!payload) {
                return;
            }
            var taskMsg = "Updating SWAT print.prt header";
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(taskMsg + "...");
            }
            wepp.appendStatus(taskMsg + "...");

            return http.postJsonWithSessionToken(
                url_for_run("swat/print-prt/meta", { prefix: "/rq-engine/api" }),
                payload,
                { form: formElement }
            )
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && (response.error || response.errors)) {
                        wepp.pushResponseStacktrace(wepp, response);
                        return;
                    }
                    var message = taskMsg + "... Success";
                    if (statusAdapter && typeof statusAdapter.html === "function") {
                        statusAdapter.html(message);
                    }
                    wepp.appendStatus(message);
                })
                .catch(function (error) {
                    wepp.pushResponseStacktrace(wepp, toResponsePayload(http, error));
                });
        };

        wepp.handleSwatPrintPrtChange = function (input) {
            var payload = buildSwatPrintPrtPayload(input);
            if (!payload) {
                return;
            }
            wepp.updateSwatPrintPrt(payload);
        };

        wepp.handleSwatPrintPrtMetaChange = function () {
            var payload = buildSwatPrintPrtMetaPayload();
            wepp.updateSwatPrintPrtMeta(payload);
        };

        wepp.run = function () {
            var taskMsg = "Submitting wepp run";

            wepp.reset_panel_state(wepp, {
                taskMessage: taskMsg,
                resultsTarget: resultsContainer,
                hintTarget: hintAdapter
            });

            resetCompletionSeen();
            resetPrepCompletionSeen();
            ensureWeppStatusStream();
            wepp.connect_status_stream(wepp);
            if (hasSwatControls) {
                resetSwatCompletionSeen();
                ensureSwatStatusStream();
                connectSwatStatusStream();
            }

            var payload = forms.serializeForm(formElement, { format: "json" }) || {};

            if (weppEvents && typeof weppEvents.emit === "function") {
                weppEvents.emit("wepp:run:started", { payload: payload });
            }
            setActiveWeppRunEvent("run");

            http.postJsonWithSessionToken(
                url_for_run("run-wepp", { prefix: "/rq-engine/api" }),
                payload,
                { form: formElement }
            )
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && (response.error || response.errors)) {
                        wepp.pushResponseStacktrace(wepp, response);
                        return;
                    }
                    var jobId = response && response.job_id ? String(response.job_id) : "";
                    var message = "";
                    if (jobId) {
                        message = "run_wepp_rq job submitted: " + jobId;
                    } else if (response && typeof response.message === "string" && response.message.trim()) {
                        message = response.message.trim();
                    } else {
                        message = "Run WEPP inputs updated.";
                    }
                    if (statusAdapter && typeof statusAdapter.html === "function") {
                        statusAdapter.html(message);
                    }
                    if (jobId) {
                        wepp.appendStatus(message, { job_id: jobId });
                        wepp.poll_completion_event = "WEPP_RUN_TASK_COMPLETED";
                        wepp.set_rq_job_id(wepp, jobId);
                        if (weppEvents && typeof weppEvents.emit === "function") {
                            weppEvents.emit("wepp:run:queued", { job_id: jobId, payload: payload });
                        }
                    } else {
                        wepp.appendStatus(message);
                        wepp.set_rq_job_id(wepp, null);
                        if (weppEvents && typeof weppEvents.emit === "function") {
                            weppEvents.emit("wepp:run:completed", { job_id: null, payload: payload });
                        }
                    }
                })
                .catch(function (error) {
                    if (weppEvents && typeof weppEvents.emit === "function") {
                        weppEvents.emit("wepp:run:error", toResponsePayload(http, error));
                    }
                    wepp.pushResponseStacktrace(wepp, toResponsePayload(http, error));
                });
        };

        wepp.report = function () {
            var taskMsg = "Fetching Summary";
            var resultsHtml = "";

            if (infoAdapter && typeof infoAdapter.text === "function") {
                infoAdapter.text("");
            }
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(taskMsg + "...");
            }
            if (stacktraceAdapter && typeof stacktraceAdapter.text === "function") {
                stacktraceAdapter.text("");
            }

            http.request(url_for_run("report/wepp/results/"))
                .then(function (result) {
                    var body = result && result.body;
                    if (typeof body === "string" && resultsContainer) {
                        resultsContainer.innerHTML = body;
                        resultsHtml = body;
                    }
                })
                .catch(function (error) {
                    wepp.pushResponseStacktrace(wepp, toResponsePayload(http, error));
                });

            http.request(url_for_run("report/wepp/run_summary/"))
                .then(function (result) {
                    var body = result && result.body;
                    if (typeof body === "string") {
                        if (infoAdapter && typeof infoAdapter.html === "function") {
                            infoAdapter.html(body);
                        } else if (infoElement) {
                            infoElement.innerHTML = body;
                        }
                    }
                    if (statusAdapter && typeof statusAdapter.html === "function") {
                        statusAdapter.html(taskMsg + "... Success");
                    }
                    wepp.appendStatus(taskMsg + "... Success");
                    try {
                        Project.getInstance().set_preferred_units();
                    } catch (error) {
                        console.warn("[WEPP] Failed to apply preferred units", error);
                    }
                    if (weppEvents && typeof weppEvents.emit === "function") {
                        weppEvents.emit("wepp:report:loaded", {
                            summary: typeof body === "string" ? body : "",
                            results: resultsHtml
                        });
                    }
                })
                .catch(function (error) {
                    wepp.pushResponseStacktrace(wepp, toResponsePayload(http, error));
                });
        };

        wepp.runWatershed = function () {
            var taskMsg = "Submitting WEPP watershed run";

            wepp.reset_panel_state(wepp, {
                taskMessage: taskMsg,
                resultsTarget: resultsContainer,
                hintTarget: hintAdapter
            });

            resetCompletionSeen();
            resetPrepCompletionSeen();
            ensureWeppStatusStream();
            wepp.connect_status_stream(wepp);
            if (hasSwatControls) {
                resetSwatCompletionSeen();
                ensureSwatStatusStream();
                connectSwatStatusStream();
            }

            var payload = forms.serializeForm(formElement, { format: "json" }) || {};

            if (weppEvents && typeof weppEvents.emit === "function") {
                weppEvents.emit("wepp:run_watershed:started", { payload: payload });
            }
            setActiveWeppRunEvent("run_watershed");

            http.postJsonWithSessionToken(
                url_for_run("run-wepp-watershed", { prefix: "/rq-engine/api" }),
                payload,
                { form: formElement }
            )
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && (response.error || response.errors)) {
                        wepp.pushResponseStacktrace(wepp, response);
                        return;
                    }
                    var jobId = response && response.job_id ? String(response.job_id) : "";
                    var message = "";
                    if (jobId) {
                        message = "run_wepp_watershed_rq job submitted: " + jobId;
                    } else if (response && typeof response.message === "string" && response.message.trim()) {
                        message = response.message.trim();
                    } else {
                        message = "Run WEPP watershed inputs updated.";
                    }
                    if (statusAdapter && typeof statusAdapter.html === "function") {
                        statusAdapter.html(message);
                    }
                    if (jobId) {
                        wepp.appendStatus(message, { job_id: jobId });
                        wepp.poll_completion_event = "WEPP_RUN_TASK_COMPLETED";
                        wepp.set_rq_job_id(wepp, jobId);
                        if (weppEvents && typeof weppEvents.emit === "function") {
                            weppEvents.emit("wepp:run_watershed:queued", { job_id: jobId, payload: payload });
                        }
                    } else {
                        wepp.appendStatus(message);
                        wepp.set_rq_job_id(wepp, null);
                        if (weppEvents && typeof weppEvents.emit === "function") {
                            weppEvents.emit("wepp:run_watershed:completed", { job_id: null, payload: payload });
                        }
                    }
                })
                .catch(function (error) {
                    if (weppEvents && typeof weppEvents.emit === "function") {
                        weppEvents.emit("wepp:run_watershed:error", toResponsePayload(http, error));
                    }
                    wepp.pushResponseStacktrace(wepp, toResponsePayload(http, error));
                });
        };

        wepp.prepWatershedOnly = function () {
            var taskMsg = "Submitting WEPP prep-only run";

            wepp.reset_panel_state(wepp, {
                taskMessage: taskMsg,
                resultsTarget: resultsContainer,
                hintTarget: hintAdapter
            });

            resetCompletionSeen();
            resetPrepCompletionSeen();
            ensureWeppStatusStream();
            wepp.connect_status_stream(wepp);

            var payload = forms.serializeForm(formElement, { format: "json" }) || {};

            if (weppEvents && typeof weppEvents.emit === "function") {
                weppEvents.emit("wepp:prep_only:started", { payload: payload });
            }
            setActiveWeppRunEvent("prep_only");

            http.postJsonWithSessionToken(
                url_for_run("prep-wepp-watershed", { prefix: "/rq-engine/api" }),
                payload,
                { form: formElement }
            )
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && (response.error || response.errors)) {
                        wepp.pushResponseStacktrace(wepp, response);
                        return;
                    }
                    var jobId = response && response.job_id ? String(response.job_id) : "";
                    var message = "";
                    if (jobId) {
                        message = "prep_wepp_watershed_rq job submitted: " + jobId;
                    } else if (response && typeof response.message === "string" && response.message.trim()) {
                        message = response.message.trim();
                    } else {
                        message = "Prep-only WEPP inputs updated.";
                    }
                    if (statusAdapter && typeof statusAdapter.html === "function") {
                        statusAdapter.html(message);
                    }
                    if (jobId) {
                        wepp.appendStatus(message, { job_id: jobId });
                        wepp.poll_completion_event = "WEPP_PREP_TASK_COMPLETED";
                        wepp.set_rq_job_id(wepp, jobId);
                        if (weppEvents && typeof weppEvents.emit === "function") {
                            weppEvents.emit("wepp:prep_only:queued", { job_id: jobId, payload: payload });
                        }
                    } else {
                        wepp.appendStatus(message);
                        wepp.set_rq_job_id(wepp, null);
                        if (weppEvents && typeof weppEvents.emit === "function") {
                            weppEvents.emit("wepp:prep_only:completed", { job_id: null, payload: payload });
                        }
                    }
                })
                .catch(function (error) {
                    if (weppEvents && typeof weppEvents.emit === "function") {
                        weppEvents.emit("wepp:prep_only:error", toResponsePayload(http, error));
                    }
                    wepp.pushResponseStacktrace(wepp, toResponsePayload(http, error));
                });
        };

        wepp.runNoPrep = function () {
            var taskMsg = "Submitting WEPP no-prep run";

            wepp.reset_panel_state(wepp, {
                taskMessage: taskMsg,
                resultsTarget: resultsContainer,
                hintTarget: hintAdapter
            });

            resetCompletionSeen();
            resetPrepCompletionSeen();
            ensureWeppStatusStream();
            wepp.connect_status_stream(wepp);
            if (hasSwatControls) {
                resetSwatCompletionSeen();
                ensureSwatStatusStream();
                connectSwatStatusStream();
            }

            var payload = forms.serializeForm(formElement, { format: "json" }) || {};

            if (weppEvents && typeof weppEvents.emit === "function") {
                weppEvents.emit("wepp:run:started", { payload: payload });
            }
            setActiveWeppRunEvent("run");

            http.postJsonWithSessionToken(
                url_for_run("run-wepp-npprep", { prefix: "/rq-engine/api" }),
                payload,
                { form: formElement }
            )
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && (response.error || response.errors)) {
                        wepp.pushResponseStacktrace(wepp, response);
                        return;
                    }
                    var jobId = response && response.job_id ? String(response.job_id) : "";
                    var message = "";
                    if (jobId) {
                        message = "run_wepp_noprep_rq job submitted: " + jobId;
                    } else if (response && typeof response.message === "string" && response.message.trim()) {
                        message = response.message.trim();
                    } else {
                        message = "Run WEPP no-prep inputs updated.";
                    }
                    if (statusAdapter && typeof statusAdapter.html === "function") {
                        statusAdapter.html(message);
                    }
                    if (jobId) {
                        wepp.appendStatus(message, { job_id: jobId });
                        wepp.poll_completion_event = "WEPP_RUN_TASK_COMPLETED";
                        wepp.set_rq_job_id(wepp, jobId);
                        if (weppEvents && typeof weppEvents.emit === "function") {
                            weppEvents.emit("wepp:run:queued", { job_id: jobId, payload: payload });
                        }
                    } else {
                        wepp.appendStatus(message);
                        wepp.set_rq_job_id(wepp, null);
                        if (weppEvents && typeof weppEvents.emit === "function") {
                            weppEvents.emit("wepp:run:completed", { job_id: null, payload: payload });
                        }
                    }
                })
                .catch(function (error) {
                    if (weppEvents && typeof weppEvents.emit === "function") {
                        weppEvents.emit("wepp:run:error", toResponsePayload(http, error));
                    }
                    wepp.pushResponseStacktrace(wepp, toResponsePayload(http, error));
                });
        };

        wepp.runWatershedNoPrep = function () {
            var taskMsg = "Submitting WEPP watershed run (no-prep)";

            wepp.reset_panel_state(wepp, {
                taskMessage: taskMsg,
                resultsTarget: resultsContainer,
                hintTarget: hintAdapter
            });

            resetCompletionSeen();
            resetPrepCompletionSeen();
            ensureWeppStatusStream();
            wepp.connect_status_stream(wepp);
            if (hasSwatControls) {
                resetSwatCompletionSeen();
                ensureSwatStatusStream();
                connectSwatStatusStream();
            }

            var payload = forms.serializeForm(formElement, { format: "json" }) || {};

            if (weppEvents && typeof weppEvents.emit === "function") {
                weppEvents.emit("wepp:run_watershed:started", { payload: payload });
            }
            setActiveWeppRunEvent("run_watershed");

            http.postJsonWithSessionToken(
                url_for_run("run-wepp-watershed-no-prep", { prefix: "/rq-engine/api" }),
                payload,
                { form: formElement }
            )
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && (response.error || response.errors)) {
                        wepp.pushResponseStacktrace(wepp, response);
                        return;
                    }
                    var jobId = response && response.job_id ? String(response.job_id) : "";
                    var message = "";
                    if (jobId) {
                        message = "run_wepp_watershed_noprep_rq job submitted: " + jobId;
                    } else if (response && typeof response.message === "string" && response.message.trim()) {
                        message = response.message.trim();
                    } else {
                        message = "Run WEPP watershed no-prep inputs updated.";
                    }
                    if (statusAdapter && typeof statusAdapter.html === "function") {
                        statusAdapter.html(message);
                    }
                    if (jobId) {
                        wepp.appendStatus(message, { job_id: jobId });
                        wepp.poll_completion_event = "WEPP_RUN_TASK_COMPLETED";
                        wepp.set_rq_job_id(wepp, jobId);
                        if (weppEvents && typeof weppEvents.emit === "function") {
                            weppEvents.emit("wepp:run_watershed:queued", { job_id: jobId, payload: payload });
                        }
                    } else {
                        wepp.appendStatus(message);
                        wepp.set_rq_job_id(wepp, null);
                        if (weppEvents && typeof weppEvents.emit === "function") {
                            weppEvents.emit("wepp:run_watershed:completed", { job_id: null, payload: payload });
                        }
                    }
                })
                .catch(function (error) {
                    if (weppEvents && typeof weppEvents.emit === "function") {
                        weppEvents.emit("wepp:run_watershed:error", toResponsePayload(http, error));
                    }
                    wepp.pushResponseStacktrace(wepp, toResponsePayload(http, error));
                });
        };

        wepp.runSwatNoPrep = function () {
            var taskMsg = "Submitting SWAT run (no-prep)";

            var cachedResults = wepp.resultsContainer;
            wepp.resultsContainer = null;
            wepp.reset_panel_state(wepp, {
                taskMessage: taskMsg,
                hintTarget: swatHintAdapter
            });
            wepp.resultsContainer = cachedResults;

            resetSwatCompletionSeen();
            resetPrepCompletionSeen();
            ensureWeppStatusStream();
            ensureSwatStatusStream();
            wepp.connect_status_stream(wepp);
            connectSwatStatusStream();

            var payload = forms.serializeForm(formElement, { format: "json" }) || {};

            http.postJsonWithSessionToken(
                url_for_run("run-swat-noprep", { prefix: "/rq-engine/api" }),
                payload,
                { form: formElement }
            )
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && (response.error || response.errors)) {
                        wepp.pushResponseStacktrace(wepp, response);
                        return;
                    }
                    var jobId = response && response.job_id ? String(response.job_id) : "";
                    var message = "";
                    if (jobId) {
                        message = "run_swat_noprep_rq job submitted: " + jobId;
                    } else if (response && typeof response.message === "string" && response.message.trim()) {
                        message = response.message.trim();
                    } else {
                        message = "SWAT no-prep inputs updated.";
                    }
                    if (statusAdapter && typeof statusAdapter.html === "function") {
                        statusAdapter.html(message);
                    }
                    if (jobId) {
                        wepp.appendStatus(message, { job_id: jobId });
                        wepp.poll_completion_event = "SWAT_RUN_TASK_COMPLETED";
                        wepp.set_rq_job_id(wepp, jobId);
                    } else {
                        wepp.appendStatus(message);
                        wepp.set_rq_job_id(wepp, null);
                    }
                })
                .catch(function (error) {
                    wepp.pushResponseStacktrace(wepp, toResponsePayload(http, error));
                });
        };

        wepp.runSwat = function () {
            var taskMsg = "Submitting SWAT run";

            var cachedResults = wepp.resultsContainer;
            wepp.resultsContainer = null;
            wepp.reset_panel_state(wepp, {
                taskMessage: taskMsg,
                hintTarget: swatHintAdapter
            });
            wepp.resultsContainer = cachedResults;

            resetSwatCompletionSeen();
            resetPrepCompletionSeen();
            ensureWeppStatusStream();
            ensureSwatStatusStream();
            wepp.connect_status_stream(wepp);
            connectSwatStatusStream();

            var payload = forms.serializeForm(formElement, { format: "json" }) || {};

            http.postJsonWithSessionToken(
                url_for_run("run-swat", { prefix: "/rq-engine/api" }),
                payload,
                { form: formElement }
            )
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && (response.error || response.errors)) {
                        wepp.pushResponseStacktrace(wepp, response);
                        return;
                    }
                    var jobId = response && response.job_id ? String(response.job_id) : "";
                    var message = "";
                    if (jobId) {
                        message = "run_swat_rq job submitted: " + jobId;
                    } else if (response && typeof response.message === "string" && response.message.trim()) {
                        message = response.message.trim();
                    } else {
                        message = "SWAT inputs updated.";
                    }
                    if (statusAdapter && typeof statusAdapter.html === "function") {
                        statusAdapter.html(message);
                    }
                    if (jobId) {
                        wepp.appendStatus(message, { job_id: jobId });
                        wepp.poll_completion_event = "SWAT_RUN_TASK_COMPLETED";
                        wepp.set_rq_job_id(wepp, jobId);
                    } else {
                        wepp.appendStatus(message);
                        wepp.set_rq_job_id(wepp, null);
                    }
                })
                .catch(function (error) {
                    wepp.pushResponseStacktrace(wepp, toResponsePayload(http, error));
                });
        };

        function ensureDelegates() {
            if (wepp._delegates && wepp._delegates.length) {
                return;
            }

            wepp._delegates.push(dom.delegate(formElement, "click", '[data-wepp-action="run"]', function (event) {
                if (event && typeof event.preventDefault === "function") {
                    event.preventDefault();
                }
                wepp.run();
            }));

            wepp._delegates.push(dom.delegate(formElement, "click", '[data-wepp-action="run-noprep"]', function (event) {
                if (event && typeof event.preventDefault === "function") {
                    event.preventDefault();
                }
                wepp.runNoPrep();
            }));

            wepp._delegates.push(dom.delegate(formElement, "click", '[data-wepp-action="run-watershed"]', function (event) {
                if (event && typeof event.preventDefault === "function") {
                    event.preventDefault();
                }
                wepp.runWatershed();
            }));

            wepp._delegates.push(dom.delegate(formElement, "click", '[data-wepp-action="prep-watershed"]', function (event) {
                if (event && typeof event.preventDefault === "function") {
                    event.preventDefault();
                }
                wepp.prepWatershedOnly();
            }));

            wepp._delegates.push(dom.delegate(formElement, "click", '[data-wepp-action="run-watershed-noprep"]', function (event) {
                if (event && typeof event.preventDefault === "function") {
                    event.preventDefault();
                }
                wepp.runWatershedNoPrep();
            }));

            wepp._delegates.push(dom.delegate(formElement, "click", '[data-wepp-action="run-swat"]', function (event) {
                if (event && typeof event.preventDefault === "function") {
                    event.preventDefault();
                }
                wepp.runSwat();
            }));

            wepp._delegates.push(dom.delegate(formElement, "click", '[data-wepp-action="run-swat-noprep"]', function (event) {
                if (event && typeof event.preventDefault === "function") {
                    event.preventDefault();
                }
                wepp.runSwatNoPrep();
            }));

            wepp._delegates.push(dom.delegate(formElement, "change", "[data-wepp-routine]", function () {
                var routine = this.getAttribute("data-wepp-routine");
                if (!routine) {
                    return;
                }
                wepp.set_run_wepp_routine(routine, Boolean(this.checked));
            }));

            wepp._delegates.push(dom.delegate(formElement, "change", '[data-wepp-action="upload-cover-transform"]', function () {
                wepp.handleCoverTransformUpload(this);
            }));

            wepp._delegates.push(dom.delegate(formElement, "change", '[data-wepp-role="reveg-scenario"]', function () {
                wepp.handleRevegetationScenarioChange(this.value);
            }));

            wepp._delegates.push(dom.delegate(formElement, "change", "[data-swat-print-prt]", function () {
                wepp.handleSwatPrintPrtChange(this);
            }));

            wepp._delegates.push(dom.delegate(formElement, "change", "[data-swat-print-prt-meta]", function () {
                wepp.handleSwatPrintPrtMetaChange();
            }));
        }

        ensureDelegates();
        wepp.handleRevegetationScenarioChange(revegSelect ? revegSelect.value : "");

        var bootstrapState = {
            modeListenersBound: false,
            reportTriggered: false
        };

        wepp.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            var controllerContext = helper && typeof helper.getControllerContext === "function"
                ? helper.getControllerContext(ctx, "wepp")
                : {};

            var jobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "run_wepp_rq")
                : null;
            var completionEvent = null;
            if (!jobId && helper && typeof helper.resolveJobId === "function") {
                var prepJobId = helper.resolveJobId(ctx, "prep_wepp_watershed_rq");
                if (prepJobId) {
                    jobId = prepJobId;
                    completionEvent = "WEPP_PREP_TASK_COMPLETED";
                    setActiveWeppRunEvent("prep_only");
                }
            }
            if (!jobId && controllerContext.job_id) {
                jobId = controllerContext.job_id;
            }
            if (!jobId) {
                var jobIds = ctx && (ctx.jobIds || ctx.jobs);
                if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "prep_wepp_watershed_rq")) {
                    var prepOnlyValue = jobIds.prep_wepp_watershed_rq;
                    if (prepOnlyValue !== undefined && prepOnlyValue !== null) {
                        jobId = String(prepOnlyValue);
                        completionEvent = "WEPP_PREP_TASK_COMPLETED";
                        setActiveWeppRunEvent("prep_only");
                    }
                }
                if (!jobId && jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "run_wepp_rq")) {
                    var value = jobIds.run_wepp_rq;
                    if (value !== undefined && value !== null) {
                        jobId = String(value);
                        completionEvent = "WEPP_RUN_TASK_COMPLETED";
                        setActiveWeppRunEvent("run");
                    }
                }
                if (!jobId && jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "run_wepp_watershed_rq")) {
                    var watershedValue = jobIds.run_wepp_watershed_rq;
                    if (watershedValue !== undefined && watershedValue !== null) {
                        jobId = String(watershedValue);
                        completionEvent = "WEPP_RUN_TASK_COMPLETED";
                        setActiveWeppRunEvent("run_watershed");
                    }
                }
                if (!jobId && jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "run_wepp_noprep_rq")) {
                    var noprepValue = jobIds.run_wepp_noprep_rq;
                    if (noprepValue !== undefined && noprepValue !== null) {
                        jobId = String(noprepValue);
                        completionEvent = "WEPP_RUN_TASK_COMPLETED";
                        setActiveWeppRunEvent("run");
                    }
                }
                if (!jobId && jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "run_wepp_watershed_noprep_rq")) {
                    var watershedNoPrepValue = jobIds.run_wepp_watershed_noprep_rq;
                    if (watershedNoPrepValue !== undefined && watershedNoPrepValue !== null) {
                        jobId = String(watershedNoPrepValue);
                        completionEvent = "WEPP_RUN_TASK_COMPLETED";
                        setActiveWeppRunEvent("run_watershed");
                    }
                }
                if (!jobId && jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "run_swat_rq")) {
                    var swatValue = jobIds.run_swat_rq;
                    if (swatValue !== undefined && swatValue !== null) {
                        jobId = String(swatValue);
                        completionEvent = "SWAT_RUN_TASK_COMPLETED";
                    }
                }
                if (!jobId && jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "run_swat_noprep_rq")) {
                    var swatNoPrepValue = jobIds.run_swat_noprep_rq;
                    if (swatNoPrepValue !== undefined && swatNoPrepValue !== null) {
                        jobId = String(swatNoPrepValue);
                        completionEvent = "SWAT_RUN_TASK_COMPLETED";
                    }
                }
            }

            if (typeof wepp.set_rq_job_id === "function") {
                if (jobId) {
                    wepp.poll_completion_event = completionEvent || "WEPP_RUN_TASK_COMPLETED";
                    if (wepp.poll_completion_event === "SWAT_RUN_TASK_COMPLETED") {
                        resetSwatCompletionSeen();
                        ensureWeppStatusStream();
                        ensureSwatStatusStream();
                        connectSwatStatusStream();
                    } else if (wepp.poll_completion_event === "WEPP_PREP_TASK_COMPLETED") {
                        resetPrepCompletionSeen();
                        ensureWeppStatusStream();
                    } else {
                        resetCompletionSeen();
                        ensureWeppStatusStream();
                        if (hasSwatControls) {
                            resetSwatCompletionSeen();
                            ensureSwatStatusStream();
                            connectSwatStatusStream();
                        }
                    }
                }
                wepp.set_rq_job_id(wepp, jobId);
            }

            if (!bootstrapState.modeListenersBound && typeof wepp.setMode === "function") {
                var modeInputs = document.querySelectorAll("input[name='wepp_mode']");
                modeInputs.forEach(function (input) {
                    input.addEventListener("change", function () {
                        wepp.setMode();
                    });
                });
                var singleSelectionInput = document.getElementById("wepp_single_selection");
                if (singleSelectionInput) {
                    singleSelectionInput.addEventListener("change", function () {
                        wepp.setMode();
                    });
                }
                bootstrapState.modeListenersBound = modeInputs.length > 0 || Boolean(singleSelectionInput);
                if (bootstrapState.modeListenersBound) {
                    try {
                        wepp.setMode();
                    } catch (err) {
                        console.warn("[WEPP] Failed to apply initial mode", err);
                    }
                }
            }

            var weppData = (ctx.data && ctx.data.wepp) || {};
            var hasRun = controllerContext.hasRun;
            if (hasRun === undefined) {
                hasRun = weppData.hasRun;
            }
            if (hasRun && !bootstrapState.reportTriggered && typeof wepp.report === "function") {
                wepp.report();
                bootstrapState.reportTriggered = true;
            }

            return wepp;
        };

        return wepp;
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
    globalThis.Wepp = Wepp;
}
