/* ----------------------------------------------------------------------------
 * Observed
 * Doc: controllers_js/README.md — Observed Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var Observed = (function () {
    "use strict";

    var instance;

    var FORM_ID = "observed_form";
    var WS_CHANNEL = "observed";
    var TASK_NAME = "observed:model-fit";
    var RUN_MESSAGE = "Running observed model fit";

    var SELECTORS = {
        form: "#" + FORM_ID,
        info: "#info",
        status: "#status",
        stacktrace: "#stacktrace",
        rqJob: "#rq_job",
        textarea: "#observed_text",
        hint: "#hint_run_wepp"
    };

    var ACTIONS = {
        run: '[data-action="observed-run"]'
    };

    var EVENT_NAMES = [
        "observed:data:loaded",
        "observed:model:fit",
        "observed:error",
        "job:started",
        "job:completed",
        "job:error"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.delegate !== "function" || typeof dom.hide !== "function" || typeof dom.show !== "function") {
            throw new Error("Observed controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Observed controller requires WCForms helpers.");
        }
        if (!http || typeof http.postJson !== "function" || typeof http.getJson !== "function") {
            throw new Error("Observed controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Observed controller requires WCEvents helpers.");
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

    function normalizeError(http, error) {
        if (http && typeof http.isHttpError === "function" && http.isHttpError(error)) {
            var detail = error.detail || error.message || "Request failed";
            var stacktrace = [];
            if (error.body && typeof error.body === "object") {
                if (Array.isArray(error.body.StackTrace)) {
                    stacktrace = error.body.StackTrace;
                } else if (typeof error.body.StackTrace === "string") {
                    stacktrace = [error.body.StackTrace];
                }
                if (error.body.Error) {
                    detail = error.body.Error;
                }
            }
            return {
                Success: false,
                Error: detail,
                StackTrace: stacktrace
            };
        }
        return {
            Success: false,
            Error: (error && error.message) || "Request failed"
        };
    }

    function createInstance() {
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
            console.warn("[Observed] Unable to locate form element:", err);
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
        var textAreaElement = formElement ? dom.qs(SELECTORS.textarea, formElement) : null;
        var hintElement = formElement ? dom.qs(SELECTORS.hint, formElement) : null;
        var statusPanelElement = dom.qs("#observed_status_panel");
        var stacktracePanelElement = dom.qs("#observed_stacktrace_panel");
        var spinnerElement = statusPanelElement ? statusPanelElement.querySelector("#braille") : null;

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
            textarea: textAreaElement,
            statusPanelEl: statusPanelElement,
            stacktracePanelEl: stacktracePanelElement,
            statusSpinnerEl: spinnerElement,
            statusStream: null,
            command_btn_id: "btn_run_observed",
            state: {
                visible: false
            },
            _delegates: []
        });

        controller.attach_status_stream(controller, {
            element: statusPanelElement,
            form: formElement,
            channel: WS_CHANNEL,
            runId: window.runid || window.runId || null,
            stacktrace: stacktracePanelElement ? { element: stacktracePanelElement } : null,
            spinner: spinnerElement
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

        controller.showControl = function () {
            controller.state.visible = true;
            if (controller.container) {
                dom.show(controller.container);
            }
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("observed:data:loaded", { available: true });
            }
        };

        controller.hideControl = function () {
            controller.state.visible = false;
            if (controller.container) {
                dom.hide(controller.container);
            }
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("observed:data:loaded", { available: false });
            }
        };

        controller.onWeppRunCompleted = function () {
            http.getJson("query/climate_has_observed/").then(function (hasObserved) {
                var available = false;
                if (typeof hasObserved === "boolean") {
                    available = hasObserved;
                } else if (hasObserved && typeof hasObserved === "object" && typeof hasObserved.available === "boolean") {
                    available = hasObserved.available;
                }

                if (available) {
                    controller.showControl();
                } else {
                    controller.hideControl();
                }
            }).catch(function (error) {
                controller.pushErrorStacktrace(controller, error);
                if (controller.events && typeof controller.events.emit === "function") {
                    controller.events.emit("observed:error", {
                        context: "climate_has_observed",
                        error: error
                    });
                }
            });
        };

        controller.report = function () {
            if (!controller.info || typeof controller.info.html !== "function") {
                return;
            }
            var href = url_for_run("report/observed/");
            controller.info.html("<a href='" + href + "' target='_blank'>View Model Fit Results</a>");
        };

        controller.run_model_fit = function () {
            if (!controller.form) {
                return;
            }

            controller.info.html("");
            controller.status.html(RUN_MESSAGE + "…");
            controller.stacktrace.text("");
            controller.hideStacktrace();
            if (controller.hint && typeof controller.hint.text === "function") {
                controller.hint.text("");
            }

            var payload = forms.serializeForm(controller.form, { format: "json" }) || {};
            var text = "";
            if (typeof payload.data === "string" && payload.data) {
                text = payload.data;
            } else if (typeof payload.observed_text === "string") {
                text = payload.observed_text;
            } else if (controller.textarea && typeof controller.textarea.value === "string") {
                text = controller.textarea.value;
            }

            var submission = { data: text };

            controller.triggerEvent("job:started", {
                task: TASK_NAME,
                payload: submission
            });
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("observed:model:fit", {
                    status: "started",
                    task: TASK_NAME,
                    payload: submission
                });
            }

            controller.connect_status_stream(controller);

            http.postJson("tasks/run_model_fit/", submission, { form: controller.form }).then(function (response) {
                var body = response && response.body !== undefined ? response.body : response;
                var normalized = body || {};

                if (normalized.Success === true || normalized.success === true) {
                    controller.status.html(RUN_MESSAGE + "… done.");
                    controller.report();
                    if (controller.events && typeof controller.events.emit === "function") {
                        controller.events.emit("observed:model:fit", {
                            status: "completed",
                            task: TASK_NAME,
                            payload: submission,
                            response: normalized
                        });
                    }
                    controller.triggerEvent("job:completed", {
                        task: TASK_NAME,
                        payload: submission,
                        response: normalized
                    });
                } else {
                    controller.pushResponseStacktrace(controller, normalized);
                    if (controller.events && typeof controller.events.emit === "function") {
                        controller.events.emit("observed:error", {
                            task: TASK_NAME,
                            payload: submission,
                            error: normalized
                        });
                    }
                    controller.triggerEvent("job:error", {
                        task: TASK_NAME,
                        payload: submission,
                        error: normalized
                    });
                }
            }).catch(function (error) {
                var normalizedError = normalizeError(http, error);
                controller.pushResponseStacktrace(controller, normalizedError);
                if (controller.events && typeof controller.events.emit === "function") {
                    controller.events.emit("observed:error", {
                        task: TASK_NAME,
                        payload: submission,
                        error: normalizedError
                    });
                }
                controller.triggerEvent("job:error", {
                    task: TASK_NAME,
                    payload: submission,
                    error: normalizedError
                });
            }).finally(function () {
                controller.disconnect_status_stream(controller);
            });
        };

        controller.runModelFit = controller.run_model_fit;

        controller.dispose = function () {
            controller._delegates.forEach(function (unsubscribe) {
                if (typeof unsubscribe === "function") {
                    unsubscribe();
                }
            });
            controller._delegates = [];
            controller.disconnect_status_stream(controller);
        };

        if (formElement) {
            controller._delegates.push(dom.delegate(formElement, "click", ACTIONS.run, function (event) {
                event.preventDefault();
                controller.run_model_fit();
            }));
        }

        controller.hideStacktrace();

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
})();

if (typeof globalThis !== "undefined") {
    globalThis.Observed = Observed;
}
