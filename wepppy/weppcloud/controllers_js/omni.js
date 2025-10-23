/* ----------------------------------------------------------------------------
 * Omni
 * Doc: controllers_js/README.md — Omni Controller Reference (2024 helper migration)
 * ----------------------------------------------------------------------------
 */
var Omni = (function () {
    var instance;

    var MAX_SBS_FILE_BYTES = 100 * 1024 * 1024;
    var ALLOWED_SBS_FILE_EXTENSIONS = new Set(["tif", "tiff", "img"]);
    var SCENARIO_ORDER = [
        "uniform_low",
        "uniform_moderate",
        "uniform_high",
        "sbs_map",
        "undisturbed",
        "prescribed_fire",
        "thinning",
        "mulch"
    ];
    var EVENT_NAMES = [
        "omni:scenarios:loaded",
        "omni:scenario:added",
        "omni:scenario:removed",
        "omni:scenario:updated",
        "omni:run:started",
        "omni:run:completed",
        "omni:run:error"
    ];

    var SCENARIO_CATALOG = {
        uniform_low: {
            label: "Uniform Low Severity Fire",
            controls: []
        },
        uniform_moderate: {
            label: "Uniform Moderate Severity Fire",
            controls: []
        },
        uniform_high: {
            label: "Uniform High Severity Fire",
            controls: []
        },
        sbs_map: {
            label: "SBS Map",
            controls: [
                {
                    type: "file",
                    name: "sbs_file",
                    label: "Upload SBS File",
                    help: "GeoTIFF/IMG, 100 MB maximum."
                }
            ]
        },
        undisturbed: {
            label: "Undisturbed",
            controls: [],
            condition: function (ctx) {
                var disturbed = resolveDisturbed();
                if (!disturbed) {
                    return false;
                }
                if (typeof disturbed.get_has_sbs_cached === "function") {
                    var cached = disturbed.get_has_sbs_cached();
                    if (cached !== undefined) {
                        return cached === true;
                    }
                }
                if (typeof disturbed.has_sbs === "function") {
                    try {
                        return disturbed.has_sbs({ forceRefresh: false }) === true;
                    } catch (err) {
                        console.warn("[Omni] Disturbed.has_sbs failed", err);
                    }
                }
                return false;
            }
        },
        prescribed_fire: {
            label: "Prescribed Fire",
            controls: [],
            condition: function (ctx) {
                var disturbed = resolveDisturbed();
                var hasSbs = false;
                if (disturbed) {
                    if (typeof disturbed.get_has_sbs_cached === "function") {
                        var cached = disturbed.get_has_sbs_cached();
                        if (cached !== undefined) {
                            hasSbs = cached === true;
                        }
                    } else if (typeof disturbed.has_sbs === "function") {
                        try {
                            hasSbs = disturbed.has_sbs({ forceRefresh: false }) === true;
                        } catch (err) {
                            console.warn("[Omni] Disturbed.has_sbs failed", err);
                        }
                    }
                }
                if (!hasSbs) {
                    return true;
                }
                if (ctx && typeof ctx.hasUndisturbed === "function") {
                    return ctx.hasUndisturbed();
                }
                return false;
            }
        },
        thinning: {
            label: "Thinning",
            controls: [
                {
                    type: "select",
                    name: "canopy_cover",
                    label: "Canopy cover reduction to",
                    options: [
                        { value: "40%", label: "40%" },
                        { value: "65%", label: "65%" }
                    ]
                },
                {
                    type: "select",
                    name: "ground_cover",
                    label: "Ground cover",
                    options: [
                        { value: "93%", label: "93% – Cable" },
                        { value: "90%", label: "90% – Forward" },
                        { value: "85%", label: "85% – Skidder" },
                        { value: "75%", label: "75%" }
                    ]
                }
            ]
        },
        mulch: {
            label: "Mulching",
            controls: [
                {
                    type: "select",
                    name: "ground_cover_increase",
                    label: "Ground cover increase",
                    options: [
                        { value: "15%", label: "15% – ½ tons/acre" },
                        { value: "30%", label: "30% – 1 ton/acre" },
                        { value: "60%", label: "60% – 2 tons/acre" }
                    ]
                },
                {
                    type: "select",
                    name: "base_scenario",
                    label: "Base scenario",
                    options: [
                        { value: "uniform_low", label: "Uniform Low Severity Fire" },
                        { value: "uniform_moderate", label: "Uniform Moderate Severity Fire" },
                        { value: "uniform_high", label: "Uniform High Severity Fire" },
                        { value: "sbs_map", label: "SBS Map" }
                    ]
                }
            ]
        }
    };

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function") {
            throw new Error("Omni controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Omni controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("Omni controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Omni controller requires WCEvents helpers.");
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

    function resolveDisturbed() {
        if (!window.Disturbed || typeof window.Disturbed.getInstance !== "function") {
            return null;
        }
        try {
            return window.Disturbed.getInstance();
        } catch (err) {
            console.warn("[Omni] Unable to resolve Disturbed controller", err);
        }
        return null;
    }

    function hasUndisturbedScenario(container) {
        if (!container) {
            return false;
        }
        var selects = container.querySelectorAll("[data-omni-role='scenario-select']");
        for (var i = 0; i < selects.length; i += 1) {
            if (selects[i].value === "undisturbed") {
                return true;
            }
        }
        return false;
    }

    function scenarioIsAvailable(key, container) {
        var config = SCENARIO_CATALOG[key];
        if (!config) {
            return false;
        }
        if (typeof config.condition === "function") {
            try {
                return !!config.condition({
                    hasUndisturbed: function () {
                        return hasUndisturbedScenario(container);
                    }
                });
            } catch (err) {
                console.warn("[Omni] Scenario condition failed for " + key, err);
                return false;
            }
        }
        return true;
    }

    function ensureOption(parent, value, label) {
        var option = parent.ownerDocument.createElement("option");
        option.value = value;
        option.textContent = label === undefined ? value : label;
        parent.appendChild(option);
        return option;
    }

    function populateScenarioSelect(select, container) {
        if (!select) {
            return;
        }
        var currentValue = select.value;
        while (select.firstChild) {
            select.removeChild(select.firstChild);
        }

        ensureOption(select, "", "Select scenario");
        SCENARIO_ORDER.forEach(function (key) {
            if (!scenarioIsAvailable(key, container)) {
                return;
            }
            var config = SCENARIO_CATALOG[key];
            ensureOption(select, key, config.label);
        });

        if (currentValue && select.querySelector('option[value="' + currentValue + '"]')) {
            select.value = currentValue;
        } else {
            select.value = "";
        }
    }

    function extractFileName(path) {
        if (!path) {
            return "";
        }
        var normalized = String(path);
        var parts = normalized.split(/[\\/]/);
        return parts.length ? parts[parts.length - 1] : normalized;
    }

    function createFieldWrapper(document, control) {
        var field = document.createElement("div");
        field.className = "wc-field";

        var label = document.createElement("label");
        label.className = "wc-field__label";
        label.textContent = control.label || control.name || "";

        var inputRow = document.createElement("div");
        inputRow.className = "wc-field__input-row";

        field.appendChild(label);
        field.appendChild(inputRow);

        return { field: field, row: inputRow };
    }

    function createControlElement(document, control, scenarioIndex, values) {
        var name = control.name;
        var fieldWrap = createFieldWrapper(document, control);
        var row = fieldWrap.row;
        var value = values && values[name] !== undefined ? values[name] : null;

        if (control.type === "select") {
            var select = document.createElement("select");
            select.className = "wc-field__control";
            select.name = name;
            select.id = name + "_" + scenarioIndex;
            select.dataset.omniField = name;

            (control.options || []).forEach(function (option) {
                var optValue = option && typeof option === "object" ? option.value : option;
            var optLabel = option && typeof option === "object" ? option.label : option;
                ensureOption(select, optValue, optLabel);
            });

            if (value !== null && value !== undefined) {
                select.value = value;
            }

            row.appendChild(select);
        } else if (control.type === "file") {
            var input = document.createElement("input");
            input.type = "file";
            input.className = "wc-field__control";
            input.name = name;
            input.id = name + "_" + scenarioIndex;
            input.accept = ".tif,.tiff,.img";
            input.dataset.omniField = name;
            input.dataset.omniRole = "scenario-file";
            row.appendChild(input);

            var hint = document.createElement("p");
            hint.className = "wc-field__help";
            hint.textContent = control.help || "GeoTIFF/IMG, 100 MB maximum.";
            fieldWrap.field.appendChild(hint);

            if (values && values.sbs_file_path) {
                var existing = document.createElement("p");
                existing.className = "wc-field__help";
                existing.textContent = "Current file: " + extractFileName(values.sbs_file_path);
                fieldWrap.field.appendChild(existing);
            }
        }

        return fieldWrap.field;
    }

    function readScenarioDefinition(scenarioItem) {
        if (!scenarioItem) {
            return null;
        }
        var select = scenarioItem.querySelector("[data-omni-role='scenario-select']");
        if (!select || !select.value) {
            return null;
        }
        var definition = { type: select.value };
        var inputs = scenarioItem.querySelectorAll("[data-omni-field]");
        inputs.forEach(function (input) {
            var fieldName = input.dataset.omniField;
            if (!fieldName) {
                return;
            }
            if (input.type === "file") {
                if (input.files && input.files.length > 0) {
                    definition[fieldName] = input.files[0].name;
                }
                return;
            }
            definition[fieldName] = input.value;
        });
        return definition;
    }

    function validateSbsFile(file) {
        if (!file) {
            return;
        }
        var name = file.name || "";
        var dot = name.lastIndexOf(".");
        var ext = dot >= 0 ? name.slice(dot + 1).toLowerCase() : "";
        if (!ALLOWED_SBS_FILE_EXTENSIONS.has(ext)) {
            throw new Error("SBS maps must be .tif, .tiff, or .img files.");
        }
        if (file.size > MAX_SBS_FILE_BYTES) {
            throw new Error("SBS maps must be 100 MB or smaller.");
        }
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var http = helpers.http;
        var events = helpers.events;

        var omni = controlBase();
        var omniEvents = null;
        var scenarioCounter = 0;

        if (events && typeof events.createEmitter === "function") {
            var baseEmitter = events.createEmitter();
            if (typeof events.useEventMap === "function") {
                omniEvents = events.useEventMap(EVENT_NAMES, baseEmitter);
            } else {
                omniEvents = baseEmitter;
            }
        }

        if (omniEvents) {
            omni.events = omniEvents;
        }

        var formElement = dom.ensureElement("#omni_form", "Omni form not found.");
        var infoElement = dom.qs("#omni_form #info");
        var statusElement = dom.qs("#omni_form #status");
        var stacktraceElement = dom.qs("#omni_form #stacktrace");
        var rqJobElement = dom.qs("#omni_form #rq_job");
        var spinnerElement = dom.qs("#omni_form #braille");
        var hintElement = dom.qs("#hint_run_omni");
        var scenarioContainer = dom.ensureElement("#scenario-container", "Omni scenario container not found.");

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);
        var hintAdapter = createLegacyAdapter(hintElement);

        omni.form = formElement;
        omni.info = infoAdapter;
        omni.status = statusAdapter;
        omni.stacktrace = stacktraceAdapter;
        omni.rq_job = rqJobAdapter;
        omni.statusSpinnerEl = spinnerElement;
        omni.command_btn_id = "btn_run_omni";
        omni.hint = hintAdapter;

        omni.attach_status_stream(omni, {
            form: formElement,
            channel: "omni",
            runId: window.runid || window.runId || null,
            spinner: spinnerElement
        });

        var baseTriggerEvent = omni.triggerEvent.bind(omni);
        omni.triggerEvent = function (eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === "OMNI_SCENARIO_RUN_TASK_COMPLETED") {
                omni.report_scenarios();
                omni.disconnect_status_stream(omni);
                if (omniEvents && typeof omniEvents.emit === "function") {
                    omniEvents.emit("omni:run:completed", payload || {});
                }
            } else if (normalized === "END_BROADCAST") {
                omni.disconnect_status_stream(omni);
            }

            baseTriggerEvent(eventName, payload);
        };

        function emitScenarioUpdate(scenarioItem) {
            if (!omniEvents || typeof omniEvents.emit !== "function") {
                return;
            }
            var definition = readScenarioDefinition(scenarioItem);
            omniEvents.emit("omni:scenario:updated", {
                scenario: definition,
                element: scenarioItem
            });
        }

        function refreshScenarioOptions() {
            var selects = scenarioContainer.querySelectorAll("[data-omni-role='scenario-select']");
            selects.forEach(function (select) {
                var previous = select.value;
                populateScenarioSelect(select, scenarioContainer);
                if (previous && select.value === previous) {
                    emitScenarioUpdate(select.closest("[data-omni-scenario-item='true']"));
                }
            });
        }

        function updateScenarioControls(scenarioItem, values) {
            if (!scenarioItem) {
                return;
            }
            var select = scenarioItem.querySelector("[data-omni-role='scenario-select']");
            var controlsHost = scenarioItem.querySelector("[data-omni-scenario-controls]");
            if (!controlsHost) {
                return;
            }
            controlsHost.innerHTML = "";

            if (!select || !select.value) {
                return;
            }

            var config = SCENARIO_CATALOG[select.value];
            if (!config) {
                return;
            }

            (config.controls || []).forEach(function (control) {
                var controlField = createControlElement(
                    scenarioItem.ownerDocument,
                    control,
                    scenarioItem.dataset.index || "0",
                    values
                );
                controlsHost.appendChild(controlField);
            });
        }

        function addScenario(prefill, options) {
            var opts = options || {};
            var scenarioItem = formElement.ownerDocument.createElement("div");
            scenarioItem.className = "scenario-item wc-card wc-card--subtle";
            scenarioItem.dataset.index = String(scenarioCounter++);
            scenarioItem.dataset.omniScenarioItem = "true";
            scenarioItem.innerHTML = [
                '<div class="wc-card__body wc-stack">',
                '  <div class="wc-field">',
                '    <label class="wc-field__label" for="omni_scenario_' + scenarioItem.dataset.index + '">Scenario</label>',
                '    <select class="wc-field__control"',
                '            id="omni_scenario_' + scenarioItem.dataset.index + '"',
                '            name="scenario"',
                '            data-omni-role="scenario-select">',
                '      <option value="">Select scenario</option>',
                '    </select>',
                '  </div>',
                '  <div class="scenario-controls wc-stack" data-omni-scenario-controls></div>',
                '</div>',
                '<footer class="wc-card__footer">',
                '  <button type="button" class="pure-button button-error disable-readonly" data-omni-action="remove-scenario">',
                '    Remove',
                '  </button>',
                '</footer>'
            ].join("\n");

            scenarioContainer.appendChild(scenarioItem);

            var select = scenarioItem.querySelector("[data-omni-role='scenario-select']");
            populateScenarioSelect(select, scenarioContainer);

            if (prefill && prefill.type) {
                select.value = prefill.type;
            }
            updateScenarioControls(scenarioItem, prefill || null);

            if (!opts.deferRefresh) {
                refreshScenarioOptions();
            }

            if (omniEvents && typeof omniEvents.emit === "function") {
                omniEvents.emit("omni:scenario:added", {
                    scenario: readScenarioDefinition(scenarioItem),
                    element: scenarioItem
                });
            }

            return scenarioItem;
        }

        function removeScenario(target) {
            var scenarioItem = target.closest("[data-omni-scenario-item='true']");
            if (!scenarioItem) {
                return;
            }

            scenarioItem.remove();
            refreshScenarioOptions();

            if (omniEvents && typeof omniEvents.emit === "function") {
                omniEvents.emit("omni:scenario:removed", { element: scenarioItem });
            }
        }

        function serializeScenarios() {
            var items = scenarioContainer.querySelectorAll("[data-omni-scenario-item='true']");
            var scenarios = [];
            var formData = new FormData(formElement);
            if (typeof formData.delete === "function") {
                formData.delete("scenarios");
            }

            items.forEach(function (item, index) {
                var select = item.querySelector("[data-omni-role='scenario-select']");
                if (!select || !select.value) {
                    return;
                }

                var scenarioDef = { type: select.value };
                var config = SCENARIO_CATALOG[select.value] || {};
                var controls = item.querySelectorAll("[data-omni-field]");

                controls.forEach(function (input) {
                    var name = input.dataset.omniField;
                    if (!name) {
                        return;
                    }

                    if (input.type === "file") {
                        if (input.files && input.files.length > 0) {
                            var file = input.files[0];
                            if (select.value === "sbs_map") {
                                validateSbsFile(file);
                            }
                            formData.append("scenarios[" + index + "][" + name + "]", file);
                            scenarioDef[name] = file.name;
                        }
                        return;
                    }

                    if (input.value !== undefined && input.value !== null && input.value !== "") {
                        scenarioDef[name] = input.value;
                    }
                });

                scenarios.push(scenarioDef);
            });

            formData.append("scenarios", JSON.stringify(scenarios));
            return { formData: formData, scenarios: scenarios };
        }

        function clearStatus() {
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html("");
            }
            if (hintAdapter && typeof hintAdapter.text === "function") {
                hintAdapter.text("");
            }
            if (stacktraceAdapter && typeof stacktraceAdapter.html === "function") {
                stacktraceAdapter.html("");
            }
        }

        function setStatus(message) {
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(message || "");
            }
        }

        omni.serializeScenarios = serializeScenarios;

        omni.run_omni_scenarios = function () {
            clearStatus();

            var payload;
            try {
                payload = serializeScenarios();
            } catch (err) {
                var message = err && err.message ? err.message : "Validation failed. Check SBS uploads.";
                setStatus(message);
                if (hintAdapter && typeof hintAdapter.text === "function") {
                    hintAdapter.text(message);
                }
                if (omniEvents && typeof omniEvents.emit === "function") {
                    omniEvents.emit("omni:run:error", { error: err });
                }
                return;
            }

            setStatus("Submitting omni run...");
            omni.connect_status_stream(omni);

            if (omniEvents && typeof omniEvents.emit === "function") {
                omniEvents.emit("omni:run:started", { scenarios: payload.scenarios });
            }

            http.request("rq/api/run_omni", {
                method: "POST",
                body: payload.formData,
                form: formElement
            }).then(function (response) {
                var body = response && response.body ? response.body : null;
                if (body && body.Success === true) {
                    setStatus("run_omni_rq job submitted: " + body.job_id);
                    omni.set_rq_job_id(omni, body.job_id);
                    if (hintAdapter && typeof hintAdapter.text === "function") {
                        hintAdapter.text("");
                    }
                    if (omniEvents && typeof omniEvents.emit === "function") {
                        omniEvents.emit("omni:run:completed", {
                            jobId: body.job_id,
                            scenarios: payload.scenarios
                        });
                    }
                } else if (body) {
                    omni.pushResponseStacktrace(omni, body);
                    if (omniEvents && typeof omniEvents.emit === "function") {
                        omniEvents.emit("omni:run:error", { response: body });
                    }
                }
            }).catch(function (error) {
                var payload = toResponsePayload(http, error);
                omni.pushResponseStacktrace(omni, payload);
                setStatus(payload && payload.Error ? payload.Error : "Omni run failed.");
                if (omniEvents && typeof omniEvents.emit === "function") {
                    omniEvents.emit("omni:run:error", { error: error });
                }
            });
        };

        omni.runOmniScenarios = omni.run_omni_scenarios;

        omni.load_scenarios_from_backend = function () {
            clearStatus();
            return http.getJson("api/omni/get_scenarios").then(function (data) {
                if (!Array.isArray(data)) {
                    throw new Error("Invalid scenario format");
                }

                scenarioContainer.innerHTML = "";
                scenarioCounter = 0;

                data.forEach(function (scenario) {
                    var item = addScenario(scenario, { deferRefresh: true });
                    var select = item.querySelector("[data-omni-role='scenario-select']");
                    if (select && scenario.type) {
                        select.value = scenario.type;
                    }
                    updateScenarioControls(item, scenario);
                });

                refreshScenarioOptions();

                if (omniEvents && typeof omniEvents.emit === "function") {
                    omniEvents.emit("omni:scenarios:loaded", { scenarios: data });
                }
            }).catch(function (error) {
                console.error("Error loading scenarios:", error);
                setStatus("Unable to load saved scenarios.");
                if (omniEvents && typeof omniEvents.emit === "function") {
                    omniEvents.emit("omni:run:error", { error: error });
                }
            });
        };

        omni.report_scenarios = function () {
            if (infoAdapter && typeof infoAdapter.html === "function") {
                infoAdapter.html("");
            }

            http.request(url_for_run("report/omni_scenarios/"), {
                method: "GET",
                headers: { Accept: "text/html" }
            }).then(function (response) {
                var body = response && response.body ? response.body : "";
                omni.info.html(body);
            }).catch(function (error) {
                var payload = toResponsePayload(http, error);
                omni.pushResponseStacktrace(omni, payload);
            });
        };

        dom.delegate(formElement, "click", "[data-omni-action='add-scenario']", function (event) {
            event.preventDefault();
            addScenario();
        });

        dom.delegate(formElement, "click", "[data-omni-action='remove-scenario']", function (event) {
            event.preventDefault();
            removeScenario(event.target);
        });

        dom.delegate(formElement, "click", "[data-omni-action='run-scenarios']", function (event) {
            event.preventDefault();
            omni.run_omni_scenarios();
        });

        dom.delegate(scenarioContainer, "change", "[data-omni-role='scenario-select']", function (event, matched) {
            var item = matched.closest("[data-omni-scenario-item='true']");
            updateScenarioControls(item);
            refreshScenarioOptions();
            emitScenarioUpdate(item);
        });

        dom.delegate(scenarioContainer, "change", "[data-omni-field]", function (event, matched) {
            var item = matched.closest("[data-omni-scenario-item='true']");
            emitScenarioUpdate(item);
        });

        document.addEventListener("disturbed:has_sbs_changed", function () {
            refreshScenarioOptions();
        });

        return omni;
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
    globalThis.Omni = Omni;
}
