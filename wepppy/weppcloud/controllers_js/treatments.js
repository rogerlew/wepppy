/* ----------------------------------------------------------------------------
 * Treatments
 * Doc: controllers_js/README.md — Treatments Controller Reference (2025 helper migration)
 * ----------------------------------------------------------------------------
 */
var Treatments = (function () {
    var instance;

    var MODE_PANEL_MAP = {
        1: "#treatments_mode1_controls",
        4: "#treatments_mode4_controls"
    };

    var EVENT_NAMES = [
        "treatments:list:loaded",
        "treatments:scenario:updated",
        "treatments:mode:changed",
        "treatments:mode:error",
        "treatments:selection:changed",
        "treatments:run:started",
        "treatments:run:submitted",
        "treatments:run:error",
        "treatments:job:started",
        "treatments:job:completed",
        "treatments:job:failed",
        "treatments:status:updated"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (!dom || typeof dom.ensureElement !== "function") {
            throw new Error("Treatments controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Treatments controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("Treatments controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Treatments controller requires WCEvents helpers.");
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

    function parseMode(value, fallback) {
        if (value === undefined || value === null || value === "") {
            return fallback;
        }
        var parsed = parseInt(value, 10);
        if (Number.isNaN(parsed)) {
            return fallback;
        }
        return parsed;
    }

    function getOptionSnapshot(selectElement) {
        if (!selectElement || !selectElement.options) {
            return [];
        }
        return Array.prototype.slice.call(selectElement.options).map(function (option) {
            return {
                value: option.value,
                label: option.textContent,
                selected: Boolean(option.selected)
            };
        });
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var events = helpers.events;

        var treatments = controlBase();
        var treatmentsEvents = null;

        if (events && typeof events.createEmitter === "function") {
            var emitterBase = events.createEmitter();
            if (typeof events.useEventMap === "function") {
                treatmentsEvents = events.useEventMap(EVENT_NAMES, emitterBase);
            } else {
                treatmentsEvents = emitterBase;
            }
        }

        if (treatmentsEvents) {
            treatments.events = treatmentsEvents;
        }

        var formElement = dom.ensureElement("#treatments_form", "Treatments form not found.");
        var infoElement = dom.qs("[data-treatments-role=\"info\"]", formElement) || dom.qs("#info", formElement);
        var statusElement = dom.qs("[data-treatments-role=\"status\"]", formElement) || dom.qs("#status", formElement);
        var stacktraceElement = dom.qs("[data-treatments-role=\"stacktrace\"]", formElement) || dom.qs("#stacktrace", formElement);
        var statusPanelEl = dom.qs("#treatments_status_panel");
        var stacktracePanelEl = dom.qs("#treatments_stacktrace_panel");
        var hintElement = dom.qs("[data-treatments-role=\"hint\"]") || dom.qs("#hint_build_treatments");
        var rqJobElement = dom.qs("[data-treatments-role=\"job\"]", formElement) || dom.qs("#rq_job", formElement);
        var selectionElement = dom.qs("[data-treatments-role=\"selection\"]", formElement) || dom.qs("#treatments_single_selection", formElement);

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var hintAdapter = createLegacyAdapter(hintElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);

        treatments.form = formElement;
        treatments.info = infoAdapter;
        treatments.status = statusAdapter;
        treatments.stacktrace = stacktraceAdapter;
        treatments.statusPanelEl = statusPanelEl || null;
        treatments.stacktracePanelEl = stacktracePanelEl || null;
        treatments.statusStream = null;
        treatments.command_btn_id = "btn_build_treatments";
        treatments.hint = hintAdapter;
        treatments.rq_job = rqJobAdapter;

        var spinnerElement = statusPanelEl ? statusPanelEl.querySelector("#braille") : null;
        treatments.statusSpinnerEl = spinnerElement;

        function snapshotForm() {
            try {
                return forms.serializeForm(formElement, { format: "json" }) || {};
            } catch (err) {
                return {};
            }
        }

        function getSelectionValue() {
            if (!selectionElement) {
                return null;
            }
            var value = selectionElement.value;
            if (value === undefined || value === null || value === "") {
                return null;
            }
            return String(value);
        }

        function applyModeToRadios(modeValue) {
            var radios = formElement.querySelectorAll("input[name=\"treatments_mode\"]");
            if (!radios) {
                return;
            }
            Array.prototype.slice.call(radios).forEach(function (radio) {
                radio.checked = String(radio.value) === String(modeValue);
            });
        }

        function updateScenarioEmit(source) {
            if (!treatmentsEvents) {
                return;
            }
            treatmentsEvents.emit("treatments:scenario:updated", {
                mode: treatments.mode,
                selection: getSelectionValue(),
                source: source || "controller"
            });
        }

        function emitStatus(message, meta) {
            if (!message) {
                return;
            }
            if (treatments.statusStream && typeof treatments.statusStream.append === "function") {
                treatments.statusStream.append(message, meta || null);
            } else if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(message);
            } else if (statusElement) {
                statusElement.innerHTML = message;
            }
            if (hintAdapter && typeof hintAdapter.text === "function") {
                hintAdapter.text(message);
            } else if (hintElement) {
                hintElement.textContent = message;
            }
            if (treatmentsEvents) {
                treatmentsEvents.emit("treatments:status:updated", {
                    message: message,
                    meta: meta || null
                });
            }
        }

        treatments.appendStatus = emitStatus;

        treatments.hideStacktrace = function () {
            if (stacktraceAdapter && typeof stacktraceAdapter.hide === "function") {
                stacktraceAdapter.hide();
                return;
            }
            if (stacktraceElement) {
                stacktraceElement.hidden = true;
                stacktraceElement.style.display = "none";
            }
        };

        function resetBeforeRun(taskMessage) {
            if (infoAdapter && typeof infoAdapter.text === "function") {
                infoAdapter.text("");
            } else if (infoElement) {
                infoElement.textContent = "";
            }
            if (stacktraceAdapter && typeof stacktraceAdapter.text === "function") {
                stacktraceAdapter.text("");
            } else if (stacktraceElement) {
                stacktraceElement.textContent = "";
            }
            treatments.hideStacktrace();
            if (rqJobAdapter && typeof rqJobAdapter.text === "function") {
                rqJobAdapter.text("");
            }
            if (hintAdapter && typeof hintAdapter.text === "function") {
                hintAdapter.text("");
            } else if (hintElement) {
                hintElement.textContent = "";
            }
            if (taskMessage) {
                emitStatus(taskMessage + "...");
            }
        }

        function handleModeError(error, normalized, selectionValue) {
            var payload = toResponsePayload(http, error);
            treatments.pushResponseStacktrace(treatments, payload);
            if (treatmentsEvents) {
                treatmentsEvents.emit("treatments:mode:error", {
                    mode: normalized,
                    selection: selectionValue,
                    error: payload,
                    cause: error
                });
            }
        }

        function postModeUpdate(normalized, selectionValue) {
            return http.postJson(url_for_run("tasks/set_treatments_mode/"), {
                mode: normalized,
                single_selection: selectionValue
            }, { form: formElement }).then(function (result) {
                var response = result && result.body ? result.body : null;
                if (response && response.Success === false) {
                    treatments.pushResponseStacktrace(treatments, response);
                    if (treatmentsEvents) {
                        treatmentsEvents.emit("treatments:mode:error", {
                            mode: normalized,
                            selection: selectionValue,
                            response: response
                        });
                    }
                    return response;
                }
                updateScenarioEmit("server");
                return response;
            }).catch(function (error) {
                handleModeError(error, normalized, selectionValue);
                throw error;
            });
        }

        treatments.updateModeUI = function (mode) {
            var normalized = parseMode(mode, treatments.mode);
            Object.keys(MODE_PANEL_MAP).forEach(function (key) {
                var selector = MODE_PANEL_MAP[key];
                if (!selector) {
                    return;
                }
                var panel = dom.qs(selector);
                if (!panel) {
                    return;
                }
                if (parseInt(key, 10) === normalized) {
                    dom.show(panel);
                } else {
                    dom.hide(panel);
                }
            });
            applyModeToRadios(normalized);
        };

        treatments.setMode = function (mode, options) {
            var normalized = parseMode(
                mode !== undefined ? mode : (snapshotForm().treatments_mode),
                treatments.mode !== undefined ? treatments.mode : -1
            );
            var selectionValue = getSelectionValue();

            treatments.mode = normalized;
            treatments.updateModeUI(normalized);

            if (treatmentsEvents) {
                treatmentsEvents.emit("treatments:mode:changed", {
                    mode: normalized,
                    selection: selectionValue,
                    source: options && options.source ? options.source : "controller"
                });
            }

            if (options && options.skipRequest) {
                updateScenarioEmit(options.source || "controller");
                return Promise.resolve({ skipped: true });
            }

            return postModeUpdate(normalized, selectionValue);
        };

        treatments.build = function () {
            var taskMessage = "Building treatments";
            resetBeforeRun(taskMessage);

            if (treatmentsEvents) {
                treatmentsEvents.emit("treatments:run:started", {
                    mode: treatments.mode,
                    selection: getSelectionValue()
                });
            }

            treatments.connect_status_stream(treatments);

            var formData = new FormData(formElement);

            http.request(url_for_run("rq/api/build_treatments"), {
                method: "POST",
                body: formData,
                form: formElement
            }).then(function (result) {
                var response = result && result.body ? result.body : null;
                if (response && response.Success === true) {
                    var message = "build_treatments job submitted: " + response.job_id;
                    emitStatus(message);
                    treatments.set_rq_job_id(treatments, response.job_id);
                    if (treatmentsEvents) {
                        treatmentsEvents.emit("treatments:run:submitted", {
                            jobId: response.job_id,
                            mode: treatments.mode,
                            selection: getSelectionValue()
                        });
                    }
                    return;
                }
                if (response) {
                    treatments.pushResponseStacktrace(treatments, response);
                    if (treatmentsEvents) {
                        treatmentsEvents.emit("treatments:run:error", {
                            mode: treatments.mode,
                            selection: getSelectionValue(),
                            response: response
                        });
                    }
                }
            }).catch(function (error) {
                var payload = toResponsePayload(http, error);
                treatments.pushResponseStacktrace(treatments, payload);
                if (treatmentsEvents) {
                    treatmentsEvents.emit("treatments:run:error", {
                        mode: treatments.mode,
                        selection: getSelectionValue(),
                        error: payload,
                        cause: error
                    });
                }
            });
        };

        treatments.report = function () {
            http.request(url_for_run("report/treatments/"), {
                method: "GET",
                headers: { Accept: "text/html,application/xhtml+xml" }
            }).then(function (result) {
                var html = typeof result.body === "string" ? result.body : "";
                if (infoAdapter && typeof infoAdapter.html === "function") {
                    infoAdapter.html(html);
                } else if (infoElement) {
                    infoElement.innerHTML = html;
                }
                if (treatmentsEvents) {
                    treatmentsEvents.emit("treatments:list:loaded", {
                        html: html,
                        mode: treatments.mode,
                        selection: getSelectionValue()
                    });
                }
            }).catch(function (error) {
                var payload = toResponsePayload(http, error);
                treatments.pushResponseStacktrace(treatments, payload);
                if (treatmentsEvents) {
                    treatmentsEvents.emit("treatments:run:error", {
                        error: payload,
                        cause: error,
                        action: "report"
                    });
                }
            });
        };

        treatments.restore = function (mode, singleSelection) {
            var normalized = parseMode(mode, treatments.mode !== undefined ? treatments.mode : -1);
            var selectionValue = singleSelection === undefined || singleSelection === null ? null : String(singleSelection);

            treatments.mode = normalized;
            applyModeToRadios(normalized);
            if (selectionElement && selectionValue !== null) {
                selectionElement.value = selectionValue;
            }
            treatments.updateModeUI(normalized);
            updateScenarioEmit("restore");
        };

        var baseTriggerEvent = treatments.triggerEvent.bind(treatments);
        treatments.triggerEvent = function (eventName, detail) {
            if (eventName) {
                var normalized = String(eventName).toUpperCase();
                if (treatmentsEvents) {
                    if (normalized.indexOf("STARTED") >= 0 || normalized.indexOf("QUEUED") >= 0) {
                        treatmentsEvents.emit("treatments:job:started", detail || {});
                    }
                    if (normalized.indexOf("COMPLETED") >= 0 || normalized.indexOf("FINISHED") >= 0 || normalized.indexOf("SUCCESS") >= 0) {
                        treatmentsEvents.emit("treatments:job:completed", detail || {});
                        treatments.disconnect_status_stream(treatments);
                    }
                    if (normalized.indexOf("FAILED") >= 0 || normalized.indexOf("ERROR") >= 0) {
                        treatmentsEvents.emit("treatments:job:failed", detail || {});
                    }
                }
            }
            baseTriggerEvent(eventName, detail);
        };

        function setupStatusStream() {
            treatments.detach_status_stream(treatments);
            var spinnerEl = treatments.statusSpinnerEl;
            if (!spinnerEl && treatments.statusPanelEl) {
                spinnerEl = treatments.statusPanelEl.querySelector("#braille");
                treatments.statusSpinnerEl = spinnerEl;
            }
            treatments.attach_status_stream(treatments, {
                element: treatments.statusPanelEl,
                form: formElement,
                channel: "treatments",
                stacktrace: treatments.stacktracePanelEl ? { element: treatments.stacktracePanelEl } : null,
                spinner: spinnerEl,
                logLimit: 200
            });
        }

        setupStatusStream();

        var delegates = [];

        delegates.push(dom.delegate(formElement, "change", "[data-treatments-role=\"mode\"]", function () {
            var modeAttr = this.getAttribute("data-treatments-mode");
            var normalized = parseMode(modeAttr, snapshotForm().treatments_mode);
            treatments.setMode(normalized, { source: "mode-change" });
        }));

        if (selectionElement) {
            delegates.push(dom.delegate(formElement, "change", "[data-treatments-role=\"selection\"]", function () {
                if (treatmentsEvents) {
                    treatmentsEvents.emit("treatments:selection:changed", {
                        selection: getSelectionValue(),
                        mode: treatments.mode
                    });
                }
                treatments.setMode(treatments.mode, { source: "selection-change" });
            }));
        }

        delegates.push(dom.delegate(formElement, "click", "[data-treatments-action=\"build\"]", function (event) {
            event.preventDefault();
            treatments.build();
        }));

        treatments._delegates = delegates;

        var initialSnapshot = snapshotForm();
        var initialMode = parseMode(initialSnapshot.treatments_mode, -1);
        var initialSelection = initialSnapshot.treatments_single_selection;
        if (initialSelection === undefined && selectionElement) {
            initialSelection = selectionElement.value;
        }

        treatments.mode = initialMode;
        applyModeToRadios(initialMode);
        if (selectionElement && initialSelection !== undefined && initialSelection !== null) {
            selectionElement.value = String(initialSelection);
        }
        treatments.updateModeUI(initialMode);

        var optionSnapshot = getOptionSnapshot(selectionElement);
        if (treatmentsEvents && optionSnapshot.length > 0) {
            treatmentsEvents.emit("treatments:list:loaded", {
                options: optionSnapshot,
                mode: treatments.mode,
                selection: getSelectionValue()
            });
        }
        updateScenarioEmit("init");

        treatments.destroy = function () {
            if (delegates && delegates.length) {
                delegates.forEach(function (unsubscribe) {
                    if (typeof unsubscribe === "function") {
                        try {
                            unsubscribe();
                        } catch (err) {
                            // ignore
                        }
                    }
                });
                delegates = [];
            }
            treatments.detach_status_stream(treatments);
        };

        return treatments;
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
    globalThis.Treatments = Treatments;
}
