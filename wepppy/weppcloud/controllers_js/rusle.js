/* ----------------------------------------------------------------------------
 * Rusle
 * ----------------------------------------------------------------------------
 */
var Rusle = (function () {
    "use strict";

    var instance;

    var FORM_ID = "rusle_form";
    var WS_CHANNEL = "rusle";
    var TASK_NAME = "rusle:build";
    var COMPLETE_EVENT = "RUSLE_BUILD_TASK_COMPLETED";

    var SELECTORS = {
        form: "#" + FORM_ID,
        results: "#rusle-results",
        status: "#status",
        stacktrace: "#stacktrace",
        rqJob: "#rq_job",
        hint: "#hint_build_rusle",
        statusPanel: "#rusle_status_panel",
        stacktracePanel: "#rusle_stacktrace_panel",
        rapYearSection: '[data-rusle-section="rap-year"]',
        cMode: '[data-rusle-c-mode]',
        kMode: '[data-rusle-k-mode]',
        defaultKMode: "#default_k_mode",
        runAction: '[data-rusle-action="run"]'
    };

    var EVENT_NAMES = [
        "rusle:config:loaded",
        "rusle:mode:changed",
        "rusle:k-modes:changed",
        "rusle:build:started",
        "rusle:build:queued",
        "rusle:build:completed",
        "rusle:build:failed",
        "rusle:report:loaded",
        "rusle:status:updated",
        "job:started",
        "job:completed",
        "job:error"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.delegate !== "function" || typeof dom.qs !== "function") {
            throw new Error("Rusle controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Rusle controller requires WCForms helpers.");
        }
        if (
            !http ||
            typeof http.postJsonWithSessionToken !== "function" ||
            typeof http.request !== "function" ||
            typeof http.isHttpError !== "function"
        ) {
            throw new Error("Rusle controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Rusle controller requires WCEvents helpers.");
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

        var body = coerceBody(error && error.body ? error.body : null);

        if (body && typeof body === "object") {
            if (body.error || body.errors) {
                return body;
            }
            if (body.message || body.detail) {
                return { error: { message: body.message || body.detail, details: body.details } };
            }
            return body;
        } else if (typeof body === "string" && body) {
            return { error: { message: body } };
        }

        if (http && typeof http.isHttpError === "function" && http.isHttpError(error)) {
            var detail = error && (error.detail || error.message);
            if (detail && typeof detail === "object" && (detail.error || detail.errors)) {
                return detail;
            }
            return { error: { message: detail || "Request failed" } };
        }

        return { error: { message: (error && error.message) || "Request failed" } };
    }

    function selectedKModes(formElement) {
        if (!formElement) {
            return [];
        }
        var boxes = formElement.querySelectorAll(SELECTORS.kMode);
        var modes = [];
        Array.prototype.forEach.call(boxes, function (box) {
            if (box && box.checked) {
                modes.push(String(box.value || "").trim());
            }
        });
        return modes.filter(function (mode) {
            return mode.length > 0;
        });
    }

    function ensureAtLeastOneKMode(formElement) {
        var modes = selectedKModes(formElement);
        if (modes.length > 0) {
            return modes;
        }
        var fallback = formElement ? formElement.querySelector('#rusle_k_mode_nomograph') : null;
        if (fallback) {
            fallback.checked = true;
        }
        return selectedKModes(formElement);
    }

    function syncDefaultKMode(formElement) {
        if (!formElement) {
            return;
        }
        var select = formElement.querySelector(SELECTORS.defaultKMode);
        if (!select) {
            return;
        }

        var modes = ensureAtLeastOneKMode(formElement);
        var modeSet = {};
        modes.forEach(function (mode) {
            modeSet[mode] = true;
        });

        var firstEnabled = null;
        Array.prototype.forEach.call(select.options || [], function (option) {
            var enabled = Boolean(modeSet[option.value]);
            option.disabled = !enabled;
            if (enabled && firstEnabled === null) {
                firstEnabled = option.value;
            }
        });

        if (!modeSet[select.value] && firstEnabled !== null) {
            select.value = firstEnabled;
        }
    }

    function syncRapYearVisibility(formElement) {
        if (!formElement) {
            return;
        }
        var checked = formElement.querySelector(SELECTORS.cMode + ":checked");
        var cMode = checked ? String(checked.value || "") : "observed_rap";
        var section = formElement.querySelector(SELECTORS.rapYearSection);
        if (!section) {
            return;
        }
        if (cMode === "observed_rap") {
            section.hidden = false;
            if (section.style) {
                section.style.removeProperty("display");
            }
        } else {
            section.hidden = true;
            if (section.style) {
                section.style.display = "none";
            }
        }
    }

    function buildPayload(controller) {
        var payload = controller.forms.serializeForm(controller.form, { format: "object" }) || {};
        payload.k_modes = ensureAtLeastOneKMode(controller.form);
        syncDefaultKMode(controller.form);

        if (payload.default_k_mode && payload.k_modes.indexOf(payload.default_k_mode) === -1 && payload.k_modes.length) {
            payload.default_k_mode = payload.k_modes[0];
        }

        if (payload.c_mode !== "observed_rap") {
            delete payload.rap_year;
        } else if (payload.rap_year === "" || payload.rap_year === null || payload.rap_year === undefined) {
            delete payload.rap_year;
        }

        return payload;
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

        var formElement = dom.qs(SELECTORS.form);
        var resultsElement = dom.qs(SELECTORS.results);
        var statusElement = formElement ? dom.qs(SELECTORS.status, formElement) : null;
        var stacktraceElement = formElement ? dom.qs(SELECTORS.stacktrace, formElement) : null;
        var rqJobElement = formElement ? dom.qs(SELECTORS.rqJob, formElement) : null;
        var hintElement = formElement ? dom.qs(SELECTORS.hint, formElement) : null;
        var statusPanelElement = dom.qs(SELECTORS.statusPanel);
        var stacktracePanelElement = dom.qs(SELECTORS.stacktracePanel);
        var statusSpinnerElement = statusPanelElement ? statusPanelElement.querySelector("#braille") : null;

        var controller = Object.assign(base, {
            dom: dom,
            forms: forms,
            http: http,
            events: emitter,
            form: formElement,
            resultsContainer: resultsElement,
            status: createLegacyAdapter(statusElement),
            stacktrace: createLegacyAdapter(stacktraceElement),
            rq_job: createLegacyAdapter(rqJobElement),
            hint: createLegacyAdapter(hintElement),
            statusPanelEl: statusPanelElement,
            stacktracePanelEl: stacktracePanelElement,
            statusSpinnerEl: statusSpinnerElement,
            statusStream: null,
            command_btn_id: "btn_build_rusle",
            _completion_seen: false
        });

        function getActiveRunId() {
            return window.runid || window.runId || null;
        }

        function resetCompletionSeen() {
            controller._completion_seen = false;
        }

        function appendStatus(message, meta) {
            if (!message) {
                return;
            }
            if (controller.statusStream && typeof controller.statusStream.append === "function") {
                controller.statusStream.append(message, meta || null);
            }
            if (controller.status && typeof controller.status.html === "function") {
                controller.status.html(message);
            }
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("rusle:status:updated", {
                    message: message,
                    meta: meta || null
                });
            }
        }

        function clearStatus(message) {
            if (typeof controller.reset_panel_state === "function") {
                controller.reset_panel_state(controller, {
                    message: message,
                    clearStatus: true,
                    clearSummary: true,
                    clearHint: true,
                    clearResults: true,
                    resultsTarget: controller.resultsContainer,
                    clearStacktrace: true
                });
            } else {
                controller.clear_status_messages(controller);
            }
            if (controller.hint && typeof controller.hint.text === "function") {
                controller.hint.text("");
            }
            if (controller.stacktrace && typeof controller.stacktrace.hide === "function") {
                controller.stacktrace.hide();
            }
        }

        function handleError(error) {
            var payload = toResponsePayload(http, error);
            controller.pushResponseStacktrace(controller, payload);
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("rusle:build:failed", {
                    runId: getActiveRunId(),
                    error: payload
                });
            }
            controller.triggerEvent("job:error", {
                task: TASK_NAME,
                error: payload,
                runId: getActiveRunId()
            });
            controller.disconnect_status_stream(controller);
        }

        controller.attach_status_stream(controller, {
            element: statusPanelElement,
            channel: WS_CHANNEL,
            runId: getActiveRunId(),
            stacktrace: stacktracePanelElement ? { element: stacktracePanelElement } : null,
            spinner: statusSpinnerElement,
            logLimit: 200,
            onAppend: function (detail) {
                if (controller.events && typeof controller.events.emit === "function") {
                    controller.events.emit("rusle:status:updated", detail || {});
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

        controller.syncUi = function () {
            syncRapYearVisibility(controller.form);
            syncDefaultKMode(controller.form);
            if (controller.events && typeof controller.events.emit === "function") {
                var modeControl = controller.form ? controller.form.querySelector(SELECTORS.cMode + ":checked") : null;
                controller.events.emit("rusle:mode:changed", {
                    mode: modeControl ? modeControl.value : null
                });
                controller.events.emit("rusle:k-modes:changed", {
                    k_modes: selectedKModes(controller.form)
                });
            }
        };

        controller.report = function () {
            var target = controller.resultsContainer;
            if (!target) {
                return;
            }

            http.request(url_for_run("report/rusle/results/"))
                .then(function (result) {
                    var body = result && result.body;
                    if (typeof body === "string") {
                        target.innerHTML = body;
                        if (controller.events && typeof controller.events.emit === "function") {
                            controller.events.emit("rusle:report:loaded", {
                                runId: getActiveRunId(),
                                html: body
                            });
                        }
                    }
                })
                .catch(function (error) {
                    controller.pushResponseStacktrace(controller, toResponsePayload(http, error));
                });
        };

        function submitBuild() {
            var payload = buildPayload(controller);

            http.postJsonWithSessionToken(
                url_for_run("build-rusle", { prefix: "/rq-engine/api" }),
                payload,
                { form: controller.form }
            )
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && response.job_id) {
                        var jobId = response.job_id;
                        appendStatus("build_rusle_rq job submitted: " + jobId, {
                            status: "queued",
                            job_id: jobId
                        });
                        controller.poll_completion_event = COMPLETE_EVENT;
                        controller.set_rq_job_id(controller, jobId);
                        if (controller.events && typeof controller.events.emit === "function") {
                            controller.events.emit("rusle:build:queued", {
                                runId: getActiveRunId(),
                                job_id: jobId,
                                payload: payload
                            });
                        }
                        return;
                    }

                    var errorPayload = response || { error: { message: "RUSLE build submission failed." } };
                    controller.pushResponseStacktrace(controller, errorPayload);
                    if (controller.events && typeof controller.events.emit === "function") {
                        controller.events.emit("rusle:build:failed", {
                            runId: getActiveRunId(),
                            payload: payload,
                            error: errorPayload
                        });
                    }
                    controller.triggerEvent("job:error", {
                        task: TASK_NAME,
                        payload: payload,
                        error: errorPayload
                    });
                    controller.disconnect_status_stream(controller);
                })
                .catch(handleError);
        }

        controller.run = function () {
            clearStatus("Submitting RUSLE build");
            resetCompletionSeen();
            controller.syncUi();

            var payload = buildPayload(controller);
            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("rusle:build:started", {
                    runId: getActiveRunId(),
                    payload: payload
                });
            }
            controller.triggerEvent("job:started", {
                task: TASK_NAME,
                runId: getActiveRunId(),
                payload: payload
            });

            controller.connect_status_stream(controller);
            submitBuild();
        };

        var baseTriggerEvent = controller.triggerEvent.bind(controller);
        controller.triggerEvent = function (eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === COMPLETE_EVENT) {
                if (controller._completion_seen) {
                    return baseTriggerEvent(eventName, payload);
                }
                controller._completion_seen = true;
                controller.disconnect_status_stream(controller);
                if (typeof controller.report === "function") {
                    controller.report();
                }
                if (controller.events && typeof controller.events.emit === "function") {
                    controller.events.emit("rusle:build:completed", {
                        runId: getActiveRunId(),
                        job_id: controller.rq_job_id || null,
                        detail: payload || null
                    });
                }
                baseTriggerEvent("job:completed", {
                    task: TASK_NAME,
                    runId: getActiveRunId(),
                    job_id: controller.rq_job_id || null,
                    detail: payload || null
                });
            }
            return baseTriggerEvent(eventName, payload);
        };

        if (formElement) {
            dom.delegate(formElement, "click", SELECTORS.runAction, function (event) {
                event.preventDefault();
                controller.run();
            });

            dom.delegate(formElement, "change", SELECTORS.cMode, function () {
                controller.syncUi();
            });

            dom.delegate(formElement, "change", SELECTORS.kMode, function () {
                controller.syncUi();
            });
        }

        var bootstrapState = {
            reportTriggered: false
        };

        controller.bootstrap = function bootstrap(context) {
            controller.syncUi();
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            var jobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "build_rusle_rq")
                : null;

            if (!jobId) {
                var jobIds = ctx && (ctx.jobIds || ctx.jobs);
                if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "build_rusle_rq")) {
                    var value = jobIds.build_rusle_rq;
                    if (value !== undefined && value !== null) {
                        jobId = String(value);
                    }
                }
            }

            if (typeof controller.set_rq_job_id === "function") {
                if (jobId) {
                    controller.poll_completion_event = COMPLETE_EVENT;
                    resetCompletionSeen();
                }
                controller.set_rq_job_id(controller, jobId);
            }

            if (controller.events && typeof controller.events.emit === "function") {
                controller.events.emit("rusle:config:loaded", {
                    runId: getActiveRunId(),
                    job_id: jobId || null
                });
            }

            if (!bootstrapState.reportTriggered && typeof controller.report === "function") {
                controller.report();
                bootstrapState.reportTriggered = true;
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
        },

        remount: function remount() {
            if (instance && typeof instance.detach_status_stream === "function") {
                instance.detach_status_stream(instance);
            }
            instance = createInstance();
            return instance;
        }
    };
})();

if (typeof globalThis !== "undefined") {
    globalThis.Rusle = Rusle;
}
