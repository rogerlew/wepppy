/* ----------------------------------------------------------------------------
 * Soil
 * ----------------------------------------------------------------------------
 */
var Soil = (function () {
    var instance;

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;

        if (!dom || typeof dom.ensureElement !== "function") {
            throw new Error("Soil controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Soil controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("Soil controller requires WCHttp helpers.");
        }

        return { dom: dom, forms: forms, http: http };
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

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;

        var soil = controlBase();

        var formElement = dom.ensureElement("#soil_form", "Soil form not found.");
        var infoElement = dom.qs("#soil_form #info");
        var statusElement = dom.qs("#soil_form #status");
        var stacktraceElement = dom.qs("#soil_form #stacktrace");
        var rqJobElement = dom.qs("#soil_form #rq_job");
        var hintElement = dom.qs("#soil_form #hint_build_soil");

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);
        var hintAdapter = createLegacyAdapter(hintElement);

        soil.form = formElement;
        soil.info = infoAdapter;
        soil.status = statusAdapter;
        soil.stacktrace = stacktraceAdapter;
        soil.rq_job = rqJobAdapter;
        soil.command_btn_id = "btn_build_soil";
        soil.hint = hintAdapter;
        soil.statusPanelEl = dom.qs("#soil_status_panel");
        soil.stacktracePanelEl = dom.qs("#soil_stacktrace_panel");
        var spinnerElement = soil.statusPanelEl ? soil.statusPanelEl.querySelector("#braille") : null;

        soil.attach_status_stream(soil, {
            element: soil.statusPanelEl,
            channel: "soils",
            stacktrace: soil.stacktracePanelEl ? { element: soil.stacktracePanelEl } : null,
            spinner: spinnerElement
        });

        var modePanels = [
            dom.qs("#soil_mode0_controls"),
            dom.qs("#soil_mode1_controls"),
            dom.qs("#soil_mode2_controls"),
            dom.qs("#soil_mode3_controls"),
            dom.qs("#soil_mode4_controls")
        ];

        var baseTriggerEvent = soil.triggerEvent.bind(soil);
        soil.triggerEvent = function (eventName, payload) {
            if (eventName === "SOILS_BUILD_TASK_COMPLETED") {
                soil.disconnect_status_stream(soil);
                soil.report();
                try {
                    SubcatchmentDelineation.getInstance().enableColorMap("dom_soil");
                } catch (err) {
                    console.warn("[Soil] Failed to enable Subcatchment color map", err);
                }
            }

            baseTriggerEvent(eventName, payload);
        };

        soil.hideStacktrace = function () {
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
            soil.reset_panel_state(soil, { taskMessage: taskMsg });
        }

        function handleError(error) {
            soil.pushResponseStacktrace(soil, toResponsePayload(http, error));
        }

        soil.handleModeChange = function (mode) {
            if (mode === undefined) {
                soil.setMode();
                return;
            }
            soil.setMode(parseInteger(mode, 0));
        };

        soil.handleSingleSelectionInput = function () {
            soil.setMode();
        };

        soil.handleDbSelectionChange = function () {
            soil.setMode();
        };

        soil.build = function () {
            var taskMsg = "Building soil";
            resetStatus(taskMsg);

            soil.connect_status_stream(soil);

            var params = forms.serializeForm(formElement, { format: "url" });

            http.postForm(url_for_run("rq/api/build_soils"), params, { form: formElement })
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && response.Success === true) {
                        soil.append_status_message(soil, "build_soils_rq job submitted: " + response.job_id);
                        soil.set_rq_job_id(soil, response.job_id);
                    } else if (response) {
                        soil.pushResponseStacktrace(soil, response);
                    }
                })
                .catch(handleError);
        };

        soil.report = function () {
            http.request(url_for_run("report/soils/"), {
                method: "GET",
                headers: { Accept: "text/html,application/xhtml+xml" }
            }).then(function (result) {
                var html = typeof result.body === "string" ? result.body : "";
                if (infoAdapter && typeof infoAdapter.html === "function") {
                    infoAdapter.html(html);
                } else if (infoElement) {
                    infoElement.innerHTML = html;
                }
            }).catch(handleError);
        };

        soil.restore = function (mode) {
            var modeValue = parseInteger(mode, 0);
            var radio = document.getElementById("soil_mode" + modeValue);
            if (radio) {
                radio.checked = true;
            }
            soil.showHideControls(modeValue);
        };

        soil.set_ksflag = function (state) {
            var taskMsg = "Setting ksflag (" + state + ")";
            resetStatus(taskMsg);

            http.postJson(url_for_run("tasks/set_soils_ksflag/"), { ksflag: Boolean(state) }, { form: formElement })
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && response.Success === true) {
                        soil.append_status_message(soil, taskMsg + "... Success");
                    } else if (response) {
                        soil.pushResponseStacktrace(soil, response);
                    }
                })
                .catch(handleError);
        };

        soil.set_disturbed_sol_ver = function (value) {
            if (value === undefined || value === null || value === "") {
                return;
            }

            var taskMsg = "Setting disturbed sol_ver to " + value;
            resetStatus(taskMsg);

            http.postJson(url_for_run("tasks/set_disturbed_sol_ver/"), { sol_ver: value }, { form: formElement })
                .then(function (result) {
                    var response = result && result.body ? result.body : null;
                    if (response && response.Success === true) {
                        soil.append_status_message(soil, taskMsg + "... Success");
                    } else if (response) {
                        soil.pushResponseStacktrace(soil, response);
                    }
                })
                .catch(handleError);
        };

        soil.setMode = function (mode) {
            var payload = forms.serializeForm(formElement, { format: "json" }) || {};
            var resolvedMode = mode;
            if (resolvedMode === undefined || resolvedMode === null) {
                resolvedMode = parseInteger(payload.soil_mode, 0);
            }
            resolvedMode = parseInteger(resolvedMode, 0);

            var singleSelectionRaw = payload.soil_single_selection;
            var singleDbSelection = payload.soil_single_dbselection || null;
            var singleSelection = singleSelectionRaw === undefined || singleSelectionRaw === null || singleSelectionRaw === ""
                ? null
                : parseInteger(singleSelectionRaw, null);

            soil.mode = resolvedMode;

            var taskMsg = "Setting Mode to " + resolvedMode;
            resetStatus(taskMsg);

            http.postJson(url_for_run("tasks/set_soil_mode/"), {
                mode: resolvedMode,
                soil_single_selection: singleSelection,
                soil_single_dbselection: singleDbSelection
            }, { form: formElement }).then(function (result) {
                var response = result && result.body ? result.body : null;
                if (response && response.Success === true) {
                    soil.append_status_message(soil, taskMsg + "... Success");
                } else if (response) {
                    soil.pushResponseStacktrace(soil, response);
                }
            }).catch(handleError);

            soil.showHideControls(resolvedMode);
        };

        soil.showHideControls = function (mode) {
            var numericMode = parseInteger(mode, -1);

            if (numericMode === -1) {
                modePanels.forEach(function (panel) {
                    if (panel) {
                        dom.hide(panel);
                    }
                });
                return;
            }

            if (numericMode < 0 || numericMode >= modePanels.length) {
                throw new Error("ValueError: unknown mode");
            }

            modePanels.forEach(function (panel, index) {
                if (!panel) {
                    return;
                }
                if (index === numericMode) {
                    dom.show(panel);
                } else {
                    dom.hide(panel);
                }
            });
        };

        var modeInputs = formElement.querySelectorAll('input[name="soil_mode"]');
        Array.prototype.forEach.call(modeInputs, function (input) {
            input.addEventListener("change", function (event) {
                soil.handleModeChange(event.target.value);
            });
        });

        var singleSelectionInput = document.getElementById("soil_single_selection");
        if (singleSelectionInput) {
            singleSelectionInput.addEventListener("input", soil.handleSingleSelectionInput);
            singleSelectionInput.addEventListener("change", soil.handleSingleSelectionInput);
        }

        var dbSelectionInput = document.getElementById("soil_single_dbselection");
        if (dbSelectionInput) {
            dbSelectionInput.addEventListener("change", soil.handleDbSelectionChange);
        }

        var ksflagCheckbox = document.getElementById("checkbox_run_flowpaths");
        if (ksflagCheckbox) {
            ksflagCheckbox.addEventListener("change", function (event) {
                soil.set_ksflag(event.target.checked);
            });
        }

        var solVerSelect = document.getElementById("sol_ver");
        if (solVerSelect) {
            solVerSelect.addEventListener("change", function (event) {
                soil.set_disturbed_sol_ver(event.target.value);
            });
        }

        var buildButton = document.getElementById("btn_build_soil");
        if (buildButton) {
            buildButton.addEventListener("click", function (event) {
                event.preventDefault();
                soil.build();
            });
        }

        var bootstrapState = {
            buildTriggered: false
        };

        soil.bootstrap = function bootstrap(context) {
            var ctx = context || {};
            var helper = window.WCControllerBootstrap || null;
            var controllerContext = helper && typeof helper.getControllerContext === "function"
                ? helper.getControllerContext(ctx, "soil")
                : {};

            var jobId = helper && typeof helper.resolveJobId === "function"
                ? helper.resolveJobId(ctx, "build_soils_rq")
                : null;
            if (!jobId && controllerContext.jobId) {
                jobId = controllerContext.jobId;
            }
            if (!jobId) {
                var jobIds = ctx && (ctx.jobIds || ctx.jobs);
                if (jobIds && typeof jobIds === "object" && Object.prototype.hasOwnProperty.call(jobIds, "build_soils_rq")) {
                    var value = jobIds.build_soils_rq;
                    if (value !== undefined && value !== null) {
                        jobId = String(value);
                    }
                }
            }

            if (typeof soil.set_rq_job_id === "function") {
                soil.set_rq_job_id(soil, jobId);
            }

            var settings = (ctx.data && ctx.data.soils) || {};
            var restoreMode = controllerContext.mode !== undefined && controllerContext.mode !== null
                ? controllerContext.mode
                : settings.mode;

            if (typeof soil.restore === "function") {
                soil.restore(restoreMode);
            }

            var dbSelection = controllerContext.singleDbSelection;
            if (dbSelection === undefined) {
                dbSelection = settings.singleDbSelection;
            }
            if (dbSelection === undefined) {
                dbSelection = settings.single_dbselection;
            }

            if (dbSelection !== undefined && dbSelection !== null) {
                var dbSelectElement = document.getElementById("soil_single_dbselection");
                if (dbSelectElement) {
                    dbSelectElement.value = String(dbSelection);
                }
            }

            var hasSoils = controllerContext.hasSoils;
            if (hasSoils === undefined) {
                hasSoils = settings.hasSoils;
            }
            if (hasSoils && !bootstrapState.buildTriggered && typeof soil.triggerEvent === "function") {
                soil.triggerEvent("SOILS_BUILD_TASK_COMPLETED");
                bootstrapState.buildTriggered = true;
            }

            return soil;
        };

        return soil;
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
    globalThis.Soil = Soil;
}
