/* ----------------------------------------------------------------------------
 * Disturbed Controller - Soil Burn Severity (SBS) Management
 * 
 * Handles two modes: Upload (mode 0) and Uniform (mode 1)
 * Communicates with Baer controller for dual-control scenarios
 * 
 * Documentation:
 * - Architecture: controllers_js/README.md — Disturbed Controller Reference
 * - Behavior: docs/ui-docs/control-ui-styling/sbs_controls_behavior.md
 * ----------------------------------------------------------------------------
 */
var Disturbed = (function () {
    var instance;

    var MODE_PANELS = {
        0: "#sbs_mode0_controls",
        1: "#sbs_mode1_controls"
    };

    var UNIFORM_HINT_IDS = {
        1: "#hint_low_sbs",
        2: "#hint_moderate_sbs",
        3: "#hint_high_sbs"
    };

    var UNIFORM_LABELS = {
        1: "Uniform Low SBS",
        2: "Uniform Moderate SBS",
        3: "Uniform High SBS"
    };

    var LOOKUP_VARIANT_BASE = "base";
    var LOOKUP_VARIANT_EXTENDED = "extended";

    var EVENT_NAMES = [
        "disturbed:mode:changed",
        "disturbed:sbs:state",
        "disturbed:lookup:reset",
        "disturbed:lookup:extended",
        "disturbed:lookup:deleted",
        "disturbed:lookup:synced",
        "disturbed:lookup:variant",
        "disturbed:lookup:error",
        "disturbed:upload:started",
        "disturbed:upload:completed",
        "disturbed:upload:error",
        "disturbed:remove:started",
        "disturbed:remove:completed",
        "disturbed:remove:error",
        "disturbed:uniform:started",
        "disturbed:uniform:completed",
        "disturbed:uniform:error",
        "disturbed:firedate:updated",
        "disturbed:firedate:error"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function") {
            throw new Error("Disturbed controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Disturbed controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("Disturbed controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Disturbed controller requires WCEvents helpers.");
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

    function setAdapterText(adapter, text) {
        if (!adapter || typeof adapter.text !== "function") {
            return;
        }
        adapter.text(text === undefined || text === null ? "" : String(text));
    }

    function dispatchDomEvent(name, detail) {
        if (typeof CustomEvent !== "function") {
            return;
        }
        try {
            document.dispatchEvent(new CustomEvent(name, { detail: detail || {} }));
        } catch (err) {
            console.warn("[Disturbed] Failed to dispatch " + name, err);
        }
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var events = helpers.events;

        var disturbed = controlBase();
        var disturbedEvents = null;

        if (events && typeof events.createEmitter === "function") {
            var emitterBase = events.createEmitter();
            if (typeof events.useEventMap === "function") {
                disturbedEvents = events.useEventMap(EVENT_NAMES, emitterBase);
            } else {
                disturbedEvents = emitterBase;
            }
        }

        if (disturbedEvents) {
            disturbed.events = disturbedEvents;
        }

        var formElement = dom.qs("#sbs_upload_form") || null;
        var infoElement = formElement ? dom.qs("#info", formElement) : null;
        var statusElement = formElement ? dom.qs("#status", formElement) : null;
        var stacktraceElement = formElement ? dom.qs("#stacktrace", formElement) : null;
        var rqJobElement = formElement ? dom.qs("#rq_job", formElement) : null;
        var spinnerElement = formElement ? dom.qs("#braille", formElement) : null;
        var lookupStatusElement = dom.qs("[data-disturbed-lookup-status]") || null;
        var lookupVariantInputs = dom.qsa("[data-disturbed-lookup-variant]") || [];
        var lookupModifyLinks = dom.qsa("[data-disturbed-modify-link]") || [];
        var extendedDependentControls = dom.qsa("[data-disturbed-requires-extended]") || [];

        var uploadHintElement = formElement ? dom.qs("#hint_upload_sbs", formElement) : null;
        var removeHintElement = formElement ? dom.qs("#hint_remove_sbs", formElement) : null;

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);
        var lookupStatusAdapter = createLegacyAdapter(lookupStatusElement);
        var uploadHintAdapter = createLegacyAdapter(uploadHintElement);
        var removeHintAdapter = createLegacyAdapter(removeHintElement);

        var uniformHintAdapters = {};
        Object.keys(UNIFORM_HINT_IDS).forEach(function (key) {
            var selector = UNIFORM_HINT_IDS[key];
            var node = formElement ? dom.qs(selector, formElement) : null;
            uniformHintAdapters[key] = createLegacyAdapter(node);
        });

        disturbed.form = formElement;
        disturbed.info = infoAdapter;
        disturbed.status = statusAdapter;
        disturbed.stacktrace = stacktraceAdapter;
        disturbed.rq_job = rqJobAdapter;
        disturbed.lookup_status = lookupStatusAdapter;
        disturbed.infoElement = infoElement;
        disturbed.statusSpinnerEl = spinnerElement;

        var commandButtons = [];
        [
            "#btn_upload_sbs",
            "#btn_remove_sbs",
            "#btn_remove_sbs_uniform",
            "#btn_uniform_low_sbs",
            "#btn_uniform_moderate_sbs",
            "#btn_uniform_high_sbs",
            "#btn_set_firedate"
        ].forEach(function (selector) {
            var button = formElement ? dom.qs(selector, formElement) : dom.qs(selector);
            if (button) {
                commandButtons.push(button);
            }
        });

        if (commandButtons.length > 0) {
            disturbed.command_btn_id = commandButtons;
        }

        disturbed.attach_status_stream(disturbed, {
            form: formElement,
            channel: "disturbed",
            runId: window.runid || window.runId || null,
            spinner: spinnerElement
        });

        var modePanels = {};
        Object.keys(MODE_PANELS).forEach(function (key) {
            modePanels[key] = formElement ? dom.qs(MODE_PANELS[key], formElement) : null;
        });

        var initialMode = 0;
        var initialUniform = null;
        if (formElement) {
            if (formElement.dataset) {
                if (formElement.dataset.initialMode !== undefined) {
                    initialMode = parseInteger(formElement.dataset.initialMode, 0);
                }
                if (formElement.dataset.initialUniform !== undefined) {
                    var uniformValue = formElement.dataset.initialUniform;
                    if (uniformValue === "" || uniformValue === null || uniformValue === undefined) {
                        initialUniform = null;
                    } else {
                        initialUniform = parseInteger(uniformValue, null);
                    }
                }
            }
            if (!formElement.dataset || formElement.dataset.initialMode === undefined) {
                var checked = formElement.querySelector("input[name='sbs_mode']:checked");
                initialMode = parseInteger(checked ? checked.value : initialMode, initialMode);
            }
        }

        var state = {
            mode: initialMode,
            hasSbs: undefined,
            hasSbsRequest: null,
            uniformSeverity: initialUniform,
            lookupVariant: LOOKUP_VARIANT_BASE,
            hasExtendedLookup: false
        };

        function emit(name, payload) {
            if (!disturbedEvents || typeof disturbedEvents.emit !== "function") {
                return;
            }
            disturbedEvents.emit(name, payload || {});
        }

        function startTask(taskMsg) {
            if (infoAdapter && typeof infoAdapter.text === "function") {
                infoAdapter.text("");
            }
            if (statusAdapter && typeof statusAdapter.text === "function") {
                statusAdapter.text(taskMsg + "...");
            }
            if (stacktraceAdapter && typeof stacktraceAdapter.text === "function") {
                stacktraceAdapter.text("");
            }
        }

        function setLookupStatus(message, state) {
            if (!lookupStatusAdapter || typeof lookupStatusAdapter.text !== "function") {
                return;
            }
            lookupStatusAdapter.text(message || "");
            if (lookupStatusAdapter.element) {
                if (state) {
                    lookupStatusAdapter.element.dataset.state = state;
                } else if (lookupStatusAdapter.element.dataset) {
                    delete lookupStatusAdapter.element.dataset.state;
                }
            }
        }

        function setLookupStatusError(payload, fallback) {
            var message = resolveErrorMessage(payload, fallback) || fallback || "Request failed";
            setLookupStatus(message, "error");
        }

        function setExtendedLookupAvailability(hasExtendedLookup) {
            var available = hasExtendedLookup === true;
            state.hasExtendedLookup = available;

            extendedDependentControls.forEach(function (control) {
                if (!control) {
                    return;
                }
                var tagName = String(control.tagName || "").toLowerCase();
                if (tagName === "a") {
                    if (available) {
                        control.removeAttribute("aria-disabled");
                        control.removeAttribute("tabindex");
                        if (control.dataset) {
                            delete control.dataset.disabled;
                        }
                    } else {
                        control.setAttribute("aria-disabled", "true");
                        control.setAttribute("tabindex", "-1");
                        if (control.dataset) {
                            control.dataset.disabled = "true";
                        }
                    }
                    return;
                }
                control.disabled = !available;
            });

            if (!available && state.lookupVariant === LOOKUP_VARIANT_EXTENDED) {
                setLookupVariantSelection(LOOKUP_VARIANT_BASE, { emit: false });
            }
        }

        function normalizeLookupVariant(value) {
            if (value === undefined || value === null) {
                return LOOKUP_VARIANT_BASE;
            }
            var normalized = String(value).trim().toLowerCase();
            if (normalized === LOOKUP_VARIANT_EXTENDED || normalized === "disturbed") {
                return LOOKUP_VARIANT_EXTENDED;
            }
            return LOOKUP_VARIANT_BASE;
        }

        function setLookupVariantSelection(variant, options) {
            var opts = options || {};
            var normalized = normalizeLookupVariant(variant);
            state.lookupVariant = normalized;

            lookupVariantInputs.forEach(function (input) {
                if (!input) {
                    return;
                }
                input.checked = String(input.value || "").toLowerCase() === normalized;
            });

            lookupModifyLinks.forEach(function (link) {
                if (!link || !link.dataset) {
                    return;
                }
                var matches = String(link.dataset.disturbedModifyLink || "").toLowerCase() === normalized;
                link.dataset.selected = matches ? "true" : "false";
            });

            if (opts.emit !== false) {
                emit("disturbed:lookup:variant", { lookupVariant: normalized });
            }
            return normalized;
        }

        function refreshLookupVariantSelection(reason) {
            if (lookupVariantInputs.length === 0 && lookupModifyLinks.length === 0) {
                return Promise.resolve(state.lookupVariant);
            }

            var lookupMetaUrl = url_for_run("api/disturbed/lookup_meta");

            return http
                .request(lookupMetaUrl, {
                    method: "GET",
                    form: formElement || undefined
                })
                .then(function (result) {
                    var data = result.body || {};
                    var content = data.Content || data.content || data;
                    setExtendedLookupAvailability(content.has_extended_lookup === true);
                    var variant = content.lookup_variant || state.lookupVariant;
                    var normalized = setLookupVariantSelection(variant, { emit: false });
                    emit("disturbed:lookup:variant", {
                        lookupVariant: normalized,
                        hasExtendedLookup: state.hasExtendedLookup,
                        source: reason || "api"
                    });
                    return normalized;
                })
                .catch(function (_error) {
                    return state.lookupVariant;
                });
        }

        function setLookupVariantOnServer(variant) {
            var requestedVariant = normalizeLookupVariant(variant);
            if (requestedVariant === LOOKUP_VARIANT_EXTENDED && state.hasExtendedLookup !== true) {
                setLookupVariantSelection(LOOKUP_VARIANT_BASE, { emit: false });
                setLookupStatus("Extended lookup is unavailable. Load extended table first.", "warning");
                return Promise.resolve(LOOKUP_VARIANT_BASE);
            }
            setLookupStatus("Saving lookup selection...", "pending");
            return http
                .request(url_for_run("tasks/set_lookup_variant"), {
                    method: "POST",
                    json: { lookup_variant: requestedVariant },
                    form: formElement || undefined
                })
                .then(function (result) {
                    var data = result.body || {};
                    if (data.error || data.errors) {
                        setLookupStatusError(data, "Failed to save lookup selection.");
                        return refreshLookupVariantSelection("set-lookup-variant-error");
                    }
                    var content = data.Content || data.content || data;
                    if (content.has_extended_lookup !== undefined) {
                        setExtendedLookupAvailability(content.has_extended_lookup === true);
                    }
                    var effectiveVariant = normalizeLookupVariant(content.lookup_variant || requestedVariant);
                    setLookupVariantSelection(effectiveVariant, { emit: false });
                    setLookupStatus("Active lookup set to " + effectiveVariant + ".", "success");
                    emit("disturbed:lookup:variant", {
                        lookupVariant: effectiveVariant,
                        requestedLookupVariant: requestedVariant,
                        hasExtendedLookup: state.hasExtendedLookup,
                        source: "set-lookup-variant"
                    });
                    return effectiveVariant;
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    setLookupStatusError(payload, "Failed to save lookup selection.");
                    return refreshLookupVariantSelection("set-lookup-variant-error");
                });
        }

        function completeTask(taskMsg) {
            if (statusAdapter && typeof statusAdapter.text === "function") {
                statusAdapter.text(taskMsg + "... Success");
            }
        }

        function failTask(taskMsg) {
            if (statusAdapter && typeof statusAdapter.text === "function") {
                statusAdapter.text(taskMsg + "... Failed");
            }
        }

        function setMode(mode, shouldEmit) {
            var normalized = parseInteger(mode, state.mode);
            if (!Object.prototype.hasOwnProperty.call(modePanels, String(normalized))) {
                normalized = 0;
            }
            state.mode = normalized;
            Object.keys(modePanels).forEach(function (key) {
                var panel = modePanels[key];
                if (!panel) {
                    return;
                }
                if (String(key) === String(normalized)) {
                    dom.show(panel);
                } else {
                    dom.hide(panel);
                }
            });
            if (formElement) {
                var modeInput = formElement.querySelector("input[name='sbs_mode'][value='" + normalized + "']");
                if (modeInput && !modeInput.checked) {
                    modeInput.checked = true;
                }
            }
            if (shouldEmit) {
                emit("disturbed:mode:changed", { mode: normalized });
            }
        }

        function clearUploadHint() {
            setAdapterText(uploadHintAdapter, "");
        }

        function clearRemoveHint() {
            setAdapterText(removeHintAdapter, "");
        }

        function updateCurrentFilename(filename) {
            if (!filename) {
                return;
            }
            // Find the text display showing current SBS map filename
            var displays = formElement ? formElement.querySelectorAll(".wc-field--display .wc-text-display") : [];
            for (var i = 0; i < displays.length; i++) {
                var display = displays[i];
                var label = display.parentElement ? display.parentElement.querySelector(".wc-field__label") : null;
                if (label && label.textContent && label.textContent.indexOf("Current SBS map") !== -1) {
                    display.innerHTML = "<code>" + filename + "</code>";
                    break;
                }
            }
        }

        function clearUniformHints() {
            Object.keys(uniformHintAdapters).forEach(function (key) {
                setAdapterText(uniformHintAdapters[key], "");
            });
        }

        function setUniformHint(value, text) {
            var key = String(value);
            if (!Object.prototype.hasOwnProperty.call(uniformHintAdapters, key)) {
                return;
            }
            setAdapterText(uniformHintAdapters[key], text);
        }

        function updateUniformSummary(severity) {
            var display = formElement ? formElement.querySelector('[data-uniform-summary]') : null;
            var nextSeverity;
            if (severity === undefined) {
                nextSeverity = state.uniformSeverity;
            } else if (severity === null) {
                nextSeverity = null;
            } else {
                nextSeverity = parseInteger(severity, null);
            }
            state.uniformSeverity = nextSeverity;
            if (!display) {
                return;
            }
            var summaryHtml;
            if (nextSeverity === null || nextSeverity === undefined) {
                summaryHtml = '<span class="wc-text-muted">Not set</span>';
            } else {
                summaryHtml = UNIFORM_LABELS[nextSeverity] || "Uniform " + nextSeverity + " SBS";
            }
            display.innerHTML = summaryHtml;
        }

        function syncModeFromServer(mode, severity, options) {
            var opts = options || {};
            if (mode !== undefined && mode !== null) {
                setMode(mode, opts.emit !== false);
            }
            if (severity !== undefined) {
                updateUniformSummary(severity);
            }
        }

        updateUniformSummary(state.uniformSeverity);

        function updateHasSbs(value, source) {
            var next;
            if (value === undefined || value === null) {
                next = undefined;
            } else {
                next = value === true;
            }
            var previous = state.hasSbs;
            state.hasSbs = next;
            if (previous !== next) {
                emit("disturbed:sbs:state", { hasSbs: next, source: source || null });
                dispatchDomEvent("disturbed:has_sbs_changed", { hasSbs: next, source: source || null });
            }
            return state.hasSbs;
        }

        function refreshHasSbs(reason) {
            if (state.hasSbsRequest) {
                return state.hasSbsRequest;
            }
            var request = http
                .request(url_for_run("api/disturbed/has_sbs/"), {
                    method: "GET",
                    form: formElement || undefined
                })
                .then(function (result) {
                    var body = result.body || {};
                    var hasSbs = body.has_sbs === true;
                    updateHasSbs(hasSbs, reason || "api");
                    return hasSbs;
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    emit("disturbed:sbs:state", { error: payload, source: reason || "api" });
                    return false;
                })
                .finally(function () {
                    state.hasSbsRequest = null;
                });
            state.hasSbsRequest = request;
            return request;
        }

        function handleResponseError(taskMsg, payload, errorEvent, taskName) {
            disturbed.pushResponseStacktrace(disturbed, payload);
            failTask(taskMsg);
            emit(errorEvent, { error: payload });
            disturbed.triggerEvent("job:error", { task: taskName, error: payload });
        }

        function resetLandSoilLookup() {
            var taskMsg = "Resetting disturbed lookup";
            setLookupStatus("Resetting disturbed parameters...", "pending");
            startTask(taskMsg);
            emit("disturbed:lookup:reset", {});
            disturbed.triggerEvent("job:started", { task: "disturbed:lookup:reset" });
            return http
                .request(url_for_run("tasks/reset_disturbed"), {
                    method: "POST",
                    form: formElement || undefined
                })
                .then(function (result) {
                    var data = result.body || {};
                    if (!data.error && !data.errors) {
                        completeTask(taskMsg);
                        setAdapterText(infoAdapter, "Disturbed lookup reset to defaults.");
                        setLookupStatus("Disturbed parameters reset to defaults.", "success");
                        disturbed.triggerEvent("job:completed", {
                            task: "disturbed:lookup:reset",
                            response: data
                        });
                        return data;
                    }
                    setLookupStatusError(data, "Failed to reset disturbed parameters.");
                    handleResponseError(taskMsg, data, "disturbed:lookup:error", "disturbed:lookup:reset");
                    return data;
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    setLookupStatusError(payload, "Failed to reset disturbed parameters.");
                    handleResponseError(taskMsg, payload, "disturbed:lookup:error", "disturbed:lookup:reset");
                    return payload;
                })
                .then(function (payload) {
                    refreshLookupVariantSelection("reset-base");
                    return payload;
                });
        }

        function loadExtendedLandSoilLookup() {
            var taskMsg = "Loading extended disturbed lookup";
            setLookupStatus("Loading extended disturbed parameters...", "pending");
            startTask(taskMsg);
            emit("disturbed:lookup:extended", {});
            disturbed.triggerEvent("job:started", { task: "disturbed:lookup:extended" });
            return http
                .request(url_for_run("tasks/load_extended_land_soil_lookup"), {
                    method: "POST",
                    form: formElement || undefined
                })
                .then(function (result) {
                    var data = result.body || {};
                    if (!data.error && !data.errors) {
                        completeTask(taskMsg);
                        setAdapterText(infoAdapter, "Extended disturbed lookup loaded.");
                        setLookupStatus("Extended disturbed parameters loaded.", "success");
                        disturbed.triggerEvent("job:completed", {
                            task: "disturbed:lookup:extended",
                            response: data
                        });
                        return data;
                    }
                    setLookupStatusError(data, "Failed to load extended disturbed parameters.");
                    handleResponseError(taskMsg, data, "disturbed:lookup:error", "disturbed:lookup:extended");
                    return data;
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    setLookupStatusError(payload, "Failed to load extended disturbed parameters.");
                    handleResponseError(taskMsg, payload, "disturbed:lookup:error", "disturbed:lookup:extended");
                    return payload;
                })
                .then(function (payload) {
                    refreshLookupVariantSelection("load-extended");
                    return payload;
                });
        }

        function deleteExtendedLandSoilLookup() {
            var taskMsg = "Deleting extended disturbed lookup";
            setLookupStatus("Deleting extended disturbed parameters...", "pending");
            startTask(taskMsg);
            emit("disturbed:lookup:deleted", {});
            disturbed.triggerEvent("job:started", { task: "disturbed:lookup:deleted" });
            return http
                .request(url_for_run("tasks/delete_extended_land_soil_lookup"), {
                    method: "POST",
                    form: formElement || undefined
                })
                .then(function (result) {
                    var data = result.body || {};
                    if (!data.error && !data.errors) {
                        completeTask(taskMsg);
                        setAdapterText(infoAdapter, "Extended disturbed lookup deleted.");
                        setLookupStatus("Extended disturbed parameters deleted. Base lookup is now default.", "success");
                        disturbed.triggerEvent("job:completed", {
                            task: "disturbed:lookup:deleted",
                            response: data
                        });
                        return data;
                    }
                    setLookupStatusError(data, "Failed to delete extended disturbed parameters.");
                    handleResponseError(taskMsg, data, "disturbed:lookup:error", "disturbed:lookup:deleted");
                    return data;
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    setLookupStatusError(payload, "Failed to delete extended disturbed parameters.");
                    handleResponseError(taskMsg, payload, "disturbed:lookup:error", "disturbed:lookup:deleted");
                    return payload;
                })
                .then(function (payload) {
                    refreshLookupVariantSelection("delete-extended");
                    return payload;
                });
        }

        function syncBaseToExtendedLandSoilLookup() {
            var taskMsg = "Syncing base lookup to extended";
            setLookupStatus("Syncing base table to extended table...", "pending");
            startTask(taskMsg);
            emit("disturbed:lookup:synced", {});
            disturbed.triggerEvent("job:started", { task: "disturbed:lookup:synced" });
            return http
                .request(url_for_run("tasks/sync_base_to_extended_land_soil_lookup"), {
                    method: "POST",
                    form: formElement || undefined
                })
                .then(function (result) {
                    var data = result.body || {};
                    if (!data.error && !data.errors) {
                        completeTask(taskMsg);
                        setAdapterText(infoAdapter, "Base disturbed lookup synced to extended table.");
                        setLookupStatus("Base table synced to extended table.", "success");
                        disturbed.triggerEvent("job:completed", {
                            task: "disturbed:lookup:synced",
                            response: data
                        });
                        return data;
                    }
                    setLookupStatusError(data, "Failed to sync base table to extended table.");
                    handleResponseError(taskMsg, data, "disturbed:lookup:error", "disturbed:lookup:synced");
                    return data;
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    setLookupStatusError(payload, "Failed to sync base table to extended table.");
                    handleResponseError(taskMsg, payload, "disturbed:lookup:error", "disturbed:lookup:synced");
                    return payload;
                })
                .then(function (payload) {
                    refreshLookupVariantSelection("sync-base-to-extended");
                    return payload;
                });
        }

        function uploadSbs() {
            if (!formElement) {
                return Promise.resolve(null);
            }
            var taskMsg = "Uploading SBS";
            clearUploadHint();
            startTask(taskMsg);
            emit("disturbed:upload:started", {});
            disturbed.triggerEvent("job:started", { task: "disturbed:upload" });
            var formData = new window.FormData(formElement);
            return http
                .requestWithSessionToken(url_for_run("tasks/upload-sbs/", { prefix: "/rq-engine/api" }), {
                    method: "POST",
                    body: formData,
                    form: formElement
                })
                .then(function (result) {
                    var data = result.body || {};
                    if (!data.error && !data.errors) {
                        completeTask(taskMsg);
                        setAdapterText(uploadHintAdapter, "SBS raster uploaded successfully.");
                        updateHasSbs(true, "upload");
                        
                        // Update filename display if provided
                        var resultPayload = data.result || {};
                        if (resultPayload.disturbed_fn) {
                            updateCurrentFilename(resultPayload.disturbed_fn);
                        }

                        syncModeFromServer(0, null);

                        emit("disturbed:upload:completed", { response: data });
                        disturbed.triggerEvent("SBS_UPLOAD_TASK_COMPLETE", data);
                        // Sync with baer controller
                        try {
                            var baer = typeof Baer !== "undefined" ? Baer.getInstance() : null;
                            if (baer) {
                                // Trigger event on baer form
                                if (typeof baer.triggerEvent === "function") {
                                    baer.triggerEvent("SBS_UPLOAD_TASK_COMPLETE", data);
                                }
                                // Call methods directly since forms are separate
                                setTimeout(function () {
                                    if (typeof baer.show_sbs === "function") {
                                        baer.show_sbs({ flyToBounds: true, reason: "upload" });
                                    }
                                    if (typeof baer.load_modify_class === "function") {
                                        baer.load_modify_class();
                                    }
                                }, 100);
                            }
                        } catch (e) {
                            console.warn("[Disturbed] Failed to sync Baer controller", e);
                        }
                        disturbed.triggerEvent("job:completed", {
                            task: "disturbed:upload",
                            response: data
                        });
                        refreshHasSbs("upload");
                        return data;
                    }
                    setAdapterText(uploadHintAdapter, resolveErrorMessage(data, "Upload failed."));
                    handleResponseError(taskMsg, data, "disturbed:upload:error", "disturbed:upload");
                    refreshHasSbs("upload");
                    return data;
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    setAdapterText(uploadHintAdapter, resolveErrorMessage(payload, "Upload failed."));
                    handleResponseError(taskMsg, payload, "disturbed:upload:error", "disturbed:upload");
                    refreshHasSbs("upload");
                    return payload;
                });
        }

        function removeSbs() {
            var taskMsg = "Removing SBS";
            clearUploadHint();
            clearRemoveHint();
            startTask(taskMsg);
            emit("disturbed:remove:started", {});
            disturbed.triggerEvent("job:started", { task: "disturbed:remove" });
            return http
                .request(url_for_run("tasks/remove_sbs"), {
                    method: "POST",
                    form: formElement || undefined
                })
                .then(function (result) {
                    var data = result.body || {};
                    if (!data.error && !data.errors) {
                        completeTask(taskMsg);
                        setAdapterText(removeHintAdapter, "SBS raster removed.");
                        updateHasSbs(false, "remove");
                        emit("disturbed:remove:completed", { response: data });
                        disturbed.triggerEvent("SBS_REMOVE_TASK_COMPLETE", data);
                        
                        // Remove map layer via baer controller
                        try {
                            var baer = typeof Baer !== "undefined" ? Baer.getInstance() : null;
                            if (baer) {
                                // Trigger event on baer form
                                if (typeof baer.triggerEvent === "function") {
                                    baer.triggerEvent("SBS_REMOVE_TASK_COMPLETE", data);
                                }
                                // Remove the map layer directly
                                try {
                                    var map = typeof MapController !== "undefined" ? MapController.getInstance() : null;
                                    if (map && baer.baer_map) {
                                        if (typeof map.removeLayer === "function") {
                                            map.removeLayer(baer.baer_map);
                                        }
                                        if (map.ctrls && typeof map.ctrls.removeLayer === "function") {
                                            map.ctrls.removeLayer(baer.baer_map);
                                        }
                                        baer.baer_map = null;
                                    }
                                    // Clear the SBS legend
                                    var legend = document.getElementById("sbs_legend");
                                    if (legend) {
                                        legend.innerHTML = "";
                                    }
                                } catch (mapErr) {
                                    console.warn("[Disturbed] Failed to remove map layer", mapErr);
                                }
                            }
                        } catch (e) {
                            console.warn("[Disturbed] Failed to sync Baer controller", e);
                        }
                        
                        disturbed.triggerEvent("job:completed", {
                            task: "disturbed:remove",
                            response: data
                        });
                        refreshHasSbs("remove");
                        return data;
                    }
                    setAdapterText(removeHintAdapter, resolveErrorMessage(data, "Failed to remove SBS."));
                    handleResponseError(taskMsg, data, "disturbed:remove:error", "disturbed:remove");
                    refreshHasSbs("remove");
                    return data;
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    setAdapterText(removeHintAdapter, resolveErrorMessage(payload, "Failed to remove SBS."));
                    handleResponseError(taskMsg, payload, "disturbed:remove:error", "disturbed:remove");
                    refreshHasSbs("remove");
                    return payload;
                });
        }

        function buildUniformSbs(value) {
            var severity = parseInteger(value, NaN);
            if (Number.isNaN(severity)) {
                return Promise.resolve(null);
            }
            var taskMsg = "Building uniform SBS";
            clearUniformHints();
            startTask(taskMsg);
            emit("disturbed:uniform:started", { severity: severity });
            disturbed.triggerEvent("job:started", { task: "disturbed:uniform", severity: severity });
            return http
                .request(url_for_run("tasks/build_uniform_sbs"), {
                    method: "POST",
                    json: { value: severity },
                    form: formElement || undefined
                })
                .then(function (result) {
                    var data = result.body || {};
                    if (!data.error && !data.errors) {
                        completeTask(taskMsg);
                        updateHasSbs(true, "uniform");
                        
                        // Update filename display if provided
                        var content = data.Content || {};
                        if (content.disturbed_fn) {
                            updateCurrentFilename(content.disturbed_fn);
                        }

                        syncModeFromServer(1, severity);

                        emit("disturbed:uniform:completed", {
                            response: data,
                            severity: severity
                        });
                        disturbed.triggerEvent("SBS_UPLOAD_TASK_COMPLETE", data);
                        // Sync with baer controller
                        try {
                            var baer = typeof Baer !== "undefined" ? Baer.getInstance() : null;
                            if (baer) {
                                // Trigger event on baer form
                                if (typeof baer.triggerEvent === "function") {
                                    baer.triggerEvent("SBS_UPLOAD_TASK_COMPLETE", data);
                                }
                                // Call methods directly since forms are separate
                                setTimeout(function () {
                                    if (typeof baer.show_sbs === "function") {
                                        baer.show_sbs({ flyToBounds: true, reason: "uniform" });
                                    }
                                    if (typeof baer.load_modify_class === "function") {
                                        baer.load_modify_class();
                                    }
                                }, 100);
                            }
                        } catch (e) {
                            console.warn("[Disturbed] Failed to sync Baer controller", e);
                        }
                        disturbed.triggerEvent("job:completed", {
                            task: "disturbed:uniform",
                            severity: severity,
                            response: data
                        });
                        refreshHasSbs("uniform");
                        return data;
                    }
                    setUniformHint(severity, resolveErrorMessage(data, "Failed to generate uniform SBS."));
                    handleResponseError(taskMsg, data, "disturbed:uniform:error", "disturbed:uniform");
                    refreshHasSbs("uniform");
                    return data;
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    setUniformHint(severity, resolveErrorMessage(payload, "Failed to generate uniform SBS."));
                    handleResponseError(taskMsg, payload, "disturbed:uniform:error", "disturbed:uniform");
                    refreshHasSbs("uniform");
                    return payload;
                });
        }

        function setFireDate(value) {
            var taskMsg = "Setting fire date";
            startTask(taskMsg);
            emit("disturbed:firedate:updated", { pending: true });
            disturbed.triggerEvent("job:started", { task: "disturbed:firedate" });

            var fireDate = value;
            if ((fireDate === undefined || fireDate === null) && formElement) {
                var formValues = forms.serializeForm(formElement, { format: "object" }) || {};
                if (Object.prototype.hasOwnProperty.call(formValues, "firedate")) {
                    fireDate = formValues.firedate;
                }
            }

            return http
                .request(url_for_run("tasks/set_firedate/"), {
                    method: "POST",
                    json: { fire_date: fireDate || null },
                    form: formElement || undefined
                })
                .then(function (result) {
                    var data = result.body || {};
                    if (!data.error && !data.errors) {
                        completeTask(taskMsg);
                        setAdapterText(infoAdapter, fireDate ? "Fire date set to " + fireDate + "." : "Fire date cleared.");
                        emit("disturbed:firedate:updated", { fireDate: fireDate || null });
                        disturbed.triggerEvent("job:completed", {
                            task: "disturbed:firedate",
                            response: data
                        });
                        return data;
                    }
                    handleResponseError(taskMsg, data, "disturbed:firedate:error", "disturbed:firedate");
                    return data;
                })
                .catch(function (error) {
                    var payload = toResponsePayload(http, error);
                    handleResponseError(taskMsg, payload, "disturbed:firedate:error", "disturbed:firedate");
                    return payload;
                });
        }

        function bindHandlers() {
            if (formElement) {
                if (formElement.dataset && formElement.dataset.disturbedHandlersBound === "true") {
                    return;
                }
                if (formElement.dataset) {
                    formElement.dataset.disturbedHandlersBound = "true";
                }

                dom.delegate(formElement, "change", "input[name='sbs_mode']", function (event, target) {
                    var nextMode = target ? target.value : state.mode;
                    setMode(nextMode, true);
                });

                dom.delegate(formElement, "click", "[data-sbs-action]", function (event, target) {
                    event.preventDefault();
                    var action = target.getAttribute("data-sbs-action");
                    if (!action) {
                        return;
                    }
                    if (action === "upload") {
                        uploadSbs();
                        return;
                    }
                    if (action === "remove") {
                        removeSbs();
                        return;
                    }
                    if (action === "set-firedate") {
                        var selector = target.getAttribute("data-sbs-target") || "#firedate";
                        var input = selector ? dom.qs(selector) : null;
                        var value = input ? input.value : null;
                        setFireDate(value);
                    }
                });

                dom.delegate(formElement, "change", "input[type='file'][data-auto-upload]", function (event, target) {
                    if (target.files && target.files.length > 0) {
                        uploadSbs();
                    }
                });

                dom.delegate(formElement, "click", "[data-sbs-uniform]", function (event, target) {
                    event.preventDefault();
                    var uniformValue = target.getAttribute("data-sbs-uniform");
                    buildUniformSbs(uniformValue);
                });
            }

            dom.delegate(document, "click", "[data-disturbed-action]", function (event, target) {
                event.preventDefault();
                var action = target.getAttribute("data-disturbed-action");
                if (action === "reset-lookup") {
                    resetLandSoilLookup();
                    return;
                }
                if (action === "load-extended-lookup") {
                    loadExtendedLandSoilLookup();
                    return;
                }
                if (action === "delete-extended-lookup") {
                    deleteExtendedLandSoilLookup();
                    return;
                }
                if (action === "sync-base-to-extended-lookup") {
                    syncBaseToExtendedLandSoilLookup();
                    return;
                }
            });

            dom.delegate(document, "change", "[data-disturbed-lookup-variant]", function (_event, target) {
                var requestedVariant = target ? target.value : LOOKUP_VARIANT_BASE;
                setLookupVariantSelection(requestedVariant, { emit: true });
                setLookupVariantOnServer(requestedVariant);
            });

            dom.delegate(document, "click", "[data-disturbed-requires-extended]", function (event, target) {
                if (state.hasExtendedLookup === true) {
                    return;
                }
                event.preventDefault();
                if (target && target.dataset && target.dataset.disturbedLookupVariant) {
                    setLookupVariantSelection(LOOKUP_VARIANT_BASE, { emit: false });
                }
                setLookupStatus("Extended lookup is unavailable. Load extended table first.", "warning");
            });
        }

        setMode(state.mode, false);
        bindHandlers();
        setLookupVariantSelection(state.lookupVariant, { emit: false });
        setExtendedLookupAvailability(false);
        refreshLookupVariantSelection("bootstrap");

        disturbed.reset_land_soil_lookup = resetLandSoilLookup;
        disturbed.load_extended_land_soil_lookup = loadExtendedLandSoilLookup;
        disturbed.delete_extended_land_soil_lookup = deleteExtendedLandSoilLookup;
        disturbed.sync_base_to_extended_land_soil_lookup = syncBaseToExtendedLandSoilLookup;
        disturbed.upload_sbs = uploadSbs;
        disturbed.remove_sbs = removeSbs;
        disturbed.build_uniform_sbs = buildUniformSbs;
        disturbed.set_firedate = setFireDate;
        disturbed.refresh_has_sbs = refreshHasSbs;

        disturbed.set_has_sbs_cached = function (value) {
            return updateHasSbs(value, "manual");
        };

        disturbed.get_has_sbs_cached = function () {
            return state.hasSbs;
        };

        disturbed.clear_has_sbs_cache = function () {
            return updateHasSbs(undefined, "clear");
        };

        disturbed.has_sbs = function (options) {
            var opts = options || {};
            if (opts.forceRefresh || state.hasSbs === undefined) {
                refreshHasSbs(opts.forceRefresh ? "force" : "lazy");
            }
            return state.hasSbs === true;
        };

        disturbed.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var flags = ctx.flags || {};
            var controllerContext = ctx.controllers && ctx.controllers.disturbed ? ctx.controllers.disturbed : {};
            if (flags.initialHasSbs !== undefined && typeof disturbed.set_has_sbs_cached === "function") {
                disturbed.set_has_sbs_cached(Boolean(flags.initialHasSbs));
            }

            if (controllerContext.mode !== undefined || controllerContext.uniformSeverity !== undefined) {
                syncModeFromServer(controllerContext.mode, controllerContext.uniformSeverity, { emit: false });
            }
            
            // Always bootstrap the Baer controller so task events are wired even before SBS exists.
            try {
                var baer = typeof Baer !== "undefined" ? Baer.getInstance() : null;
                if (baer && typeof baer.bootstrap === "function") {
                    baer.bootstrap(context);
                }
            } catch (e) {
                console.warn("[Disturbed] Failed to bootstrap Baer controller", e);
            }
            
            return disturbed;
        };

        return disturbed;
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

if (typeof window !== "undefined") {
    window.Disturbed = Disturbed;
} else if (typeof globalThis !== "undefined") {
    globalThis.Disturbed = Disturbed;
}
