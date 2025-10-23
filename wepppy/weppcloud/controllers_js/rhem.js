/* ----------------------------------------------------------------------------
 * Rhem
 * Doc: controllers_js/README.md — RHEM Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var Rhem = (function () {
    var instance;

    var EVENT_NAMES = [
        "rhem:config:loaded",
        "rhem:run:started",
        "rhem:run:queued",
        "rhem:run:completed",
        "rhem:run:failed",
        "rhem:status:updated"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function") {
            throw new Error("Rhem controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Rhem controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("Rhem controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Rhem controller requires WCEvents helpers.");
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

    function getActiveRunId() {
        return window.runid || window.runId || null;
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var eventsApi = helpers.events;

        var rhem = controlBase();

        var formElement = dom.ensureElement("#rhem_form", "RHEM form not found.");
        var infoElement = dom.qs("#rhem_form #info");
        var statusElement = dom.qs("#rhem_form #status");
        var stacktraceElement = dom.qs("#rhem_form #stacktrace");
        var rqJobElement = dom.qs("#rhem_form #rq_job");
        var hintElement = dom.qs("#hint_run_rhem");
        var statusPanelElement = dom.qs("#rhem_status_panel");
        var stacktracePanelElement = dom.qs("#rhem_stacktrace_panel");
        var statusSpinnerElement = statusPanelElement ? statusPanelElement.querySelector("#braille") : null;
        var resultsElement = dom.qs("#rhem-results");

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);
        var hintAdapter = createLegacyAdapter(hintElement);

        var emitter = eventsApi.useEventMap(EVENT_NAMES, eventsApi.createEmitter());

        rhem.form = formElement;
        rhem.info = infoAdapter;
        rhem.status = statusAdapter;
        rhem.stacktrace = stacktraceAdapter;
        rhem.rq_job = rqJobAdapter;
        rhem.hint = hintAdapter;
        rhem.statusPanelEl = statusPanelElement || null;
        rhem.stacktracePanelEl = stacktracePanelElement || null;
        rhem.statusSpinnerEl = statusSpinnerElement || null;
        rhem.command_btn_id = "btn_run_rhem";
        rhem.statusStream = null;
        rhem.events = emitter;

        function renderStatus(message, meta) {
            if (!message) {
                return;
            }
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(message);
            } else if (statusElement) {
                statusElement.innerHTML = message;
            }
            emitter.emit("rhem:status:updated", {
                message: message,
                meta: meta || null
            });
        }

        function appendStatus(message, meta) {
            if (!message) {
                return;
            }
            if (rhem.statusStream && typeof rhem.statusStream.append === "function") {
                rhem.statusStream.append(message, meta || null);
                return;
            }
            renderStatus(message, meta);
        }
        rhem.appendStatus = appendStatus;

        function clearStatus(taskMsg) {
            if (infoAdapter && typeof infoAdapter.text === "function") {
                infoAdapter.text("");
            }
            rhem.clear_status_messages(rhem);
            if (taskMsg) {
                appendStatus(taskMsg + "...", { phase: "pending" });
            }
            if (stacktraceAdapter && typeof stacktraceAdapter.text === "function") {
                stacktraceAdapter.text("");
            } else if (stacktraceElement) {
                stacktraceElement.textContent = "";
            }
            if (hintAdapter && typeof hintAdapter.text === "function") {
                hintAdapter.text("");
            }
            rhem.hideStacktrace();
        }

        function handleError(error) {
            var payload = toResponsePayload(http, error);
            rhem.pushResponseStacktrace(rhem, payload);
            emitter.emit("rhem:run:failed", {
                runId: getActiveRunId(),
                error: payload
            });
            rhem.triggerEvent("job:error", {
                task: "rhem:run",
                error: payload
            });
            rhem.disconnect_status_stream(rhem);
        }
        rhem.attach_status_stream(rhem, {
            element: rhem.statusPanelEl,
            channel: "rhem",
            runId: getActiveRunId(),
            stacktrace: rhem.stacktracePanelEl ? { element: rhem.stacktracePanelEl } : null,
            spinner: rhem.statusSpinnerEl,
            logLimit: 200,
            onAppend: function (detail) {
                renderStatus(detail ? detail.message : "", detail ? detail.meta : null);
                emitter.emit("rhem:status:updated", detail || {});
            },
            onTrigger: function (detail) {
                if (detail && detail.event) {
                    rhem.triggerEvent(detail.event, detail);
                }
                emitter.emit("rhem:status:updated", detail || {});
            }
        });

        emitter.emit("rhem:config:loaded", {
            hasStatusStream: Boolean(rhem.statusStream),
            runId: getActiveRunId()
        });

        rhem.hideStacktrace = function () {
            if (stacktraceAdapter && typeof stacktraceAdapter.hide === "function") {
                stacktraceAdapter.hide();
                return;
            }
            if (stacktraceElement) {
                stacktraceElement.hidden = true;
                stacktraceElement.style.display = "none";
            }
        };

        function submitRunRequest() {
            var payload = forms.serializeForm(formElement, { format: "object" }) || {};
            http.postJson("rq/api/run_rhem_rq", payload, { form: formElement })
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && (response.Success === true || response.success === true)) {
                        var jobId = response.job_id || response.jobId || null;
                        appendStatus("run_rhem_rq job submitted: " + jobId, {
                            status: "queued"
                        });
                        rhem.set_rq_job_id(rhem, jobId);
                        emitter.emit("rhem:run:queued", {
                            runId: getActiveRunId(),
                            jobId: jobId
                        });
                        return;
                    }
                    var errorPayload = response || { Error: "RHEM job submission failed." };
                    rhem.pushResponseStacktrace(rhem, errorPayload);
                    emitter.emit("rhem:run:failed", {
                        runId: getActiveRunId(),
                        error: errorPayload
                    });
                    rhem.triggerEvent("job:error", {
                        task: "rhem:run",
                        error: errorPayload
                    });
                    rhem.disconnect_status_stream(rhem);
                })
                .catch(handleError);
        }

        rhem.run = function () {
            var taskMsg = "Submitting RHEM run";
            clearStatus(taskMsg);

            rhem.triggerEvent("job:started", {
                task: "rhem:run",
                runId: getActiveRunId()
            });
            emitter.emit("rhem:run:started", {
                runId: getActiveRunId(),
                jobId: null
            });

            rhem.connect_status_stream(rhem);

            submitRunRequest();
        };

        rhem.report = function () {
            var taskMsg = "Fetching Summary";
            clearStatus(taskMsg);

            http.request(url_for_run("report/rhem/results/"), {
                method: "GET",
                headers: { Accept: "text/html,application/xhtml+xml" }
            }).then(function (result) {
                var html = typeof result.body === "string" ? result.body : "";
                if (resultsElement) {
                    resultsElement.innerHTML = html;
                }
            }).catch(handleError);

            http.request(url_for_run("report/rhem/run_summary/"), {
                method: "GET",
                headers: { Accept: "text/html,application/xhtml+xml" }
            }).then(function (result) {
                var html = typeof result.body === "string" ? result.body : "";
                if (infoAdapter && typeof infoAdapter.html === "function") {
                    infoAdapter.html(html);
                } else if (infoElement) {
                    infoElement.innerHTML = html;
                }
                appendStatus(taskMsg + "... Success", { status: "completed" });

                if (window.Project && typeof window.Project.getInstance === "function") {
                    try {
                        var project = window.Project.getInstance();
                        if (project && typeof project.set_preferred_units === "function") {
                            project.set_preferred_units();
                        }
                    } catch (err) {
                        console.warn("[Rhem] Failed to set preferred units", err);
                    }
                }

                emitter.emit("rhem:run:completed", {
                    runId: getActiveRunId(),
                    jobId: rhem.rq_job_id || null
                });
                rhem.triggerEvent("job:completed", {
                    task: "rhem:run",
                    jobId: rhem.rq_job_id || null
                });
            }).catch(handleError);
        };

        var baseTriggerEvent = rhem.triggerEvent.bind(rhem);
        rhem.triggerEvent = function (eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === "RHEM_RUN_TASK_COMPLETED") {
                rhem.disconnect_status_stream(rhem);
                rhem.report();
            }
            baseTriggerEvent(eventName, payload);
        };

        dom.delegate(formElement, "click", "[data-rhem-action='run']", function (event) {
            event.preventDefault();
            rhem.run();
        });

        var bootstrapState = {
            reportLoaded: false
        };

        rhem.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            var controllerContext = helper && typeof helper.getControllerContext === "function"
                ? helper.getControllerContext(ctx, "rhem")
                : {};

            var jobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "run_rhem_rq")
                : null;
            if (!jobId && controllerContext.jobId) {
                jobId = controllerContext.jobId;
            }
            if (!jobId) {
                var jobIds = ctx && (ctx.jobIds || ctx.jobs);
                if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "run_rhem_rq")) {
                    var value = jobIds.run_rhem_rq;
                    if (value !== undefined && value !== null) {
                        jobId = String(value);
                    }
                }
            }

            if (typeof rhem.set_rq_job_id === "function") {
                rhem.set_rq_job_id(rhem, jobId);
            }

            var rhemData = (ctx.data && ctx.data.rhem) || {};
            var hasRun = controllerContext.hasRun;
            if (hasRun === undefined) {
                hasRun = rhemData.hasRun;
            }

            if (hasRun && !bootstrapState.reportLoaded && typeof rhem.report === "function") {
                rhem.report();
                bootstrapState.reportLoaded = true;
            }

            return rhem;
        };

        return rhem;
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
    globalThis.Rhem = Rhem;
}
