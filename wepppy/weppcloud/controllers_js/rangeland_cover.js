/* ----------------------------------------------------------------------------
 * Rangeland Cover
 * Doc: controllers_js/README.md — Rangeland Cover Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var RangelandCover = (function () {
    "use strict";

    var instance;

    var EVENT_NAMES = [
        "rangeland:config:loaded",
        "rangeland:mode:changed",
        "rangeland:rap-year:changed",
        "rangeland:run:started",
        "rangeland:run:completed",
        "rangeland:run:failed",
        "rangeland:report:loaded",
        "rangeland:report:failed"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function" || typeof dom.delegate !== "function") {
            throw new Error("Rangeland cover controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Rangeland cover controller requires WCForms helpers.");
        }
        if (!http || typeof http.postJson !== "function" || typeof http.request !== "function") {
            throw new Error("Rangeland cover controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Rangeland cover controller requires WCEvents helpers.");
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
        if (typeof value === "number" && !Number.isNaN(value)) {
            return value;
        }
        var parsed = parseInt(value, 10);
        if (Number.isNaN(parsed)) {
            return fallback;
        }
        return parsed;
    }

    function parseOptionalInteger(value) {
        if (value === undefined || value === null || value === "") {
            return null;
        }
        if (typeof value === "number" && !Number.isNaN(value)) {
            return value;
        }
        var parsed = parseInt(value, 10);
        if (Number.isNaN(parsed)) {
            return value;
        }
        return parsed;
    }

    function parseCoverValue(value) {
        if (value === undefined || value === null || value === "") {
            return value;
        }
        if (typeof value === "number" && !Number.isNaN(value)) {
            return value;
        }
        if (typeof value === "string") {
            var trimmed = value.trim();
            if (trimmed === "") {
                return "";
            }
            var parsed = parseFloat(trimmed);
            if (!Number.isNaN(parsed)) {
                return parsed;
            }
        }
        return value;
    }

    function resolveFieldValue(values, keys) {
        if (!values) {
            return undefined;
        }
        for (var i = 0; i < keys.length; i += 1) {
            var key = keys[i];
            if (Object.prototype.hasOwnProperty.call(values, key)) {
                return values[key];
            }
        }
        return undefined;
    }

    function readFormState(forms, formElement) {
        var values = forms.serializeForm(formElement, { format: "json" }) || {};
        var defaults = {
            bunchgrass: parseCoverValue(resolveFieldValue(values, ["input_bunchgrass_cover", "bunchgrass_cover"])),
            forbs: parseCoverValue(resolveFieldValue(values, ["input_forbs_cover", "forbs_cover"])),
            sodgrass: parseCoverValue(resolveFieldValue(values, ["input_sodgrass_cover", "sodgrass_cover"])),
            shrub: parseCoverValue(resolveFieldValue(values, ["input_shrub_cover", "shrub_cover"])),
            basal: parseCoverValue(resolveFieldValue(values, ["input_basal_cover", "basal_cover"])),
            rock: parseCoverValue(resolveFieldValue(values, ["input_rock_cover", "rock_cover"])),
            litter: parseCoverValue(resolveFieldValue(values, ["input_litter_cover", "litter_cover"])),
            cryptogams: parseCoverValue(resolveFieldValue(values, ["input_cryptogams_cover", "cryptogams_cover"]))
        };

        return {
            mode: parseInteger(values.rangeland_cover_mode, 0),
            rapYear: parseOptionalInteger(values.rap_year),
            defaults: defaults
        };
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var events = helpers.events;

        var rangeland = controlBase();
        var rangelandEvents = null;

        if (events && typeof events.createEmitter === "function") {
            var emitterBase = events.createEmitter();
            if (typeof events.useEventMap === "function") {
                rangelandEvents = events.useEventMap(EVENT_NAMES, emitterBase);
            } else {
                rangelandEvents = emitterBase;
            }
        }

        if (rangelandEvents) {
            rangeland.events = rangelandEvents;
        }

        var formElement = dom.ensureElement("#rangeland_cover_form", "Rangeland cover form not found.");
        var infoElement = dom.qs("#rangeland_cover_form #info");
        var statusElement = dom.qs("#rangeland_cover_form #status");
        var stacktraceElement = dom.qs("#rangeland_cover_form #stacktrace");
        var rqJobElement = dom.qs("#rangeland_cover_form #rq_job");
        var hintElement = dom.qs("#hint_build_rangeland_cover");
        var statusPanelElement = dom.qs("#rangeland_status_panel");
        var stacktracePanelElement = dom.qs("#rangeland_stacktrace_panel");
        var spinnerElement = statusPanelElement ? statusPanelElement.querySelector("#braille") : null;
        var rapSectionElement = dom.qs("[data-rangeland-rap-section]", formElement);

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);
        var hintAdapter = createLegacyAdapter(hintElement);

        rangeland.form = formElement;
        rangeland.info = infoAdapter;
        rangeland.status = statusAdapter;
        rangeland.stacktrace = stacktraceAdapter;
        rangeland.rq_job = rqJobAdapter;
        rangeland.hint = hintAdapter;
        rangeland.statusPanelEl = statusPanelElement || null;
        rangeland.stacktracePanelEl = stacktracePanelElement || null;
        rangeland.statusSpinnerEl = spinnerElement || null;
        rangeland.infoElement = infoElement;
        rangeland.command_btn_id = "btn_build_rangeland_cover";

        rangeland.attach_status_stream(rangeland, {
            element: statusPanelElement,
            form: formElement,
            channel: "rangeland_cover",
            runId: window.runid || window.runId || null,
            stacktrace: stacktracePanelElement ? { element: stacktracePanelElement } : null,
            spinner: spinnerElement
        });

        function resetCompletionSeen() {
            rangeland._completion_seen = false;
        }

        rangeland.poll_completion_event = "RANGELAND_COVER_BUILD_TASK_COMPLETED";
        resetCompletionSeen();

        function emit(eventName, payload) {
            if (!rangelandEvents || typeof rangelandEvents.emit !== "function") {
                return;
            }
            rangelandEvents.emit(eventName, payload || {});
        }

        function resetStatus(taskMsg) {
            if (infoAdapter && typeof infoAdapter.text === "function") {
                infoAdapter.text("");
            }
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(taskMsg ? taskMsg + "..." : "");
            }
            rangeland.hideStacktrace();
            if (stacktraceAdapter && typeof stacktraceAdapter.text === "function") {
                stacktraceAdapter.text("");
            } else if (stacktraceElement) {
                stacktraceElement.textContent = "";
            }
        }

        function setStatusMessage(message) {
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(message || "");
            } else if (statusElement) {
                statusElement.textContent = message || "";
            }
        }

        function handleError(error, contextMessage) {
            var payload = toResponsePayload(http, error);
            rangeland.pushResponseStacktrace(rangeland, payload);
            var message = resolveErrorMessage(payload, "Request failed.");
            setStatusMessage(contextMessage || message || "Request failed.");
        }

        rangeland.hideStacktrace = function () {
            if (stacktraceAdapter && typeof stacktraceAdapter.hide === "function") {
                stacktraceAdapter.hide();
            }
            if (stacktraceElement) {
                stacktraceElement.hidden = true;
                stacktraceElement.style.display = "none";
            }
        };

        rangeland.showStacktrace = function () {
            if (stacktraceAdapter && typeof stacktraceAdapter.show === "function") {
                stacktraceAdapter.show();
            }
            if (stacktraceElement) {
                stacktraceElement.hidden = false;
                if (stacktraceElement.style.display === "none") {
                    stacktraceElement.style.removeProperty("display");
                }
            }
        };

        rangeland.showHideControls = function (mode) {
            if (!rapSectionElement) {
                return;
            }
            if (parseInteger(mode, 0) === 2) {
                dom.show(rapSectionElement);
            } else {
                dom.hide(rapSectionElement);
            }
        };

        rangeland.setMode = function (mode) {
            var state = readFormState(forms, formElement);
            var nextMode = parseInteger(mode, state.mode);
            var rapYearValue = state.rapYear;

            var previousMode = rangeland.mode;
            var previousRapYear = rangeland.rap_year;

            rangeland.mode = nextMode;
            rangeland.rap_year = rapYearValue;

            var rapYearLabel = rapYearValue === null || rapYearValue === undefined ? "" : String(rapYearValue);
            var taskMsg = "Setting Mode to " + nextMode + (rapYearLabel ? " (" + rapYearLabel + ")" : "");
            resetStatus(taskMsg);

            rangeland.showHideControls(nextMode);

            http.postJson(url_for_run("tasks/set_rangeland_cover_mode/"), {
                mode: nextMode,
                rap_year: rapYearValue
            }, { form: formElement }).then(function (result) {
                var response = result && result.body ? result.body : null;
                if (response && (response.error || response.errors)) {
                    rangeland.pushResponseStacktrace(rangeland, response);
                } else {
                    setStatusMessage(taskMsg + "... Success");
                }
            }).catch(function (error) {
                handleError(error, "Failed to set rangeland cover mode.");
            });

            if (nextMode !== previousMode) {
                emit("rangeland:mode:changed", { mode: nextMode });
            }
            if (rapYearValue !== previousRapYear) {
                emit("rangeland:rap-year:changed", { year: rapYearValue });
            }
        };

        rangeland.handleModeChange = function (mode) {
            if (mode === undefined || mode === null) {
                rangeland.setMode();
                return;
            }
            rangeland.setMode(parseInteger(mode, 0));
        };

        rangeland.handleRapYearChange = function () {
            rangeland.setMode();
        };

        rangeland.build = function () {
            var state = readFormState(forms, formElement);
            var taskMsg = "Building rangeland cover";

            resetStatus(taskMsg);
            resetCompletionSeen();
            emit("rangeland:run:started", {
                mode: state.mode,
                defaults: state.defaults
            });

            if (typeof rangeland.connect_status_stream === "function") {
                rangeland.connect_status_stream(rangeland);
            }

            http.postJson(url_for_run("tasks/build_rangeland_cover/"), {
                rap_year: state.rapYear,
                defaults: state.defaults
            }, { form: formElement }).then(function (result) {
                var response = result && result.body ? result.body : null;
                if (response && !response.error && !response.errors) {
                    var jobId = response.job_id || null;
                    var submittedMessage = jobId ? taskMsg + "... Submitted (job " + jobId + ")" : taskMsg + "... Submitted";
                    setStatusMessage(submittedMessage);
                    if (typeof rangeland.append_status_message === "function" && jobId) {
                        rangeland.append_status_message(rangeland, "build_rangeland_cover job submitted: " + jobId);
                    }
                    if (typeof rangeland.set_rq_job_id === "function") {
                        rangeland.poll_completion_event = "RANGELAND_COVER_BUILD_TASK_COMPLETED";
                        rangeland.set_rq_job_id(rangeland, jobId);
                    }
                } else if (response) {
                    rangeland.pushResponseStacktrace(rangeland, response);
                    emit("rangeland:run:failed", { error: response, mode: state.mode });
                    if (typeof rangeland.set_rq_job_id === "function") {
                        rangeland.set_rq_job_id(rangeland, null);
                    }
                    if (typeof rangeland.disconnect_status_stream === "function") {
                        rangeland.disconnect_status_stream(rangeland);
                    }
                    if (typeof rangeland.reset_status_spinner === "function") {
                        rangeland.reset_status_spinner(rangeland);
                    }
                }
            }).catch(function (error) {
                handleError(error, "Failed to build rangeland cover.");
                emit("rangeland:run:failed", { error: error, mode: state.mode });
                if (typeof rangeland.set_rq_job_id === "function") {
                    rangeland.set_rq_job_id(rangeland, null);
                }
                if (typeof rangeland.disconnect_status_stream === "function") {
                    rangeland.disconnect_status_stream(rangeland);
                }
                if (typeof rangeland.reset_status_spinner === "function") {
                    rangeland.reset_status_spinner(rangeland);
                }
            });
        };

        rangeland.report = function () {
            http.request(url_for_run("report/rangeland_cover/"), {
                method: "GET",
                headers: { Accept: "text/html,application/xhtml+xml" }
            }).then(function (result) {
                var html = typeof result.body === "string" ? result.body : "";
                if (infoAdapter && typeof infoAdapter.html === "function") {
                    infoAdapter.html(html);
                } else if (infoElement) {
                    infoElement.innerHTML = html;
                }
                emit("rangeland:report:loaded", { html: html });
            }).catch(function (error) {
                handleError(error, "Failed to load rangeland cover report.");
                emit("rangeland:report:failed", { error: error });
            });
        };

        var baseTriggerEvent = rangeland.triggerEvent.bind(rangeland);
        rangeland.triggerEvent = function (eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === "RANGELAND_COVER_BUILD_TASK_COMPLETED") {
                if (rangeland._completion_seen) {
                    return baseTriggerEvent(eventName, payload);
                }
                rangeland._completion_seen = true;
                rangeland.disconnect_status_stream(rangeland);
                try {
                    SubcatchmentDelineation.getInstance().enableColorMap("rangeland_cover");
                } catch (err) {
                    console.warn("[RangelandCover] Failed to enable Subcatchment color map", err);
                }
                rangeland.report();
                emit("rangeland:run:completed", payload || {});
            }

            return baseTriggerEvent(eventName, payload);
        };

        function ensureDelegates() {
            if (rangeland._delegates) {
                return;
            }

            rangeland._delegates = [];

            rangeland._delegates.push(dom.delegate(formElement, "change", "[data-rangeland-role=\"mode\"]", function (event) {
                event.preventDefault();
                var modeAttr = this.getAttribute("data-rangeland-mode");
                var nextMode = modeAttr !== null ? modeAttr : this.value;
                rangeland.handleModeChange(nextMode);
            }));

            rangeland._delegates.push(dom.delegate(formElement, "change", "[data-rangeland-input=\"rap-year\"]", function () {
                rangeland.handleRapYearChange();
            }));

            rangeland._delegates.push(dom.delegate(formElement, "click", "[data-rangeland-action=\"build\"]", function (event) {
                event.preventDefault();
                rangeland.build();
            }));
        }

        ensureDelegates();

        var initialState = readFormState(forms, formElement);
        rangeland.mode = initialState.mode;
        rangeland.rap_year = initialState.rapYear;
        rangeland.showHideControls(initialState.mode);
        emit("rangeland:config:loaded", {
            mode: initialState.mode,
            rapYear: initialState.rapYear,
            defaults: initialState.defaults
        });

        var bootstrapState = {
            reportTriggered: false,
            modeApplied: false
        };

        rangeland.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            var controllerContext = helper && typeof helper.getControllerContext === "function"
                ? helper.getControllerContext(ctx, "rangelandCover")
                : {};

            var jobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "build_rangeland_cover_rq")
                : null;
            if (!jobId && controllerContext.job_id) {
                jobId = controllerContext.job_id;
            }
            if (!jobId) {
                var jobIds = ctx && (ctx.jobIds || ctx.jobs);
                if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "build_rangeland_cover_rq")) {
                    var jobIdValue = jobIds.build_rangeland_cover_rq;
                    if (jobIdValue !== undefined && jobIdValue !== null) {
                        jobId = String(jobIdValue);
                    }
                }
            }
            if (typeof rangeland.set_rq_job_id === "function") {
                rangeland.set_rq_job_id(rangeland, jobId);
            }

            var mode = controllerContext.mode;
            if (mode === undefined && ctx.data && ctx.data.rangelandCover) {
                mode = ctx.data.rangelandCover.mode;
            }
            if (!bootstrapState.modeApplied && typeof rangeland.setMode === "function") {
                try {
                    rangeland.setMode(mode);
                } catch (err) {
                    console.warn("[RangelandCover] Failed to apply bootstrap mode", err);
                }
                bootstrapState.modeApplied = true;
            }

            var hasCovers = controllerContext.hasCovers;
            if (hasCovers === undefined && ctx.data && ctx.data.rangelandCover) {
                hasCovers = ctx.data.rangelandCover.hasCovers;
            }

            if (hasCovers && !bootstrapState.reportTriggered && typeof rangeland.report === "function") {
                rangeland.report();
                bootstrapState.reportTriggered = true;
                try {
                    SubcatchmentDelineation.getInstance().enableColorMap("rangeland_cover");
                } catch (err) {
                    console.warn("[RangelandCover] Failed to enable Subcatchment color map", err);
                }
            }

            return rangeland;
        };

        return rangeland;
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
    globalThis.RangelandCover = RangelandCover;
}
