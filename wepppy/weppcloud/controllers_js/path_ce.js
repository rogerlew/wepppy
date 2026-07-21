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
    var DEFAULT_TREATMENTS = [
        { label: "0.5 tons/acre", scenario: "mulch_15_sbs_map", unit_cost: 2475, quantity: 0.5, fixed_cost: 500 },
        { label: "1 tons/acre", scenario: "mulch_30_sbs_map", unit_cost: 2475, quantity: 1, fixed_cost: 1000 },
        { label: "2 tons/acre", scenario: "mulch_60_sbs_map", unit_cost: 2475, quantity: 2, fixed_cost: 1500 }
    ];
    var MULCH_SCENARIOS = ["mulch_15_sbs_map", "mulch_30_sbs_map", "mulch_60_sbs_map"];
    var MULCH_SCENARIO_RE = /^mulch_(\d+)_sbs_map$/;

    // label and rate are load-bearing derivations from the scenario name
    // (mirrors presets.label_for_scenario: mulch_{n}_sbs_map -> n/30 tons/acre)
    function rateForScenario(scenario) {
        var match = MULCH_SCENARIO_RE.exec(String(scenario || ""));
        if (!match) {
            return null;
        }
        return Number(match[1]) / 30;
    }

    function labelForScenario(scenario) {
        var rate = rateForScenario(scenario);
        return rate === null ? null : String(rate) + " tons/acre";
    }
    var EVENT_NAMES = [
        "pathce:config:loaded",
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

    function setUnitizedValue(input, value) {
        if (!input) {
            return;
        }
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
    }

    function readUnitizedValue(input) {
        if (!input) {
            return null;
        }
        // UnitizerClient maintains the canonical dataset as the user edits the
        // (possibly display-converted) field; without it the raw value IS the
        // canonical value and the dataset may be stale.
        var unitizerActive = typeof window !== "undefined" && Boolean(window.UnitizerClient);
        var canonical = unitizerActive && input.dataset ? input.dataset.unitizerCanonicalValue : null;
        var sourceValue = canonical && canonical !== "" ? canonical : input.value;
        return toNumber(sourceValue);
    }

    function refreshUnitizer(scope) {
        if (typeof window !== "undefined" && window.UnitizerClient && typeof window.UnitizerClient.ready === "function") {
            window.UnitizerClient.ready()
                .then(function (client) {
                    // registration (not just update) is required for dynamic
                    // inputs: it attaches the input/change handlers that keep
                    // dataset.unitizerCanonicalValue current as the user edits
                    if (client && typeof client.registerNumericInputs === "function") {
                        client.registerNumericInputs(scope || undefined);
                    }
                    if (client && typeof client.updateNumericFields === "function") {
                        client.updateNumericFields(scope || undefined);
                    }
                    // keep [data-unitizer-label] spans (e.g. the treatment
                    // table's Unit Cost header) on the active display unit
                    if (client && typeof client.updateUnitLabels === "function") {
                        client.updateUnitLabels(scope || undefined);
                    }
                })
                .catch(function () {
                    /* noop */
                });
        }
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

    // Sddc values are stored canonically in tonne/yr (weight-annual); the
    // summary swaps in the unitizer's multi-unit blocks when the client is up
    function applyUnitizedSummaryValues(controller) {
        var summaryElement = controller.summaryElement;
        if (!summaryElement || typeof window === "undefined" || !window.UnitizerClient
            || typeof window.UnitizerClient.ready !== "function") {
            return;
        }
        window.UnitizerClient.ready()
            .then(function (client) {
                if (!client || typeof client.renderValue !== "function") {
                    return;
                }
                var nodes = summaryElement.querySelectorAll("[data-pathce-canonical]");
                Array.prototype.forEach.call(nodes, function (node) {
                    var html = client.renderValue(
                        node.getAttribute("data-pathce-canonical"),
                        node.getAttribute("data-pathce-canonical-unit") || "tonne/yr",
                        { includeUnits: true }
                    );
                    if (html) {
                        node.innerHTML = html;
                    }
                });
            })
            .catch(function () {
                /* noop — fallback canonical text already rendered */
            });
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
        var solverLabel = data.primary_status === 1 ? "Optimal" : "Second-best (thresholds infeasible)";
        var sweep = data.sweep || {};
        var rows = [
            ["Solution", solverLabel],
            ["Schema", data.schema_mode || "—"],
            ["Selected Hillslopes", Array.isArray(data.selected_hillslopes) ? String(data.selected_hillslopes.length) : "—"],
            ["Total Cost (variable, $)", formatNumber(data.total_cost)],
            ["Total Fixed Cost ($)", formatNumber(data.total_fixed_cost)],
            ["Total Sddc Reduction", formatNumber(data.total_sddc_reduction), data.total_sddc_reduction],
            ["Final Sddc", formatNumber(data.final_sddc), data.final_sddc],
            ["Untreatable (threshold not met)", data.n_untreatable !== undefined ? String(data.n_untreatable) : "—"],
            ["Sweep Cells", sweep.n_cells !== undefined && sweep.n_cells !== null ? String(sweep.n_cells) + (sweep.n_errors ? " (" + sweep.n_errors + " failed)" : "") : "—"]
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
            var canonical = entry.length > 2 ? toNumber(entry[2]) : null;
            if (canonical !== null) {
                // fallback text shows the canonical unit; the unitizer
                // enhancement below replaces it with preference-aware blocks
                dd.textContent = entry[1] + " tonne/yr";
                dd.setAttribute("data-pathce-canonical", String(canonical));
                dd.setAttribute("data-pathce-canonical-unit", "tonne/yr");
            } else {
                dd.textContent = entry[1];
            }
            item.appendChild(dt);
            item.appendChild(dd);
            fragment.appendChild(item);
        });
        summaryElement.appendChild(fragment);
        applyUnitizedSummaryValues(controller);
    }

    var RESULT_RESOURCES = [
        {
            key: "report",
            label: "Interactive Report",
            hint: "Treatment selection map, threshold analysis with sliders, and the 3D cost surface (Quarto HTML)."
        },
        {
            key: "selection",
            label: "Selection CSV",
            hint: "Selected hillslopes with their assigned treatment, area, and acre-based cost."
        },
        {
            key: "sdyd",
            label: "Final Sdyd CSV",
            hint: "Post-treatment sediment yield for every hillslope in the analysis."
        },
        {
            key: "untreatable",
            label: "Untreatable CSV",
            hint: "Hillslopes that cannot meet the yield threshold with any configured treatment."
        },
        {
            key: "sweep",
            label: "Threshold Sweep CSV",
            hint: "Solver results across the threshold grid — the data behind the report's sliders and cost surface."
        }
    ];

    function renderLinks(controller, results) {
        var linksElement = controller.linksElement;
        var panelElement = controller.resultsPanelElement;
        if (!linksElement) {
            return;
        }
        linksElement.textContent = "";
        var doc = window.document;
        var data = results && typeof results === "object" ? results : {};
        var report = data.report || {};
        var artifacts = data.artifacts || {};
        var entryCount = 0;

        function addEntry(href, label, hint) {
            var item = doc.createElement("div");
            var anchor = doc.createElement("a");
            anchor.className = "wc-link wc-link--file";
            anchor.href = href;
            anchor.target = "_blank";
            anchor.rel = "noopener";
            anchor.textContent = label;
            item.appendChild(anchor);
            var help = doc.createElement("p");
            help.className = "wc-field__help";
            help.textContent = hint;
            item.appendChild(help);
            linksElement.appendChild(item);
            entryCount += 1;
        }

        RESULT_RESOURCES.forEach(function (resource) {
            if (resource.key === "report") {
                if (report.html) {
                    addEntry(endpoint("report/path_ce/"), resource.label, resource.hint);
                } else if (report.skipped_reason) {
                    var note = doc.createElement("p");
                    note.className = "wc-field__help";
                    note.textContent = "Report not rendered: " + report.skipped_reason;
                    linksElement.appendChild(note);
                    entryCount += 1;
                }
                return;
            }
            var relpath = artifacts[resource.key];
            if (relpath) {
                addEntry(endpoint("download/" + relpath + "?as_csv=1"), resource.label, resource.hint);
            }
        });

        if (panelElement) {
            panelElement.hidden = entryCount === 0;
        }
    }

    function renderPreconditions(controller, statusData) {
        var element = controller.preconditionsElement;
        if (!element) {
            return;
        }
        var statusName = statusData && typeof statusData.status === "string" ? statusData.status.toLowerCase() : "";
        element.textContent = "";
        element.classList.remove("wc-field__help--error");

        var doc = window.document;
        // prefer the structured list surfaced by the status endpoint; fall
        // back to prose parsing for older payloads
        var structured = statusData && Array.isArray(statusData.precondition_errors)
            ? statusData.precondition_errors.filter(function (item) { return item; })
            : [];
        var lines = structured;
        if (!lines.length) {
            var message = statusData && statusData.status_message ? String(statusData.status_message) : "";
            var isPreconditionFailure = statusName === "failed" && /run Omni|Omni scenario|Omni contrast|precondition|unreadable|re-run watershed/i.test(message);
            if (!isPreconditionFailure) {
                return;
            }
            lines = message.split(";").map(function (part) { return part.trim(); }).filter(Boolean);
        }
        if (!lines.length) {
            return;
        }
        element.classList.add("wc-field__help--error");
        lines.forEach(function (line) {
            var paragraph = doc.createElement("p");
            paragraph.textContent = String(line);
            element.appendChild(paragraph);
        });
    }

    function syncDerivedTreatmentFields(row) {
        if (!row) {
            return;
        }
        var scenarioField = row.querySelector('[data-pathce-field="scenario"]');
        var labelField = row.querySelector('[data-pathce-field="label"]');
        var quantityField = row.querySelector('[data-pathce-field="quantity"]');
        var scenario = scenarioField ? scenarioField.value : "";
        var label = labelForScenario(scenario);
        var rate = rateForScenario(scenario);
        if (labelField) {
            labelField.value = label === null ? "" : label;
        }
        if (quantityField) {
            quantityField.value = rate === null ? "" : String(rate);
        }
    }

    function createTreatmentRow(option) {
        var doc = window.document;
        var row = doc.createElement("tr");
        var scenario = option && option.scenario ? String(option.scenario) : MULCH_SCENARIOS[0];
        TREATMENT_FIELDS.forEach(function (field) {
            var cell = doc.createElement("td");
            var control;
            if (field === "scenario") {
                control = doc.createElement("select");
                var scenarios = MULCH_SCENARIOS.slice();
                // keep a stored scenario visible even if it is not a stock option
                if (scenario && scenarios.indexOf(scenario) === -1) {
                    scenarios.push(scenario);
                }
                scenarios.forEach(function (name) {
                    var opt = doc.createElement("option");
                    opt.value = name;
                    opt.textContent = name;
                    control.appendChild(opt);
                });
                control.value = scenario;
            } else {
                control = doc.createElement("input");
                if (field === "label") {
                    control.type = "text";
                } else {
                    control.type = "number";
                    control.step = "any";
                    control.min = "0";
                }
                var value = option && Object.prototype.hasOwnProperty.call(option, field) ? option[field] : "";
                if (field === "unit_cost") {
                    // stored $/acre (D4); unitizer converts the display when SI is active
                    control.setAttribute("data-unitizer-category", "currency-area");
                    control.setAttribute("data-unitizer-unit", "$/acre");
                    setUnitizedValue(control, value === null || value === undefined ? "" : value);
                } else {
                    control.value = value === null || value === undefined ? "" : String(value);
                }
            }
            if (field === "label" || field === "quantity") {
                // derived from the scenario; not user-editable
                control.readOnly = true;
                control.tabIndex = -1;
            }
            control.setAttribute("data-pathce-field", field);
            cell.appendChild(control);
            row.appendChild(cell);
        });
        var actionCell = doc.createElement("td");
        var removeButton = doc.createElement("button");
        removeButton.type = "button";
        removeButton.setAttribute("data-pathce-action", "remove-treatment");
        removeButton.textContent = "Remove";
        actionCell.appendChild(removeButton);
        row.appendChild(actionCell);
        syncDerivedTreatmentFields(row);
        return row;
    }

    function renderTreatmentOptions(controller, options) {
        var body = controller.treatmentsBody;
        var list = Array.isArray(options) && options.length ? options : DEFAULT_TREATMENTS;
        if (!body) {
            if (controller.state && controller.state.config) {
                controller.state.config.treatments = list.slice();
            }
            return;
        }
        body.textContent = "";
        list.forEach(function (option) {
            body.appendChild(createTreatmentRow(option));
        });
        refreshUnitizer(controller.form);
    }

    function appendTreatmentRow(controller, option) {
        var body = controller.treatmentsBody;
        if (!body) {
            return null;
        }
        var seed = option || {};
        if (!seed.scenario) {
            // default to the first scenario not already configured (duplicates
            // are rejected server-side), prefilled with that tier's defaults
            var used = Array.prototype.map.call(
                body.querySelectorAll('[data-pathce-field="scenario"]'),
                function (field) { return field.value; }
            );
            var unused = MULCH_SCENARIOS.filter(function (name) {
                return used.indexOf(name) === -1;
            });
            var scenario = unused.length ? unused[0] : MULCH_SCENARIOS[0];
            var defaults = DEFAULT_TREATMENTS.filter(function (entry) {
                return entry.scenario === scenario;
            })[0];
            seed = Object.assign({}, defaults || { scenario: scenario }, seed);
        }
        var row = createTreatmentRow(seed);
        body.appendChild(row);
        refreshUnitizer(controller.form);
        emitEvent(controller, "pathce:treatment:added", { option: seed, row: row });
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
            if (controller.state && controller.state.config && Array.isArray(controller.state.config.treatments)) {
                return controller.state.config.treatments.slice();
            }
            return [];
        }
        var rows = body.querySelectorAll("tr");
        var options = [];
        Array.prototype.slice.call(rows).forEach(function (row) {
            var getInput = function (name) {
                return row.querySelector('[data-pathce-field="' + name + '"]');
            };
            var getField = function (name) {
                var input = getInput(name);
                return input ? input.value : "";
            };
            var scenario = String(getField("scenario") || "").trim();
            // label and rate are derived from the scenario, not read from the
            // (readonly) fields — guarantees the server's derivation contract
            var derivedLabel = labelForScenario(scenario);
            var label = derivedLabel !== null ? derivedLabel : String(getField("label") || "").trim();
            if (!label && !scenario) {
                return;
            }
            var derivedRate = rateForScenario(scenario);
            var quantity = derivedRate !== null ? derivedRate : toNumber(getField("quantity"));
            var unitCost = readUnitizedValue(getInput("unit_cost"));
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

    function buildPayload(forms, controller) {
        var formElement = controller.form;
        var values = forms.serializeForm(formElement, { format: "json" }) || {};
        var severity = normalizeSeverity(values.severity_filter);
        var slopeMin = toNumber(values.slope_min);
        var slopeMax = toNumber(values.slope_max);
        // the Sddc input is unitized: read the canonical (tonne/yr) value, not
        // the possibly display-converted field value
        var sddc = readUnitizedValue(controller.sddcInput);
        if (sddc === null) {
            sddc = toNumber(values.sddc_threshold);
        }
        var sdyd = toNumber(values.sdyd_threshold);
        var payload = {
            slope_range: [slopeMin, slopeMax],
            severity_filter: severity,
            treatments: harvestTreatmentOptions(controller)
        };
        // blank thresholds are omitted so the server's partial-merge keeps the
        // currently configured values instead of silently resetting to 0
        if (sddc !== null) {
            payload.sddc_threshold = sddc;
        }
        if (sdyd !== null) {
            payload.sdyd_threshold = sdyd;
        }
        return payload;
    }

    function extractErrorMessage(response) {
        if (!response || typeof response !== "object") {
            return null;
        }
        var error = response.error;
        if (!error) {
            return null;
        }
        if (typeof error === "string") {
            return error;
        }
        if (typeof error === "object" && error.message) {
            return String(error.message);
        }
        return "Request failed.";
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
        controller.job_status_poll_interval_ms = 2000;

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
        controller.treatmentsBody = treatmentsBody || null;
        controller.linksElement = dom.qs("#path_ce_links");
        controller.resultsPanelElement = dom.qs("#path_ce_results_panel");
        controller.preconditionsElement = dom.qs("#path_ce_preconditions");
        controller.sddcInput = dom.qs("#path_ce_sddc_threshold");

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
            setUnitizedValue(controller.sddcInput, values.sddc_threshold);
            renderTreatmentOptions(controller, state.config.treatments || []);
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
            renderPreconditions(controller, data);

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
            renderLinks(controller, results);
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

        function handleRun(event) {
            event.preventDefault();
            controller.run();
        }

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
        dom.delegate(formElement, "change", "select[data-pathce-field='scenario']", function (event) {
            var row = event && event.target && typeof event.target.closest === "function"
                ? event.target.closest("tr")
                : null;
            syncDerivedTreatmentFields(row);
            emitEvent(controller, "pathce:treatment:updated", { row: row });
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
                    // error_factory responses arrive as HTTP 200 with an error body
                    var errorMessage = extractErrorMessage(response);
                    if (errorMessage) {
                        setMessage(controller, errorMessage, true);
                        if (typeof controller.stop_job_status_polling === "function") {
                            controller.stop_job_status_polling(controller);
                        }
                        if (typeof controller.reset_status_spinner === "function") {
                            controller.reset_status_spinner(controller);
                        }
                        state.lastEmittedStatus = "error";
                        emitEvent(controller, "pathce:run:error", { error: errorMessage });
                        controller.triggerEvent("job:error", { task: "pathce:run", error: errorMessage });
                        var runError = new Error(errorMessage);
                        runError.pathceHandled = true;
                        throw runError;
                    }
                    var jobId = response && response.job_id;
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
                    if (error && error.pathceHandled) {
                        throw error;
                    }
                    setMessage(controller, "Failed to enqueue PATH Cost-Effective run.", true);
                    controller.pushErrorStacktrace(controller, error);
                    // Preserve the last job_id hint so users can still inspect the previous attempt.
                    controller.stop_job_status_polling(controller);
                    controller.reset_status_spinner(controller);
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

            if (!jobId && controllerContext && controllerContext.job_id) {
                jobId = controllerContext.job_id;
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
