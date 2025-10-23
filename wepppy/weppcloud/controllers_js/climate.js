/* ----------------------------------------------------------------------------
 * Climate (Pure UI + Legacy Console)
 * Doc: controllers_js/README.md — Climate Controller Reference (2024 helper migration)
 * ----------------------------------------------------------------------------
 */
var Climate = (function () {
    "use strict";

    var instance;

    var EVENT_NAMES = [
        "climate:dataset:changed",
        "climate:dataset:mode",
        "climate:station:mode",
        "climate:station:selected",
        "climate:station:list:loading",
        "climate:station:list:loaded",
        "climate:build:started",
        "climate:build:completed",
        "climate:build:failed",
        "climate:precip:mode",
        "climate:upload:completed",
        "climate:upload:failed",
        "climate:gridmet:updated"
    ];

    function ensureHelpers() {
        var dom = window.WCDom;
        var forms = window.WCForms;
        var http = window.WCHttp;
        var events = window.WCEvents;

        if (
            !dom ||
            typeof dom.ensureElement !== "function" ||
            typeof dom.delegate !== "function" ||
            typeof dom.show !== "function" ||
            typeof dom.hide !== "function"
        ) {
            throw new Error("Climate controller requires WCDom helpers.");
        }
        if (!forms || typeof forms.serializeForm !== "function") {
            throw new Error("Climate controller requires WCForms helpers.");
        }
        if (!http || typeof http.request !== "function") {
            throw new Error("Climate controller requires WCHttp helpers.");
        }
        if (!events || typeof events.createEmitter !== "function") {
            throw new Error("Climate controller requires WCEvents helpers.");
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

    function parseJsonScript(id) {
        if (!id) {
            return null;
        }
        var element = document.getElementById(id);
        if (!element) {
            return null;
        }
        var raw = element.textContent || element.innerText || "";
        if (!raw) {
            return null;
        }
        try {
            return JSON.parse(raw);
        } catch (err) {
            console.error("[Climate] Failed to parse JSON from #" + id, err);
            return null;
        }
    }

    function ensureArray(value) {
        if (Array.isArray(value)) {
            return value.slice();
        }
        if (value === undefined || value === null) {
            return [];
        }
        return [value];
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

    function toggleChoiceDisabled(input, disabled) {
        if (!input) {
            return;
        }
        var isDisabled = Boolean(disabled);
        input.disabled = isDisabled;
        if (isDisabled) {
            input.setAttribute("aria-disabled", "true");
        } else {
            input.removeAttribute("aria-disabled");
        }
        if (typeof input.closest === "function") {
            var wrapper = input.closest(".wc-choice");
            if (wrapper) {
                if (isDisabled) {
                    wrapper.classList.add("is-disabled");
                } else {
                    wrapper.classList.remove("is-disabled");
                }
            }
        }
    }

    function getRadioValue(radios) {
        if (!radios || radios.length === 0) {
            return null;
        }
        for (var i = 0; i < radios.length; i += 1) {
            if (radios[i] && radios[i].checked) {
                return radios[i].value;
            }
        }
        return null;
    }

    function setRadioValue(radios, targetValue) {
        if (!radios || radios.length === 0) {
            return;
        }
        var normalized = targetValue !== undefined && targetValue !== null ? String(targetValue) : null;
        for (var i = 0; i < radios.length; i += 1) {
            var radio = radios[i];
            if (!radio) {
                continue;
            }
            radio.checked = normalized !== null && String(radio.value) === normalized;
        }
    }

    function createInstance() {
        var helpers = ensureHelpers();
        var dom = helpers.dom;
        var forms = helpers.forms;
        var http = helpers.http;
        var events = helpers.events;

        var climate = controlBase();
        var climateEvents = events.useEventMap(EVENT_NAMES, events.createEmitter());

        var formElement = dom.ensureElement("#climate_form", "Climate form not found.");
        var infoElement = dom.qs("#climate_form #info");
        var statusElement = dom.qs("#climate_form #status");
        var stacktraceElement = dom.qs("#climate_form #stacktrace");
        var rqJobElement = dom.qs("#climate_form #rq_job");
        var hintUploadElement = dom.qs("#hint_upload_cli");
        var hintBuildElement = dom.qs("#hint_build_climate");

        var infoAdapter = createLegacyAdapter(infoElement);
        var statusAdapter = createLegacyAdapter(statusElement);
        var stacktraceAdapter = createLegacyAdapter(stacktraceElement);
        var rqJobAdapter = createLegacyAdapter(rqJobElement);
        var uploadHintAdapter = createLegacyAdapter(hintUploadElement);
        var buildHintAdapter = createLegacyAdapter(hintBuildElement);

        climate.form = formElement;
        climate.info = infoAdapter;
        climate.status = statusAdapter;
        climate.stacktrace = stacktraceAdapter;
        climate.rq_job = rqJobAdapter;
        climate.command_btn_id = "btn_build_climate";
        climate.events = climateEvents;

        climate.statusPanelEl = dom.qs("#climate_status_panel");
        climate.stacktracePanelEl = dom.qs("#climate_stacktrace_panel");
        climate.statusSpinnerEl = climate.statusPanelEl ? climate.statusPanelEl.querySelector("#braille") : null;
        climate.statusStream = null;

        climate.datasetMessage = dom.qs("#climate_dataset_message");
        climate.stationSelect = dom.qs("#climate_station_selection");
        climate.monthliesContainer = dom.qs("#climate_monthlies");
        climate.catalogHiddenInput = dom.qs("#climate_catalog_id");
        climate.modeHiddenInput = dom.qs("#climate_mode");
        climate.userDefinedSection = dom.qs("#climate_userdefined");
        climate.cligenSection = dom.qs("#climate_cligen");
        climate.hintUpload = uploadHintAdapter;
        climate.hintBuild = buildHintAdapter;

        climate.datasetRadios = dom.qsa("input[name=\"climate_dataset_choice\"]", formElement);
        climate.stationModeRadios = dom.qsa("input[name=\"climatestation_mode\"]", formElement);
        climate.spatialModeRadios = dom.qsa("input[name=\"climate_spatialmode\"]", formElement);
        climate.precipModeRadios = dom.qsa("input[name=\"precip_scaling_mode\"]", formElement);
        climate.buildModeRadios = dom.qsa("input[name=\"climate_build_mode\"]", formElement);
        climate.gridmetCheckbox = dom.qs("#checkbox_use_gridmet_wind_when_applicable");

        climate.sectionNodes = dom.qsa("[data-climate-section]", formElement);
        climate.precipSections = dom.qsa("[data-precip-section]", formElement);

        climate.catalogData = ensureArray(parseJsonScript("climate_catalog_data"));
        climate.datasetMap = {};
        climate.catalogData.forEach(function (dataset) {
            if (dataset && dataset.catalog_id) {
                climate.datasetMap[dataset.catalog_id] = dataset;
            }
        });

        climate.datasetId = null;
        climate._previousStationMode = null;
        climate._delegates = [];

        function handleError(error) {
            climate.pushResponseStacktrace(climate, toResponsePayload(http, error));
        }

        climate.appendStatus = function (message, meta) {
            if (!message) {
                return;
            }
            if (climate.statusStream && typeof climate.statusStream.append === "function") {
                climate.statusStream.append(message, meta || null);
                return;
            }
            if (statusAdapter && typeof statusAdapter.html === "function") {
                statusAdapter.html(message);
                return;
            }
            if (statusElement) {
                statusElement.innerHTML = message;
            }
        };

        climate.attachStatusStream = function () {
            climate.detach_status_stream(climate);

            if (!climate.statusSpinnerEl && climate.statusPanelEl) {
                climate.statusSpinnerEl = climate.statusPanelEl.querySelector("#braille");
            }

            var stacktraceConfig = climate.stacktracePanelEl ? { element: climate.stacktracePanelEl } : null;

            climate.attach_status_stream(climate, {
                element: climate.statusPanelEl,
                form: formElement,
                channel: "climate",
                runId: window.runid || window.runId || null,
                logLimit: 400,
                stacktrace: stacktraceConfig,
                spinner: climate.statusSpinnerEl,
                autoConnect: true
            });

            return climate.statusStream;
        };

        function formatDatasetMessage(dataset) {
            var lines = [];
            if (!dataset) {
                return lines;
            }
            if (dataset.help_text) {
                lines.push(dataset.help_text);
            } else if (dataset.description) {
                lines.push(dataset.description);
            } else {
                lines.push("Configure the dataset-specific options below.");
            }
            if (dataset.rap_compatible) {
                lines.push("Compatible with RAP time-series workflows.");
            }
            if (dataset.ui_exposed === false) {
                lines.push("This dataset is read-only in the Pure UI and managed through catalog metadata.");
            }
            if (dataset.metadata && dataset.metadata.year_bounds) {
                var bounds = dataset.metadata.year_bounds;
                var minYear = bounds.min || bounds.min_start || bounds.start;
                var maxYear = bounds.max || bounds.max_end || bounds.end;
                if (minYear || maxYear) {
                    var rangeText = "Available years";
                    if (minYear && maxYear) {
                        rangeText += ": " + minYear + "–" + maxYear + ".";
                    } else if (minYear) {
                        rangeText += " from " + minYear + ".";
                    } else if (maxYear) {
                        rangeText += " through " + maxYear + ".";
                    }
                    lines.push(rangeText);
                }
            }
            return lines;
        }

        climate.getDataset = function (catalogId) {
            if (catalogId && climate.datasetMap[catalogId]) {
                return climate.datasetMap[catalogId];
            }
            if (climate.catalogData.length > 0) {
                return climate.catalogData[0];
            }
            return null;
        };

        climate.updateDatasetMessage = function (dataset) {
            if (!climate.datasetMessage) {
                return;
            }
            climate.datasetMessage.innerHTML = "";
            var messages = formatDatasetMessage(dataset);
            if (!messages.length) {
                return;
            }
            messages.forEach(function (line, index) {
                var paragraph = document.createElement("p");
                paragraph.className = index === 0 ? "wc-alert__body" : "wc-alert__meta";
                paragraph.textContent = line;
                climate.datasetMessage.appendChild(paragraph);
            });
        };

        climate.updateSectionVisibility = function (dataset) {
            if (!climate.sectionNodes || climate.sectionNodes.length === 0) {
                return;
            }
            var inputs = ensureArray(dataset && dataset.inputs).map(function (value) {
                return String(value || "");
            });
            var spatialDefined = ensureArray(dataset && dataset.spatial_modes).length > 1;
            climate.sectionNodes.forEach(function (node) {
                if (!node || !node.getAttribute) {
                    return;
                }
                var key = node.getAttribute("data-climate-section");
                if (!key) {
                    return;
                }
                var shouldShow = inputs.indexOf(key) !== -1;
                if (key === "spatial_mode") {
                    shouldShow = shouldShow && spatialDefined;
                }
                node.hidden = !shouldShow;
            });
        };

        climate.updateSpatialModes = function (dataset, options) {
            var opts = options || {};
            if (!climate.spatialModeRadios || climate.spatialModeRadios.length === 0) {
                return;
            }
            var allowed = ensureArray(dataset && dataset.spatial_modes)
                .map(function (value) {
                    return parseInteger(value, null);
                })
                .filter(function (value) {
                    return value !== null && !Number.isNaN(value);
                });
            if (!allowed.length) {
                allowed = [0];
            }
            var defaultMode = dataset && dataset.default_spatial_mode !== undefined && dataset.default_spatial_mode !== null
                ? parseInteger(dataset.default_spatial_mode, allowed[0])
                : allowed[0];
            var currentValue = parseInteger(getRadioValue(climate.spatialModeRadios), defaultMode);
            var nextValue = currentValue;

            climate.spatialModeRadios.forEach(function (radio) {
                if (!radio) {
                    return;
                }
                var value = parseInteger(radio.value, null);
                var enabled = value !== null && allowed.indexOf(value) !== -1;
                toggleChoiceDisabled(radio, !enabled);
                if (!enabled && value === currentValue) {
                    nextValue = defaultMode;
                }
            });

            if (Number.isNaN(currentValue) || nextValue !== currentValue) {
                climate.setSpatialMode(nextValue, { silent: true });
            } else if (opts.silent) {
                climate.setSpatialMode(currentValue, { silent: true });
            }
        };

        climate.updateStationVisibility = function (dataset) {
            var section = document.getElementById("climate_station_section");
            if (!section) {
                return;
            }
            var stationModes = ensureArray(dataset && dataset.station_modes)
                .map(function (value) {
                    return parseInteger(value, null);
                })
                .filter(function (value) {
                    return value !== null && !Number.isNaN(value);
                });
            if (!stationModes.length) {
                stationModes = [0];
            }
            var shouldShow = stationModes.some(function (value) {
                return value !== 4;
            });
            section.hidden = !shouldShow;
        };

        climate.updateStationModes = function (dataset, options) {
            var opts = options || {};
            if (!climate.stationModeRadios || climate.stationModeRadios.length === 0) {
                return;
            }
            var allowed = ensureArray(dataset && dataset.station_modes)
                .map(function (value) {
                    return parseInteger(value, null);
                })
                .filter(function (value) {
                    return value !== null && !Number.isNaN(value);
                });
            if (!allowed.length) {
                allowed = [0];
            }
            var currentValue = parseInteger(getRadioValue(climate.stationModeRadios), allowed[0]);
            var nextValue = currentValue;

            climate.stationModeRadios.forEach(function (radio) {
                if (!radio) {
                    return;
                }
                var value = parseInteger(radio.value, null);
                var enabled = value !== null && allowed.indexOf(value) !== -1;
                toggleChoiceDisabled(radio, !enabled);
                if (!enabled && value === currentValue) {
                    nextValue = allowed[0];
                }
            });

            if (Number.isNaN(currentValue) || nextValue !== currentValue) {
                climate.setStationMode(nextValue, { silent: true, skipRefresh: true });
            } else if (opts.silent) {
                climate.setStationMode(currentValue, { silent: true, skipRefresh: true });
            }

            if (!(opts.skipStationRefresh || (allowed.length === 1 && allowed[0] === 4))) {
                climate.refreshStationSelection();
            } else if (allowed.length === 1 && allowed[0] === 4 && climate.stationSelect) {
                climate.stationSelect.innerHTML = "";
            }
        };

        climate.applyDataset = function (catalogId, options) {
            var dataset = climate.getDataset(catalogId);
            if (!dataset) {
                return null;
            }
            climate.datasetId = dataset.catalog_id || null;
            if (climate.catalogHiddenInput) {
                climate.catalogHiddenInput.value = dataset.catalog_id || "";
            }
            if (climate.modeHiddenInput) {
                climate.modeHiddenInput.value = dataset.climate_mode !== undefined && dataset.climate_mode !== null
                    ? String(dataset.climate_mode)
                    : "";
            }
            if (climate.datasetRadios && climate.datasetRadios.length > 0) {
                setRadioValue(climate.datasetRadios, dataset.catalog_id);
            }
            climate.updateDatasetMessage(dataset);
            climate.updateSectionVisibility(dataset);
            climate.updateSpatialModes(dataset, options || {});
            climate.updateStationModes(dataset, options || {});
            climate.updateStationVisibility(dataset);
            climate.events.emit("climate:dataset:mode", {
                catalogId: dataset.catalog_id,
                climateMode: dataset.climate_mode
            });
            return dataset;
        };

        climate.handleDatasetChange = function (catalogId) {
            infoAdapter.text("");
            stacktraceAdapter.text("");

            var dataset = climate.applyDataset(catalogId, { skipPersist: true, skipStationRefresh: true });
            if (!dataset) {
                return;
            }
            climate.events.emit("climate:dataset:changed", {
                catalogId: dataset.catalog_id,
                dataset: dataset
            });

            climate.setCatalogMode(dataset.catalog_id, dataset.climate_mode)
                .then(function () {
                    var stationModes = ensureArray(dataset.station_modes)
                        .map(function (value) {
                            return parseInteger(value, null);
                        })
                        .filter(function (value) {
                            return value !== null && !Number.isNaN(value);
                        });
                    if (stationModes.length === 1 && stationModes[0] === 4 && climate.stationSelect) {
                        climate.stationSelect.innerHTML = "";
                    } else {
                        climate.refreshStationSelection();
                    }
                    climate.viewStationMonthlies();
                })
                .catch(function (error) {
                    handleError(error);
                });
        };

        climate.setCatalogMode = function (catalogId, mode) {
            infoAdapter.text("");
            stacktraceAdapter.text("");

            var payload = {};
            var normalizedMode = parseInteger(mode, null);
            if (normalizedMode !== null && !Number.isNaN(normalizedMode)) {
                payload.mode = normalizedMode;
            }
            if (catalogId !== undefined && catalogId !== null && catalogId !== "") {
                payload.catalog_id = catalogId;
            }
            return http.postJson("tasks/set_climate_mode/", payload, { form: formElement })
                .then(function (response) {
                    var body = response.body || {};
                    if (body.Success === true) {
                        climate.triggerEvent("CLIMATE_SETMODE_TASK_COMPLETED", body);
                        return body;
                    }
                    climate.pushResponseStacktrace(climate, body);
                    return Promise.reject(body);
                })
                .catch(function (error) {
                    handleError(error);
                    return Promise.reject(error);
                });
        };

        climate.setStationMode = function (mode, options) {
            var opts = options || {};
            var parsedMode = parseInteger(mode, -1);
            setRadioValue(climate.stationModeRadios, parsedMode);

            if (parsedMode !== 4) {
                climate._previousStationMode = parsedMode;
            }

            if (opts.silent) {
                if (!opts.skipRefresh) {
                    climate.refreshStationSelection();
                }
                climate.events.emit("climate:station:mode", { mode: parsedMode, silent: true });
                return Promise.resolve(null);
            }

            infoAdapter.text("");
            stacktraceAdapter.text("");

            climate.events.emit("climate:station:mode", { mode: parsedMode, silent: false });

            return http.postJson("tasks/set_climatestation_mode/", { mode: parsedMode }, { form: formElement })
                .then(function (response) {
                    var body = response.body || {};
                    if (body.Success === true) {
                        climate.triggerEvent("CLIMATE_SETSTATIONMODE_TASK_COMPLETED", body);
                        if (!opts.skipRefresh) {
                            climate.refreshStationSelection();
                        }
                        return body;
                    }
                    climate.pushResponseStacktrace(climate, body);
                    return Promise.reject(body);
                })
                .catch(function (error) {
                    handleError(error);
                    return Promise.reject(error);
                });
        };

        climate.setSpatialMode = function (mode, options) {
            var opts = options || {};
            var parsedMode = parseInteger(mode, 0);
            setRadioValue(climate.spatialModeRadios, parsedMode);

            if (opts.silent) {
                return Promise.resolve(null);
            }

            infoAdapter.text("");
            stacktraceAdapter.text("");

            return http.postJson("tasks/set_climate_spatialmode/", { spatialmode: parsedMode }, { form: formElement })
                .then(function (response) {
                    var body = response.body || {};
                    if (body.Success === true) {
                        climate.triggerEvent("CLIMATE_SETSPATIALMODE_TASK_COMPLETED", body);
                        return body;
                    }
                    climate.pushResponseStacktrace(climate, body);
                    return Promise.reject(body);
                })
                .catch(function (error) {
                    handleError(error);
                    return Promise.reject(error);
                });
        };

        climate.refreshStationSelection = function () {
            if (!climate.stationSelect) {
                return;
            }
            var mode = parseInteger(getRadioValue(climate.stationModeRadios), -1);
            if (mode === -1 || mode === 4) {
                return;
            }

            infoAdapter.text("");
            stacktraceAdapter.text("");

            var endpoint = null;
            if (mode === 0) {
                endpoint = "view/closest_stations/";
            } else if (mode === 1) {
                endpoint = "view/heuristic_stations/";
            } else if (mode === 2) {
                endpoint = "view/eu_heuristic_stations/";
            } else if (mode === 3) {
                endpoint = "view/au_heuristic_stations/";
            }
            if (!endpoint) {
                return;
            }

            climate.events.emit("climate:station:list:loading", { mode: mode });

            http.request(endpoint, { params: { mode: mode } })
                .then(function (response) {
                    var body = response.body;
                    climate.stationSelect.innerHTML = typeof body === "string" ? body : "";
                    climate.triggerEvent("CLIMATE_SETSTATION_TASK_COMPLETED", { mode: mode });
                    climate.events.emit("climate:station:list:loaded", { mode: mode });
                })
                .catch(function (error) {
                    handleError(error);
                });
        };

        climate.setStation = function (station) {
            var selectedStation = station;
            if (selectedStation === undefined || selectedStation === null) {
                selectedStation = climate.stationSelect ? climate.stationSelect.value : null;
            }
            if (!selectedStation) {
                return;
            }

            infoAdapter.text("");
            stacktraceAdapter.text("");

            climate.events.emit("climate:station:selected", { station: selectedStation });

            http.postJson("tasks/set_climatestation/", { station: selectedStation }, { form: formElement })
                .then(function (response) {
                    var body = response.body || {};
                    if (body.Success === true) {
                        climate.triggerEvent("CLIMATE_SETSTATION_TASK_COMPLETED", body);
                        return;
                    }
                    climate.pushResponseStacktrace(climate, body);
                })
                .catch(function (error) {
                    handleError(error);
                });
        };

        climate.viewStationMonthlies = function () {
            if (!climate.monthliesContainer) {
                return;
            }
            var project = window.Project && typeof window.Project.getInstance === "function" ? window.Project.getInstance() : null;
            http.request("view/climate_monthlies/", { params: {} })
                .then(function (response) {
                    var body = response.body;
                    climate.monthliesContainer.innerHTML = typeof body === "string" ? body : "";
                    if (project && typeof project.set_preferred_units === "function") {
                        project.set_preferred_units();
                    }
                })
                .catch(function (error) {
                    handleError(error);
                });
        };

        climate.handlePrecipScalingModeChange = function (mode) {
            var parsedMode = parseInteger(mode, -1);
            if (climate.precipModeRadios && climate.precipModeRadios.length > 0) {
                setRadioValue(climate.precipModeRadios, parsedMode);
            }
            if (climate.precipSections) {
                climate.precipSections.forEach(function (section) {
                    if (!section || !section.getAttribute) {
                        return;
                    }
                    var key = parseInteger(section.getAttribute("data-precip-section"), -1);
                    section.hidden = key !== parsedMode;
                });
            }
            climate.events.emit("climate:precip:mode", { mode: parsedMode });
        };

        climate.report = function () {
            var project = window.Project && typeof window.Project.getInstance === "function" ? window.Project.getInstance() : null;
            http.request(url_for_run("report/climate/"), { params: {}, method: "GET" })
                .then(function (response) {
                    var body = response.body;
                    if (infoAdapter && typeof infoAdapter.html === "function") {
                        infoAdapter.html(typeof body === "string" ? body : "");
                    } else if (infoElement) {
                        infoElement.innerHTML = typeof body === "string" ? body : "";
                    }
                    if (project && typeof project.set_preferred_units === "function") {
                        project.set_preferred_units();
                    }
                })
                .catch(function (error) {
                    handleError(error);
                });
        };

        climate.build = function () {
            var taskMsg = "Building climate";
            infoAdapter.text("");
            statusAdapter.html(taskMsg + "...");
            stacktraceAdapter.text("");
            climate.appendStatus(taskMsg + "...");

            var payload = forms.serializeForm(formElement, { format: "json" });
            climate.events.emit("climate:build:started", { payload: payload });

            http.postJson("rq/api/build_climate", payload, { form: formElement })
                .then(function (response) {
                    var body = response.body || {};
                    if (body.Success === true) {
                        var message = "build_climate job submitted: " + body.job_id;
                        statusAdapter.html(message);
                        climate.appendStatus(message);
                        climate.set_rq_job_id(climate, body.job_id);
                        climate.events.emit("climate:build:completed", { jobId: body.job_id, payload: payload });
                        return;
                    }
                    climate.pushResponseStacktrace(climate, body);
                    climate.events.emit("climate:build:failed", { payload: payload, response: body });
                })
                .catch(function (error) {
                    handleError(error);
                    climate.events.emit("climate:build:failed", { payload: payload, error: error });
                });
        };

        climate.upload_cli = function () {
            infoAdapter.text("");
            stacktraceAdapter.text("");

            var formData = new FormData(formElement);
            http.request("tasks/upload_cli/", {
                method: "POST",
                body: formData,
                form: formElement
            }).then(function (response) {
                var body = response.body || {};
                if (body.Success === true) {
                    climate.appendStatus("User-defined climate uploaded successfully.");
                    climate.triggerEvent("CLIMATE_BUILD_TASK_COMPLETED", body);
                    climate.events.emit("climate:upload:completed", body);
                    return;
                }
                climate.pushResponseStacktrace(climate, body);
                climate.events.emit("climate:upload:failed", body);
            }).catch(function (error) {
                handleError(error);
                climate.events.emit("climate:upload:failed", { error: error });
            });
        };

        climate.set_use_gridmet_wind_when_applicable = function (state) {
            var normalizedState = Boolean(state);
            statusAdapter.html("Setting use_gridmet_wind_when_applicable (" + normalizedState + ")...");
            stacktraceAdapter.text("");

            http.postJson("tasks/set_use_gridmet_wind_when_applicable/", { state: normalizedState }, { form: formElement })
                .then(function (response) {
                    var body = response.body || {};
                    if (body.Success === true) {
                        var message = "use_gridmet_wind_when_applicable updated.";
                        statusAdapter.html(message);
                        climate.appendStatus(message);
                        climate.events.emit("climate:gridmet:updated", { state: normalizedState });
                        return;
                    }
                    climate.pushResponseStacktrace(climate, body);
                })
                .catch(function (error) {
                    handleError(error);
                });
        };

        climate.setBuildMode = function (mode, options) {
            var opts = options || {};
            var parsedMode = parseInteger(mode, 0);
            if (climate.buildModeRadios && climate.buildModeRadios.length > 0) {
                setRadioValue(climate.buildModeRadios, parsedMode);
            }
            if (parsedMode === 1) {
                if (climate.userDefinedSection) {
                    dom.show(climate.userDefinedSection);
                }
                if (climate.cligenSection) {
                    dom.hide(climate.cligenSection);
                }
                if (!opts.skipStationMode) {
                    climate.setStationMode(4, { silent: false, skipRefresh: true });
                    if (climate.stationSelect) {
                        climate.stationSelect.innerHTML = "";
                    }
                }
            } else {
                if (climate.userDefinedSection) {
                    dom.hide(climate.userDefinedSection);
                }
                if (climate.cligenSection) {
                    dom.show(climate.cligenSection);
                }
                if (!opts.skipStationMode) {
                    var restoreMode = climate._previousStationMode;
                    if (restoreMode === null || restoreMode === undefined || restoreMode === 4) {
                        restoreMode = 0;
                    }
                    climate.setStationMode(restoreMode, { silent: false });
                }
            }
        };

        climate.handleBuildModeChange = function (value) {
            climate.setBuildMode(value, { skipStationMode: false });
        };

        climate.handleModeChange = function (value) {
            var parsedMode = parseInteger(value, null);
            if (climate.modeHiddenInput) {
                climate.modeHiddenInput.value = parsedMode !== null && !Number.isNaN(parsedMode) ? String(parsedMode) : "";
            }
            climate.setCatalogMode(climate.datasetId, parsedMode)
                .then(function () {
                    climate.viewStationMonthlies();
                })
                .catch(function (error) {
                    handleError(error);
                });
        };

        var baseTriggerEvent = climate.triggerEvent.bind(climate);
        climate.triggerEvent = function (eventName, payload) {
            var normalized = eventName ? String(eventName).toUpperCase() : "";
            if (normalized === "CLIMATE_SETSTATIONMODE_TASK_COMPLETED") {
                climate.refreshStationSelection();
                climate.viewStationMonthlies();
            } else if (normalized === "CLIMATE_SETSTATION_TASK_COMPLETED") {
                climate.viewStationMonthlies();
            } else if (normalized === "CLIMATE_BUILD_TASK_COMPLETED" || normalized === "CLIMATE_BUILD_COMPLETE") {
                climate.report();
            }
            baseTriggerEvent(eventName, payload);
        };

        if (typeof dom.delegate === "function") {
            climate._delegates.push(dom.delegate(formElement, "change", "[data-climate-action=\"dataset\"]", function (event, matched) {
                event.preventDefault();
                var value = matched ? matched.value : null;
                climate.handleDatasetChange(value);
            }));

            climate._delegates.push(dom.delegate(formElement, "change", "[data-climate-action=\"station-mode\"]", function (event, matched) {
                event.preventDefault();
                var value = matched ? matched.value : null;
                climate.setStationMode(value);
            }));

            climate._delegates.push(dom.delegate(formElement, "change", "[data-climate-action=\"spatial-mode\"]", function (event, matched) {
                event.preventDefault();
                var value = matched ? matched.value : null;
                climate.setSpatialMode(value);
            }));

            climate._delegates.push(dom.delegate(formElement, "change", "[data-climate-action=\"mode\"]", function (event, matched) {
                event.preventDefault();
                var value = matched ? matched.value : null;
                climate.handleModeChange(value);
            }));

            climate._delegates.push(dom.delegate(formElement, "change", "[data-climate-action=\"station-select\"]", function (event, matched) {
                event.preventDefault();
                var value = matched ? matched.value : null;
                climate.setStation(value);
            }));

            climate._delegates.push(dom.delegate(formElement, "change", "[data-climate-action=\"precip-mode\"]", function (event, matched) {
                event.preventDefault();
                var value = matched ? matched.value : null;
                climate.handlePrecipScalingModeChange(value);
            }));

            climate._delegates.push(dom.delegate(formElement, "change", "[data-climate-action=\"gridmet-wind\"]", function (event, matched) {
                event.preventDefault();
                var checked = matched ? matched.checked : false;
                climate.set_use_gridmet_wind_when_applicable(checked);
            }));

            climate._delegates.push(dom.delegate(formElement, "change", "[data-climate-action=\"build-mode\"]", function (event, matched) {
                event.preventDefault();
                var value = matched ? matched.value : null;
                climate.handleBuildModeChange(value);
            }));

            climate._delegates.push(dom.delegate(formElement, "click", "[data-climate-action=\"upload-cli\"]", function (event) {
                event.preventDefault();
                climate.upload_cli();
            }));

            climate._delegates.push(dom.delegate(formElement, "click", "[data-climate-action=\"build\"]", function (event) {
                event.preventDefault();
                climate.build();
            }));
        }

        var initialDatasetId = null;
        if (climate.catalogHiddenInput && climate.catalogHiddenInput.value) {
            initialDatasetId = climate.catalogHiddenInput.value;
        }
        if (!initialDatasetId && climate.datasetRadios && climate.datasetRadios.length > 0) {
            var radioValue = getRadioValue(climate.datasetRadios);
            if (radioValue !== null) {
                initialDatasetId = radioValue;
            }
        }
        if (initialDatasetId) {
            climate.applyDataset(initialDatasetId, { skipPersist: true, skipStationRefresh: true });
        }

        var initialPrecip = dom.qs("input[name=\"precip_scaling_mode\"]:checked", formElement);
        if (initialPrecip) {
            climate.handlePrecipScalingModeChange(initialPrecip.value);
        } else {
            climate.handlePrecipScalingModeChange(null);
        }

        if (climate.buildModeRadios && climate.buildModeRadios.length > 0) {
            var initialBuildMode = getRadioValue(climate.buildModeRadios);
            climate.setBuildMode(initialBuildMode, { skipStationMode: true });
        }

        climate.attachStatusStream();
        climate.refreshStationSelection();
        climate.viewStationMonthlies();

        return climate;
    }

    function initialise() {
        if (!instance) {
            instance = createInstance();
        }
        return instance;
    }

    if (typeof document !== "undefined") {
        var bootstrapClimate = function () {
            try {
                Climate.getInstance();
            } catch (err) {
                console.error("[Climate] Initialisation failed:", err);
            }
        };
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", bootstrapClimate, { once: true });
        } else {
            setTimeout(bootstrapClimate, 0);
        }
    }

    return {
        getInstance: function () {
            return initialise();
        }
    };
}());

if (typeof globalThis !== "undefined") {
    globalThis.Climate = Climate;
}
