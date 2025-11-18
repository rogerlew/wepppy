/* ----------------------------------------------------------------------------
 * Landuse
 * ----------------------------------------------------------------------------
 */
var Landuse = (function () {
    var instance;

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function") {
            throw new Error("Landuse controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Landuse controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("Landuse controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Landuse controller requires WCEvents helpers.");
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

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var events = helpers.events;

        var landuse = controlBase();
        var landuseEvents = null;

        if (events && typeof events.createEmitter === "function") {
            var emitterBase = events.createEmitter();
            if (typeof events.useEventMap === "function") {
                landuseEvents = events.useEventMap([
                    "landuse:build:started",
                    "landuse:build:completed",
                    "landuse:report:loaded",
                    "landuse:mode:change",
                    "landuse:db:change"
                ], emitterBase);
            } else {
                landuseEvents = emitterBase;
            }
        }

        if (landuseEvents) {
            landuse.events = landuseEvents;
        }

        var formElement = dom.ensureElement("#landuse_form", "Landuse form not found.");
        var infoElement = dom.qs("#landuse_form #info");
        var statusElement = dom.qs("#landuse_form #status");
        var stacktraceElement = dom.qs("#landuse_form #stacktrace");
        var rqJobElement = dom.qs("#landuse_form #rq_job");
        var hintElement = dom.qs("#hint_build_landuse");

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);
        var hintAdapter = createLegacyAdapter(hintElement);

        landuse.form = formElement;
        landuse.info = infoAdapter;
        landuse.status = statusAdapter;
        landuse.stacktrace = stacktraceAdapter;
        landuse.rq_job = rqJobAdapter;
        landuse.command_btn_id = "btn_build_landuse";
        landuse.hint = hintAdapter;
        landuse.infoElement = infoElement;
        landuse.statusPanelEl = dom.qs("#landuse_status_panel");
        landuse.stacktracePanelEl = dom.qs("#landuse_stacktrace_panel");
        landuse.statusStream = null;
        var spinnerElement = landuse.statusPanelEl ? landuse.statusPanelEl.querySelector("#braille") : null;

        landuse.attach_status_stream(landuse, {
            element: landuse.statusPanelEl,
            channel: "landuse",
            stacktrace: landuse.stacktracePanelEl ? { element: landuse.stacktracePanelEl } : null,
            spinner: spinnerElement
        });

        var modePanels = [
            dom.qs("#landuse_mode0_controls"),
            dom.qs("#landuse_mode1_controls"),
            dom.qs("#landuse_mode2_controls"),
            dom.qs("#landuse_mode3_controls"),
            dom.qs("#landuse_mode4_controls")
        ];

        var baseTriggerEvent = landuse.triggerEvent.bind(landuse);
        landuse.triggerEvent = function (eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === "LANDUSE_BUILD_TASK_COMPLETED") {
                landuse.disconnect_status_stream(landuse);
                landuse.report();
                try {
                    SubcatchmentDelineation.getInstance().enableColorMap("dom_lc");
                } catch (err) {
                    console.warn("[Landuse] Failed to enable Subcatchment color map", err);
                }
                if (landuseEvents && typeof landuseEvents.emit === "function") {
                    landuseEvents.emit("landuse:build:completed", payload || {});
                }
            }

            baseTriggerEvent(eventName, payload);
        };

        landuse.hideStacktrace = function () {
            if (stacktraceAdapter && typeof stacktraceAdapter.hide === "function") {
                stacktraceAdapter.hide();
                return;
            }
            if (stacktraceElement) {
                stacktraceElement.hidden = true;
                stacktraceElement.style.display = "none";
            }
        };

        function resetStatus(taskMsg) {
            landuse.reset_panel_state(landuse, { taskMessage: taskMsg });
        }

        function handleError(error) {
            landuse.pushResponseStacktrace(landuse, toResponsePayload(http, error));
        }

        function ensureReportDelegates() {
            if (!landuse.infoElement) {
                return;
            }

            if (landuse._reportDelegates) {
                return;
            }

            landuse._reportDelegates = [];

            landuse._reportDelegates.push(dom.delegate(landuse.infoElement, "click", "[data-landuse-toggle]", function (event) {
                event.preventDefault();
                var toggle = this;
                var targetId = toggle.getAttribute("data-landuse-toggle");
                if (!targetId) {
                    return;
                }
                var panel = document.getElementById(targetId);
                if (!panel) {
                    return;
                }
                if (panel.tagName && panel.tagName.toLowerCase() === "details") {
                    var willOpen = !panel.open;
                    panel.open = willOpen;
                    toggle.setAttribute("aria-expanded", willOpen ? "true" : "false");
                    if (typeof panel.closest === "function") {
                        var row = panel.closest("tr");
                        if (row) {
                            if (willOpen) {
                                row.classList.add("is-open");
                            } else {
                                row.classList.remove("is-open");
                            }
                        }
                    }
                    if (willOpen && typeof panel.scrollIntoView === "function") {
                        panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
                    }
                }
            }));

            landuse._reportDelegates.push(dom.delegate(landuse.infoElement, "change", "[data-landuse-role=\"mapping-select\"]", function () {
                var domId = this.getAttribute("data-landuse-dom");
                var value = this.value;
                if (domId === undefined || domId === null || value === undefined) {
                    return;
                }
                landuse.modify_mapping(String(domId), value);
            }));

            landuse._reportDelegates.push(dom.delegate(landuse.infoElement, "change", "[data-landuse-role=\"coverage-select\"]", function () {
                var domId = this.getAttribute("data-landuse-dom");
                var cover = this.getAttribute("data-landuse-cover");
                var value = this.value;
                if (domId === undefined || domId === null || cover === undefined || cover === null) {
                    return;
                }
                landuse.modify_coverage(String(domId), String(cover), value);
            }));
        }

        landuse.bindReportEvents = function () {
            ensureReportDelegates();
        };

        function ensureFormDelegates() {
            if (landuse._formDelegates) {
                return;
            }

            landuse._formDelegates = [];

            landuse._formDelegates.push(dom.delegate(formElement, "change", "[data-landuse-role=\"mode\"]", function () {
                var modeAttr = this.getAttribute("data-landuse-mode");
                var nextMode = modeAttr !== null ? modeAttr : this.value;
                landuse.handleModeChange(nextMode);
            }));

            landuse._formDelegates.push(dom.delegate(formElement, "change", "[data-landuse-role=\"single-selection\"]", function () {
                landuse.handleSingleSelectionChange();
            }));

            landuse._formDelegates.push(dom.delegate(formElement, "change", "[data-landuse-role=\"db\"]", function () {
                landuse.setLanduseDb(this.value);
            }));

            landuse._formDelegates.push(dom.delegate(formElement, "click", "[data-landuse-action=\"build\"]", function (event) {
                event.preventDefault();
                landuse.build();
            }));
        }

        landuse.build = function () {
            var taskMsg = "Building landuse";
            resetStatus(taskMsg);

            if (landuseEvents && typeof landuseEvents.emit === "function") {
                landuseEvents.emit("landuse:build:started", {
                    mode: landuse.mode
                });
            }

            landuse.connect_status_stream(landuse);

            var formData = new FormData(formElement);

            http.request(url_for_run("rq/api/build_landuse"), {
                method: "POST",
                body: formData,
                form: formElement
            }).then(function (result) {
                var response = result && result.body ? result.body : null;
                if (response && response.Success === true) {
                    landuse.append_status_message(landuse, "build_landuse job submitted: " + response.job_id);
                    landuse.set_rq_job_id(landuse, response.job_id);
                } else if (response) {
                    landuse.pushResponseStacktrace(landuse, response);
                }
            }).catch(handleError);
        };

        landuse.modify_coverage = function (domId, cover, value) {
            var payload = {
                dom: domId,
                cover: cover,
                value: value
            };

            http.postJson(url_for_run("tasks/modify_landuse_coverage/"), payload, { form: formElement })
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && response.Success === false) {
                        landuse.pushResponseStacktrace(landuse, response);
                    }
                })
                .catch(handleError);
        };

        landuse.modify_mapping = function (domId, newDom) {
            var payload = {
                dom: domId,
                newdom: newDom
            };

            http.postJson(url_for_run("tasks/modify_landuse_mapping/"), payload, { form: formElement })
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && response.Success === false) {
                        landuse.pushResponseStacktrace(landuse, response);
                        return;
                    }
                    landuse.report();
                })
                .catch(handleError);
        };

        landuse.report = function () {
            http.request(url_for_run("report/landuse/"), {
                method: "GET",
                headers: { Accept: "text/html,application/xhtml+xml" }
            }).then(function (result) {
                var html = typeof result.body === "string" ? result.body : "";
                if (infoAdapter && typeof infoAdapter.html === "function") {
                    infoAdapter.html(html);
                } else if (infoElement) {
                    infoElement.innerHTML = html;
                }
                landuse.bindReportEvents();
                if (landuseEvents && typeof landuseEvents.emit === "function") {
                    landuseEvents.emit("landuse:report:loaded", { html: html });
                }
                if (window.UnitizerClient && typeof window.UnitizerClient.ready === "function") {
                    window.UnitizerClient.ready().then(function (client) {
                        if (client && typeof client.updateNumericFields === "function" && infoElement) {
                            client.updateNumericFields(infoElement);
                        }
                    }).catch(function (error) {
                        console.warn("[Landuse] Failed to update unitizer fields", error);
                    });
                }
            }).catch(handleError);
        };

        landuse.restore = function (mode, singleSelection) {
            var modeValue = parseInteger(mode, 0);
            var singleValue = singleSelection === undefined || singleSelection === null ? null : String(singleSelection);

            var radio = document.getElementById("landuse_mode" + modeValue);
            if (radio) {
                radio.checked = true;
            }

            var singleSelect = document.getElementById("landuse_single_selection");
            if (singleSelect && singleValue !== null && singleValue !== "") {
                singleSelect.value = singleValue;
            }

            landuse.showHideControls(modeValue);
        };

        landuse.handleModeChange = function (mode) {
            if (mode === undefined) {
                landuse.setMode();
                return;
            }
            landuse.setMode(parseInteger(mode, 0));
        };

        landuse.handleSingleSelectionChange = function () {
            landuse.setMode();
        };

        landuse.setMode = function (mode) {
            var payload = forms.serializeForm(formElement, { format: "json" }) || {};

            if (mode === undefined || mode === null) {
                mode = parseInteger(payload.landuse_mode, 0);
            }

            var singleSelection = payload.landuse_single_selection;
            landuse.mode = mode;

            var taskMsg = "Setting Mode to " + mode + " (" + (singleSelection || "") + ")";
            resetStatus(taskMsg);

            http.postJson(url_for_run("tasks/set_landuse_mode/"), {
                mode: mode,
                landuse_single_selection: singleSelection
            }, { form: formElement }).then(function (result) {
                var response = result && result.body ? result.body : null;
                if (response && response.Success === true) {
                    landuse.append_status_message(landuse, taskMsg + "... Success");
                } else if (response) {
                    landuse.pushResponseStacktrace(landuse, response);
                }
            }).catch(handleError);

            landuse.showHideControls(mode);

            if (landuseEvents && typeof landuseEvents.emit === "function") {
                landuseEvents.emit("landuse:mode:change", {
                    mode: mode,
                    singleSelection: singleSelection !== undefined && singleSelection !== null ? String(singleSelection) : null
                });
            }
        };

        landuse.setLanduseDb = function (db) {
            var value = db;
            if (value === undefined) {
                var select = document.getElementById("landuse_db");
                if (select && select.value !== undefined) {
                    value = select.value;
                } else {
                    var checked = formElement.querySelector("input[name='landuse_db']:checked");
                    value = checked ? checked.value : null;
                }
            }

            if (value === undefined || value === null) {
                return;
            }

            var taskMsg = "Setting Landuse Db to " + value;
            resetStatus(taskMsg);

            http.postJson(url_for_run("tasks/set_landuse_db/"), { landuse_db: value }, { form: formElement })
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && response.Success === true) {
                        landuse.append_status_message(landuse, taskMsg + "... Success");
                    } else if (response) {
                        landuse.pushResponseStacktrace(landuse, response);
                    }
                })
                .catch(handleError);

            if (landuse.mode !== undefined) {
                landuse.showHideControls(landuse.mode);
            }

            if (landuseEvents && typeof landuseEvents.emit === "function") {
                landuseEvents.emit("landuse:db:change", { db: value });
            }
        };

        landuse.showHideControls = function (mode) {
            var numericMode = parseInteger(mode, -1);

            modePanels.forEach(function (panel, index) {
                if (!panel) {
                    return;
                }
                if (numericMode === index) {
                    dom.show(panel);
                } else {
                    dom.hide(panel);
                }
            });

            if (numericMode < 0 || numericMode > modePanels.length - 1) {
                if (numericMode === -1) {
                    modePanels.forEach(function (panel) {
                        if (panel) {
                            dom.hide(panel);
                        }
                    });
                    return;
                }
                throw new Error("ValueError: unknown mode");
            }
        };

        ensureFormDelegates();
        ensureReportDelegates();

        var bootstrapState = {
            buildTriggered: false
        };

        landuse.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            var controllerContext = helper && typeof helper.getControllerContext === "function"
                ? helper.getControllerContext(ctx, "landuse")
                : {};

            var jobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "build_landuse_rq")
                : null;
            if (!jobId && controllerContext.jobId) {
                jobId = controllerContext.jobId;
            }
            if (!jobId) {
                var jobIds = ctx && (ctx.jobIds || ctx.jobs);
                if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "build_landuse_rq")) {
                    var value = jobIds.build_landuse_rq;
                    if (value !== undefined && value !== null) {
                        jobId = String(value);
                    }
                }
            }

            if (typeof landuse.set_rq_job_id === "function") {
                landuse.set_rq_job_id(landuse, jobId);
            }

            var settings = (ctx.data && ctx.data.landuse) || {};
            var restoreMode = controllerContext.mode !== undefined && controllerContext.mode !== null
                ? controllerContext.mode
                : settings.mode;
            var restoreSelection = controllerContext.singleSelection !== undefined && controllerContext.singleSelection !== null
                ? controllerContext.singleSelection
                : settings.singleSelection;

            if (typeof landuse.restore === "function") {
                landuse.restore(restoreMode, restoreSelection);
            }

            var hasLanduse = controllerContext.hasLanduse;
            if (hasLanduse === undefined) {
                hasLanduse = settings.hasLanduse;
            }

            if (hasLanduse && !bootstrapState.buildTriggered && typeof landuse.triggerEvent === "function") {
                landuse.triggerEvent("LANDUSE_BUILD_TASK_COMPLETED");
                bootstrapState.buildTriggered = true;
            }

            return landuse;
        };

        return landuse;
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
    globalThis.Landuse = Landuse;
}
