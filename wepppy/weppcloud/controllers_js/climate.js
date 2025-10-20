/* ----------------------------------------------------------------------------
 * Climate (Pure UI)
 * ----------------------------------------------------------------------------
 */
var Climate = (function () {
    var instance;

    function parseJSONScript(id) {
        var el = document.getElementById(id);
        if (!el) {
            return null;
        }
        var text = el.textContent || el.innerText || "";
        if (!text.length) {
            return null;
        }
        try {
            return JSON.parse(text);
        } catch (err) {
            console.error("Failed to parse JSON from element #" + id, err);
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

    function intOr(value, fallback) {
        var parsed = parseInt(value, 10);
        return isNaN(parsed) ? fallback : parsed;
    }

    function createInstance() {
        var that = controlBase();

        that.form = $("#climate_form");
        that.status = $("#climate_form #status");
        that.info = $("#climate_form #info");
        that.stacktrace = $("#climate_form #stacktrace");
        that.rq_job = $("#climate_form #rq_job");
        that.command_btn_id = "btn_build_climate";
        that.statusPanelEl = document.getElementById("climate_status_panel");
        that.stacktracePanelEl = document.getElementById("climate_stacktrace_panel");
        that.statusStream = null;

        that.catalogData = parseJSONScript("climate_catalog_data") || [];
        that.datasetMap = {};
        that.catalogData.forEach(function (dataset) {
            if (dataset && dataset.catalog_id) {
                that.datasetMap[dataset.catalog_id] = dataset;
            }
        });

        that.datasetRadios = $("input[name='climate_dataset_choice']");
        that.stationModeRadios = $("input[name='climatestation_mode']");
        that.spatialRadios = $("input[name='climate_spatialmode']");
        that.precipRadios = $("input[name='precip_scaling_mode']");

        that.datasetMessage = $("#climate_dataset_message");
        that.stationSelect = $("#climate_station_selection");
        that.monthliesContainer = $("#climate_monthlies");
        that.uploadButton = $("#btn_upload_cli");
        that.buildButton = $("#btn_build_climate");
        that.hintUpload = $("#hint_upload_cli");
        that.hintBuild = $("#hint_build_climate");
        that.catalogHiddenInput = $("#climate_catalog_id");
        that.modeHiddenInput = $("#climate_mode");

        that.sectionNodes = Array.prototype.slice.call(document.querySelectorAll("[data-climate-section]"));
        that.precipSections = Array.prototype.slice.call(document.querySelectorAll("[data-precip-section]"));

        that.datasetId = that.catalogHiddenInput.val() || (that.catalogData.length ? that.catalogData[0].catalog_id : null);

        const baseTriggerEvent = that.triggerEvent.bind(that);
        that.triggerEvent = function (eventName, payload) {
            var normalized = (eventName || "").toString().toUpperCase();
            if (normalized === "CLIMATE_SETSTATIONMODE_TASK_COMPLETED") {
                that.refreshStationSelection();
                that.viewStationMonthlies();
            } else if (normalized === "CLIMATE_SETSTATION_TASK_COMPLETED") {
                that.viewStationMonthlies();
            } else if (normalized === "CLIMATE_BUILD_TASK_COMPLETED" || normalized === "CLIMATE_BUILD_COMPLETE") {
                that.report();
            }

            baseTriggerEvent(eventName, payload);
        };

        that.datasetRadios.on("change", function () {
            that.handleDatasetChange(this.value);
        });

        that.stationModeRadios.on("change", function () {
            that.setStationMode(this.value);
        });

        that.spatialRadios.on("change", function () {
            that.setSpatialMode(this.value);
        });

        that.precipRadios.on("change", function () {
            that.handlePrecipScalingModeChange(this.value);
        });

        $("#checkbox_use_gridmet_wind_when_applicable").on("change", function () {
            that.set_use_gridmet_wind_when_applicable(this.checked);
        });

        if (that.uploadButton.length) {
            that.uploadButton.on("click", function () {
                that.upload_cli();
            });
        }

        ensureExtended(that);
        that.applyDataset(that.datasetId, { skipPersist: true, skipStationRefresh: true });
        that.handlePrecipScalingModeChange($("input[name='precip_scaling_mode']:checked").val());
        that.refreshStationSelection();
        that.viewStationMonthlies();

        return that;
    }

    function formatDatasetMessage(dataset) {
        var lines = [];
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

        if (!dataset.ui_exposed) {
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

    function ensureExtended(target) {
        if (!target) {
            return null;
        }
        if (!target._climateExtended) {
            extendInstance(target);
            target._climateExtended = true;
        }
        return target;
    }

    function extendInstance(that) {
        that.getDataset = function (catalogId) {
            if (catalogId && that.datasetMap[catalogId]) {
                return that.datasetMap[catalogId];
            }
            if (that.catalogData.length) {
                return that.catalogData[0];
            }
            return null;
        };

        that.applyDataset = function (catalogId, options) {
            var opts = options || {};
            var dataset = that.getDataset(catalogId);
            if (!dataset) {
                return null;
            }

            that.datasetId = dataset.catalog_id;
            that.catalogHiddenInput.val(dataset.catalog_id);
            that.modeHiddenInput.val(dataset.climate_mode);

            that.datasetRadios.each(function () {
                this.checked = (this.value === dataset.catalog_id);
            });

            that.updateDatasetMessage(dataset);
            that.updateSectionVisibility(dataset);
            that.updateSpatialModes(dataset, opts);
            that.updateStationModes(dataset, opts);
            that.updateStationVisibility(dataset);
            return dataset;
        };

        that.updateDatasetMessage = function (dataset) {
            if (!that.datasetMessage.length) {
                return;
            }
            var messages = formatDatasetMessage(dataset);
            that.datasetMessage.empty();
            messages.forEach(function (line, index) {
                var paragraph = $("<p/>", {
                    "class": index === 0 ? "wc-alert__body" : "wc-alert__meta"
                }).text(line);
                that.datasetMessage.append(paragraph);
            });
        };

        that.updateSectionVisibility = function (dataset) {
            var inputs = ensureArray(dataset.inputs).map(function (value) {
                return String(value || "");
            });
            var spatialDefined = ensureArray(dataset.spatial_modes).length > 1;

            that.sectionNodes.forEach(function (node) {
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

        that.updateSpatialModes = function (dataset, options) {
            var opts = options || {};
            var allowed = ensureArray(dataset.spatial_modes).map(function (value) {
                return parseInt(value, 10);
            }).filter(function (value) {
                return !isNaN(value);
            });
            if (!allowed.length) {
                allowed = [0];
            }
            var defaultMode = dataset.default_spatial_mode;
            if (defaultMode === undefined || defaultMode === null) {
                defaultMode = allowed[0];
            }
            defaultMode = parseInt(defaultMode, 10);
            if (isNaN(defaultMode)) {
                defaultMode = allowed[0];
            }

            var current = intOr($("input[name='climate_spatialmode']:checked").val(), defaultMode);
            var newValue = current;

            that.spatialRadios.each(function () {
                var value = parseInt(this.value, 10);
                var enabled = allowed.indexOf(value) !== -1;
                $(this).prop("disabled", !enabled);
                $(this).closest(".wc-choice").toggleClass("is-disabled", !enabled);
                if (!enabled && value === current) {
                    newValue = defaultMode;
                }
            });

            if (newValue !== current || isNaN(current)) {
                that.setSpatialMode(newValue, { silent: true });
            }
        };

        that.updateStationVisibility = function (dataset) {
            var section = document.getElementById("climate_station_section");
            if (!section) {
                return;
            }
            var stationModes = ensureArray(dataset.station_modes).map(function (value) {
                return parseInt(value, 10);
            }).filter(function (value) {
                return !isNaN(value);
            });
            if (!stationModes.length) {
                stationModes = [0];
            }
            var shouldShow = stationModes.some(function (value) {
                return value !== 4;
            });
            section.hidden = !shouldShow;
        };

        that.updateStationModes = function (dataset, options) {
            var opts = options || {};
            var allowed = ensureArray(dataset.station_modes).map(function (value) {
                return parseInt(value, 10);
            }).filter(function (value) {
                return !isNaN(value);
            });
            if (!allowed.length) {
                allowed = [0];
            }

            var current = intOr($("input[name='climatestation_mode']:checked").val(), allowed[0]);
            var newValue = current;

            that.stationModeRadios.each(function () {
                var value = intOr(this.value, -1);
                var enabled = allowed.indexOf(value) !== -1;
                $(this).prop("disabled", !enabled);
                $(this).closest(".wc-choice").toggleClass("is-disabled", !enabled);
                if (!enabled && value === current) {
                    newValue = allowed[0];
                }
            });

            if (newValue !== current || isNaN(current)) {
                that.setStationMode(newValue, { silent: true, skipRefresh: true });
            }

            if (!(opts.skipStationRefresh || allowed.length === 1 && allowed[0] === 4)) {
                that.refreshStationSelection();
            } else if (allowed.length === 1 && allowed[0] === 4) {
                that.stationSelect.empty();
            }
        };

        that.handleDatasetChange = function (catalogId) {
            var dataset = that.applyDataset(catalogId, { skipPersist: false, skipStationRefresh: true });
            if (!dataset) {
                return;
            }
            that.setCatalogMode(dataset.catalog_id, dataset.climate_mode);
            if (dataset.station_modes && dataset.station_modes.indexOf(4) !== -1 && dataset.station_modes.length === 1) {
                that.stationSelect.empty();
            } else {
                that.refreshStationSelection();
            }
            that.viewStationMonthlies();
        };

        that.setCatalogMode = function (catalogId, mode) {
            var dataset = that.getDataset(catalogId);
            if (!dataset) {
                return;
            }
            var climateMode = mode !== undefined ? mode : dataset.climate_mode;
            that.info.text("");
            that.stacktrace.text("");

            $.post({
                url: "tasks/set_climate_mode/",
                data: {
                    mode: climateMode,
                    catalog_id: dataset.catalog_id
                },
                success: function (response) {
                    if (response.Success === true) {
                        that.triggerEvent("CLIMATE_SETMODE_TASK_COMPLETED", response);
                    } else {
                        that.pushResponseStacktrace(that, response);
                    }
                },
                error: function (jqXHR) {
                    that.pushResponseStacktrace(that, jqXHR.responseJSON);
                },
                fail: function (jqXHR, textStatus, errorThrown) {
                    that.pushErrorStacktrace(that, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.setStationMode = function (mode, options) {
            var opts = options || {};
            var parsedMode = intOr(mode, -1);

            that.stationModeRadios.each(function () {
                this.checked = intOr(this.value, -1) === parsedMode;
            });

            if (opts.silent) {
                if (!opts.skipRefresh) {
                    that.refreshStationSelection();
                }
                return;
            }

            that.info.text("");
            that.stacktrace.text("");

            $.post({
                url: "tasks/set_climatestation_mode/",
                data: { mode: parsedMode },
                success: function (response) {
                    if (response.Success === true) {
                        that.triggerEvent("CLIMATE_SETSTATIONMODE_TASK_COMPLETED", response);
                    } else {
                        that.pushResponseStacktrace(that, response);
                    }
                },
                error: function (jqXHR) {
                    that.pushResponseStacktrace(that, jqXHR.responseJSON);
                },
                fail: function (jqXHR, textStatus, errorThrown) {
                    that.pushErrorStacktrace(that, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.setSpatialMode = function (mode, options) {
            var opts = options || {};
            var parsedMode = intOr(mode, 0);

            that.spatialRadios.each(function () {
                this.checked = intOr(this.value, 0) === parsedMode;
            });

            if (opts.silent) {
                return;
            }

            that.info.text("");
            that.stacktrace.text("");

            $.post({
                url: "tasks/set_climate_spatialmode/",
                data: { spatialmode: parsedMode },
                success: function (response) {
                    if (response.Success === true) {
                        that.triggerEvent("CLIMATE_SETSPATIALMODE_TASK_COMPLETED", response);
                    } else {
                        that.pushResponseStacktrace(that, response);
                    }
                },
                error: function (jqXHR) {
                    that.pushResponseStacktrace(that, jqXHR.responseJSON);
                },
                fail: function (jqXHR, textStatus, errorThrown) {
                    that.pushErrorStacktrace(that, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.refreshStationSelection = function () {
            var mode = intOr($("input[name='climatestation_mode']:checked").val(), -1);
            if (mode === -1 || mode === 4) {
                return;
            }

            that.info.text("");
            that.stacktrace.text("");

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

            $.get({
                url: endpoint,
                cache: false,
                data: { mode: mode },
                success: function (response) {
                    that.stationSelect.html(response);
                    that.triggerEvent("CLIMATE_SETSTATION_TASK_COMPLETED");
                },
                error: function (jqXHR) {
                    that.pushResponseStacktrace(that, jqXHR.responseJSON);
                },
                fail: function (jqXHR, textStatus, errorThrown) {
                    that.pushErrorStacktrace(that, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.setStation = function (station) {
            var selectedStation = station;
            if (selectedStation === undefined) {
                selectedStation = that.stationSelect.val();
            }
            if (!selectedStation) {
                return;
            }

            that.info.text("");
            that.stacktrace.text("");

            $.post({
                url: "tasks/set_climatestation/",
                data: { station: selectedStation },
                success: function (response) {
                    if (response.Success === true) {
                        that.triggerEvent("CLIMATE_SETSTATION_TASK_COMPLETED");
                    } else {
                        that.pushResponseStacktrace(that, response);
                    }
                },
                error: function (jqXHR) {
                    that.pushResponseStacktrace(that, jqXHR.responseJSON);
                },
                fail: function (jqXHR, textStatus, errorThrown) {
                    that.pushErrorStacktrace(that, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.viewStationMonthlies = function () {
            var project = Project.getInstance();
            $.get({
                url: "view/climate_monthlies/",
                cache: false,
                success: function (response) {
                    that.monthliesContainer.html(response);
                    project.set_preferred_units();
                },
                error: function (jqXHR) {
                    that.pushResponseStacktrace(that, jqXHR.responseJSON);
                },
                fail: function (jqXHR, textStatus, errorThrown) {
                    that.pushErrorStacktrace(that, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.handlePrecipScalingModeChange = function (mode) {
            var parsedMode = intOr(mode, -1);
            that.precipSections.forEach(function (section) {
                var key = intOr(section.getAttribute("data-precip-section"), -1);
                section.hidden = key !== parsedMode;
            });
        };

        that.appendStatus = function (message, meta) {
            if (that.statusStream && typeof that.statusStream.append === "function") {
                that.statusStream.append(message, meta || null);
            } else if (that.status && that.status.length) {
                that.status.text(message);
            }
        };

        that.attachStatusStream = function () {
            if (typeof StatusStream === "undefined" || !that.statusPanelEl) {
                return null;
            }
            if (that.statusStream) {
                StatusStream.disconnect(that.statusStream);
            }
            var stacktraceConfig = null;
            if (that.stacktracePanelEl) {
                stacktraceConfig = { element: that.stacktracePanelEl };
            }
            that.statusStream = StatusStream.attach({
                element: that.statusPanelEl,
                channel: "climate",
                runId: window.runid || window.runId || null,
                logLimit: 400,
                stacktrace: stacktraceConfig,
                onTrigger: function (detail) {
                    if (detail && detail.event) {
                        that.triggerEvent(detail.event, detail);
                    }
                }
            });
            return that.statusStream;
        };

        that.build = function () {
            var project = Project.getInstance();
            var task_msg = "Building climate";

            that.info.text("");
            that.status.html(task_msg + "...");
            that.stacktrace.text("");
            that.appendStatus(task_msg + "...");

            $.post({
                url: "rq/api/build_climate",
                data: that.form.serialize(),
                success: function (response) {
                    if (response.Success === true) {
                        var message = "build_climate job submitted: " + response.job_id;
                        that.status.html(message);
                        that.appendStatus(message);
                        that.set_rq_job_id(that, response.job_id);
                    } else {
                        that.pushResponseStacktrace(that, response);
                    }
                },
                error: function (jqXHR) {
                    that.pushResponseStacktrace(that, jqXHR.responseJSON);
                },
                fail: function (jqXHR, textStatus, errorThrown) {
                    that.pushErrorStacktrace(that, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.report = function () {
            var project = Project.getInstance();
            $.get({
                url: url_for_run("report/climate/"),
                cache: false,
                success: function (response) {
                    that.info.html(response);
                    project.set_preferred_units();
                },
                error: function (jqXHR) {
                    that.pushResponseStacktrace(that, jqXHR.responseJSON);
                },
                fail: function (jqXHR, textStatus, errorThrown) {
                    that.pushErrorStacktrace(that, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.upload_cli = function () {
            that.info.text("");
            that.stacktrace.text("");
            var formData = new FormData($("#climate_form")[0]);

            $.post({
                url: "tasks/upload_cli/",
                data: formData,
                contentType: false,
                cache: false,
                processData: false,
                success: function (response) {
                    if (response.Success === true) {
                        that.appendStatus("User-defined climate uploaded successfully.");
                        that.triggerEvent("CLIMATE_BUILD_TASK_COMPLETED");
                    } else {
                        that.pushResponseStacktrace(that, response);
                    }
                },
                error: function (jqXHR) {
                    that.pushResponseStacktrace(that, jqXHR.responseJSON);
                },
                fail: function (jqXHR, textStatus, errorThrown) {
                    that.pushErrorStacktrace(that, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.set_use_gridmet_wind_when_applicable = function (state) {
            that.status.html("Setting use_gridmet_wind_when_applicable (" + state + ")...");
            that.stacktrace.text("");

            $.post({
                url: "tasks/set_use_gridmet_wind_when_applicable/",
                data: JSON.stringify({ state: state }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                success: function (response) {
                    if (response.Success === true) {
                        var message = "use_gridmet_wind_when_applicable updated.";
                        that.status.html(message);
                        that.appendStatus(message);
                    } else {
                        that.pushResponseStacktrace(that, response);
                    }
                },
                error: function (jqXHR) {
                    that.pushResponseStacktrace(that, jqXHR.responseJSON);
                },
                fail: function (jqXHR, textStatus, errorThrown) {
                    that.pushErrorStacktrace(that, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that._climateExtended = true;
    }

    function initialise() {
        if (!instance) {
            instance = createInstance();
            ensureExtended(instance);
            if (instance && typeof instance.attachStatusStream === "function") {
                instance.attachStatusStream();
            }
        }
        return instance;
    }

    return {
        getInstance: function () {
            return initialise();
        }
    };
}());
