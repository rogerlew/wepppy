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
        hint: "#hint_run_observed"
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

    function normalizeError(http, error) {
        if (http && typeof http.isHttpError === "function" && http.isHttpError(error)) {
            if (error.body && typeof error.body === "object") {
                if (error.body.error !== undefined || error.body.errors !== undefined) {
                    return error.body;
                }
                if (error.body.message || error.body.detail) {
                    return { error: { message: normalizeErrorValue(error.body.message || error.body.detail) } };
                }
            }
            var detail = error.detail || error.message || "Request failed";
            return { error: { message: normalizeErrorValue(detail) || "Request failed" } };
        }
        return { error: { message: normalizeErrorValue(error && error.message) || "Request failed" } };
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
        var stacktraceElement = null;
        var controller = Object.assign(base, {
            dom: dom,
            forms: forms,
            http: http,
            events: emitter,
            form: null,
            container: null,
            statusStream: null,
            command_btn_id: "btn_run_observed",
            state: {
                visible: false,
                keepVisible: false
            },
            _delegates: []
        });

        function bindForm() {
            var nextForm = dom.qs(SELECTORS.form);
            if (nextForm === formElement) {
                return;
            }
            controller.dispose();
            formElement = nextForm;
            controller.form = nextForm;
            controller.container = nextForm
                ? nextForm.closest(".controller-section") || nextForm
                : null;
            controller.info = createLegacyAdapter(nextForm ? dom.qs(SELECTORS.info, nextForm) : null);
            controller.status = createLegacyAdapter(nextForm ? dom.qs(SELECTORS.status, nextForm) : null);
            stacktraceElement = nextForm ? dom.qs(SELECTORS.stacktrace, nextForm) : null;
            controller.stacktrace = createLegacyAdapter(stacktraceElement);
            controller.rq_job = createLegacyAdapter(nextForm ? dom.qs(SELECTORS.rqJob, nextForm) : null);
            controller.hint = createLegacyAdapter(nextForm ? dom.qs(SELECTORS.hint, nextForm) : null);
            controller.textarea = nextForm ? dom.qs(SELECTORS.textarea, nextForm) : null;
            controller.statusPanelEl = nextForm ? dom.qs("#observed_status_panel", nextForm) : null;
            controller.stacktracePanelEl = nextForm ? dom.qs("#observed_stacktrace_panel", nextForm) : null;
            controller.statusSpinnerEl = controller.statusPanelEl
                ? controller.statusPanelEl.querySelector("#braille") : null;
            if (!nextForm) {
                return;
            }
            controller.attach_status_stream(controller, {
                element: controller.statusPanelEl,
                form: nextForm,
                channel: WS_CHANNEL,
                runId: window.runid || window.runId || null,
                stacktrace: controller.stacktracePanelEl ? { element: controller.stacktracePanelEl } : null,
                spinner: controller.statusSpinnerEl
            });
            controller._delegates.push(dom.delegate(nextForm, "click", ACTIONS.run, function (event) {
                event.preventDefault();
                controller.run_model_fit();
            }));
            controller.hideStacktrace();
        }

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
            if (!controller.form || !controller.form.isConnected) {
                return;
            }
            var requestedForm = controller.form;
            return http.getJson(url_for_run("query/climate_has_observed/")).then(function (hasObserved) {
                var available = false;
                if (typeof hasObserved === "boolean") {
                    available = hasObserved;
                } else if (hasObserved && typeof hasObserved === "object" && typeof hasObserved.available === "boolean") {
                    available = hasObserved.available;
                }

                if (controller.form !== requestedForm || !requestedForm.isConnected) {
                    return;
                }
                if (available || controller.state.keepVisible) {
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
            var modelSource = payload.model_source || payload.observed_model_source;
            if (typeof modelSource === "string" && modelSource.trim()) {
                submission.model_source = modelSource.trim();
            }

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

            http.postJson(url_for_run("tasks/run_model_fit/"), submission, { form: controller.form }).then(function (response) {
                var body = response && response.body !== undefined ? response.body : response;
                var normalized = body || {};

                if (!normalized.error && !normalized.errors) {
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
            controller.detach_status_stream(controller);
        };

        bindForm();

        controller.bootstrap = function bootstrap(context) {
            bindForm();
            if (!controller.form) {
                return controller;
            }
            var ctx = context || {};
            var climateData = (ctx.data && ctx.data.climate) || {};
            var observedData = (ctx.data && ctx.data.observed) || {};
            var modFlags = (ctx.mods && ctx.mods.flags) || {};
            controller.state.keepVisible = Boolean(modFlags.observed || observedData.hasResults
                || observedData.resultsAvailable || (ctx.flags && ctx.flags.playwrightLoadAll));
            var shouldShow = controller.state.keepVisible || Boolean(climateData.hasObserved);

            if (typeof controller.hideControl === "function") {
                controller.hideControl();
            }
            if (shouldShow && typeof controller.showControl === "function") {
                controller.showControl();
            }
            if (observedData.hasResults && typeof controller.report === "function") {
                controller.report();
            }
            return controller;
        };

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
