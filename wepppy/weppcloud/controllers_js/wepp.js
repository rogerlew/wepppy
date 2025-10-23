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
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Wepp controller requires WCEvents helpers.");
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
        if (http && typeof http.isHttpError === "function" && http.isHttpError(error)) {
            var detail = error.detail || error.body || error.message || "Request failed";
            return { Error: detail };
        }
        return { Error: (error && error.message) || "Request failed" };
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
        var resultsContainer = dom.qs("#wepp-results");
        var revegSelect = dom.qs("#reveg_scenario");
        var coverTransformContainer = dom.qs("#user_defined_cover_transform_container");

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);

        wepp.form = formElement;
        wepp.info = infoAdapter;
        wepp.status = statusAdapter;
        wepp.stacktrace = stacktraceAdapter;
        wepp.rq_job = rqJobAdapter;
        wepp.command_btn_id = "btn_run_wepp";

        wepp.statusPanelEl = dom.qs("#wepp_status_panel");
        wepp.stacktracePanelEl = dom.qs("#wepp_stacktrace_panel");
        wepp.statusSpinnerEl = wepp.statusPanelEl ? wepp.statusPanelEl.querySelector("#braille") : null;
        wepp.statusStream = null;
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

        wepp.attach_status_stream(wepp, {
            element: wepp.statusPanelEl,
            channel: "wepp",
            runId: window.runid || window.runId || null,
            stacktrace: wepp.stacktracePanelEl ? { element: wepp.stacktracePanelEl } : null,
            spinner: wepp.statusSpinnerEl,
            logLimit: 400,
            onTrigger: function (detail) {
                if (detail && detail.event) {
                    wepp.triggerEvent(detail.event, detail);
                }
            }
        });

        var baseTriggerEvent = wepp.triggerEvent.bind(wepp);
        wepp.triggerEvent = function (eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === "WEPP_RUN_TASK_COMPLETED") {
                wepp.disconnect_status_stream(wepp);
                wepp.report();
                try {
                    Observed.getInstance().onWeppRunCompleted();
                } catch (err) {
                    console.warn("[WEPP] Observed controller notification failed", err);
                }
                if (weppEvents && typeof weppEvents.emit === "function") {
                    weppEvents.emit("wepp:run:completed", payload || {});
                }
            }

            baseTriggerEvent(eventName, payload);
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
            http.getJson("query/wepp/phosphorus_opts/")
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

            return http.postJson("tasks/set_run_wepp_routine/", { routine: routine, state: state }, { form: formElement })
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && response.Success === true) {
                        var message = taskMsg + "... Success";
                        if (statusAdapter && typeof statusAdapter.html === "function") {
                            statusAdapter.html(message);
                        }
                        wepp.appendStatus(message);
                    } else if (response) {
                        wepp.pushResponseStacktrace(wepp, response);
                    }
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

            http.request("tasks/upload_cover_transform", {
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

        wepp.run = function () {
            var taskMsg = "Submitting wepp run";

            if (infoAdapter && typeof infoAdapter.text === "function") {
                infoAdapter.text("");
            }
            wepp.clear_status_messages(wepp);
            if (stacktraceAdapter && typeof stacktraceAdapter.text === "function") {
                stacktraceAdapter.text("");
            }
            wepp.appendStatus(taskMsg + "...");

            wepp.connect_status_stream(wepp);

            var payload = forms.serializeForm(formElement, { format: "json" }) || {};

            if (weppEvents && typeof weppEvents.emit === "function") {
                weppEvents.emit("wepp:run:started", { payload: payload });
            }

            http.postJson("rq/api/run_wepp", payload, { form: formElement })
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && response.Success === true) {
                        var message = "run_wepp_rq job submitted: " + response.job_id;
                        if (statusAdapter && typeof statusAdapter.html === "function") {
                            statusAdapter.html(message);
                        }
                        wepp.appendStatus(message, { job_id: response.job_id });
                        wepp.set_rq_job_id(wepp, response.job_id);
                        if (weppEvents && typeof weppEvents.emit === "function") {
                            weppEvents.emit("wepp:run:queued", { jobId: response.job_id, payload: payload });
                        }
                    } else if (response) {
                        wepp.pushResponseStacktrace(wepp, response);
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

            try {
                SubcatchmentDelineation.getInstance().prefetchLossMetrics();
            } catch (error) {
                console.warn("[WEPP] Unable to prefetch loss metrics", error);
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
        }

        ensureDelegates();
        wepp.handleRevegetationScenarioChange(revegSelect ? revegSelect.value : "");

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
