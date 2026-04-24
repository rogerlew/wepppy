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
        if (typeof http.requestWithSessionToken !== "function") {
            throw new Error("Landuse controller requires WCHttp.requestWithSessionToken.");
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

    function parseTriggerJobId(payload) {
        if (payload && payload.job_id !== undefined && payload.job_id !== null) {
            var directJobId = String(payload.job_id).trim();
            if (directJobId) {
                return directJobId;
            }
        }
        if (
            payload
            && payload.status
            && payload.status.job_id !== undefined
            && payload.status.job_id !== null
        ) {
            var nestedJobId = String(payload.status.job_id).trim();
            if (nestedJobId) {
                return nestedJobId;
            }
        }
        if (!payload || !Array.isArray(payload.tokens) || payload.tokens.length === 0) {
            return null;
        }
        var token = payload.tokens[0];
        if (token === undefined || token === null) {
            return null;
        }
        var normalized = String(token).trim();
        if (!normalized) {
            return null;
        }
        if (normalized.indexOf("rq:") === 0) {
            normalized = normalized.slice(3);
        }
        return normalized || null;
    }

    function normalizeMappingEdit(edit) {
        if (!edit || typeof edit !== "object") {
            return null;
        }
        if (edit.dom === undefined || edit.dom === null || edit.newdom === undefined || edit.newdom === null) {
            return null;
        }
        var domValue = String(edit.dom).trim();
        var newDomValue = String(edit.newdom).trim();
        if (!domValue || !newDomValue) {
            return null;
        }
        return {
            dom: domValue,
            newdom: newDomValue
        };
    }

    function isReadonlyModeEnabled() {
        try {
            if (window.Project && typeof window.Project.getInstance === "function") {
                var project = window.Project.getInstance();
                if (project && project.state && project.state.readonly !== undefined) {
                    return Boolean(project.state.readonly);
                }
            }
        } catch (error) {
            return false;
        }
        return false;
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var events = helpers.events;

        var landuse = controlBase();
        var landuseEvents = null;
        var LANDUSE_BUILD_COMPLETION_EVENT = "LANDUSE_BUILD_TASK_COMPLETED";
        var LANDUSE_MAPPING_COMPLETION_EVENT = "LANDUSE_MODIFY_MAPPING_TASK_COMPLETED";

        if (events && typeof events.createEmitter === "function") {
            var emitterBase = events.createEmitter();
            if (typeof events.useEventMap === "function") {
                landuseEvents = events.useEventMap([
                    "landuse:build:started",
                    "landuse:build:completed",
                    "landuse:mapping:started",
                    "landuse:mapping:completed",
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

        function resetBuildCompletionSeen() {
            landuse._build_completion_seen = false;
        }

        function resetMappingCompletionSeen() {
            landuse._mapping_completion_seen = false;
            landuse._mapping_completion_job_id = null;
            landuse._mapping_job_id = null;
        }

        function resetStagedMappingState() {
            landuse._staged_mapping_seq = 0;
            landuse._staged_mappings = {};
            landuse._mapping_submit_inflight = false;
        }

        landuse.poll_completion_event = LANDUSE_BUILD_COMPLETION_EVENT;
        resetBuildCompletionSeen();
        resetMappingCompletionSeen();
        resetStagedMappingState();

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
            if (normalized === LANDUSE_BUILD_COMPLETION_EVENT) {
                if (landuse._build_completion_seen) {
                    return baseTriggerEvent(eventName, payload);
                }
                landuse._build_completion_seen = true;
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
            if (normalized === LANDUSE_MAPPING_COMPLETION_EVENT) {
                var triggerJobId = parseTriggerJobId(payload);
                var activeMappingJobId = landuse._mapping_job_id || null;
                if (!triggerJobId && activeMappingJobId) {
                    triggerJobId = activeMappingJobId;
                }
                if (activeMappingJobId && triggerJobId && triggerJobId !== activeMappingJobId) {
                    return baseTriggerEvent(eventName, payload);
                }
                if (landuse._mapping_completion_seen) {
                    if (
                        !landuse._mapping_completion_job_id
                        || !triggerJobId
                        || landuse._mapping_completion_job_id === triggerJobId
                    ) {
                        return baseTriggerEvent(eventName, payload);
                    }
                }
                landuse._mapping_completion_seen = true;
                landuse._mapping_completion_job_id = triggerJobId || activeMappingJobId;
                landuse.disconnect_status_stream(landuse);
                landuse.report();
                if (landuseEvents && typeof landuseEvents.emit === "function") {
                    landuseEvents.emit("landuse:mapping:completed", payload || {});
                }
            }

            return baseTriggerEvent(eventName, payload);
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
                landuse.stage_mapping(String(domId), value, this);
            }));

            landuse._reportDelegates.push(dom.delegate(landuse.infoElement, "click", "[data-landuse-action=\"submit-mapping\"]", function (event) {
                event.preventDefault();
                landuse.submit_staged_mappings();
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
            landuse.sync_staged_mapping_ui();
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
            resetBuildCompletionSeen();

            if (landuseEvents && typeof landuseEvents.emit === "function") {
                landuseEvents.emit("landuse:build:started", {
                    mode: landuse.mode
                });
            }

            landuse.connect_status_stream(landuse);

            var formData = new FormData(formElement);

            http.requestWithSessionToken(
                url_for_run("build-landuse", { prefix: "/rq-engine/api" }),
                {
                    method: "POST",
                    body: formData,
                    form: formElement
                }
            ).then(function (result) {
                var response = result && result.body ? result.body : null;
                if (response && response.job_id) {
                    landuse.append_status_message(landuse, "build_landuse job submitted: " + response.job_id);
                    landuse.poll_completion_event = LANDUSE_BUILD_COMPLETION_EVENT;
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

            http.requestWithSessionToken(
                url_for_run("modify-landuse-coverage", { prefix: "/rq-engine/api" }),
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                    form: formElement
                }
            )
                .then(function (result) {
                    return result;
                })
                .catch(handleError);
        };

        landuse.sync_staged_mapping_ui = function () {
            if (!landuse.infoElement) {
                return;
            }
            resetStagedMappingState();
            var mappingSelects = landuse.infoElement.querySelectorAll("[data-landuse-role=\"mapping-select\"]");
            mappingSelects.forEach(function (select) {
                var currentValue = select.value === undefined || select.value === null ? "" : String(select.value);
                select.setAttribute("data-landuse-current", currentValue);
                var row = typeof select.closest === "function" ? select.closest("[data-landuse-row]") : null;
                if (row) {
                    row.removeAttribute("data-landuse-mapping-pending");
                }
            });
            landuse.update_staged_mapping_status();
        };

        landuse.get_staged_mapping_edits = function () {
            var staged = landuse._staged_mappings || {};
            return Object.keys(staged)
                .map(function (key) {
                    return staged[key];
                })
                .sort(function (a, b) {
                    return a.seq - b.seq;
                })
                .map(function (entry) {
                    return {
                        dom: entry.dom,
                        newdom: entry.newdom
                    };
                });
        };

        landuse.update_staged_mapping_status = function () {
            if (!landuse.infoElement) {
                return;
            }
            var button = landuse.infoElement.querySelector("[data-landuse-action=\"submit-mapping\"]");
            var status = landuse.infoElement.querySelector("[data-landuse-role=\"mapping-pending-status\"]");
            var editCount = landuse.get_staged_mapping_edits().length;
            var inflight = !!landuse._mapping_submit_inflight;
            var readonly = isReadonlyModeEnabled();
            var mappingSelects = landuse.infoElement.querySelectorAll("[data-landuse-role=\"mapping-select\"]");

            mappingSelects.forEach(function (select) {
                if (inflight) {
                    if (!select.disabled) {
                        select.disabled = true;
                        select.setAttribute("data-landuse-inflight-disabled", "true");
                    }
                    return;
                }
                if (select.getAttribute("data-landuse-inflight-disabled") === "true") {
                    if (!readonly) {
                        select.disabled = false;
                    }
                    select.removeAttribute("data-landuse-inflight-disabled");
                }
            });

            if (status) {
                if (inflight) {
                    status.textContent = "Submitting mapping edits...";
                } else if (editCount === 0) {
                    status.textContent = "No pending mapping edits.";
                } else if (editCount === 1) {
                    status.textContent = "1 mapping edit staged.";
                } else {
                    status.textContent = editCount + " mapping edits staged.";
                }
            }

            if (button) {
                var disableSubmit = inflight || editCount === 0 || readonly;
                button.disabled = disableSubmit;
                button.setAttribute("aria-disabled", disableSubmit ? "true" : "false");
                if (inflight) {
                    button.textContent = "Applying Mapping Edits...";
                } else if (editCount === 0) {
                    button.textContent = "Apply Mapping Edits";
                } else if (editCount === 1) {
                    button.textContent = "Apply 1 Mapping Edit";
                } else {
                    button.textContent = "Apply " + editCount + " Mapping Edits";
                }
            }
        };

        landuse.stage_mapping = function (domId, newDom, selectElement) {
            if (landuse._mapping_submit_inflight) {
                return;
            }
            var normalizedDom = String(domId).trim();
            if (!normalizedDom) {
                return;
            }
            var normalizedNewDom = String(newDom).trim();
            if (!normalizedNewDom) {
                return;
            }

            var baseline = "";
            if (selectElement) {
                baseline = selectElement.getAttribute("data-landuse-current");
                if (baseline === null || baseline === undefined || baseline === "") {
                    baseline = selectElement.value === undefined || selectElement.value === null
                        ? ""
                        : String(selectElement.value);
                    selectElement.setAttribute("data-landuse-current", baseline);
                }
            }

            if (baseline && normalizedNewDom === baseline) {
                delete landuse._staged_mappings[normalizedDom];
            } else {
                var existing = landuse._staged_mappings[normalizedDom];
                if (existing) {
                    existing.newdom = normalizedNewDom;
                } else {
                    landuse._staged_mapping_seq += 1;
                    landuse._staged_mappings[normalizedDom] = {
                        dom: normalizedDom,
                        newdom: normalizedNewDom,
                        seq: landuse._staged_mapping_seq
                    };
                }
            }

            if (selectElement && typeof selectElement.closest === "function") {
                var row = selectElement.closest("[data-landuse-row]");
                if (row) {
                    if (Object.prototype.hasOwnProperty.call(landuse._staged_mappings, normalizedDom)) {
                        row.setAttribute("data-landuse-mapping-pending", "true");
                    } else {
                        row.removeAttribute("data-landuse-mapping-pending");
                    }
                }
            }

            landuse.update_staged_mapping_status();
        };

        landuse.submit_staged_mappings = function () {
            if (landuse._mapping_submit_inflight) {
                return;
            }
            var stagedEdits = landuse.get_staged_mapping_edits();
            if (stagedEdits.length === 0) {
                landuse.update_staged_mapping_status();
                return;
            }
            landuse.submit_mapping_batch(stagedEdits, { clear_staged: true });
        };

        landuse.submit_mapping_batch = function (edits, options) {
            var normalizedEdits = Array.isArray(edits)
                ? edits.map(normalizeMappingEdit).filter(function (entry) {
                    return !!entry;
                })
                : [];
            if (normalizedEdits.length === 0) {
                return;
            }
            var taskMsg = normalizedEdits.length === 1
                ? "Updating landuse mapping"
                : "Updating landuse mapping (" + normalizedEdits.length + " edits)";
            var payload = {
                mappings: normalizedEdits
            };
            var shouldClearStaged = options && options.clear_staged === true;

            landuse._mapping_request_seq = (landuse._mapping_request_seq || 0) + 1;
            var requestSeq = landuse._mapping_request_seq;

            landuse._mapping_submit_inflight = true;
            landuse.update_staged_mapping_status();
            resetStatus(taskMsg);
            resetMappingCompletionSeen();
            landuse.connect_status_stream(landuse);
            if (landuseEvents && typeof landuseEvents.emit === "function") {
                landuseEvents.emit("landuse:mapping:started", payload);
            }

            http.requestWithSessionToken(
                url_for_run("modify-landuse-mapping", { prefix: "/rq-engine/api" }),
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                    form: formElement
                }
            )
                .then(function (result) {
                    if (requestSeq !== landuse._mapping_request_seq) {
                        return;
                    }
                    var response = result && result.body ? result.body : null;
                    if (response && response.job_id) {
                        landuse.append_status_message(landuse, "modify_landuse_mapping job submitted: " + response.job_id);
                        landuse.poll_completion_event = LANDUSE_MAPPING_COMPLETION_EVENT;
                        landuse._mapping_job_id = response.job_id;
                        landuse.set_rq_job_id(landuse, response.job_id);
                        if (shouldClearStaged) {
                            landuse.sync_staged_mapping_ui();
                        }
                        landuse._mapping_submit_inflight = false;
                        landuse.update_staged_mapping_status();
                        return;
                    }
                    if (response) {
                        landuse.pushResponseStacktrace(landuse, response);
                    }
                    landuse.disconnect_status_stream(landuse);
                    landuse._mapping_submit_inflight = false;
                    landuse.update_staged_mapping_status();
                })
                .catch(function (error) {
                    if (requestSeq !== landuse._mapping_request_seq) {
                        return;
                    }
                    landuse.disconnect_status_stream(landuse);
                    landuse._mapping_submit_inflight = false;
                    landuse.update_staged_mapping_status();
                    handleError(error);
                });
        };

        landuse.modify_mapping = function (domId, newDom) {
            var normalizedEdit = normalizeMappingEdit({ dom: domId, newdom: newDom });
            if (!normalizedEdit) {
                return;
            }
            landuse.submit_mapping_batch([normalizedEdit], { clear_staged: false });
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

            http.requestWithSessionToken(
                url_for_run("set-landuse-mode", { prefix: "/rq-engine/api" }),
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        mode: mode,
                        landuse_single_selection: singleSelection
                    }),
                    form: formElement
                }
            ).then(function (result) {
                landuse.append_status_message(landuse, taskMsg + "... Success");
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

            http.requestWithSessionToken(
                url_for_run("set-landuse-db", { prefix: "/rq-engine/api" }),
                {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ landuse_db: value }),
                    form: formElement
                }
            )
                .then(function (result) {
                    landuse.append_status_message(landuse, taskMsg + "... Success");
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

            var buildJobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "build_landuse_rq")
                : null;
            var mappingJobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "modify_landuse_mapping_rq")
                : null;
            if (!buildJobId && !mappingJobId && controllerContext.job_id) {
                buildJobId = controllerContext.job_id;
            }
            if (!buildJobId && !mappingJobId) {
                var jobIds = ctx && (ctx.jobIds || ctx.jobs);
                if (
                    jobIds
                    && typeof jobIds === "object"
                    && Object.prototype.hasOwnProperty.call(jobIds, "modify_landuse_mapping_rq")
                ) {
                    var mappingValue = jobIds.modify_landuse_mapping_rq;
                    if (mappingValue !== undefined && mappingValue !== null) {
                        mappingJobId = String(mappingValue);
                    }
                }
                if (
                    !mappingJobId
                    && jobIds
                    && typeof jobIds === "object"
                    && Object.prototype.hasOwnProperty.call(jobIds, "build_landuse_rq")
                ) {
                    var value = jobIds.build_landuse_rq;
                    if (value !== undefined && value !== null) {
                        buildJobId = String(value);
                    }
                }
            }

            var jobId = mappingJobId || buildJobId || null;
            landuse.poll_completion_event = mappingJobId
                ? LANDUSE_MAPPING_COMPLETION_EVENT
                : LANDUSE_BUILD_COMPLETION_EVENT;
            landuse._mapping_job_id = mappingJobId || null;

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

            if (hasLanduse && !mappingJobId && !bootstrapState.buildTriggered && typeof landuse.triggerEvent === "function") {
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
