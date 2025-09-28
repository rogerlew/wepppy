/* ----------------------------------------------------------------------------
 * Climate
 * ----------------------------------------------------------------------------
 */
var Climate = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        const SECTION_IDS = [
            '#climate_spatialmode_controls',
            '#input_years_container',
            '#climate_mode0_controls',
            '#climate_mode5_controls',
            '#observed_years_container',
            '#future_years_container',
            '#climate_mode4_controls',
            '#climate_mode6_controls',
            '#climate_mode7_controls',
            '#climate_mode8_controls',
            '#climate_mode10_controls',
            '#climate_mode13_controls',
            '#climate_mode14_controls'
        ];

        const MODE_CONFIG = {
            '-1': { show: [], allowSpatialMode2: false, showBuildButton: false },
            0: { show: ['#input_years_container', '#climate_mode0_controls'], allowSpatialMode2: false, showBuildButton: true },
            2: { show: ['#climate_spatialmode_controls', '#observed_years_container'], allowSpatialMode2: true, showBuildButton: true },
            3: { show: ['#climate_spatialmode_controls', '#future_years_container'], allowSpatialMode2: false, showBuildButton: true },
            4: { show: ['#climate_mode4_controls'], allowSpatialMode2: false, showBuildButton: true },
            5: { show: ['#climate_spatialmode_controls', '#input_years_container', '#climate_mode5_controls'], allowSpatialMode2: false, showBuildButton: true },
            6: { show: ['#climate_spatialmode_controls', '#climate_mode6_controls'], allowSpatialMode2: false, showBuildButton: true },
            7: { show: ['#climate_spatialmode_controls', '#climate_mode7_controls'], allowSpatialMode2: false, showBuildButton: true },
            8: { show: ['#climate_spatialmode_controls', '#input_years_container', '#climate_mode8_controls'], allowSpatialMode2: false, showBuildButton: true },
            9: { show: ['#climate_spatialmode_controls', '#observed_years_container'], allowSpatialMode2: true, showBuildButton: true },
            10: { show: ['#climate_spatialmode_controls', '#input_years_container', '#climate_mode10_controls'], allowSpatialMode2: false, showBuildButton: true },
            11: { show: ['#climate_spatialmode_controls', '#observed_years_container'], allowSpatialMode2: true, showBuildButton: true },
            13: { show: ['#climate_spatialmode_controls', '#observed_years_container', '#climate_mode13_controls'], allowSpatialMode2: false, showBuildButton: true },
            14: { show: ['#climate_mode14_controls'], allowSpatialMode2: false, showBuildButton: true }
        };

        const PRECIP_SECTIONS = [
            '#climate_precipscaling_mode1_controls',
            '#climate_precipscaling_mode2_controls',
            '#climate_precipscaling_mode3_controls',
            '#climate_precipscaling_mode4_controls'
        ];

        function parseMode(value, fallback) {
            var parsed = parseInt(value, 10);
            return Number.isNaN(parsed) ? fallback : parsed;
        }

        that.form = $("#climate_form");
        that.info = $("#climate_form #info");
        that.status = $("#climate_form  #status");
        that.stacktrace = $("#climate_form #stacktrace");
        that.ws_client = new WSClient('climate_form', 'climate');
        that.ws_client.attachControl(that);
        that.rq_job_id = null;
        that.rq_job = $("#climate_form #rq_job");
        that.command_btn_id = 'btn_build_climate';

        const baseTriggerEvent = that.triggerEvent.bind(that);
        that.triggerEvent = function (eventName, payload) {
            if (eventName === 'CLIMATE_SETSTATIONMODE_TASK_COMPLETED') {
                that.refreshStationSelection();
                that.viewStationMonthlies();
            } else if (eventName === 'CLIMATE_SETSTATION_TASK_COMPLETED') {
                that.viewStationMonthlies();
            } else if (eventName === 'CLIMATE_BUILD_TASK_COMPLETED') {
                that.ws_client.disconnect();
                that.report();
            }

            baseTriggerEvent(eventName, payload);
        };

        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.stationselection = $("#climate_station_selection");

        that.setBuildMode = function (mode) {
            var self = instance;
            self.mode = parseMode(mode, 0);
            if (self.mode === 0) {
                $("#climate_cligen").show();
                $("#climate_userdefined").hide();
                //self.setStationMode(-1);
            } else {
                $("#climate_cligen").hide();
                $("#climate_userdefined").show();
                self.setStationMode(4);
            }
        };

        that.setStationMode = function (mode) {
            var self = instance;
            if (mode === undefined) {
                mode = $("input[name='climatestation_mode']:checked").val();
            }

            var parsedMode = parseMode(mode, -1);
            var task_msg = "Setting Station Mode to " + parsedMode;

            self.info.text("");
            self.stacktrace.text("");

            // sync climate with nodb
            $.post({
                url: "tasks/set_climatestation_mode/",
                data: { "mode": parsedMode },
                success: function success(response) {
                    if (response.Success === true) {
                        self.triggerEvent('CLIMATE_SETSTATIONMODE_TASK_COMPLETED');
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.upload_cli = function () {
            var self = instance;

            var task_msg = "Uploading cli";

            self.info.text("");
            self.stacktrace.text("");

            var formData = new FormData($('#climate_form')[0]);

            $.post({
                url: "tasks/upload_cli/",
                data: formData,
                contentType: false,
                cache: false,
                processData: false,
                success: function success(response) {
                    if (response.Success === true) {
                        self.triggerEvent('CLIMATE_BUILD_TASK_COMPLETED');
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.refreshStationSelection = function () {
            var self = instance;

            var mode = $("input[name='climatestation_mode']:checked").val();
            if (mode === undefined) {
                return;
            }
            mode = parseMode(mode, -1);

            var task_msg = "Fetching Stations " + mode;

            self.info.text("");
            self.stacktrace.text("");

            if (mode === 0) {
                // sync climate with nodb
                $.get({
                    url: "view/closest_stations/",
                    cache: false,
                    data: { "mode": mode },
                    success: function success(response) {
                        self.stationselection.html(response);
                        self.triggerEvent('CLIMATE_SETSTATION_TASK_COMPLETED');
                    },
                    error: function error(jqXHR) {
                        self.pushResponseStacktrace(self, jqXHR.responseJSON);
                    },
                    fail: function fail(jqXHR, textStatus, errorThrown) {
                        self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                    }
                });
            } else if (mode === 1) {
                // sync climate with nodb
                $.get({
                    url: "view/heuristic_stations/",
                    data: { "mode": mode },
                    cache: false,
                    success: function success(response) {
                        self.stationselection.html(response);
                        self.triggerEvent('CLIMATE_SETSTATION_TASK_COMPLETED');
                    },
                    error: function error(jqXHR) {
                        self.pushResponseStacktrace(self, jqXHR.responseJSON);
                    },
                    fail: function fail(jqXHR, textStatus, errorThrown) {
                        self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                    }
                });
            } else if (mode === 2) {
                // sync climate with nodb
                $.get({
                    url: "view/eu_heuristic_stations/",
                    data: { "mode": mode },
                    cache: false,
                    success: function success(response) {
                        self.stationselection.html(response);
                        self.triggerEvent('CLIMATE_SETSTATION_TASK_COMPLETED');
                    },
                    error: function error(jqXHR) {
                        self.pushResponseStacktrace(self, jqXHR.responseJSON);
                    },
                    fail: function fail(jqXHR, textStatus, errorThrown) {
                        self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                    }
                });
            } else if (mode === 3) {
                // sync climate with nodb
                $.get({
                    url: "view/au_heuristic_stations/",
                    data: { "mode": mode },
                    cache: false,
                    success: function success(response) {
                        self.stationselection.html(response);
                        self.triggerEvent('CLIMATE_SETSTATION_TASK_COMPLETED');
                    },
                    error: function error(jqXHR) {
                        self.pushResponseStacktrace(self, jqXHR.responseJSON);
                    },
                    fail: function fail(jqXHR, textStatus, errorThrown) {
                        self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                    }
                });
            } else if (mode === 4) {
                pass();
            } else if (mode === -1) {
                pass();
            } else {
                throw "Unknown mode for stationselection";
            }
        };

        that.setStation = function (station) {
            var self = instance;

            if (station === undefined) {
                station = $("#climate_station_selection").val();
            }

            var task_msg = "Setting station " + station;

            self.info.text("");
            self.stacktrace.text("");

            $.post({
                url: "tasks/set_climatestation/",
                data: { "station": station },
                success: function success(response) {
                    if (response.Success === true) {
                        self.triggerEvent('CLIMATE_SETSTATION_TASK_COMPLETED');
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.viewStationMonthlies = function () {
            var self = instance;
            var project = Project.getInstance();
            $.get({
                url: "view/climate_monthlies/",
                cache: false,
                success: function success(response) {
                    $("#climate_monthlies").html(response);
                    project.set_preferred_units();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.build = function () {
            var self = instance;
            var task_msg = "Building climate";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");
            self.ws_client.connect();

            $.post({
                url: "rq/api/build_climate",
                data: self.form.serialize(),
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(`build_climate job submitted: ${response.job_id}`);
                        self.set_rq_job_id(self, response.job_id);
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });

        };

        that.report = function () {
            var self = instance;
            var project = Project.getInstance();
            $.get({
                url: url_for_run("report/climate/"),
                cache: false,
                success: function success(response) {
                    self.info.html(response);
                    project.set_preferred_units();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };


        that.setMode = function (mode) {
            var self = instance;
            if (mode === undefined) {
                mode = $("input[name='climate_mode']:checked").val();
            }
            mode = parseMode(mode, -1);
            var climate_single_selection = $("#climate_single_selection").val();

            var task_msg = "Setting Mode to " + mode + " (" + climate_single_selection + ")";

            self.info.text("");
            self.stacktrace.text("");

            // sync climate with nodb
            $.post({
                url: "tasks/set_climate_mode/",
                data: {
                    "mode": mode,
                    "climate_single_selection": climate_single_selection
                },
                success: function success(response) {
                    if (response.Success === true) {
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
            self.showHideControls(mode);
        };

        that.showHideControls = function (mode) {
            var parsedMode = parseMode(mode, -1);
            var config = MODE_CONFIG.hasOwnProperty(parsedMode) ? MODE_CONFIG[parsedMode] : MODE_CONFIG['-1'];
            var showSet = new Set(config.show || []);

            SECTION_IDS.forEach(function (selector) {
                if (showSet.has(selector)) {
                    $(selector).show();
                } else {
                    $(selector).hide();
                }
            });

            $("#climate_spatialmode2").prop('disabled', config.allowSpatialMode2 !== true);
            if (config.showBuildButton === true) {
                $("#btn_build_climate_container").show();
            } else {
                $("#btn_build_climate_container").hide();
            }
        };

        that.updatePrecipScalingControls = function (mode) {
            var parsedMode = parseMode(mode, 0);
            var targetId = '#climate_precipscaling_mode' + parsedMode + '_controls';
            PRECIP_SECTIONS.forEach(function (selector) {
                if (selector === targetId) {
                    $(selector).show();
                } else {
                    $(selector).hide();
                }
            });
        };

        that.handleBuildModeChange = function (mode) {
            that.setBuildMode(mode);
        };

        that.handleModeChange = function (mode) {
            that.setMode(mode);
        };

        that.handleSpatialModeChange = function (mode) {
            that.setSpatialMode(mode);
        };

        that.handleStationModeChange = function (mode) {
            that.setStationMode(mode);
        };

        that.handleStationSelectionChange = function (station) {
            that.setStation(station);
        };

        that.handlePrecipScalingModeChange = function (mode) {
            if (mode === undefined) {
                mode = $('input[name="precip_scaling_mode"]:checked').val();
            }
            that.updatePrecipScalingControls(mode);
        };

        that.setSpatialMode = function (mode) {
            var self = instance;
            if (mode === undefined) {
                mode = $("input[name='climate_spatialmode']:checked").val();
            }
            var parsedMode = parseMode(mode, 0);
            var task_msg = "Setting SpatialMode to " + parsedMode;

            self.info.text("");
            self.stacktrace.text("");

            // sync climate with nodb
            $.post({
                url: "tasks/set_climate_spatialmode/",
                data: { "spatialmode": parsedMode },
                success: function success(response) {
                    if (response.Success === true) {
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.set_use_gridmet_wind_when_applicable = function (state) {
            var self = instance;
            var task_msg = "Setting use_gridmet_wind_when_applicable (" + state + ")";

            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.post({
                url: "tasks/set_use_gridmet_wind_when_applicable/",
                data: JSON.stringify({ state: state }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(task_msg + "... Success");
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(error) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };
        return that;
    }

    return {
        getInstance: function getInstance() {
            if (!instance) {
                instance = createInstance();
            }
            return instance;
        }
    };
}();
