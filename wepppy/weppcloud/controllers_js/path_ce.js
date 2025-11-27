/* ----------------------------------------------------------------------------
 * PATH Cost-Effective Control
 * Doc: controllers_js/README.md — Path CE Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var PathCE = (function () {
    var instance;

    function endpoint(path) {
        if (typeof url_for_run === "function") {
            return url_for_run(path);
        }
        if (path.charAt(0) !== "/") {
            return "/" + path;
        }
        return path;
    }

    var ENDPOINTS = {
        config: function () { return endpoint("api/path_ce/config"); },
        status: function () { return endpoint("api/path_ce/status"); },
        results: function () { return endpoint("api/path_ce/results"); },
        run: function () { return endpoint("tasks/path_cost_effective_run"); }
    };

    var TREATMENT_FIELDS = ["label", "scenario", "quantity", "unit_cost", "fixed_cost"];
    var EVENT_NAMES = [
        "pathce:config:loaded",
        "pathce:config:saved",
        "pathce:config:error",
        "pathce:treatment:added",
        "pathce:treatment:removed",
        "pathce:treatment:updated",
        "pathce:status:update",
        "pathce:results:update",
        "pathce:run:started",
        "pathce:run:completed",
        "pathce:run:error",
        "job:started",
        "job:completed",
        "job:error"
    ];

    var POLL_INTERVAL_MS = 5000;
    var TERMINAL_STATUSES = { completed: true, failed: true };

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function" || typeof dom.delegate !== "function") {
            throw new Error("PathCE controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("PathCE controller requires WCForms helpers.");
        }
        if (!http || typeof http.getJson !== "function" || typeof http.postJson !== "function") {
            throw new Error("PathCE controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function" || typeof events.useEventMap !== "function") {
            throw new Error("PathCE controller requires WCEvents helpers.");
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

    function toNumber(value) {
        if (value === undefined || value === null || value === "") {
            return null;
        }
        var num = Number(value);
        return Number.isFinite(num) ? num : null;
    }

    function normalizeSeverity(value) {
        if (value === undefined || value === null || value === "") {
            return null;
        }
        var values = Array.isArray(value) ? value : [value];
        var filtered = values
            .map(function (item) {
                if (item === undefined || item === null) {
                    return "";
                }
                return String(item).trim();
            })
            .filter(function (item) {
                return item.length > 0;
            });
        return filtered.length ? filtered : null;
    }

    function buildFormValues(config) {
        var slopeRange = Array.isArray(config && config.slope_range) ? config.slope_range : [null, null];
        return {
            sddc_threshold: config && config.sddc_threshold !== undefined && config.sddc_threshold !== null ? config.sddc_threshold : "",
            sdyd_threshold: config && config.sdyd_threshold !== undefined && config.sdyd_threshold !== null ? config.sdyd_threshold : "",
            slope_min: slopeRange[0] !== undefined && slopeRange[0] !== null ? slopeRange[0] : "",
            slope_max: slopeRange[1] !== undefined && slopeRange[1] !== null ? slopeRange[1] : "",
            severity_filter: config && config.severity_filter ? config.severity_filter : []
        };
    }

    function applyFormValues(forms, formElement, values) {
        if (forms && typeof forms.applyValues === "function") {
            forms.applyValues(formElement, values);
            return;
        }
        if (!formElement || !values) {
            return;
        }
        Object.keys(values).forEach(function (name) {
            var field = formElement.elements.namedItem(name);
            if (!field) {
                return;
            }
            var value = values[name];
            if (field instanceof window.HTMLSelectElement && field.multiple) {
                var selectedValues = normalizeSeverity(value) || [];
                Array.prototype.slice.call(field.options).forEach(function (option) {
                    option.selected = selectedValues.indexOf(option.value) !== -1;
                });
                return;
            }
            if (field instanceof window.RadioNodeList) {
                Array.prototype.slice.call(field).forEach(function (input) {
                    input.checked = String(input.value) === String(value);
                });
                return;
            }
            if (field instanceof window.HTMLInputElement && field.type === "checkbox") {
                field.checked = Boolean(value);
                return;
            }
            if (value === null || value === undefined) {
                field.value = "";
            } else {
                field.value = value;
            }
        });
    }

    function setMessage(controller, message, isError) {
        if (controller.message && typeof controller.message.text === "function") {
            controller.message.text(message || "");
        }
        if (controller.messageElement) {
            if (isError) {
                controller.messageElement.classList.add("wc-field__help--error");
            } else {
                controller.messageElement.classList.remove("wc-field__help--error");
            }
        }
    }

    function updateBraille(controller, progress) {
        var text = "";
        if (typeof progress === "number" && !Number.isNaN(progress)) {
            var clamped = Math.max(0, Math.min(1, progress));
            text = "Progress: " + Math.round(clamped * 100) + "%";
        }
        if (controller.braille && typeof controller.braille.text === "function") {
            controller.braille.text(text);
        }
    }

    function formatNumber(value) {
        if (value === undefined || value === null) {
            return "—";
        }
        var num = Number(value);
        if (!Number.isFinite(num)) {
            return "—";
        }
        return num.toFixed(2);
    }

    function renderSummary(controller, results) {
        var summaryElement = controller.summaryElement;
        if (!summaryElement) {
            return;
        }
        summaryElement.textContent = "";
        var doc = window.document;
        var data = results && typeof results === "object" ? results : {};
        if (Object.keys(data).length === 0) {
            var emptyItem = doc.createElement("div");
            emptyItem.className = "wc-summary-pane__item";
            var emptyTerm = doc.createElement("dt");
            emptyTerm.className = "wc-summary-pane__term";
            emptyTerm.textContent = "Summary";
            var emptyDef = doc.createElement("dd");
            emptyDef.className = "wc-summary-pane__definition";
            emptyDef.textContent = "No results yet.";
            emptyItem.appendChild(emptyTerm);
            emptyItem.appendChild(emptyDef);
            summaryElement.appendChild(emptyItem);
            return;
        }
        var rows = [
            ["Status", data.status || "unknown"],
            ["Used Secondary Solver", data.used_secondary ? "Yes" : "No"],
            ["Total Cost (variable)", formatNumber(data.total_cost)],
            ["Total Fixed Cost", formatNumber(data.total_fixed_cost)],
            ["Total Sddc Reduction", formatNumber(data.total_sddc_reduction)],
            ["Final Sddc", formatNumber(data.final_sddc)]
        ];
        var fragment = doc.createDocumentFragment();
        rows.forEach(function (entry) {
            var item = doc.createElement("div");
            item.className = "wc-summary-pane__item";
            var dt = doc.createElement("dt");
            dt.className = "wc-summary-pane__term";
            dt.textContent = entry[0];
            var dd = doc.createElement("dd");
            dd.className = "wc-summary-pane__definition";
            dd.textContent = entry[1];
            item.appendChild(dt);
            item.appendChild(dd);
            fragment.appendChild(item);
        });
        summaryElement.appendChild(fragment);
    }

    function readMulchCosts(costInputs) {
        var costs = {};
        var list = Array.isArray(costInputs) ? costInputs : [];
        list.forEach(function (input) {
            if (!input || typeof input.getAttribute !== "function") {
                return;
            }
            var scenario = input.getAttribute("data-pathce-cost");
            if (!scenario) {
                return;
            }
            var canonicalAttr = input.dataset ? input.dataset.unitizerCanonicalValue : null;
            var sourceValue = canonicalAttr && canonicalAttr !== "" ? canonicalAttr : input.value;
            var value = toNumber(sourceValue);
            costs[scenario] = value === null ? 0 : value;
        });
        return costs;
    }

    function createTreatmentRow(option) {
        var doc = window.document;
        var row = doc.createElement("tr");
        TREATMENT_FIELDS.forEach(function (field) {
            var cell = doc.createElement("td");
            var input = doc.createElement("input");
            input.setAttribute("data-pathce-field", field);
            if (field === "label" || field === "scenario") {
                input.type = "text";
            } else {
                input.type = "number";
                input.step = "any";
                input.min = "0";
            }
            var value = option && Object.prototype.hasOwnProperty.call(option, field) ? option[field] : "";
            input.value = value === null || value === undefined ? "" : String(value);
            cell.appendChild(input);
            row.appendChild(cell);
        });
        var actionCell = doc.createElement("td");
        var removeButton = doc.createElement("button");
        removeButton.type = "button";
        removeButton.setAttribute("data-pathce-action", "remove-treatment");
        removeButton.textContent = "Remove";
        actionCell.appendChild(removeButton);
        row.appendChild(actionCell);
        return row;
    }

    function renderTreatmentOptions(controller, options) {
        var body = controller.treatmentsBody;
        var list = Array.isArray(options) ? options : [];
        if (!body) {
            if (controller.state && controller.state.config) {
                controller.state.config.treatment_options = list.slice();
            }
            return;
        }
        body.textContent = "";
        list.forEach(function (option) {
            body.appendChild(createTreatmentRow(option));
        });
    }

    function appendTreatmentRow(controller, option) {
        var body = controller.treatmentsBody;
        if (!body) {
            return null;
        }
        var row = createTreatmentRow(option || {});
        body.appendChild(row);
        emitEvent(controller, "pathce:treatment:added", { option: option || {}, row: row });
        return row;
    }

    function removeTreatmentRow(controller, row) {
        var body = controller.treatmentsBody;
        if (!body || !row || !row.parentNode) {
            return;
        }
        if (row.parentNode === body) {
            body.removeChild(row);
            emitEvent(controller, "pathce:treatment:removed", { row: row });
        }
    }

    function harvestTreatmentOptions(controller) {
        var body = controller.treatmentsBody;
        if (!body) {
            if (controller.state && controller.state.config && Array.isArray(controller.state.config.treatment_options)) {
                return controller.state.config.treatment_options.slice();
            }
            return [];
        }
        var rows = body.querySelectorAll("tr");
        var options = [];
        Array.prototype.slice.call(rows).forEach(function (row) {
            var getField = function (name) {
                var input = row.querySelector('[data-pathce-field="' + name + '"]');
                return input ? input.value : "";
            };
            var label = String(getField("label") || "").trim();
            var scenario = String(getField("scenario") || "").trim();
            if (!label && !scenario) {
                return;
            }
            var quantity = toNumber(getField("quantity"));
            var unitCost = toNumber(getField("unit_cost"));
            var fixedCost = toNumber(getField("fixed_cost"));
            options.push({
                label: label,
                scenario: scenario,
                quantity: quantity === null ? 0 : quantity,
                unit_cost: unitCost === null ? 0 : unitCost,
                fixed_cost: fixedCost === null ? 0 : fixedCost
            });
        });
        emitEvent(controller, "pathce:treatment:updated", { options: options });
        return options;
    }

    function applyMulchCosts(costInputs, costMap) {
        var list = Array.isArray(costInputs) ? costInputs : [];
        var formScope = null;
        list.forEach(function (input) {
            if (!input || typeof input.getAttribute !== "function") {
                return;
            }
            var scenario = input.getAttribute("data-pathce-cost");
            if (!scenario) {
                return;
            }
            var value = costMap && Object.prototype.hasOwnProperty.call(costMap, scenario)
                ? costMap[scenario]
                : null;
            var hasValue = value !== null && value !== undefined && value !== "";
            input.value = hasValue ? String(value) : "";
            if (input.dataset) {
                input.dataset.unitizerCanonicalValue = hasValue ? String(value) : "";
                if (!input.dataset.unitizerActiveUnit) {
                    var canonicalUnit = input.getAttribute("data-unitizer-unit");
                    if (canonicalUnit) {
                        input.dataset.unitizerActiveUnit = canonicalUnit;
                    }
                }
            }
            if (!formScope && typeof input.closest === "function") {
                formScope = input.closest("form");
            }
        });

        if (typeof window !== "undefined" && window.UnitizerClient && typeof window.UnitizerClient.ready === "function") {
            window.UnitizerClient.ready()
                .then(function (client) {
                    if (client && typeof client.updateNumericFields === "function") {
                        client.updateNumericFields(formScope || undefined);
                    }
                })
                .catch(function () {
                    /* noop */
                });
        }
    }

    function buildPayload(forms, controller) {
        var formElement = controller.form;
        var values = forms.serializeForm(formElement, { format: "json" }) || {};
        var severity = normalizeSeverity(values.severity_filter);
        var slopeMin = toNumber(values.slope_min);
        var slopeMax = toNumber(values.slope_max);
        var sddc = toNumber(values.sddc_threshold);
        var sdyd = toNumber(values.sdyd_threshold);
        return {
            sddc_threshold: sddc === null ? 0 : sddc,
            sdyd_threshold: sdyd === null ? 0 : sdyd,
            slope_range: [slopeMin, slopeMax],
            severity_filter: severity,
            mulch_costs: readMulchCosts(controller.mulchCostInputs),
            treatment_options: harvestTreatmentOptions(controller)
        };
    }

    function updateStatusMessage(controller, message) {
        if (controller.status && typeof controller.status.text === "function") {
            controller.status.text(message || "");
        }
    }

    function emitEvent(controller, name, payload) {
        if (!controller || !name) {
            return;
        }
        var emitter = controller.events;
        if (emitter && typeof emitter.emit === "function") {
            emitter.emit(name, payload || {});
        }
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var events = helpers.events;

        var controller = controlBase();
        var state = {
            config: {},
            pollTimer: null,
            statusFetchInFlight: false,
            resultsFetchInFlight: false,
            lastStatusValue: null,
            lastEmittedStatus: null,
            lastJobId: null,
            statusStartedAt: null
        };
        controller.state = state;
        controller.job_status_poll_interval_ms = 1200;

        var emitter = events.useEventMap(EVENT_NAMES, events.createEmitter());
        controller.events = emitter;

        var formElement = dom.ensureElement("#path_ce_form", "PATH Cost-Effective form not found.");
        var messageElement = dom.ensureElement("#path_ce_message", "PATH Cost-Effective message element missing.");
        var hintElement = dom.ensureElement("#path_ce_hint", "PATH Cost-Effective hint element missing.");
        var summaryElement = dom.ensureElement("#path_ce_summary", "PATH Cost-Effective summary element missing.");
        var jobElement = dom.ensureElement("#path_ce_rq_job", "PATH Cost-Effective job element missing.");
        var brailleElement = dom.ensureElement("#path_ce_braille", "PATH Cost-Effective braille element missing.");
        var stacktraceElement = dom.ensureElement("#path_ce_stacktrace", "PATH Cost-Effective stacktrace element missing.");
        var statusElement = dom.qs("#path_ce_form #status");
        var infoElement = dom.qs("#path_ce_form #info");
        var treatmentsBody = dom.qs("#path_ce_treatments_table tbody") || dom.qs("#path_ce_treatments_table");

        var hintAdapter = createLegacyAdapter(hintElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var jobAdapter = createLegacyAdapter(jobElement);
        var brailleAdapter = createLegacyAdapter(brailleElement);
        var infoAdapter = createLegacyAdapter(infoElement);
        var messageAdapter = createLegacyAdapter(messageElement);

        controller.form = formElement;
        controller.message = messageAdapter;
        controller.hint = hintAdapter;
        controller.stacktrace = stacktraceAdapter;
        controller.status = statusAdapter;
        controller.rq_job = jobAdapter;
        controller.braille = brailleAdapter;
        controller.info = infoAdapter;
        controller.summaryElement = summaryElement;
        controller.hintElement = hintElement;
        controller.messageElement = messageElement;
        controller.brailleElement = brailleElement;
        controller.command_btn_id = ["path_ce_run"];
        controller.mulchCostInputs = Array.prototype.slice.call(
            formElement.querySelectorAll("[data-pathce-cost]")
        );
        controller.treatmentsBody = treatmentsBody || null;

        var baseTriggerEvent = controller.triggerEvent.bind(controller);
        controller.triggerEvent = function (eventName, payload) {
            if (eventName && eventName.indexOf("job:") === 0) {
                emitEvent(controller, eventName, payload);
            }
            baseTriggerEvent(eventName, payload);
        };

        function applyConfig(config) {
            state.config = Object.assign({}, config || {});
            var values = buildFormValues(state.config);
            applyFormValues(forms, formElement, values);
            applyMulchCosts(controller.mulchCostInputs, state.config.mulch_costs || {});
            renderTreatmentOptions(controller, state.config.treatment_options || []);
            emitEvent(controller, "pathce:config:loaded", { config: state.config });
        }

        function stopPolling() {
            if (state.pollTimer) {
                window.clearInterval(state.pollTimer);
                state.pollTimer = null;
            }
        }

        function startPolling() {
            if (!state.pollTimer) {
                state.pollTimer = window.setInterval(function () {
                    refreshStatus();
                    refreshResults();
                }, POLL_INTERVAL_MS);
            }
            refreshStatus();
            refreshResults();
        }

        function applyStatus(payload) {
            var data = payload || {};
            var statusName = typeof data.status === "string" ? data.status.toLowerCase() : "";
            var previousStatus = state.lastStatusValue;
            var recentRun = state.statusStartedAt && Date.now() - state.statusStartedAt < 3000;
            if (state.lastJobId && previousStatus === "running" && recentRun) {
                // Ignore stale responses immediately after a new run kicks off
                if (statusName && statusName !== "running") {
                    return;
                }
            }

            state.lastStatusValue = statusName || null;

            if (state.lastStatusValue === "running") {
                state.statusStartedAt = Date.now();
            }

            updateStatusMessage(controller, data.status || "");
            setMessage(controller, data.status_message || "", statusName === "failed");
            updateBraille(controller, data.progress);

            emitEvent(controller, "pathce:status:update", { status: data });

            if (statusName === "running") {
                startPolling();
                if (state.lastEmittedStatus !== "running") {
                    state.lastEmittedStatus = "running";
                    controller.triggerEvent("job:started", { task: "pathce:run", job_id: state.lastJobId, status: data });
                }
                return;
            }

            if (!statusName) {
                return;
            }

            if (TERMINAL_STATUSES[statusName]) {
                stopPolling();
                if (state.lastEmittedStatus !== statusName) {
                    state.lastEmittedStatus = statusName;
                    var eventPayload = { task: "pathce:run", job_id: state.lastJobId, status: data };
                    if (statusName === "completed") {
                        controller.triggerEvent("job:completed", eventPayload);
                        emitEvent(controller, "pathce:run:completed", { job_id: state.lastJobId, status: data });
                    } else {
                        controller.triggerEvent("job:error", eventPayload);
                        emitEvent(controller, "pathce:run:error", { job_id: state.lastJobId, status: data });
                    }
                }
            }
        }

        function applyResults(payload) {
            var results = payload && payload.results ? payload.results : {};
            renderSummary(controller, results);
            emitEvent(controller, "pathce:results:update", { results: results });
        }

        function refreshStatus() {
            if (state.statusFetchInFlight) {
                return Promise.resolve(null);
            }
            state.statusFetchInFlight = true;
            return http.getJson(ENDPOINTS.status(), { params: { _: Date.now() } })
                .then(function (data) {
                    applyStatus(data);
                    return data;
                })
                .catch(function (error) {
                    console.warn("[PathCE] status poll failed", error);
                    return null;
                })
                .finally(function () {
                    state.statusFetchInFlight = false;
                });
        }

        function refreshResults() {
            if (state.resultsFetchInFlight) {
                return Promise.resolve(null);
            }
            state.resultsFetchInFlight = true;
            return http.getJson(ENDPOINTS.results(), { params: { _: Date.now() } })
                .then(function (data) {
                    applyResults(data);
                    return data;
                })
                .catch(function (error) {
                    console.warn("[PathCE] result poll failed", error);
                    return null;
                })
                .finally(function () {
                    state.resultsFetchInFlight = false;
                });
        }

        function handleSave(event) {
            event.preventDefault();
            controller.saveConfig();
        }

        function handleRun(event) {
            event.preventDefault();
            controller.run();
        }

        dom.delegate(formElement, "click", "[data-pathce-action='save-config']", handleSave);
        dom.delegate(formElement, "click", "[data-pathce-action='run']", handleRun);
        dom.delegate(formElement, "click", "[data-pathce-action='add-treatment']", function (event) {
            event.preventDefault();
            appendTreatmentRow(controller, {});
        });
        dom.delegate(formElement, "click", "[data-pathce-action='remove-treatment']", function (event) {
            event.preventDefault();
            var row = event && event.target && typeof event.target.closest === "function"
                ? event.target.closest("tr")
                : null;
            removeTreatmentRow(controller, row);
        });

        controller.fetchConfig = function () {
            setMessage(controller, "Loading PATH Cost-Effective configuration…");
            return http.getJson(ENDPOINTS.config(), { params: { _: Date.now() } })
                .then(function (response) {
                    var config = response && response.config ? response.config : {};
                    applyConfig(config);
                    setMessage(controller, "");
                    if (controller.stacktrace && typeof controller.stacktrace.empty === "function") {
                        controller.stacktrace.empty();
                    }
                    return config;
                })
                .catch(function (error) {
                    setMessage(controller, "Failed to load configuration.", true);
                    controller.pushErrorStacktrace(controller, error);
                    emitEvent(controller, "pathce:config:error", { error: error });
                    throw error;
                });
        };

        controller.saveConfig = function () {
            var payload = buildPayload(forms, controller);
            setMessage(controller, "Saving configuration…");
            return http.postJson(ENDPOINTS.config(), payload, { form: formElement })
                .then(function (result) {
                    var response = result && result.body !== undefined ? result.body : result;
                    var nextConfig = response && response.config ? response.config : payload;
                    applyConfig(nextConfig);
                    setMessage(controller, "Configuration saved.");
                    if (controller.stacktrace && typeof controller.stacktrace.empty === "function") {
                        controller.stacktrace.empty();
                    }
                    emitEvent(controller, "pathce:config:saved", { config: state.config, response: response });
                    return response;
                })
                .catch(function (error) {
                    setMessage(controller, "Failed to save configuration.", true);
                    controller.pushErrorStacktrace(controller, error);
                    emitEvent(controller, "pathce:config:error", { error: error });
                    throw error;
                });
        };

        controller.run = function () {
            if (typeof controller.reset_panel_state === "function") {
                controller.reset_panel_state(controller, {
                    clearJobHint: false,
                    clearStacktrace: true
                });
            }
            setMessage(controller, "Starting PATH Cost-Effective run…");
            if (controller.stacktrace && typeof controller.stacktrace.empty === "function") {
                controller.stacktrace.empty();
            }
            if (controller.status && typeof controller.status.text === "function") {
                controller.status.text("");
            }
            var statusLog = dom.qs("#path_ce_status_panel [data-status-log]");
            if (statusLog) {
                statusLog.textContent = "";
            }
            state.statusStartedAt = Date.now();
            var payload = buildPayload(forms, controller);
            stopPolling();
            return http.postJson(ENDPOINTS.run(), payload, { form: formElement })
                .then(function (result) {
                    var response = result && result.body !== undefined ? result.body : result;
                    var jobId = response && (response.job_id || response.jobId);
                    state.lastJobId = jobId || null;
                    state.lastEmittedStatus = "running";
                    state.lastStatusValue = "running";
                    if (jobId) {
                        controller.set_rq_job_id(controller, jobId);
                    } else {
                        controller.set_rq_job_id(controller, null);
                    }
                    if (controller.stacktrace && typeof controller.stacktrace.empty === "function") {
                        controller.stacktrace.empty();
                    }
                    controller.triggerEvent("job:started", { task: "pathce:run", job_id: state.lastJobId, response: response });
                    emitEvent(controller, "pathce:run:started", { job_id: state.lastJobId, response: response });
                    setMessage(controller, "PATH Cost-Effective job submitted. Monitoring status…");
                    startPolling();
                    refreshResults();
                    return response;
                })
                .catch(function (error) {
                    setMessage(controller, "Failed to enqueue PATH Cost-Effective run.", true);
                    controller.pushErrorStacktrace(controller, error);
                    controller.set_rq_job_id(controller, null);
                    state.lastEmittedStatus = "error";
                    emitEvent(controller, "pathce:run:error", { error: error });
                    controller.triggerEvent("job:error", { task: "pathce:run", error: error });
                    throw error;
                });
        };

        controller.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            var controllerContext = helper && typeof helper.getControllerContext === "function"
                ? helper.getControllerContext(ctx, "pathCe")
                : {};

            var jobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "run_path_ce")
                : null;

            if (!jobId && controllerContext && controllerContext.jobId) {
                jobId = controllerContext.jobId;
            }

            if (!jobId) {
                var jobIds = ctx && (ctx.jobIds || ctx.jobs);
                if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "run_path_ce")) {
                    var value = jobIds.run_path_ce;
                    if (value !== undefined && value !== null) {
                        jobId = String(value);
                    }
                }
            }

            state.lastJobId = jobId || null;

            if (typeof controller.set_rq_job_id === "function") {
                controller.set_rq_job_id(controller, jobId || null);
            }
        };

        controller.init = function () {
            controller.fetchConfig()
                .catch(function () {
                    return null;
                })
                .finally(function () {
                    refreshStatus();
                    refreshResults();
                });
        };

        return controller;
    }

    return {
        getInstance: function () {
            if (!instance) {
                instance = createInstance();
                instance.init();
            }
            return instance;
        }
    };
})();

window.PathCE = PathCE;
