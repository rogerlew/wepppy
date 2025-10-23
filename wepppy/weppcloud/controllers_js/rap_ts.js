/* ----------------------------------------------------------------------------
 * RAP Time Series
 * Doc: controllers_js/README.md — RAP Time Series Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var RAP_TS = (function () {
    "use strict";

    var instance;

    var FORM_ID = "rap_ts_form";
    var WS_CHANNEL = "rap_ts";
    var TASK_NAME = "rap:timeseries:run";
    var RUN_MESSAGE = "Acquiring RAP time series";
    var COMPLETE_MESSAGE = "RAP time series fetched and analyzed";

    var SELECTORS = {
        form: "#" + FORM_ID,
        info: "#info",
        status: "#status",
        stacktrace: "#stacktrace",
        rqJob: "#rq_job",
        hint: "#hint_build_rap_ts"
    };

    var ACTIONS = {
        run: '[data-rap-action="run"]'
    };

    var EVENT_NAMES = [
        "rap:schedule:loaded",
        "rap:timeseries:run:started",
        "rap:timeseries:run:completed",
        "rap:timeseries:run:error",
        "rap:timeseries:status",
        "job:started",
        "job:completed",
        "job:error"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.delegate !== "function" || typeof dom.qs !== "function" || typeof dom.show !== "function" || typeof dom.hide !== "function") {
            throw new Error("RAP_TS controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("RAP_TS controller requires WCForms helpers.");
        }
        if (!http || typeof http.postJson !== "function" || typeof http.isHttpError !== "function") {
            throw new Error("RAP_TS controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("RAP_TS controller requires WCEvents helpers.");
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
                if (element.style && element.style.display === "none") {
                    element.style.removeProperty("display");
                }
            },
            hide: function () {
                element.hidden = true;
                if (element.style) {
                    element.style.display = "none";
                }
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
            var detail = error.detail || error.message || "Request failed";
            var body = error.body;
            if (body && typeof body === "object") {
                if (body.Error) {
                    detail = body.Error;
                }
                if (Array.isArray(body.StackTrace)) {
                    return {
                        Success: false,
                        Error: detail,
                        StackTrace: body.StackTrace
                    };
                }
            }
            return {
                Success: false,
                Error: detail
            };
        }
        return {
            Success: false,
            Error: (error && error.message) || "Request failed"
        };
    }

    function parseSchedule(dom) {
        try {
            var node = dom.qs("[data-rap-schedule]");
            if (!node) {
                return [];
            }
            var raw = node.textContent || node.value || node.getAttribute("data-rap-schedule") || "";
            if (!raw) {
                return [];
            }
            var trimmed = raw.trim();
            if (!trimmed) {
                return [];
            }
            var parsed = JSON.parse(trimmed);
            return parsed;
        } catch (err) {
            console.warn("[RAP_TS] Unable to parse schedule payload", err);
            return [];
        }
    }

    function createInstance() {
        if (typeof controlBase !== "function") {
            throw new Error("RAP_TS controller requires controlBase helper.");
        }

        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var eventsApi = helpers.events;

        var base = controlBase();
        var emitter = null;

        if (eventsApi && typeof eventsApi.createEmitter === "function") {
            var baseEmitter = eventsApi.createEmitter();
            emitter = typeof eventsApi.useEventMap === "function"
                ? eventsApi.useEventMap(EVENT_NAMES, baseEmitter)
                : baseEmitter;
        }

        var formElement = null;
        try {
            formElement = dom.qs(SELECTORS.form);
        } catch (err) {
            console.warn("[RAP_TS] Unable to resolve RAP time series form:", err);
        }

        var containerElement = null;
        if (formElement && typeof formElement.closest === "function") {
            containerElement = formElement.closest(".controller-section");
        }
        if (!containerElement) {
            containerElement = formElement || null;
        }

        var infoElement = formElement ? dom.qs(SELECTORS.info, formElement) : null;
        var statusElement = formElement ? dom.qs(SELECTORS.status, formElement) : null;
        var stacktraceElement = formElement ? dom.qs(SELECTORS.stacktrace, formElement) : null;
        var rqJobElement = formElement ? dom.qs(SELECTORS.rqJob, formElement) : null;
        var hintElement = formElement ? dom.qs(SELECTORS.hint, formElement) : null;
        var statusPanelElement = dom.qs("#rap_ts_status_panel");
        var stacktracePanelElement = dom.qs("#rap_ts_stacktrace_panel");
        var statusSpinnerElement = statusPanelElement ? statusPanelElement.querySelector("#braille") : null;

        var controller = Object.assign(base, {
            dom: dom,
            forms: forms,
            http: http,
            events: emitter,
            form: formElement,
            container: containerElement,
            info: createLegacyAdapter(infoElement),
            status: createLegacyAdapter(statusElement),
            stacktrace: createLegacyAdapter(stacktraceElement),
            rq_job: createLegacyAdapter(rqJobElement),
            hint: createLegacyAdapter(hintElement),
            statusPanelEl: statusPanelElement,
            stacktracePanelEl: stacktracePanelElement,
            statusStream: null,
            statusSpinnerEl: statusSpinnerElement,
            command_btn_id: "btn_build_rap_ts",
            _delegates: [],
            state: {
                schedule: [],
                lastSubmission: null
            }
        });

        var baseTriggerEvent = controller.triggerEvent.bind(controller);

        function dispatchControlEvent(eventName, payload) {
            baseTriggerEvent(eventName, payload);
        }

        controller.appendStatus = function (message, meta) {
            if (!message) {
                return;
            }
            if (controller.statusStream && typeof controller.statusStream.append === "function") {
                controller.statusStream.append(message, meta || null);
            }
            if (controller.status && typeof controller.status.html === "function") {
                controller.status.html(message);
            }
        };

        controller.setStatusMessage = controller.appendStatus;

        controller.attach_status_stream(controller, {
            element: controller.statusPanelEl,
            channel: WS_CHANNEL,
            runId: window.runid || window.runId || null,
            stacktrace: controller.stacktracePanelEl ? { element: controller.stacktracePanelEl } : null,
            spinner: controller.statusSpinnerEl,
            logLimit: 200,
            onTrigger: function (detail) {
                if (detail && detail.event) {
                    controller.triggerEvent(detail.event, detail);
                }
            }
        });

        controller.hideStacktrace = function () {
            if (controller.stacktrace && typeof controller.stacktrace.hide === "function") {
                controller.stacktrace.hide();
                return;
            }
            if (stacktraceElement) {
                stacktraceElement.hidden = true;
                stacktraceElement.style.display = "none";
            }
        };

        controller.report = function () {
            controller.setStatusMessage(COMPLETE_MESSAGE);
        };

        controller.handleRunCompletion = function (detail) {
            controller.report();
            controller.disconnect_status_stream(controller);
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("rap:timeseries:run:completed", {
                    task: TASK_NAME,
                    jobId: controller.rq_job_id || null,
                    submission: controller.state.lastSubmission,
                    detail: detail || null
                });
                controller.events.emit("rap:timeseries:status", {
                    status: "completed",
                    task: TASK_NAME,
                    jobId: controller.rq_job_id || null,
                    submission: controller.state.lastSubmission,
                    detail: detail || null
                });
            }
            dispatchControlEvent("job:completed", {
                task: TASK_NAME,
                jobId: controller.rq_job_id || null,
                detail: detail || null,
                submission: controller.state.lastSubmission
            });
        };

        controller.triggerEvent = function (eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === "RAP_TS_TASK_COMPLETED") {
                controller.handleRunCompletion(payload || null);
            }
            baseTriggerEvent(eventName, payload);
        };

        controller.acquire = function (overridePayload) {
            if (!controller.form) {
                return;
            }

            controller.info.html("");
            controller.stacktrace.empty();
            controller.hideStacktrace();
            if (controller.hint && typeof controller.hint.text === "function") {
                controller.hint.text("");
            }

            var submission = forms.serializeForm(controller.form, { format: "json" }) || {};
            if (overridePayload && typeof overridePayload === "object") {
                Object.keys(overridePayload).forEach(function (key) {
                    submission[key] = overridePayload[key];
                });
            }
            controller.state.lastSubmission = submission;

            controller.setStatusMessage(RUN_MESSAGE + "…");
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("rap:timeseries:run:started", {
                    task: TASK_NAME,
                    payload: submission
                });
                controller.events.emit("rap:timeseries:status", {
                    status: "started",
                    task: TASK_NAME,
                    payload: submission
                });
            }
            dispatchControlEvent("job:started", {
                task: TASK_NAME,
                payload: submission
            });

            controller.connect_status_stream(controller);

            function handleError(result) {
                controller.pushResponseStacktrace(controller, result);
                controller.setStatusMessage("Failed to acquire RAP time series");
                if (controller.events && typeof controller.events.emit === "function") {
                    controller.events.emit("rap:timeseries:run:error", {
                        task: TASK_NAME,
                        payload: submission,
                        error: result
                    });
                    controller.events.emit("rap:timeseries:status", {
                        status: "error",
                        task: TASK_NAME,
                        payload: submission,
                        error: result
                    });
                }
                dispatchControlEvent("job:error", {
                    task: TASK_NAME,
                    payload: submission,
                    error: result
                });
                controller.disconnect_status_stream(controller);
            }

            http.postJson("rq/api/acquire_rap_ts", submission, { form: controller.form }).then(function (response) {
                var body = response && response.body !== undefined ? response.body : response;
                var normalized = body || {};
                if (normalized.Success === true || normalized.success === true) {
                    var jobId = normalized.job_id || normalized.jobId || null;
                    var message = "fetch_and_analyze_rap_ts_rq job submitted";
                    if (jobId) {
                        message += ": " + jobId;
                    }
                    controller.setStatusMessage(message, { status: "queued", jobId: jobId });
                    controller.set_rq_job_id(controller, jobId);
                    if (controller.events && typeof controller.events.emit === "function") {
                        controller.events.emit("rap:timeseries:status", {
                            status: "queued",
                            task: TASK_NAME,
                            payload: submission,
                            jobId: jobId,
                            response: normalized
                        });
                    }
                    return;
                }

                handleError(normalized);
            }).catch(function (error) {
                handleError(toResponsePayload(http, error));
            });
        };

        controller.dispose = function () {
            controller._delegates.forEach(function (unsubscribe) {
                if (typeof unsubscribe === "function") {
                    unsubscribe();
                }
            });
            controller._delegates = [];
            controller.disconnect_status_stream(controller);
        };

        controller.hideStacktrace();

        controller.state.schedule = parseSchedule(dom);
        if (controller.events && typeof controller.events.emit === "function") {
            controller.events.emit("rap:schedule:loaded", {
                schedule: controller.state.schedule
            });
        }
        dispatchControlEvent("rap:schedule:loaded", {
            schedule: controller.state.schedule
        });

        if (controller.form) {
            controller._delegates.push(dom.delegate(controller.form, "click", ACTIONS.run, function (event) {
                event.preventDefault();
                controller.acquire();
            }));
        }

        return controller;
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
    globalThis.RAP_TS = RAP_TS;
}
