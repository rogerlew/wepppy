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
        "sbs_map",
        "uniform_low",
        "uniform_moderate",
        "uniform_high",
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
        "omni:run:error",
        "omni:contrast:run:completed",
        "omni:contrast:dry-run:completed"
    ];
    var CONTRAST_COMPLETION_EVENT = "OMNI_CONTRAST_RUN_TASK_COMPLETED";
    var CONTRAST_DELETE_COMPLETION_EVENT = "OMNI_CONTRAST_DELETE_TASK_COMPLETED";
    var CONTRAST_SELECTION_MODES = {
        cumulative: "cumulative",
        user_defined_areas: "user_defined_areas",
        user_defined_hillslope_groups: "user_defined_hillslope_groups",
        stream_order: "stream_order"
    };
    var CONTRAST_HILLSLOPE_LIMIT_MAX = 100;

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
            controls: []
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
        if (typeof http.requestWithSessionToken !== "function") {
            throw new Error("Omni controller requires WCHttp.requestWithSessionToken.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Omni controller requires WCEvents helpers.");
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

    function normalizeErrorValue(value) {
        if (value === undefined || value === null) {
            return null;
        }
        if (typeof value === "string") {
            return value;
        }
        if (Array.isArray(value)) {
            return value.map(function (item) { return item === undefined || item === null ? "" : String(item); }).join("\n");
        }
        if (typeof value === "object") {
            if (typeof value.message === "string") {
                return value.message;
            }
            if (typeof value.detail === "string") {
                return value.detail;
            }
            if (typeof value.details === "string") {
                return value.details;
            }
            if (value.details !== undefined) {
                return normalizeErrorValue(value.details);
            }
            try {
                return JSON.stringify(value);
            } catch (err) {
                return String(value);
            }
        }
        return String(value);
    }

    function formatErrorList(errors) {
        if (!Array.isArray(errors)) {
            return null;
        }
        var parts = [];
        errors.forEach(function (entry) {
            if (entry === undefined || entry === null) {
                return;
            }
            if (typeof entry === "string") {
                parts.push(entry);
                return;
            }
            if (typeof entry.message === "string") {
                parts.push(entry.message);
                return;
            }
            if (typeof entry.detail === "string") {
                parts.push(entry.detail);
                return;
            }
            if (typeof entry.code === "string") {
                parts.push(entry.code);
                return;
            }
            try {
                parts.push(JSON.stringify(entry));
            } catch (err) {
                parts.push(String(entry));
            }
        });
        return parts.length ? parts.join("\n") : null;
    }

    function resolveErrorMessage(payload, fallback) {
        if (!payload) {
            return fallback || null;
        }
        if (payload.error !== undefined) {
            var message = normalizeErrorValue(payload.error);
            if (message) {
                return message;
            }
        }
        if (payload.errors) {
            var errorList = formatErrorList(payload.errors);
            if (errorList) {
                return errorList;
            }
        }
        if (payload.message !== undefined) {
            return normalizeErrorValue(payload.message);
        }
        if (payload.detail !== undefined) {
            return normalizeErrorValue(payload.detail);
        }
        return fallback || null;
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
            if (body.error !== undefined || body.errors !== undefined) {
                return body;
            }
            var fallbackMessage = normalizeErrorValue(body.message || body.detail);
            var errorList = formatErrorList(body.errors);
            if (fallbackMessage || errorList) {
                return {
                    error: {
                        message: fallbackMessage || errorList || "Request failed",
                        details: body.details !== undefined ? body.details : undefined
                    },
                    errors: body.errors
                };
            }
        } else if (typeof body === "string" && body) {
            return { error: { message: body } };
        }

        if (error && typeof error === "object" && (error.error !== undefined || error.errors !== undefined)) {
            return error;
        }

        if (http && typeof http.isHttpError === "function" && http.isHttpError(error)) {
            var detail = error && (error.detail || error.message);
            if (detail && typeof detail === "object" && (detail.error !== undefined || detail.errors !== undefined)) {
                return detail;
            }
            return { error: { message: normalizeErrorValue(detail) || "Request failed" } };
        }

        return { error: { message: normalizeErrorValue(error && error.message) || "Request failed" } };
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

    function scenarioNameFromDefinition(definition) {
        if (!definition || !definition.type) {
            return null;
        }
        var type = String(definition.type);
        var normalizedType = type.toLowerCase();
        var typeAlias = {
            "1": "uniform_low",
            "2": "uniform_moderate",
            "3": "uniform_high",
            "4": "thinning",
            "5": "mulch",
            "8": "sbs_map",
            "9": "undisturbed",
            "10": "prescribed_fire"
        };
        if (typeAlias[normalizedType]) {
            normalizedType = typeAlias[normalizedType];
        }

        if (normalizedType === "thinning") {
            var canopy = String(definition.canopy_cover || "").replace(/%/g, "");
            var ground = String(definition.ground_cover || "").replace(/%/g, "");
            if (!canopy || !ground) {
                return null;
            }
            return normalizedType + "_" + canopy + "_" + ground;
        }

        if (normalizedType === "mulch") {
            var increase = String(definition.ground_cover_increase || "").replace(/%/g, "");
            var base = String(definition.base_scenario || "").trim();
            if (!increase || !base) {
                return null;
            }
            return normalizedType + "_" + increase + "_" + base;
        }

        if (normalizedType === "sbs_map") {
            var rawPath = String(definition.sbs_file_path || definition.sbs_map || definition.sbs_file || "");
            var fileName = rawPath.split(/[/\\\\]/).pop() || "";
            if (!fileName) {
                return normalizedType;
            }
            try {
                return normalizedType + "_" + btoa(fileName).replace(/=+$/g, "");
            } catch (err) {
                return normalizedType;
            }
        }

        return normalizedType;
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

    function formatJobHint(jobId) {
        if (!jobId) {
            return "";
        }
        var host = "";
        if (typeof window !== "undefined" && window.location && window.location.host) {
            host = window.location.host;
        }
        var dashboardUrl = host
            ? "https://" + host + "/weppcloud/rq/job-dashboard/" + encodeURIComponent(jobId)
            : "/weppcloud/rq/job-dashboard/" + encodeURIComponent(jobId);
        return 'job_id: <a href="' + dashboardUrl + '" target="_blank" rel="noopener noreferrer">' + jobId + "</a>";
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var http = helpers.http;
        var events = helpers.events;

        var omni = controlBase();
        var omniEvents = null;
        var scenarioCounter = 0;
        var deleteButton = null;
        var deleteModal = null;
        var deleteModalList = null;
        var deleteModalConfirm = null;
        var pendingDeleteSelections = [];

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
        deleteButton = dom.qs("#omni_form [data-omni-action='delete-selected']");
        deleteModal = dom.qs("#omni-delete-modal");
        deleteModalList = deleteModal ? deleteModal.querySelector("[data-omni-role='delete-list']") : null;
        deleteModalConfirm = deleteModal ? deleteModal.querySelector("[data-omni-action='confirm-delete']") : null;
        var scenarioContainer = dom.ensureElement("#scenario-container", "Omni scenario container not found.");
        var contrastFormElement = dom.qs("#omni_contrasts_form");
        var contrastModeSelect = contrastFormElement
            ? contrastFormElement.querySelector("[data-omni-contrast-role='selection-mode']")
            : null;
        var contrastStreamOrderInput = contrastFormElement
            ? contrastFormElement.querySelector("input[name='omni_contrast_selection_mode'][value='stream_order']")
            : null;
        var contrastControlSelect = contrastFormElement
            ? contrastFormElement.querySelector("[data-omni-contrast-role='control-scenario']")
            : null;
        var contrastScenarioSelect = contrastFormElement
            ? contrastFormElement.querySelector("[data-omni-contrast-role='contrast-scenario']")
            : null;
        var contrastRunButton = contrastFormElement
            ? contrastFormElement.querySelector("[data-omni-contrast-action='run-contrasts']")
            : null;
        var contrastGeojsonInput = contrastFormElement
            ? contrastFormElement.querySelector("input[name='omni_contrast_geojson']")
            : null;
        var contrastGeojsonPathInput = contrastFormElement
            ? contrastFormElement.querySelector("input[name='omni_contrast_geojson_path']")
            : null;
        var contrastHillslopeGroupsInput = contrastFormElement
            ? contrastFormElement.querySelector(
                "textarea[name='omni_contrast_hillslope_groups'], input[name='omni_contrast_hillslope_groups']"
            )
            : null;
        var contrastHillslopeLimitInput = contrastFormElement
            ? contrastFormElement.querySelector("input[name='omni_contrast_hillslope_limit']")
            : null;
        var contrastOrderReductionInput = contrastFormElement
            ? contrastFormElement.querySelector("input[name='order_reduction_passes']")
            : null;
        var contrastPairsInput = contrastFormElement
            ? contrastFormElement.querySelector("[data-omni-contrast-role='pairs']")
            : null;
        var contrastPairContainer = contrastFormElement
            ? contrastFormElement.querySelector("[data-omni-contrast-role='pair-container']")
            : null;
        var contrastDryRunButton = contrastFormElement
            ? contrastFormElement.querySelector("[data-omni-contrast-action='dry-run']")
            : null;
        var contrastDeleteModal = dom.qs("#omni-contrasts-delete-modal");
        var contrastDeleteModalConfirm = contrastDeleteModal
            ? contrastDeleteModal.querySelector("[data-omni-contrast-action='confirm-delete-contrasts']")
            : null;
        var contrastOutputInputs = contrastFormElement ? {
            ebe: contrastFormElement.querySelector("input[name='omni_contrast_output_ebe_pw0']"),
            chanOut: contrastFormElement.querySelector("input[name='omni_contrast_output_chan_out']"),
            tcrOut: contrastFormElement.querySelector("input[name='omni_contrast_output_tcr_out']"),
            chnwb: contrastFormElement.querySelector("input[name='omni_contrast_output_chnwb']"),
            soil: contrastFormElement.querySelector("input[name='omni_contrast_output_soil_pw0']"),
            plot: contrastFormElement.querySelector("input[name='omni_contrast_output_plot_pw0']")
        } : null;

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
        omni._completion_seen = false;

        var contrastController = null;
        var contrastInfoAdapter = null;
        var contrastStatusAdapter = null;
        var contrastStacktraceAdapter = null;
        var contrastRqJobAdapter = null;
        var contrastHintAdapter = null;

        if (contrastFormElement) {
            var contrastInfoElement = dom.qs("#omni_contrasts_form #info");
            var contrastStatusElement = dom.qs("#omni_contrasts_form #status");
            var contrastStacktraceElement = dom.qs("#omni_contrasts_form #stacktrace");
            var contrastRqJobElement = dom.qs("#omni_contrasts_form #rq_job");
            var contrastSpinnerElement = dom.qs("#omni_contrasts_form #braille");
            var contrastHintElement = dom.qs("#hint_run_omni_contrasts");

            contrastInfoAdapter = createLegacyAdapter(contrastInfoElement);
            contrastStatusAdapter = createLegacyAdapter(contrastStatusElement);
            contrastStacktraceAdapter = createLegacyAdapter(contrastStacktraceElement);
            contrastRqJobAdapter = createLegacyAdapter(contrastRqJobElement);
            contrastHintAdapter = createLegacyAdapter(contrastHintElement);

            contrastController = controlBase();
            contrastController.form = contrastFormElement;
            contrastController.info = contrastInfoAdapter;
            contrastController.status = contrastStatusAdapter;
            contrastController.stacktrace = contrastStacktraceAdapter;
            contrastController.rq_job = contrastRqJobAdapter;
            contrastController.statusSpinnerEl = contrastSpinnerElement;
            contrastController.command_btn_id = "btn_run_omni_contrasts";
            contrastController.hint = contrastHintAdapter;
            contrastController._completion_seen = false;

            contrastController.attach_status_stream(contrastController, {
                form: contrastFormElement,
                channel: "omni_contrasts",
                runId: window.runid || window.runId || null,
                spinner: contrastSpinnerElement
            });

            omni.contrastController = contrastController;
        }

        var contrastScenarioOptions = null;
        var contrastPairsInitialized = false;
        var contrastPairRunMarkers = null;

        omni.attach_status_stream(omni, {
            form: formElement,
            channel: "omni",
            runId: window.runid || window.runId || null,
            spinner: spinnerElement
        });

        function resetCompletionSeen() {
            omni._completion_seen = false;
        }

        var baseTriggerEvent = omni.triggerEvent.bind(omni);
        omni.triggerEvent = function (eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === "OMNI_SCENARIO_RUN_TASK_COMPLETED") {
                if (omni._completion_seen) {
                    return baseTriggerEvent(eventName, payload);
                }
                omni._completion_seen = true;
                omni.report_scenarios();
                if (typeof omni.load_scenarios_from_backend === "function") {
                    omni.load_scenarios_from_backend();
                }
                loadContrastPairRunMarkers();
                omni.disconnect_status_stream(omni);
                if (omniEvents && typeof omniEvents.emit === "function") {
                    omniEvents.emit("omni:run:completed", payload || {});
                }
            } else if (normalized === "END_BROADCAST") {
                omni.disconnect_status_stream(omni);
            }

            return baseTriggerEvent(eventName, payload);
        };

        if (contrastController) {
            var baseContrastTriggerEvent = contrastController.triggerEvent.bind(contrastController);
            contrastController.triggerEvent = function (eventName, payload) {
                var normalized = eventName ? String(eventName).toUpperCase() : "";
                if (normalized === CONTRAST_COMPLETION_EVENT) {
                    if (typeof omni.report_contrasts === "function") {
                        omni.report_contrasts();
                    } else if (contrastInfoAdapter && typeof contrastInfoAdapter.html === "function") {
                        contrastInfoAdapter.html("Omni contrasts completed.");
                    }
                    if (omniEvents && typeof omniEvents.emit === "function") {
                        omniEvents.emit("omni:contrast:run:completed", payload || {});
                    }
                } else if (normalized === CONTRAST_DELETE_COMPLETION_EVENT) {
                    clearContrastSummary();
                    setContrastStatus("Contrasts deleted.");
                } else if (normalized === "END_BROADCAST") {
                    contrastController.disconnect_status_stream(contrastController);
                }

                return baseContrastTriggerEvent(eventName, payload);
            };
        }

        function emitScenarioUpdate(scenarioItem) {
            if (!omniEvents || typeof omniEvents.emit !== "function") {
                return;
            }
            var definition = readScenarioDefinition(scenarioItem);
            syncScenarioSelectionState(scenarioItem, definition);
            updateDeleteButtonState();
            omniEvents.emit("omni:scenario:updated", {
                scenario: definition,
                element: scenarioItem
            });
        }

        function syncScenarioSelectionState(scenarioItem, definition) {
            if (!scenarioItem) {
                return;
            }
            var checkbox = scenarioItem.querySelector("[data-omni-role='scenario-select-toggle']");
            var scenarioName = scenarioNameFromDefinition(definition || readScenarioDefinition(scenarioItem));
            scenarioItem.dataset.omniScenarioName = scenarioName || "";
            if (!checkbox) {
                return;
            }
            var enabled = Boolean(scenarioName);
            checkbox.disabled = !enabled;
            if (!enabled) {
                checkbox.checked = false;
            }
        }

        function collectSelectedScenarios() {
            var items = scenarioContainer.querySelectorAll("[data-omni-scenario-item='true']");
            var selections = [];
            items.forEach(function (item) {
                var checkbox = item.querySelector("[data-omni-role='scenario-select-toggle']");
                if (!checkbox || checkbox.disabled || !checkbox.checked) {
                    return;
                }
                var definition = readScenarioDefinition(item);
                var scenarioName = scenarioNameFromDefinition(definition);
                if (scenarioName) {
                    selections.push({
                        item: item,
                        name: scenarioName,
                        definition: definition
                    });
                }
            });
            return selections;
        }

        function updateDeleteButtonState() {
            if (!deleteButton) {
                return;
            }
            var selections = collectSelectedScenarios();
            deleteButton.disabled = selections.length === 0;
        }

        function openDeleteModal() {
            var selections = collectSelectedScenarios();
            if (selections.length === 0) {
                setStatus("Select at least one scenario to delete.");
                return;
            }
            if (!deleteModal || !deleteModalList) {
                setStatus("Delete dialog unavailable.");
                return;
            }
            deleteModalList.innerHTML = "";
            selections.forEach(function (selection) {
                var li = deleteModal.ownerDocument.createElement("li");
                li.textContent = selection.name || "Scenario";
                deleteModalList.appendChild(li);
            });
            pendingDeleteSelections = selections;
            openModal(deleteModal);
        }

        function pruneDeletedScenarios(removedNames) {
            if (!removedNames || removedNames.length === 0) {
                return;
            }
            var removedSet = new Set(removedNames.map(function (name) {
                return String(name);
            }));
            var items = scenarioContainer.querySelectorAll("[data-omni-scenario-item='true']");
            items.forEach(function (item) {
                var scenarioName = item.dataset.omniScenarioName;
                if (scenarioName && removedSet.has(scenarioName)) {
                    item.remove();
                    if (omniEvents && typeof omniEvents.emit === "function") {
                        omniEvents.emit("omni:scenario:removed", {
                            scenario: scenarioName,
                            element: item
                        });
                    }
                }
            });
        }

        function confirmDeleteSelected() {
            if (!pendingDeleteSelections.length) {
                closeModal(deleteModal);
                return;
            }
            var names = pendingDeleteSelections
                .map(function (entry) { return entry.name; })
                .filter(Boolean);
            if (!names.length) {
                closeModal(deleteModal);
                return;
            }

            setStatus("Deleting selected scenarios...");
            if (deleteModalConfirm) {
                deleteModalConfirm.disabled = true;
            }

            http.postJson(url_for_run("api/omni/delete_scenarios"), { scenario_names: names }, { form: formElement })
                .then(function (response) {
                    var body = response && response.body ? response.body : {};
                    var content = body && body.Content ? body.Content : {};
                    var removed = Array.isArray(content.removed) ? content.removed : [];
                    var missing = Array.isArray(content.missing) ? content.missing : [];

                    if (removed.length) {
                        pruneDeletedScenarios(removed);
                    }

                    refreshScenarioOptions();
                    updateDeleteButtonState();

                    var parts = [];
                    if (removed.length) {
                        parts.push("Removed " + removed.length + " scenario(s).");
                    }
                    if (missing.length) {
                        parts.push("Missing: " + missing.join(", "));
                    }
                    setStatus(parts.join(" ") || "No scenarios deleted.");
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    omni.pushResponseStacktrace(omni, payload);
                    setStatus(resolveErrorMessage(payload, "Failed to delete scenarios."));
                    if (omniEvents && typeof omniEvents.emit === "function") {
                        omniEvents.emit("omni:run:error", { error: error });
                    }
                })
                .finally(function () {
                    pendingDeleteSelections = [];
                    if (deleteModalConfirm) {
                        deleteModalConfirm.disabled = false;
                    }
                    closeModal(deleteModal);
                });
        }

        function openContrastDeleteModal() {
            if (!contrastDeleteModal) {
                setContrastStatus("Delete dialog unavailable.");
                return;
            }
            openModal(contrastDeleteModal);
        }

        function confirmDeleteContrasts() {
            if (!contrastFormElement) {
                return;
            }
            setContrastStatus("Deleting contrasts...");
            clearContrastSummary();

            if (contrastDeleteModalConfirm) {
                contrastDeleteModalConfirm.disabled = true;
            }

            if (contrastController && typeof contrastController.connect_status_stream === "function") {
                contrastController.connect_status_stream(contrastController);
            }

            http.requestWithSessionToken(
                url_for_run("delete-omni-contrasts", { prefix: "/rq-engine/api" }),
                {
                    method: "POST",
                    form: contrastFormElement
                }
            )
                .then(function (response) {
                    var body = response && response.body ? response.body : null;
                    if (body && (body.error || body.errors)) {
                        contrastController.pushResponseStacktrace(contrastController, body);
                        setContrastStatus(resolveErrorMessage(body, "Failed to delete contrasts."));
                        return;
                    }
                    var jobId = null;
                    if (body) {
                        if (body.job_id) {
                            jobId = body.job_id;
                        } else if (body.result && body.result.job_id) {
                            jobId = body.result.job_id;
                        } else if (body.Content && body.Content.job_id) {
                            jobId = body.Content.job_id;
                        }
                    }

                    if (jobId) {
                        setContrastStatus("delete_omni_contrasts_rq job submitted: " + jobId);
                        if (contrastController) {
                            contrastController.poll_completion_event = CONTRAST_DELETE_COMPLETION_EVENT;
                            if (typeof contrastController.set_rq_job_id === "function") {
                                contrastController.set_rq_job_id(contrastController, jobId);
                            }
                        }
                        if (contrastHintAdapter && typeof contrastHintAdapter.html === "function") {
                            contrastHintAdapter.html(formatJobHint(jobId));
                            if (typeof contrastHintAdapter.show === "function") {
                                contrastHintAdapter.show();
                            }
                        }
                        return;
                    }

                    var message = body && body.message ? body.message : "Contrasts deleted.";
                    setContrastStatus(message);
                    if (contrastInfoAdapter && typeof contrastInfoAdapter.html === "function") {
                        contrastInfoAdapter.html("");
                    }
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    contrastController.pushResponseStacktrace(contrastController, payload);
                    setContrastStatus(resolveErrorMessage(payload, "Failed to delete contrasts."));
                })
                .finally(function () {
                    if (contrastDeleteModalConfirm) {
                        contrastDeleteModalConfirm.disabled = false;
                    }
                    closeModal(contrastDeleteModal);
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
            updateContrastScenarioOptions();
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

            syncScenarioSelectionState(scenarioItem, values || readScenarioDefinition(scenarioItem));
        }

        function addScenario(prefill, options) {
            var opts = options || {};
            var scenarioItem = formElement.ownerDocument.createElement("div");
            scenarioItem.className = "scenario-item wc-card wc-card--subtle";
            scenarioItem.dataset.index = String(scenarioCounter++);
            scenarioItem.dataset.omniScenarioItem = "true";
            scenarioItem.innerHTML = [
                '<div class="wc-card__body scenario-item__body">',
                '  <div class="scenario-item__inputs">',
                '    <label class="scenario-item__selector" aria-label="Select scenario for deletion">',
                '      <input type="checkbox"',
                '             class="disable-readonly"',
                '             data-omni-role="scenario-select-toggle"',
                '             title="Select scenario for deletion" />',
                '    </label>',
                '    <div class="wc-field scenario-item__field">',
                '      <label class="wc-field__label" for="omni_scenario_' + scenarioItem.dataset.index + '">Scenario</label>',
                '      <select class="wc-field__control"',
                '              id="omni_scenario_' + scenarioItem.dataset.index + '"',
                '              name="scenario"',
                '              data-omni-role="scenario-select">',
                '        <option value="">Select scenario</option>',
                '      </select>',
                '    </div>',
                '    <div class="scenario-controls scenario-item__controls" data-omni-scenario-controls></div>',
                '  </div>',
                '  <div class="scenario-item__actions">',
                '    <button type="button" class="pure-button button-error disable-readonly" data-omni-action="remove-scenario">',
                '      Remove',
                '    </button>',
                '  </div>',
                '</div>'
            ].join("\n");

            scenarioContainer.appendChild(scenarioItem);

            var select = scenarioItem.querySelector("[data-omni-role='scenario-select']");
            populateScenarioSelect(select, scenarioContainer);

            if (prefill && prefill.type) {
                select.value = prefill.type;
            }
            updateScenarioControls(scenarioItem, prefill || null);
            syncScenarioSelectionState(scenarioItem, prefill || readScenarioDefinition(scenarioItem));
            updateDeleteButtonState();

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
            updateDeleteButtonState();

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
            if (stacktraceAdapter && typeof stacktraceAdapter.html === "function") {
                stacktraceAdapter.html("");
            }
        }

        function clearSummary() {
            if (infoAdapter && typeof infoAdapter.html === "function") {
                infoAdapter.html("");
            }
        }

        function setStatus(message) {
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(message || "");
            }
        }

        function clearContrastStatus() {
            if (contrastStatusAdapter && typeof contrastStatusAdapter.html === "function") {
                contrastStatusAdapter.html("");
            }
            if (contrastStacktraceAdapter && typeof contrastStacktraceAdapter.html === "function") {
                contrastStacktraceAdapter.html("");
            }
        }

        function clearContrastSummary() {
            if (contrastInfoAdapter && typeof contrastInfoAdapter.html === "function") {
                contrastInfoAdapter.html("");
            }
        }

        function setContrastStatus(message) {
            if (contrastStatusAdapter && typeof contrastStatusAdapter.html === "function") {
                contrastStatusAdapter.html(message || "");
            }
        }

        function escapeHtml(value) {
            var text = value === undefined || value === null ? "" : String(value);
            return text.replace(/[&<>"']/g, function (match) {
                return {
                    "&": "&amp;",
                    "<": "&lt;",
                    ">": "&gt;",
                    '"': "&quot;",
                    "'": "&#39;"
                }[match] || match;
            });
        }

        function runStatusLabel(status) {
            if (!status) {
                return "unknown";
            }
            return String(status).replace(/_/g, " ");
        }

        function runStatusState(status) {
            var token = status ? String(status) : "";
            if (token === "up_to_date") {
                return "success";
            }
            if (token === "needs_run") {
                return "warning";
            }
            if (token === "skipped") {
                return "attention";
            }
            return "info";
        }

        function formatRunStatusChip(status) {
            var label = runStatusLabel(status);
            var state = runStatusState(status);
            return '<span class="wc-status-chip" data-state="' + state + '">' + escapeHtml(label) + "</span>";
        }

        function formatSkipStatus(skipStatus) {
            if (!skipStatus || !skipStatus.skipped) {
                return "-";
            }
            var reason = skipStatus.reason ? String(skipStatus.reason) : "";
            if (!reason) {
                return "Skipped";
            }
            return 'Skipped <span class="wc-text-muted">(Reason: ' + escapeHtml(reason) + ")</span>";
        }

        function clampContrastHillslopeLimit() {
            if (!contrastHillslopeLimitInput) {
                return;
            }
            var mode = resolveContrastMode();
            if (mode !== CONTRAST_SELECTION_MODES.cumulative) {
                return;
            }
            var rawValue = contrastHillslopeLimitInput.value;
            if (!rawValue) {
                return;
            }
            var parsed = parseInt(rawValue, 10);
            if (!Number.isFinite(parsed)) {
                return;
            }
            if (parsed > CONTRAST_HILLSLOPE_LIMIT_MAX) {
                contrastHillslopeLimitInput.value = String(CONTRAST_HILLSLOPE_LIMIT_MAX);
                setContrastStatus("Hillslope limit capped at " + CONTRAST_HILLSLOPE_LIMIT_MAX + " for cumulative mode.");
            }
        }

        function renderContrastDryRunReport(report) {
            if (!contrastInfoAdapter || typeof contrastInfoAdapter.html !== "function") {
                return;
            }
            if (!report || !report.items) {
                contrastInfoAdapter.html('<p class="wc-text-muted">No contrasts available for dry run.</p>');
                return;
            }

            var selectionMode = normalizeContrastMode(report.selection_mode || "");
            var items = Array.isArray(report.items) ? report.items : [];
            if (!items.length) {
                contrastInfoAdapter.html('<p class="wc-text-muted">No contrasts available for dry run.</p>');
                return;
            }

            var columns = [];
            if (selectionMode === CONTRAST_SELECTION_MODES.user_defined_areas) {
                columns = [
                    { key: "contrast_id", label: "Contrast" },
                    { key: "control_scenario", label: "Control" },
                    { key: "contrast_scenario", label: "Contrast" },
                    { key: "area_label", label: "Area" },
                    { key: "n_hillslopes", label: "Hillslopes" },
                    { key: "skip_status", label: "Skip status" },
                    { key: "run_status", label: "Run status" }
                ];
            } else if (selectionMode === CONTRAST_SELECTION_MODES.user_defined_hillslope_groups) {
                columns = [
                    { key: "contrast_id", label: "Contrast" },
                    { key: "control_scenario", label: "Control" },
                    { key: "contrast_scenario", label: "Contrast" },
                    { key: "group_index", label: "Group" },
                    { key: "n_hillslopes", label: "Hillslopes" },
                    { key: "skip_status", label: "Skip status" },
                    { key: "run_status", label: "Run status" }
                ];
            } else if (selectionMode === CONTRAST_SELECTION_MODES.stream_order) {
                columns = [
                    { key: "contrast_id", label: "Contrast" },
                    { key: "control_scenario", label: "Control" },
                    { key: "contrast_scenario", label: "Contrast" },
                    { key: "subcatchments_group", label: "Subcatchments group" },
                    { key: "n_hillslopes", label: "Hillslopes" },
                    { key: "skip_status", label: "Skip status" },
                    { key: "run_status", label: "Run status" }
                ];
            } else {
                columns = [
                    { key: "contrast_id", label: "Contrast" },
                    { key: "topaz_id", label: "Topaz ID" },
                    { key: "skip_status", label: "Skip status" },
                    { key: "run_status", label: "Run status" }
                ];
            }

            var headerCells = columns.map(function (column) {
                return "<th>" + escapeHtml(column.label) + "</th>";
            }).join("");

            var bodyRows = items.map(function (item) {
                var cells = columns.map(function (column) {
                    var value = item ? item[column.key] : "";
                    if (column.key === "run_status") {
                        return "<td>" + formatRunStatusChip(value) + "</td>";
                    }
                    if (column.key === "skip_status") {
                        return "<td>" + formatSkipStatus(value) + "</td>";
                    }
                    return "<td>" + escapeHtml(value === undefined || value === null ? "-" : value) + "</td>";
                }).join("");
                return "<tr>" + cells + "</tr>";
            }).join("");

            var html = [
                '<div class="wc-stack">',
                '<p class="wc-text-muted">Dry run results (' + escapeHtml(selectionMode || "cumulative") + ').</p>',
                '<div class="wc-table-wrapper wc-table-wrapper--compact">',
                '<table class="wc-table wc-table--dense wc-table--compact">',
                "<thead><tr>" + headerCells + "</tr></thead>",
                "<tbody>" + bodyRows + "</tbody>",
                "</table>",
                "</div>",
                "</div>"
            ].join("");

            contrastInfoAdapter.html(html);
        }

        function normalizeContrastMode(value) {
            var token = value ? String(value).trim().toLowerCase() : "";
            if (token === "user-defined-areas" || token === "user_defined_areas") {
                return CONTRAST_SELECTION_MODES.user_defined_areas;
            }
            if (
                token === "user-defined-hillslope-groups"
                || token === "user-defined-hillslope-group"
                || token === "user_defined_hillslope_groups"
            ) {
                return CONTRAST_SELECTION_MODES.user_defined_hillslope_groups;
            }
            if (
                token === "stream-order-pruning"
                || token === "stream_order_pruning"
                || token === "stream_order"
            ) {
                return CONTRAST_SELECTION_MODES.stream_order;
            }
            return CONTRAST_SELECTION_MODES.cumulative;
        }

        function resolveContrastMode() {
            var rawValue = "";
            if (contrastFormElement) {
                var checked = contrastFormElement.querySelector(
                    "input[name='omni_contrast_selection_mode']:checked"
                );
                if (checked && checked.value) {
                    rawValue = checked.value;
                }
            }
            if (!rawValue && contrastModeSelect && contrastModeSelect.value) {
                rawValue = contrastModeSelect.value;
            }
            return normalizeContrastMode(rawValue);
        }

        function isStreamOrderAllowed() {
            if (!contrastStreamOrderInput) {
                return true;
            }
            return !contrastStreamOrderInput.disabled;
        }

        function resolveBaseScenarioOption() {
            var runFlags = window.runContext && window.runContext.flags ? window.runContext.flags : null;
            var hasSbs = runFlags ? Boolean(runFlags.initialHasSbs) : false;
            return {
                value: hasSbs ? "sbs_map" : "undisturbed",
                label: hasSbs ? "Base Scenario (SBS Map)" : "Base Scenario (Undisturbed)"
            };
        }

        function buildContrastScenarioOptions(definitions) {
            var options = [{ value: "", label: "Select scenario" }];
            var baseOption = resolveBaseScenarioOption();
            var seen = new Set();
            if (baseOption && baseOption.value) {
                options.push(baseOption);
                seen.add(baseOption.value);
            }

            (definitions || []).forEach(function (definition) {
                var scenarioName = scenarioNameFromDefinition(definition);
                if (!scenarioName || seen.has(scenarioName)) {
                    return;
                }
                seen.add(scenarioName);
                options.push({ value: scenarioName, label: scenarioName });
            });

            return options;
        }

        function collectScenarioDefinitions() {
            if (!scenarioContainer) {
                return [];
            }
            var items = scenarioContainer.querySelectorAll("[data-omni-scenario-item='true']");
            var definitions = [];
            items.forEach(function (item) {
                var definition = readScenarioDefinition(item);
                if (definition) {
                    definitions.push(definition);
                }
            });
            return definitions;
        }

        function parseContrastPairsInput() {
            if (!contrastPairsInput) {
                return [];
            }
            var raw = contrastPairsInput.value;
            if (!raw) {
                return [];
            }
            try {
                var parsed = JSON.parse(raw);
                if (!Array.isArray(parsed)) {
                    return [];
                }
                return parsed
                    .map(function (entry) {
                        if (!entry || typeof entry !== "object") {
                            return null;
                        }
                        var control = entry.control_scenario;
                        var contrast = entry.contrast_scenario;
                        if (!control || !contrast) {
                            return null;
                        }
                        return {
                            control_scenario: String(control),
                            contrast_scenario: String(contrast)
                        };
                    })
                    .filter(Boolean);
            } catch (err) {
                return [];
            }
        }

        function getContrastPairRows() {
            if (!contrastPairContainer) {
                return [];
            }
            return Array.prototype.slice.call(
                contrastPairContainer.querySelectorAll("[data-omni-contrast-pair-item='true']")
            );
        }

        function setContrastPairRowError(row, message) {
            if (!row) {
                return;
            }
            var errorEl = row.querySelector("[data-omni-contrast-pair-role='error']");
            if (!errorEl) {
                return;
            }
            if (!message) {
                errorEl.textContent = "";
                errorEl.hidden = true;
                return;
            }
            errorEl.textContent = message;
            errorEl.hidden = false;
        }

        function collectContrastPairs() {
            var rows = getContrastPairRows();
            var pairs = [];
            var seen = new Set();
            rows.forEach(function (row) {
                var control = row.querySelector("[data-omni-contrast-pair-field='control']");
                var contrast = row.querySelector("[data-omni-contrast-pair-field='contrast']");
                var controlValue = control && control.value ? String(control.value).trim() : "";
                var contrastValue = contrast && contrast.value ? String(contrast.value).trim() : "";
                if (!controlValue || !contrastValue) {
                    return;
                }
                var key = controlValue + "::" + contrastValue;
                if (seen.has(key)) {
                    return;
                }
                seen.add(key);
                pairs.push({
                    control_scenario: controlValue,
                    contrast_scenario: contrastValue
                });
            });
            return pairs;
        }

        function syncContrastPairsInput() {
            if (!contrastPairsInput) {
                return;
            }
            var pairs = collectContrastPairs();
            contrastPairsInput.value = JSON.stringify(pairs);
        }

        function applyContrastPairOptions(select, options) {
            if (!select) {
                return;
            }
            var saved = select.dataset ? select.dataset.omniContrastPairSelected : "";
            var savedApplied = select.dataset
                ? select.dataset.omniContrastPairSelectedApplied === "true"
                : false;
            var previous = select.value;
            if (!previous && saved && !savedApplied) {
                previous = saved;
            }
            select.innerHTML = "";
            options.forEach(function (option) {
                var node = document.createElement("option");
                node.value = option.value;
                var label = option.label;
                if (
                    contrastPairRunMarkers
                    && option.value
                    && contrastPairRunMarkers[option.value] === false
                ) {
                    label = option.label + " (not run)";
                }
                node.textContent = label;
                select.appendChild(node);
            });
            if (previous && options.some(function (opt) { return opt.value === previous; })) {
                select.value = previous;
                if (saved && previous === saved && select.dataset) {
                    select.dataset.omniContrastPairSelectedApplied = "true";
                }
            }
        }

        function updateContrastPairOptions(options) {
            if (!contrastPairContainer) {
                return;
            }
            getContrastPairRows().forEach(function (row) {
                var controlSelect = row.querySelector("[data-omni-contrast-pair-field='control']");
                var contrastSelect = row.querySelector("[data-omni-contrast-pair-field='contrast']");
                applyContrastPairOptions(controlSelect, options);
                applyContrastPairOptions(contrastSelect, options);
            });
            updateContrastActionState();
        }

        function createContrastPairRow(pair) {
            var row = document.createElement("div");
            row.className = "contrast-pair-item scenario-item wc-card wc-card--subtle";
            row.dataset.omniContrastPairItem = "true";
            row.innerHTML = [
                '<div class="wc-card__body wc-stack">',
                '  <div class="scenario-item__body contrast-pair-item__body">',
                '    <div class="scenario-item__inputs contrast-pair-item__inputs">',
                '      <span class="scenario-item__selector" aria-hidden="true"></span>',
                '      <div class="wc-field scenario-item__field">',
                '        <label class="wc-field__label">Control scenario</label>',
                '        <select class="wc-field__control" data-omni-contrast-pair-field="control"></select>',
                '      </div>',
                '      <div class="wc-field scenario-item__field">',
                '        <label class="wc-field__label">Contrast scenario</label>',
                '        <select class="wc-field__control" data-omni-contrast-pair-field="contrast"></select>',
                '      </div>',
                '      <div class="contrast-pair-item__placeholder" aria-hidden="true"></div>',
                '    </div>',
                '    <div class="scenario-item__actions">',
                '      <button type="button" class="pure-button button-error disable-readonly" data-omni-contrast-action="remove-pair">Remove</button>',
                '    </div>',
                '  </div>',
                '  <p class="wc-field__help wc-text-muted" data-omni-contrast-pair-role="error" hidden></p>',
                '</div>'
            ].join("");

            var controlSelect = row.querySelector("[data-omni-contrast-pair-field='control']");
            var contrastSelect = row.querySelector("[data-omni-contrast-pair-field='contrast']");
            if (controlSelect && pair && pair.control_scenario) {
                controlSelect.dataset.omniContrastPairSelected = String(pair.control_scenario);
            }
            if (contrastSelect && pair && pair.contrast_scenario) {
                contrastSelect.dataset.omniContrastPairSelected = String(pair.contrast_scenario);
            }
            return row;
        }

        function addContrastPairRow(pair) {
            if (!contrastPairContainer) {
                return;
            }
            var row = createContrastPairRow(pair || {});
            contrastPairContainer.appendChild(row);
            if (contrastScenarioOptions) {
                updateContrastPairOptions(contrastScenarioOptions);
            }
        }

        function ensureContrastPairsInitialized() {
            if (contrastPairsInitialized || !contrastPairContainer) {
                return;
            }
            contrastPairsInitialized = true;
            var pairs = parseContrastPairsInput();
            if (!pairs.length) {
                addContrastPairRow();
            } else {
                pairs.forEach(function (pair) {
                    addContrastPairRow(pair);
                });
            }
            syncContrastPairsInput();
            validateContrastPairs();
        }

        function validateContrastPairs() {
            if (!contrastPairContainer) {
                return true;
            }
            var rows = getContrastPairRows();
            if (!rows.length) {
                return false;
            }
            var pairMap = new Map();
            rows.forEach(function (row) {
                var control = row.querySelector("[data-omni-contrast-pair-field='control']");
                var contrast = row.querySelector("[data-omni-contrast-pair-field='contrast']");
                var controlValue = control && control.value ? String(control.value).trim() : "";
                var contrastValue = contrast && contrast.value ? String(contrast.value).trim() : "";
                if (!controlValue || !contrastValue) {
                    return;
                }
                var key = controlValue + "::" + contrastValue;
                var entries = pairMap.get(key) || [];
                entries.push(row);
                pairMap.set(key, entries);
            });

            var hasErrors = false;
            rows.forEach(function (row) {
                var control = row.querySelector("[data-omni-contrast-pair-field='control']");
                var contrast = row.querySelector("[data-omni-contrast-pair-field='contrast']");
                var controlValue = control && control.value ? String(control.value).trim() : "";
                var contrastValue = contrast && contrast.value ? String(contrast.value).trim() : "";
                var blockingMessage = "";
                var warningMessage = "";
                if (!controlValue || !contrastValue) {
                    blockingMessage = "Select both control and contrast scenarios.";
                } else {
                    var key = controlValue + "::" + contrastValue;
                    if (pairMap.get(key) && pairMap.get(key).length > 1) {
                        blockingMessage = "Duplicate pair.";
                    } else if (contrastPairRunMarkers && contrastPairRunMarkers[controlValue] === false) {
                        warningMessage = "Control scenario has not run.";
                    } else if (contrastPairRunMarkers && contrastPairRunMarkers[contrastValue] === false) {
                        warningMessage = "Contrast scenario has not run.";
                    }
                }
                setContrastPairRowError(row, blockingMessage || warningMessage);
                if (blockingMessage) {
                    hasErrors = true;
                }
            });

            syncContrastPairsInput();
            return !hasErrors && collectContrastPairs().length > 0;
        }

        function loadContrastPairRunMarkers() {
            if (!contrastFormElement) {
                return;
            }
            http.getJson(url_for_run("api/omni/get_scenario_run_state")).then(function (data) {
                contrastPairRunMarkers = data && data.run_markers ? data.run_markers : {};
                if (contrastScenarioOptions) {
                    updateContrastPairOptions(contrastScenarioOptions);
                }
            }).catch(function () {
                contrastPairRunMarkers = null;
                if (contrastScenarioOptions) {
                    updateContrastPairOptions(contrastScenarioOptions);
                }
            });
        }

        function getContrastGeojsonPath() {
            if (!contrastGeojsonPathInput) {
                return "";
            }
            var value = contrastGeojsonPathInput.value;
            return value ? String(value).trim() : "";
        }

        function hasContrastGeojson() {
            var fileList = contrastGeojsonInput ? contrastGeojsonInput.files : null;
            if (fileList && fileList.length) {
                return true;
            }
            var path = getContrastGeojsonPath();
            return Boolean(path);
        }

        function hasContrastHillslopeGroups() {
            if (!contrastHillslopeGroupsInput) {
                return false;
            }
            var value = contrastHillslopeGroupsInput.value;
            return Boolean(value && String(value).trim());
        }

        function validateOrderReductionPasses() {
            if (!contrastOrderReductionInput) {
                return true;
            }
            var raw = contrastOrderReductionInput.value;
            if (!raw) {
                contrastOrderReductionInput.value = "1";
                return true;
            }
            var parsed = Number(raw);
            if (!Number.isFinite(parsed)) {
                return false;
            }
            if (Math.floor(parsed) !== parsed) {
                return false;
            }
            return parsed >= 1;
        }

        function collectContrastOutputOptions() {
            var defaults = {
                omni_contrast_output_ebe_pw0: true,
                omni_contrast_output_chan_out: false,
                omni_contrast_output_tcr_out: false,
                omni_contrast_output_chnwb: false,
                omni_contrast_output_soil_pw0: false,
                omni_contrast_output_plot_pw0: false
            };
            if (!contrastOutputInputs) {
                return defaults;
            }
            return {
                omni_contrast_output_ebe_pw0: contrastOutputInputs.ebe ? contrastOutputInputs.ebe.checked : defaults.omni_contrast_output_ebe_pw0,
                omni_contrast_output_chan_out: contrastOutputInputs.chanOut ? contrastOutputInputs.chanOut.checked : defaults.omni_contrast_output_chan_out,
                omni_contrast_output_tcr_out: contrastOutputInputs.tcrOut ? contrastOutputInputs.tcrOut.checked : defaults.omni_contrast_output_tcr_out,
                omni_contrast_output_chnwb: contrastOutputInputs.chnwb ? contrastOutputInputs.chnwb.checked : defaults.omni_contrast_output_chnwb,
                omni_contrast_output_soil_pw0: contrastOutputInputs.soil ? contrastOutputInputs.soil.checked : defaults.omni_contrast_output_soil_pw0,
                omni_contrast_output_plot_pw0: contrastOutputInputs.plot ? contrastOutputInputs.plot.checked : defaults.omni_contrast_output_plot_pw0
            };
        }

        function appendContrastOutputOptions(formData) {
            if (!formData || typeof formData.set !== "function") {
                return;
            }
            var options = collectContrastOutputOptions();
            Object.keys(options).forEach(function (key) {
                formData.set(key, options[key] ? "true" : "false");
            });
        }

        function updateContrastActionState() {
            var mode = resolveContrastMode();
            var streamOrderAllowed = mode !== CONTRAST_SELECTION_MODES.stream_order || isStreamOrderAllowed();
            var canRunMode = (
                mode === CONTRAST_SELECTION_MODES.cumulative
                || mode === CONTRAST_SELECTION_MODES.user_defined_areas
                || mode === CONTRAST_SELECTION_MODES.user_defined_hillslope_groups
                || mode === CONTRAST_SELECTION_MODES.stream_order
            ) && streamOrderAllowed;
            var hasGeojson = mode !== CONTRAST_SELECTION_MODES.user_defined_areas || hasContrastGeojson();
            var hasGroups = mode !== CONTRAST_SELECTION_MODES.user_defined_hillslope_groups || hasContrastHillslopeGroups();
            var pairsValid = true;
            if (
                mode === CONTRAST_SELECTION_MODES.user_defined_areas
                || mode === CONTRAST_SELECTION_MODES.user_defined_hillslope_groups
                || mode === CONTRAST_SELECTION_MODES.stream_order
            ) {
                ensureContrastPairsInitialized();
                pairsValid = validateContrastPairs();
            }
            var orderPassesValid = true;
            if (mode === CONTRAST_SELECTION_MODES.stream_order) {
                orderPassesValid = validateOrderReductionPasses();
            }
            var canSubmit = canRunMode
                && (mode !== CONTRAST_SELECTION_MODES.user_defined_areas || (pairsValid && hasGeojson))
                && (mode !== CONTRAST_SELECTION_MODES.user_defined_hillslope_groups || (pairsValid && hasGroups))
                && (mode !== CONTRAST_SELECTION_MODES.stream_order || (pairsValid && orderPassesValid));
            if (contrastRunButton) {
                contrastRunButton.disabled = !canSubmit;
            }
            if (contrastDryRunButton) {
                contrastDryRunButton.disabled = !canSubmit;
            }
            return {
                mode: mode,
                canRunMode: canRunMode,
                hasGeojson: hasGeojson,
                hasGroups: hasGroups,
                pairsValid: pairsValid,
                orderPassesValid: orderPassesValid,
                canSubmit: canSubmit
            };
        }

        function updateContrastScenarioOptions(definitions) {
            var options = buildContrastScenarioOptions(definitions || collectScenarioDefinitions());
            contrastScenarioOptions = options;
            var mode = resolveContrastMode();
            if (
                mode === CONTRAST_SELECTION_MODES.user_defined_areas
                || mode === CONTRAST_SELECTION_MODES.user_defined_hillslope_groups
                || mode === CONTRAST_SELECTION_MODES.stream_order
            ) {
                ensureContrastPairsInitialized();
            }
            var selects = [contrastControlSelect, contrastScenarioSelect];
            selects.forEach(function (select) {
                if (!select) {
                    return;
                }
                var saved = select.getAttribute("data-omni-contrast-selected") || "";
                var savedApplied = select.dataset && select.dataset.omniContrastSelectedApplied === "true";
                var previous = select.value;
                if (!previous && saved && !savedApplied) {
                    previous = saved;
                }
                select.innerHTML = "";
                options.forEach(function (option) {
                    var node = document.createElement("option");
                    node.value = option.value;
                    node.textContent = option.label;
                    select.appendChild(node);
                });
                if (previous && options.some(function (opt) { return opt.value === previous; })) {
                    select.value = previous;
                    if (saved && previous === saved && select.dataset) {
                        select.dataset.omniContrastSelectedApplied = "true";
                    }
                }
            });
            updateContrastPairOptions(options);
            updateContrastActionState();
        }

        function syncContrastMode() {
            if (!contrastFormElement) {
                return;
            }
            var mode = resolveContrastMode();
            var sections = contrastFormElement.querySelectorAll("[data-omni-contrast-mode]");
            sections.forEach(function (section) {
                var allowed = section.dataset.omniContrastMode
                    ? section.dataset.omniContrastMode.split(/\s+/)
                    : [];
                section.hidden = allowed.indexOf(mode) === -1;
            });
            var state = updateContrastActionState();
            if (!state.canRunMode) {
                if (state.mode === CONTRAST_SELECTION_MODES.stream_order && !isStreamOrderAllowed()) {
                    setContrastStatus("Stream-order pruning requires WBT channel delineation.");
                    return;
                }
                clearContrastStatus();
                return;
            }
            if (state.mode === CONTRAST_SELECTION_MODES.user_defined_areas && !state.hasGeojson) {
                setContrastStatus("Upload a GeoJSON file to run user-defined contrasts.");
                return;
            }
            if (
                (state.mode === CONTRAST_SELECTION_MODES.user_defined_areas
                    || state.mode === CONTRAST_SELECTION_MODES.user_defined_hillslope_groups
                    || state.mode === CONTRAST_SELECTION_MODES.stream_order)
                && !state.pairsValid
            ) {
                setContrastStatus("Resolve contrast pair errors to run contrasts.");
                return;
            }
            if (state.mode === CONTRAST_SELECTION_MODES.user_defined_hillslope_groups && !state.hasGroups) {
                setContrastStatus("Enter hillslope groups to run user-defined contrasts.");
                return;
            }
            if (state.mode === CONTRAST_SELECTION_MODES.stream_order && !state.orderPassesValid) {
                setContrastStatus("Order reduction passes must be at least 1.");
                return;
            }
            clearContrastStatus();
        }

        function openModal(modal) {
            if (!modal) {
                return;
            }
            var manager = typeof window !== "undefined" ? window.ModalManager : null;
            if (manager && typeof manager.open === "function") {
                manager.open(modal);
                return;
            }
            modal.removeAttribute("hidden");
            modal.style.display = "flex";
            modal.classList.add("is-visible");
            if (typeof document !== "undefined") {
                document.body.classList.add("wc-modal-open");
            }
        }

        function closeModal(modal) {
            if (!modal) {
                return;
            }
            var manager = typeof window !== "undefined" ? window.ModalManager : null;
            if (manager && typeof manager.close === "function") {
                manager.close(modal);
                return;
            }
            modal.classList.remove("is-visible");
            modal.setAttribute("hidden", "hidden");
            modal.style.display = "";
            if (typeof document !== "undefined") {
                document.body.classList.remove("wc-modal-open");
            }
        }

        function bindModalDismiss(modal) {
            if (!modal) {
                return;
            }
            var dismissers = modal.querySelectorAll("[data-modal-dismiss]");
            dismissers.forEach(function (btn) {
                btn.addEventListener("click", function (event) {
                    event.preventDefault();
                    closeModal(modal);
                });
            });
        }

        bindModalDismiss(deleteModal);
        bindModalDismiss(contrastDeleteModal);

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

            clearSummary();
            resetCompletionSeen();
            setStatus("Submitting omni run...");
            omni.connect_status_stream(omni);

            if (omniEvents && typeof omniEvents.emit === "function") {
                omniEvents.emit("omni:run:started", { scenarios: payload.scenarios });
            }

            http.requestWithSessionToken(
                url_for_run("run-omni", { prefix: "/rq-engine/api" }),
                {
                    method: "POST",
                    body: payload.formData,
                    form: formElement
                }
            ).then(function (response) {
                var body = response && response.body ? response.body : null;
                if (body && (body.error || body.errors)) {
                    omni.pushResponseStacktrace(omni, body);
                    if (omniEvents && typeof omniEvents.emit === "function") {
                        omniEvents.emit("omni:run:error", { response: body });
                    }
                    return;
                }
                if (body) {
                    setStatus("run_omni_rq job submitted: " + body.job_id);
                    omni.poll_completion_event = "OMNI_SCENARIO_RUN_TASK_COMPLETED";
                    omni.set_rq_job_id(omni, body.job_id);
                    if (hintAdapter && typeof hintAdapter.html === "function") {
                        hintAdapter.html(formatJobHint(body.job_id));
                        if (typeof hintAdapter.show === "function") {
                            hintAdapter.show();
                        }
                    }
                    if (omniEvents && typeof omniEvents.emit === "function") {
                        omniEvents.emit("omni:run:completed", {
                            job_id: body.job_id,
                            scenarios: payload.scenarios
                        });
                    }
                }
            }).catch(function (error) {
                var payload = toResponsePayload(http, error);
                omni.pushResponseStacktrace(omni, payload);
                setStatus(resolveErrorMessage(payload, "Omni run failed."));
                if (omniEvents && typeof omniEvents.emit === "function") {
                    omniEvents.emit("omni:run:error", { error: error });
                }
            });
        };

        omni.run_omni_contrasts = function () {
            if (!contrastController || !contrastFormElement) {
                return;
            }
            clearContrastStatus();

            var mode = resolveContrastMode();
            var state = updateContrastActionState();
            if (!state.canRunMode) {
                if (mode === CONTRAST_SELECTION_MODES.stream_order && !isStreamOrderAllowed()) {
                    setContrastStatus("Stream-order pruning requires WBT channel delineation.");
                    return;
                }
                setContrastStatus("Select a valid contrast selection mode.");
                return;
            }
            if (mode === CONTRAST_SELECTION_MODES.user_defined_areas) {
                if (!state.pairsValid) {
                    setContrastStatus("Resolve contrast pair errors before running contrasts.");
                    return;
                }
                if (!hasContrastGeojson()) {
                    setContrastStatus("Upload a GeoJSON file to run user-defined contrasts.");
                    return;
                }
            } else if (mode === CONTRAST_SELECTION_MODES.user_defined_hillslope_groups) {
                if (!state.pairsValid) {
                    setContrastStatus("Resolve contrast pair errors before running contrasts.");
                    return;
                }
                if (!hasContrastHillslopeGroups()) {
                    setContrastStatus("Enter hillslope groups to run user-defined contrasts.");
                    return;
                }
            } else if (mode === CONTRAST_SELECTION_MODES.stream_order) {
                if (!state.pairsValid) {
                    setContrastStatus("Resolve contrast pair errors before running contrasts.");
                    return;
                }
                if (!state.orderPassesValid) {
                    setContrastStatus("Order reduction passes must be at least 1.");
                    return;
                }
            } else {
                var controlValue = contrastControlSelect ? contrastControlSelect.value : "";
                var contrastValue = contrastScenarioSelect ? contrastScenarioSelect.value : "";
                if (!controlValue || !contrastValue) {
                    setContrastStatus("Select both control and contrast scenarios.");
                    return;
                }
            }

            clearContrastSummary();
            clampContrastHillslopeLimit();
            contrastController._completion_seen = false;
            setContrastStatus("Submitting omni contrasts...");
            contrastController.connect_status_stream(contrastController);

            var formData = new FormData(contrastFormElement);
            if (typeof formData.set === "function") {
                formData.set("omni_contrast_selection_mode", mode);
                appendContrastOutputOptions(formData);
                if (
                    mode === CONTRAST_SELECTION_MODES.user_defined_areas
                    || mode === CONTRAST_SELECTION_MODES.user_defined_hillslope_groups
                    || mode === CONTRAST_SELECTION_MODES.stream_order
                ) {
                    formData.delete("omni_control_scenario");
                    formData.delete("omni_contrast_scenario");
                }
            }

            http.requestWithSessionToken(
                url_for_run("run-omni-contrasts", { prefix: "/rq-engine/api" }),
                {
                    method: "POST",
                    body: formData,
                    form: contrastFormElement
                }
            ).then(function (response) {
                var body = response && response.body ? response.body : null;
                if (body && (body.error || body.errors)) {
                    contrastController.pushResponseStacktrace(contrastController, body);
                    return;
                }
                if (body) {
                    setContrastStatus("run_omni_contrasts_rq job submitted: " + body.job_id);
                    contrastController.poll_completion_event = CONTRAST_COMPLETION_EVENT;
                    contrastController.set_rq_job_id(contrastController, body.job_id);
                    if (contrastHintAdapter && typeof contrastHintAdapter.html === "function") {
                        contrastHintAdapter.html(formatJobHint(body.job_id));
                        if (typeof contrastHintAdapter.show === "function") {
                            contrastHintAdapter.show();
                        }
                    }
                }
            }).catch(function (error) {
                var payload = toResponsePayload(http, error);
                contrastController.pushResponseStacktrace(contrastController, payload);
                setContrastStatus(resolveErrorMessage(payload, "Omni contrasts failed."));
            });
        };

        omni.dry_run_omni_contrasts = function () {
            if (!contrastController || !contrastFormElement) {
                return;
            }
            clearContrastStatus();

            var mode = resolveContrastMode();
            var state = updateContrastActionState();
            if (!state.canRunMode) {
                if (mode === CONTRAST_SELECTION_MODES.stream_order && !isStreamOrderAllowed()) {
                    setContrastStatus("Stream-order pruning requires WBT channel delineation.");
                    return;
                }
                setContrastStatus("Select a valid contrast selection mode.");
                return;
            }
            if (mode === CONTRAST_SELECTION_MODES.user_defined_areas) {
                if (!state.pairsValid) {
                    setContrastStatus("Resolve contrast pair errors before dry run.");
                    return;
                }
                if (!hasContrastGeojson()) {
                    setContrastStatus("Upload a GeoJSON file to dry run user-defined contrasts.");
                    return;
                }
            } else if (mode === CONTRAST_SELECTION_MODES.user_defined_hillslope_groups) {
                if (!state.pairsValid) {
                    setContrastStatus("Resolve contrast pair errors before dry run.");
                    return;
                }
                if (!hasContrastHillslopeGroups()) {
                    setContrastStatus("Enter hillslope groups to dry run user-defined contrasts.");
                    return;
                }
            } else if (mode === CONTRAST_SELECTION_MODES.stream_order) {
                if (!state.pairsValid) {
                    setContrastStatus("Resolve contrast pair errors before dry run.");
                    return;
                }
                if (!state.orderPassesValid) {
                    setContrastStatus("Order reduction passes must be at least 1.");
                    return;
                }
            } else {
                var controlValue = contrastControlSelect ? contrastControlSelect.value : "";
                var contrastValue = contrastScenarioSelect ? contrastScenarioSelect.value : "";
                if (!controlValue || !contrastValue) {
                    setContrastStatus("Select both control and contrast scenarios.");
                    return;
                }
            }

            clearContrastSummary();
            clampContrastHillslopeLimit();
            setContrastStatus("Running dry run...");

            var formData = new FormData(contrastFormElement);
            if (typeof formData.set === "function") {
                formData.set("omni_contrast_selection_mode", mode);
                appendContrastOutputOptions(formData);
                if (
                    mode === CONTRAST_SELECTION_MODES.user_defined_areas
                    || mode === CONTRAST_SELECTION_MODES.user_defined_hillslope_groups
                    || mode === CONTRAST_SELECTION_MODES.stream_order
                ) {
                    formData.delete("omni_control_scenario");
                    formData.delete("omni_contrast_scenario");
                }
            }

            http.requestWithSessionToken(
                url_for_run("run-omni-contrasts-dry-run", { prefix: "/rq-engine/api" }),
                {
                    method: "POST",
                    body: formData,
                    form: contrastFormElement
                }
            ).then(function (response) {
                var body = response && response.body ? response.body : null;
                if (body && (body.error || body.errors)) {
                    contrastController.pushResponseStacktrace(contrastController, body);
                    setContrastStatus(resolveErrorMessage(body, "Dry run failed."));
                    return;
                }
                if (!body || !body.result) {
                    setContrastStatus("Dry run response missing results.");
                    return;
                }
                setContrastStatus("Dry run complete.");
                renderContrastDryRunReport(body.result);
                if (omniEvents && typeof omniEvents.emit === "function") {
                    omniEvents.emit("omni:contrast:dry-run:completed", { result: body.result });
                }
            }).catch(function (error) {
                var payload = toResponsePayload(http, error);
                contrastController.pushResponseStacktrace(contrastController, payload);
                setContrastStatus(resolveErrorMessage(payload, "Dry run failed."));
            });
        };

        omni.runOmniScenarios = omni.run_omni_scenarios;

        omni.load_scenarios_from_backend = function () {
            clearStatus();
            var endpoint = url_for_run("api/omni/get_scenarios");
            return http.getJson(endpoint).then(function (data) {
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
                    syncScenarioSelectionState(item, scenario);
                });

                refreshScenarioOptions();
                updateContrastScenarioOptions(data);
                updateDeleteButtonState();

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

        omni.report_contrasts = function () {
            if (!contrastInfoAdapter || typeof contrastInfoAdapter.html !== "function") {
                return;
            }
            contrastInfoAdapter.html("");

            http.request(url_for_run("report/omni_contrasts/"), {
                method: "GET",
                headers: { Accept: "text/html" }
            }).then(function (response) {
                var body = response && response.body ? response.body : "";
                contrastInfoAdapter.html(body);
            }).catch(function (error) {
                var payload = toResponsePayload(http, error);
                if (contrastController && typeof contrastController.pushResponseStacktrace === "function") {
                    contrastController.pushResponseStacktrace(contrastController, payload);
                } else {
                    omni.pushResponseStacktrace(omni, payload);
                }
            });
        };

        dom.delegate(formElement, "click", "[data-omni-action='add-scenario']", function (event) {
            event.preventDefault();
            addScenario();
        });

        dom.delegate(formElement, "click", "[data-omni-action='delete-selected']", function (event) {
            event.preventDefault();
            openDeleteModal();
        });

        dom.delegate(formElement, "click", "[data-omni-action='remove-scenario']", function (event) {
            event.preventDefault();
            removeScenario(event.target);
        });

        dom.delegate(formElement, "click", "[data-omni-action='run-scenarios']", function (event) {
            event.preventDefault();
            omni.run_omni_scenarios();
        });

        if (contrastFormElement) {
            dom.delegate(contrastFormElement, "click", "[data-omni-contrast-action='run-contrasts']", function (event) {
                event.preventDefault();
                omni.run_omni_contrasts();
            });
            dom.delegate(contrastFormElement, "click", "[data-omni-contrast-action='dry-run']", function (event) {
                event.preventDefault();
                omni.dry_run_omni_contrasts();
            });
            dom.delegate(contrastFormElement, "click", "[data-omni-contrast-action='delete-contrasts']", function (event) {
                event.preventDefault();
                openContrastDeleteModal();
            });
            dom.delegate(contrastFormElement, "click", "[data-omni-contrast-action='add-pair']", function (event) {
                event.preventDefault();
                ensureContrastPairsInitialized();
                addContrastPairRow();
                updateContrastActionState();
            });
            dom.delegate(contrastFormElement, "click", "[data-omni-contrast-action='remove-pair']", function (event) {
                event.preventDefault();
                var row = event.target.closest("[data-omni-contrast-pair-item='true']");
                if (row && row.parentNode) {
                    row.parentNode.removeChild(row);
                }
                if (getContrastPairRows().length === 0) {
                    addContrastPairRow();
                }
                updateContrastActionState();
            });
            dom.delegate(contrastFormElement, "change", "[data-omni-contrast-pair-field]", function () {
                updateContrastActionState();
            });
            if (contrastModeSelect) {
                contrastModeSelect.addEventListener("change", function () {
                    syncContrastMode();
                });
            }
            if (contrastHillslopeLimitInput) {
                contrastHillslopeLimitInput.addEventListener("change", function () {
                    clampContrastHillslopeLimit();
                });
                contrastHillslopeLimitInput.addEventListener("blur", function () {
                    clampContrastHillslopeLimit();
                });
            }
            if (contrastOrderReductionInput) {
                contrastOrderReductionInput.addEventListener("change", function () {
                    updateContrastActionState();
                    syncContrastMode();
                });
                contrastOrderReductionInput.addEventListener("blur", function () {
                    updateContrastActionState();
                    syncContrastMode();
                });
            }
            if (contrastGeojsonInput) {
                contrastGeojsonInput.addEventListener("change", function () {
                    updateContrastActionState();
                });
            }
            if (contrastHillslopeGroupsInput) {
                contrastHillslopeGroupsInput.addEventListener("input", function () {
                    updateContrastActionState();
                    syncContrastMode();
                });
                contrastHillslopeGroupsInput.addEventListener("change", function () {
                    updateContrastActionState();
                    syncContrastMode();
                });
            }
            syncContrastMode();
            updateContrastScenarioOptions();
            loadContrastPairRunMarkers();
        }

        dom.delegate(scenarioContainer, "change", "[data-omni-role='scenario-select']", function (event, matched) {
            var item = matched.closest("[data-omni-scenario-item='true']");
            updateScenarioControls(item);
            refreshScenarioOptions();
            emitScenarioUpdate(item);
            syncScenarioSelectionState(item);
            updateDeleteButtonState();
        });

        dom.delegate(scenarioContainer, "change", "[data-omni-field]", function (event, matched) {
            var item = matched.closest("[data-omni-scenario-item='true']");
            emitScenarioUpdate(item);
            syncScenarioSelectionState(item);
            updateDeleteButtonState();
        });

        dom.delegate(scenarioContainer, "change", "[data-omni-role='scenario-select-toggle']", function () {
            updateDeleteButtonState();
        });

        document.addEventListener("disturbed:has_sbs_changed", function () {
            refreshScenarioOptions();
        });

        if (deleteModalConfirm) {
            deleteModalConfirm.addEventListener("click", function (event) {
                event.preventDefault();
                confirmDeleteSelected();
            });
        }
        if (contrastDeleteModalConfirm) {
            contrastDeleteModalConfirm.addEventListener("click", function (event) {
                event.preventDefault();
                confirmDeleteContrasts();
            });
        }

        var bootstrapState = {
            scenariosLoaded: false,
            reportDisplayed: false,
            contrastReportDisplayed: false
        };

        omni.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            var controllerContext = helper && typeof helper.getControllerContext === "function"
                ? helper.getControllerContext(ctx, "omni")
                : {};
            var jobIds = ctx && (ctx.jobIds || ctx.jobs);

            var jobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "run_omni_rq")
                : null;
            if (!jobId && controllerContext.job_id) {
                jobId = controllerContext.job_id;
            }
            if (!jobId) {
                if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "run_omni_rq")) {
                    var value = jobIds.run_omni_rq;
                    if (value !== undefined && value !== null) {
                        jobId = String(value);
                    }
                }
            }

            if (jobId) {
                resetCompletionSeen();
                omni.poll_completion_event = "OMNI_SCENARIO_RUN_TASK_COMPLETED";
            }
            if (typeof omni.set_rq_job_id === "function") {
                omni.set_rq_job_id(omni, jobId);
            }

            if (contrastController) {
                var contrastJobId = helper && typeof helper.resolveJobId === "function"
                    ? helper.resolveJobId(ctx, "run_omni_contrasts_rq")
                    : null;
                if (!contrastJobId) {
                    if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "run_omni_contrasts_rq")) {
                        var contrastValue = jobIds.run_omni_contrasts_rq;
                        if (contrastValue !== undefined && contrastValue !== null) {
                            contrastJobId = String(contrastValue);
                        }
                    }
                }
                if (contrastJobId) {
                    contrastController._completion_seen = false;
                    contrastController.poll_completion_event = CONTRAST_COMPLETION_EVENT;
                }
                if (typeof contrastController.set_rq_job_id === "function") {
                    contrastController.set_rq_job_id(contrastController, contrastJobId);
                }
            }

            if (!bootstrapState.scenariosLoaded && typeof omni.load_scenarios_from_backend === "function") {
                omni.load_scenarios_from_backend();
                bootstrapState.scenariosLoaded = true;
            }

            var omniData = (ctx.data && ctx.data.omni) || {};
            var hasRanScenarios = controllerContext.hasRanScenarios;
            if (hasRanScenarios === undefined) {
                hasRanScenarios = omniData.hasRanScenarios;
            }
            var hasRanContrasts = controllerContext.hasRanContrasts;
            if (hasRanContrasts === undefined) {
                hasRanContrasts = omniData.hasRanContrasts;
            }

            if (hasRanScenarios && !bootstrapState.reportDisplayed && typeof omni.report_scenarios === "function") {
                omni.report_scenarios();
                bootstrapState.reportDisplayed = true;
            }
            if (hasRanContrasts && !bootstrapState.contrastReportDisplayed && typeof omni.report_contrasts === "function") {
                omni.report_contrasts();
                bootstrapState.contrastReportDisplayed = true;
            }

            return omni;
        };

        return omni;
    }

    return {
        getInstance: function getInstance() {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        },
        remount: function remount() {
            instance = null;
            return this.getInstance();
        }
    };
}());

if (typeof globalThis !== "undefined") {
    globalThis.Omni = Omni;
}
