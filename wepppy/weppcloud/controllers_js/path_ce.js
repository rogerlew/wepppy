/* ----------------------------------------------------------------------------
 * PATH Cost-Effective Control
 * Doc: controllers_js/README.md — Path CE Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var PathCE = (function () {
    var instance;

    var ENDPOINTS = {
        config: "api/path_ce/config",
        status: "api/path_ce/status",
        results: "api/path_ce/results",
        run: "tasks/path_cost_effective_run"
    };

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

    var DEFAULT_TREATMENT_LABEL = "New Treatment";
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

    function ensureScenarioOptions(state, config) {
        var defaults = [
            "mulch_15_sbs_map",
            "mulch_30_sbs_map",
            "mulch_60_sbs_map",
            "sbs_map",
            "undisturbed"
        ];
        var options = defaults.slice();
        if (config && Array.isArray(config.available_scenarios)) {
            options = options.concat(config.available_scenarios);
        }
        if (config && Array.isArray(config.treatment_options)) {
            config.treatment_options.forEach(function (option) {
                if (option && option.scenario) {
                    options.push(String(option.scenario));
                }
            });
        }
        var seen = Object.create(null);
        var unique = [];
        options.forEach(function (item) {
            var key = item === undefined || item === null ? "" : String(item);
            if (!key) {
                return;
            }
            if (seen[key]) {
                return;
            }
            seen[key] = true;
            unique.push(key);
        });
        state.availableScenarios = unique;
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

    function setHint(controller, message, isError) {
        if (controller.hint && typeof controller.hint.text === "function") {
            controller.hint.text(message || "");
        }
        if (controller.hintElement) {
            if (isError) {
                controller.hintElement.classList.add("wc-field__help--error");
            } else {
                controller.hintElement.classList.remove("wc-field__help--error");
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
            var empty = doc.createElement("dt");
            empty.textContent = "No results yet.";
            summaryElement.appendChild(empty);
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
            var dt = doc.createElement("dt");
            dt.textContent = entry[0];
            var dd = doc.createElement("dd");
            dd.textContent = entry[1];
            fragment.appendChild(dt);
            fragment.appendChild(dd);
        });
        summaryElement.appendChild(fragment);
    }

    function createTreatmentRow(controller, treatment, index) {
        var doc = window.document;
        var row = doc.createElement("tr");
        row.dataset.index = String(index);

        var labelCell = doc.createElement("td");
        var labelInput = doc.createElement("input");
        labelInput.type = "text";
        labelInput.className = "pure-input-1 path-ce-label";
        labelInput.setAttribute("data-pathce-field", "label");
        labelInput.value = treatment && treatment.label ? String(treatment.label) : "";
        labelCell.appendChild(labelInput);
        row.appendChild(labelCell);

        var scenarioCell = doc.createElement("td");
        var scenarioSelect = doc.createElement("select");
        scenarioSelect.className = "pure-input-1 path-ce-scenario";
        scenarioSelect.setAttribute("data-pathce-field", "scenario");
        var scenarios = controller.state && Array.isArray(controller.state.availableScenarios)
            ? controller.state.availableScenarios.slice()
            : [];
        var selectedScenario = treatment && treatment.scenario ? String(treatment.scenario) : "";
        if (selectedScenario && scenarios.indexOf(selectedScenario) === -1) {
            scenarios.push(selectedScenario);
        }
        if (!scenarios.length) {
            scenarios.push("");
        }
        scenarios.forEach(function (optionValue) {
            var option = doc.createElement("option");
            option.value = optionValue;
            option.textContent = optionValue;
            if (optionValue === selectedScenario) {
                option.selected = true;
            }
            scenarioSelect.appendChild(option);
        });
        scenarioCell.appendChild(scenarioSelect);
        row.appendChild(scenarioCell);

        function createNumberInput(fieldName, value) {
            var input = doc.createElement("input");
            input.type = "number";
            input.className = "pure-input-1 path-ce-" + fieldName.replace("_", "-");
            input.step = "any";
            input.setAttribute("data-pathce-field", fieldName);
            if (value !== undefined && value !== null && value !== "") {
                input.value = String(value);
            } else {
                input.value = "0";
            }
            return input;
        }

        var quantityCell = doc.createElement("td");
        quantityCell.appendChild(createNumberInput("quantity", treatment ? treatment.quantity : null));
        row.appendChild(quantityCell);

        var unitCostCell = doc.createElement("td");
        unitCostCell.appendChild(createNumberInput("unit_cost", treatment ? treatment.unit_cost : null));
        row.appendChild(unitCostCell);

        var fixedCostCell = doc.createElement("td");
        fixedCostCell.appendChild(createNumberInput("fixed_cost", treatment ? treatment.fixed_cost : null));
        row.appendChild(fixedCostCell);

        var actionsCell = doc.createElement("td");
        actionsCell.className = "wc-table__actions";
        var removeButton = doc.createElement("button");
        removeButton.type = "button";
        removeButton.className = "pure-button pure-button-secondary";
        removeButton.setAttribute("data-pathce-action", "remove-treatment");
        removeButton.textContent = "Remove";
        actionsCell.appendChild(removeButton);
        row.appendChild(actionsCell);

        return row;
    }

    function renderTreatments(controller, treatments) {
        var body = controller.treatmentsBody;
        if (!body) {
            return;
        }
        var doc = window.document;
        body.textContent = "";
        var list = Array.isArray(treatments) ? treatments : [];
        if (list.length === 0) {
            return;
        }
        var fragment = doc.createDocumentFragment();
        list.forEach(function (item, index) {
            fragment.appendChild(createTreatmentRow(controller, item || {}, index));
        });
        body.appendChild(fragment);
    }

    function readTreatmentRow(row) {
        if (!row) {
            return null;
        }
        var getValue = function (field) {
            var element = row.querySelector('[data-pathce-field="' + field + '"]');
            if (!element) {
                return "";
            }
            return element.value;
        };
        var label = (getValue("label") || "").trim();
        var scenario = (getValue("scenario") || "").trim();
        var quantity = toNumber(getValue("quantity"));
        var unitCost = toNumber(getValue("unit_cost"));
        var fixedCost = toNumber(getValue("fixed_cost"));
        return {
            label: label,
            scenario: scenario,
            quantity: quantity === null ? 0 : quantity,
            unit_cost: unitCost === null ? 0 : unitCost,
            fixed_cost: fixedCost === null ? 0 : fixedCost
        };
    }

    function collectTreatments(controller) {
        var body = controller.treatmentsBody;
        if (!body) {
            return [];
        }
        var rows = Array.prototype.slice.call(body.querySelectorAll("tr"));
        var treatments = [];
        rows.forEach(function (row) {
            var data = readTreatmentRow(row);
            if (!data) {
                return;
            }
            if (!data.label || !data.scenario) {
                return;
            }
            treatments.push(data);
        });
        return treatments;
    }

    function reindexTreatmentRows(controller) {
        var body = controller.treatmentsBody;
        if (!body) {
            return;
        }
        Array.prototype.forEach.call(body.querySelectorAll("tr"), function (row, idx) {
            row.dataset.index = String(idx);
        });
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
            treatment_options: collectTreatments(controller)
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
            availableScenarios: [],
            pollTimer: null,
            statusFetchInFlight: false,
            resultsFetchInFlight: false,
            lastStatusValue: null,
            lastEmittedStatus: null,
            lastJobId: null
        };
        controller.state = state;
        controller.job_status_poll_interval_ms = 1200;

        var emitter = events.useEventMap(EVENT_NAMES, events.createEmitter());
        controller.events = emitter;

        var formElement = dom.ensureElement("#path_ce_form", "PATH Cost-Effective form not found.");
        var hintElement = dom.ensureElement("#path_ce_hint", "PATH Cost-Effective hint element missing.");
        var summaryElement = dom.ensureElement("#path_ce_summary", "PATH Cost-Effective summary element missing.");
        var treatmentsBody = dom.ensureElement("#path_ce_treatments_table tbody", "PATH Cost-Effective treatments table missing.");
        var jobElement = dom.ensureElement("#path_ce_rq_job", "PATH Cost-Effective job element missing.");
        var brailleElement = dom.ensureElement("#path_ce_braille", "PATH Cost-Effective braille element missing.");
        var stacktraceElement = dom.ensureElement("#path_ce_stacktrace", "PATH Cost-Effective stacktrace element missing.");
        var statusElement = dom.qs("#path_ce_form #status");
        var infoElement = dom.qs("#path_ce_form #info");

        var hintAdapter = createLegacyAdapter(hintElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var jobAdapter = createLegacyAdapter(jobElement);
        var brailleAdapter = createLegacyAdapter(brailleElement);
        var infoAdapter = createLegacyAdapter(infoElement);

        controller.form = formElement;
        controller.hint = hintAdapter;
        controller.stacktrace = stacktraceAdapter;
        controller.status = statusAdapter;
        controller.rq_job = jobAdapter;
        controller.braille = brailleAdapter;
        controller.info = infoAdapter;
        controller.summaryElement = summaryElement;
        controller.hintElement = hintElement;
        controller.treatmentsBody = treatmentsBody;
        controller.brailleElement = brailleElement;
        controller.command_btn_id = ["path_ce_run"];

        var baseTriggerEvent = controller.triggerEvent.bind(controller);
        controller.triggerEvent = function (eventName, payload) {
            if (eventName && eventName.indexOf("job:") === 0) {
                emitEvent(controller, eventName, payload);
            }
            baseTriggerEvent(eventName, payload);
        };

        function applyConfig(config) {
            state.config = Object.assign({}, config || {});
            ensureScenarioOptions(state, state.config);
            var values = buildFormValues(state.config);
            applyFormValues(forms, formElement, values);
            renderTreatments(controller, state.config.treatment_options || []);
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
            state.lastStatusValue = statusName || null;

            updateStatusMessage(controller, data.status || "");
            setHint(controller, data.status_message || "", statusName === "failed");
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
            return http.getJson(ENDPOINTS.status, { params: { _: Date.now() } })
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
            return http.getJson(ENDPOINTS.results, { params: { _: Date.now() } })
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

        function handleAddTreatment(event) {
            event.preventDefault();
            var scenarios = state.availableScenarios;
            var defaultScenario = scenarios && scenarios.length ? scenarios[0] : "";
            var treatment = {
                label: DEFAULT_TREATMENT_LABEL,
                scenario: defaultScenario,
                quantity: 0,
                unit_cost: 0,
                fixed_cost: 0
            };
            var rowCount = controller.treatmentsBody ? controller.treatmentsBody.querySelectorAll("tr").length : 0;
            var row = createTreatmentRow(controller, treatment, rowCount);
            if (controller.treatmentsBody) {
                controller.treatmentsBody.appendChild(row);
            }
            reindexTreatmentRows(controller);
            emitEvent(controller, "pathce:treatment:added", { index: rowCount, treatment: treatment });
            var focusTarget = row.querySelector('[data-pathce-field="label"]');
            if (focusTarget && typeof focusTarget.focus === "function") {
                focusTarget.focus();
            }
        }

        function handleRemoveTreatment(event, matched) {
            event.preventDefault();
            if (!matched) {
                return;
            }
            var row = matched.closest("tr");
            if (!row || !controller.treatmentsBody) {
                return;
            }
            var index = Array.prototype.indexOf.call(controller.treatmentsBody.querySelectorAll("tr"), row);
            var snapshot = readTreatmentRow(row);
            row.remove();
            reindexTreatmentRows(controller);
            emitEvent(controller, "pathce:treatment:removed", { index: index, treatment: snapshot });
        }

        function handleTreatmentFieldChange(event, matched) {
            if (!matched || !controller.treatmentsBody) {
                return;
            }
            var row = matched.closest("tr");
            if (!row) {
                return;
            }
            var index = Array.prototype.indexOf.call(controller.treatmentsBody.querySelectorAll("tr"), row);
            var treatment = readTreatmentRow(row);
            emitEvent(controller, "pathce:treatment:updated", { index: index, treatment: treatment });
        }

        function handleSave(event) {
            event.preventDefault();
            controller.saveConfig();
        }

        function handleRun(event) {
            event.preventDefault();
            controller.run();
        }

        dom.delegate(formElement, "click", "[data-pathce-action='add-treatment']", handleAddTreatment);
        dom.delegate(formElement, "click", "[data-pathce-action='remove-treatment']", handleRemoveTreatment);
        dom.delegate(formElement, "click", "[data-pathce-action='save-config']", handleSave);
        dom.delegate(formElement, "click", "[data-pathce-action='run']", handleRun);
        var treatmentFieldSelector = "[data-pathce-field]";
        dom.delegate(formElement, "input", treatmentFieldSelector, handleTreatmentFieldChange);
        dom.delegate(formElement, "change", treatmentFieldSelector, handleTreatmentFieldChange);

        controller.fetchConfig = function () {
            setHint(controller, "Loading PATH Cost-Effective configuration…");
            return http.getJson(ENDPOINTS.config, { params: { _: Date.now() } })
                .then(function (response) {
                    var config = response && response.config ? response.config : {};
                    applyConfig(config);
                    setHint(controller, "");
                    if (controller.stacktrace && typeof controller.stacktrace.empty === "function") {
                        controller.stacktrace.empty();
                    }
                    return config;
                })
                .catch(function (error) {
                    setHint(controller, "Failed to load configuration.", true);
                    controller.pushErrorStacktrace(controller, error);
                    emitEvent(controller, "pathce:config:error", { error: error });
                    throw error;
                });
        };

        controller.saveConfig = function () {
            var payload = buildPayload(forms, controller);
            setHint(controller, "Saving configuration…");
            return http.postJson(ENDPOINTS.config, payload, { form: formElement })
                .then(function (result) {
                    var response = result && result.body !== undefined ? result.body : result;
                    var nextConfig = response && response.config ? response.config : payload;
                    applyConfig(nextConfig);
                    setHint(controller, "Configuration saved.");
                    if (controller.stacktrace && typeof controller.stacktrace.empty === "function") {
                        controller.stacktrace.empty();
                    }
                    emitEvent(controller, "pathce:config:saved", { config: state.config, response: response });
                    return response;
                })
                .catch(function (error) {
                    setHint(controller, "Failed to save configuration.", true);
                    controller.pushErrorStacktrace(controller, error);
                    emitEvent(controller, "pathce:config:error", { error: error });
                    throw error;
                });
        };

        controller.run = function () {
            setHint(controller, "Starting PATH Cost-Effective run…");
            stopPolling();
            return http.postJson(ENDPOINTS.run, {}, { form: formElement })
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
                    setHint(controller, "PATH Cost-Effective job submitted. Monitoring status…");
                    startPolling();
                    refreshResults();
                    return response;
                })
                .catch(function (error) {
                    setHint(controller, "Failed to enqueue PATH Cost-Effective run.", true);
                    controller.pushErrorStacktrace(controller, error);
                    controller.set_rq_job_id(controller, null);
                    state.lastEmittedStatus = "error";
                    emitEvent(controller, "pathce:run:error", { error: error });
                    controller.triggerEvent("job:error", { task: "pathce:run", error: error });
                    throw error;
                });
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
