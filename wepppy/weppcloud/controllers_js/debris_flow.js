/* ----------------------------------------------------------------------------
 * DebrisFlow
 * Doc: controllers_js/README.md — Debris Flow Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var DebrisFlow = (function () {
    var instance;

    var EVENT_NAMES = [
        "debris:run:started",
        "debris:run:completed",
        "debris:run:error"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function") {
            throw new Error("DebrisFlow controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("DebrisFlow controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("DebrisFlow controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("DebrisFlow controller requires WCEvents helpers.");
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
            var payload = body;
            if (payload.Error === undefined) {
                var fallback =
                    payload.detail ||
                    payload.message ||
                    payload.error ||
                    payload.errors;
                if (fallback !== undefined && fallback !== null) {
                    payload = Object.assign({}, payload, { Error: fallback });
                }
            }
            if (payload.StackTrace !== undefined || payload.Error !== undefined) {
                return payload;
            }
        } else if (typeof body === "string" && body) {
            return { Error: body };
        }

        if (error && typeof error === "object" && (error.Error !== undefined || error.StackTrace !== undefined)) {
            return error;
        }

        if (http && typeof http.isHttpError === "function" && http.isHttpError(error)) {
            var detail = error && (error.detail || error.message);
            return { Error: detail || "Request failed" };
        }

        return { Error: (error && error.message) || "Request failed" };
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var eventsApi = helpers.events;

        var emitter = eventsApi.useEventMap(EVENT_NAMES, eventsApi.createEmitter());

        var formElement = dom.qs("#debris_flow_form");
        if (!formElement) {
            var placeholder = controlBase();
            placeholder.form = null;
            placeholder.events = emitter;
            placeholder.command_btn_id = "btn_run_debris_flow";
            placeholder.run = function () {
                return null;
            };
            placeholder.report = function () {};
            placeholder.bootstrap = function () {
                return placeholder;
            };
            return placeholder;
        }

        var debris = controlBase();

        var infoElement = dom.qs("#debris_flow_form #info");
        var statusElement = dom.qs("#debris_flow_form #status");
        var stacktraceElement = dom.qs("#debris_flow_form #stacktrace");
        var rqJobElement = dom.qs("#debris_flow_form #rq_job");
        var hintElement = dom.qs("#hint_run_debris_flow");
        var statusPanelElement = dom.qs("#debris_flow_status_panel");
        var stacktracePanelElement = dom.qs("#debris_flow_stacktrace_panel");
        var spinnerElement = statusPanelElement ? statusPanelElement.querySelector("#braille") : null;

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);
        var hintAdapter = createLegacyAdapter(hintElement);

        debris.form = formElement;
        debris.info = infoAdapter;
        debris.status = statusAdapter;
        debris.stacktrace = stacktraceAdapter;
        debris.rq_job = rqJobAdapter;
        debris.hint = hintAdapter;
        debris.command_btn_id = "btn_run_debris_flow";
        debris.statusPanelEl = statusPanelElement || null;
        debris.stacktracePanelEl = stacktracePanelElement || null;
        debris.statusSpinnerEl = spinnerElement || null;
        debris._completion_seen = false;
        debris._poll_failure_seen = false;
        debris.attach_status_stream(debris, {
            element: statusPanelElement,
            form: formElement,
            channel: "debris_flow",
            runId: window.runid || window.runId || null,
            stacktrace: stacktracePanelElement ? { element: stacktracePanelElement } : null,
            spinner: spinnerElement
        });
        debris.events = emitter;

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
            if (hintAdapter && typeof hintAdapter.text === "function") {
                hintAdapter.text("");
            }
            debris.hideStacktrace();
        }

        function resetCompletionSeen() {
            debris._completion_seen = false;
            debris._poll_failure_seen = false;
        }

        function handleError(error) {
            var payload = toResponsePayload(http, error);
            debris.pushResponseStacktrace(debris, payload);
            emitter.emit("debris:run:error", { error: payload });
            debris.triggerEvent("job:error", { task: "debris:run", error: payload });
            debris.disconnect_status_stream(debris);
        }

        debris.hideStacktrace = function () {
            if (stacktraceAdapter && typeof stacktraceAdapter.hide === "function") {
                stacktraceAdapter.hide();
                return;
            }
            if (stacktraceElement) {
                stacktraceElement.hidden = true;
                stacktraceElement.style.display = "none";
            }
        };

        debris.run = function () {
            var taskMsg = "Running debris flow model fit";
            resetStatus(taskMsg);
            resetCompletionSeen();

            var payload = forms.serializeForm(formElement, { format: "object" }) || {};
            var cleanPayload = {};
            Object.keys(payload).forEach(function (key) {
                var value = payload[key];
                if (value === null || value === undefined) {
                    return;
                }
                if (typeof value === "string" && value.trim() === "") {
                    return;
                }
                cleanPayload[key] = value;
            });

            debris.triggerEvent("job:started", { task: "debris:run" });
            emitter.emit("debris:run:started", { jobId: null, task: "debris:run" });

            debris.connect_status_stream(debris);

            http.postJson(url_for_run("rq/api/run_debris_flow"), cleanPayload, { form: formElement }).then(function (response) {
                var payload = response.body || {};
                if (payload.Success === true || payload.success === true) {
                    statusAdapter.html("run_debris_flow_rq job submitted: " + payload.job_id);
                    debris.poll_completion_event = "DEBRIS_FLOW_RUN_TASK_COMPLETED";
                    debris.set_rq_job_id(debris, payload.job_id);
                    emitter.emit("debris:run:started", {
                        jobId: payload.job_id,
                        task: "debris:run",
                        status: "queued"
                    });
                } else {
                    debris.pushResponseStacktrace(debris, payload);
                    emitter.emit("debris:run:error", { error: payload });
                    debris.triggerEvent("job:error", { task: "debris:run", error: payload });
                }
            }).catch(function (error) {
                handleError(error);
            });
        };

        debris.report = function () {
            infoAdapter.html("<a href='" + url_for_run("report/debris_flow/") + "' target='_blank'>View Debris Flow Model Results</a>");
            emitter.emit("debris:run:completed", {
                jobId: debris.rq_job_id || null,
                task: "debris:run"
            });
            if (!debris._job_completion_dispatched) {
                debris._job_completion_dispatched = true;
                debris.triggerEvent("job:completed", {
                    task: "debris:run",
                    jobId: debris.rq_job_id || null
                });
            }
        };

        function handleCompletion() {
            if (debris._completion_seen) {
                return;
            }
            debris._completion_seen = true;
            debris.disconnect_status_stream(debris);
            debris.report();
        }

        function extractJobInfoStacktrace(payload) {
            if (!payload) {
                return null;
            }
            if (payload.exc_info) {
                return payload.exc_info;
            }
            if (payload.description) {
                return payload.description;
            }
            var children = payload.children || {};
            var orders = Object.keys(children);
            for (var i = 0; i < orders.length; i += 1) {
                var list = children[orders[i]] || [];
                for (var j = 0; j < list.length; j += 1) {
                    var childStack = extractJobInfoStacktrace(list[j]);
                    if (childStack) {
                        return childStack;
                    }
                }
            }
            try {
                return JSON.stringify(payload, null, 2);
            } catch (err) {
                return String(payload);
            }
        }

        function handlePollFailure(statusObj) {
            if (debris._poll_failure_seen) {
                return;
            }
            var status = statusObj && statusObj.status ? String(statusObj.status).toLowerCase() : "";
            if (status !== "failed" && status !== "stopped" && status !== "canceled") {
                return;
            }
            debris._poll_failure_seen = true;

            var jobId = debris.rq_job_id || (statusObj && statusObj.id) || null;
            var errorPayload = { Error: "Debris flow job " + status + "." };

            if (!jobId || !http || typeof http.request !== "function") {
                debris.pushResponseStacktrace(debris, errorPayload);
                emitter.emit("debris:run:error", { error: errorPayload, status: status });
                debris.triggerEvent("job:error", { task: "debris:run", error: errorPayload, status: status });
                return;
            }

            http.request("/weppcloud/rq/api/jobinfo/" + encodeURIComponent(jobId))
                .then(function (result) {
                    var payload = result && result.body ? result.body : result;
                    if (typeof payload === "string") {
                        try {
                            payload = JSON.parse(payload);
                        } catch (err) {
                            payload = { exc_info: payload };
                        }
                    }
                    var stacktrace = extractJobInfoStacktrace(payload);
                    if (stacktrace) {
                        errorPayload.StackTrace = String(stacktrace).split("\n");
                    }
                    debris.pushResponseStacktrace(debris, errorPayload);
                    emitter.emit("debris:run:error", { error: errorPayload, status: status });
                    debris.triggerEvent("job:error", { task: "debris:run", error: errorPayload, status: status });
                })
                .catch(function (error) {
                    var fallback = toResponsePayload(http, error);
                    debris.pushResponseStacktrace(debris, fallback);
                    emitter.emit("debris:run:error", { error: fallback, status: status });
                    debris.triggerEvent("job:error", { task: "debris:run", error: fallback, status: status });
                });
        }

        var baseTriggerEvent = debris.triggerEvent.bind(debris);
        debris.triggerEvent = function (eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === "DEBRIS_FLOW_RUN_TASK_COMPLETED") {
                handleCompletion();
            }
            return baseTriggerEvent(eventName, payload);
        };

        var baseHandleJobStatusResponse = debris.handle_job_status_response;
        debris.handle_job_status_response = function (self, data) {
            if (typeof baseHandleJobStatusResponse === "function") {
                baseHandleJobStatusResponse(self, data);
            }
            handlePollFailure((self && self.rq_job_status) || data || null);
        };

        formElement.addEventListener("DEBRIS_FLOW_RUN_TASK_COMPLETED", function () {
            handleCompletion();
        });

        dom.delegate(formElement, "click", "[data-debris-action='run']", function (event) {
            event.preventDefault();
            debris.run();
        });

        debris.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            var jobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "run_debris_flow_rq")
                : null;
            if (!jobId && ctx.controllers && ctx.controllers.debrisFlow && ctx.controllers.debrisFlow.jobId) {
                jobId = ctx.controllers.debrisFlow.jobId;
            }
            if (!jobId) {
                var jobIds = ctx && (ctx.jobIds || ctx.jobs);
                if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "run_debris_flow_rq")) {
                    var value = jobIds.run_debris_flow_rq;
                    if (value !== undefined && value !== null) {
                        jobId = String(value);
                    }
                }
            }
            if (typeof debris.set_rq_job_id === "function") {
                if (jobId) {
                    debris.poll_completion_event = "DEBRIS_FLOW_RUN_TASK_COMPLETED";
                    resetCompletionSeen();
                }
                debris.set_rq_job_id(debris, jobId);
            }
            if (!jobId) {
                var hasResultsAttr = formElement.getAttribute("data-debris-has-results");
                if (hasResultsAttr === "true" && typeof debris.report === "function") {
                    debris.report();
                }
            }
            return debris;
        };

        return debris;
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
    globalThis.DebrisFlow = DebrisFlow;
}
