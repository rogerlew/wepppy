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

    function readFormState(forms, formElement) {
        var values = forms.serializeForm(formElement, { format: "json" }) || {};
        var defaults = {
            bunchgrass: parseCoverValue(values.bunchgrass_cover),
            forbs: parseCoverValue(values.forbs_cover),
            sodgrass: parseCoverValue(values.sodgrass_cover),
            shrub: parseCoverValue(values.shrub_cover),
            basal: parseCoverValue(values.basal_cover),
            rock: parseCoverValue(values.rock_cover),
            litter: parseCoverValue(values.litter_cover),
            cryptogams: parseCoverValue(values.cryptogams_cover)
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
            setStatusMessage(contextMessage || payload.Error || "Request failed.");
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

            http.postJson("tasks/set_rangeland_cover_mode/", {
                mode: nextMode,
                rap_year: rapYearValue
            }, { form: formElement }).then(function (result) {
                var response = result && result.body ? result.body : null;
                if (response && response.Success === true) {
                    setStatusMessage(taskMsg + "... Success");
                } else if (response) {
                    rangeland.pushResponseStacktrace(rangeland, response);
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
            emit("rangeland:run:started", {
                mode: state.mode,
                defaults: state.defaults
            });

            http.postJson("tasks/build_rangeland_cover/", {
                rap_year: state.rapYear,
                defaults: state.defaults
            }, { form: formElement }).then(function (result) {
                var response = result && result.body ? result.body : null;
                if (response && response.Success === true) {
                    setStatusMessage(taskMsg + "... Success");
                    rangeland.triggerEvent("RANGELAND_COVER_BUILD_TASK_COMPLETED", {
                        mode: state.mode,
                        defaults: state.defaults
                    });
                } else if (response) {
                    rangeland.pushResponseStacktrace(rangeland, response);
                    emit("rangeland:run:failed", { error: response, mode: state.mode });
                }
            }).catch(function (error) {
                handleError(error, "Failed to build rangeland cover.");
                emit("rangeland:run:failed", { error: error, mode: state.mode });
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
                rangeland.disconnect_status_stream(rangeland);
                try {
                    SubcatchmentDelineation.getInstance().enableColorMap("rangeland_cover");
                } catch (err) {
                    console.warn("[RangelandCover] Failed to enable Subcatchment color map", err);
                }
                rangeland.report();
                emit("rangeland:run:completed", payload || {});
            }

            baseTriggerEvent(eventName, payload);
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
