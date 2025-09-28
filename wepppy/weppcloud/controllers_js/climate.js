/* ----------------------------------------------------------------------------
 * Climate
 * ----------------------------------------------------------------------------
 */
var Climate = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
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
            self.mode = parseInt(mode, 10);
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
            // mode is an optional parameter
            // if it isn't provided then we get the checked value
            if (mode === undefined) {
                mode = $("input[name='climatestation_mode']:checked").val();
            }

            var task_msg = "Setting Station Mode to " + mode;

            self.info.text("");
            self.stacktrace.text("");

            // sync climate with nodb
            $.post({
                url: "tasks/set_climatestation_mode/",
                data: { "mode": mode },
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
            mode = parseInt(mode, 10);

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

        that.setStation = function () {
            var self = instance;

            var station = $("#climate_station_selection").val();

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
            // mode is an optional parameter
            // if it isn't provided then we get the checked value
            if (mode === undefined) {
                mode = $("input[name='climate_mode']:checked").val();
            }
            mode = parseInt(mode, 10);
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
            if (mode === undefined) {
                mode = -1;
            }
            // show the appropriate controls
            if (mode === -1) {
                // none selected
                $("#climate_spatialmode2").prop("disabled", true);
                $("#climate_spatialmode_controls").hide();
                $("#input_years_container").hide();
                $("#climate_mode0_controls").hide();
                $("#climate_mode5_controls").hide();
                $("#observed_years_container").hide();
                $("#future_years_container").hide();
                $("#climate_mode4_controls").hide();
                $("#climate_mode6_controls").hide();
                $("#climate_mode7_controls").hide();
                $("#climate_mode8_controls").hide();
                $("#climate_mode10_controls").hide();
                $("#climate_mode13_controls").hide();
                $("#climate_mode14_controls").hide();
                $("#btn_build_climate_container").hide();
            } else if (mode === 0) {
                // vanilla
                $("#climate_spatialmode2").prop("disabled", true);
                $("#climate_spatialmode_controls").hide();
                $("#input_years_container").show();
                $("#climate_mode0_controls").show();
                $("#climate_mode5_controls").hide();
                $("#observed_years_container").hide();
                $("#future_years_container").hide();
                $("#climate_mode4_controls").hide();
                $("#climate_mode6_controls").hide();
                $("#climate_mode7_controls").hide();
                $("#climate_mode8_controls").hide();
                $("#climate_mode10_controls").hide();
                $("#climate_mode13_controls").hide();
                $("#climate_mode14_controls").hide();
                $("#btn_build_climate_container").show();
            } else if ((mode === 2) || (mode === 11)) {
                // observed daymet or gridmet
                $("#climate_spatialmode2").prop("disabled", false);
                $("#climate_spatialmode_controls").show();
                $("#input_years_container").hide();
                $("#climate_mode0_controls").hide();
                $("#climate_mode5_controls").hide();
                $("#observed_years_container").show();
                $("#future_years_container").hide();
                $("#climate_mode4_controls").hide();
                $("#climate_mode6_controls").hide();
                $("#climate_mode7_controls").hide();
                $("#climate_mode8_controls").hide();
                $("#climate_mode10_controls").hide();
                $("#climate_mode13_controls").hide();
                $("#climate_mode14_controls").hide();
                $("#btn_build_climate_container").show();
            } else if (mode === 3) {
                // future
                $("#climate_spatialmode2").prop("disabled", true);
                $("#climate_spatialmode_controls").show();
                $("#input_years_container").hide();
                $("#climate_mode0_controls").hide();
                $("#climate_mode5_controls").hide();
                $("#observed_years_container").hide();
                $("#future_years_container").show();
                $("#climate_mode4_controls").hide();
                $("#climate_mode6_controls").hide();
                $("#climate_mode7_controls").hide();
                $("#climate_mode8_controls").hide();
                $("#climate_mode10_controls").hide();
                $("#climate_mode13_controls").hide();
                $("#climate_mode14_controls").hide();
                $("#btn_build_climate_container").show();
            } else if (mode === 4) {
                // single storm
                $("#climate_spatialmode2").prop("disabled", true);
                $("#climate_spatialmode_controls").hide();
                $("#input_years_container").hide();
                $("#climate_mode0_controls").hide();
                $("#climate_mode5_controls").hide();
                $("#observed_years_container").hide();
                $("#future_years_container").hide();
                $("#climate_mode4_controls").show();
                $("#climate_mode6_controls").hide();
                $("#climate_mode7_controls").hide();
                $("#climate_mode8_controls").hide();
                $("#climate_mode10_controls").hide();
                $("#climate_mode13_controls").hide();
                $("#climate_mode14_controls").hide();
                $("#btn_build_climate_container").show();
            } else if (mode === 14) {
                // single storm
                $("#climate_spatialmode2").prop("disabled", true);
                $("#climate_spatialmode_controls").hide();
                $("#input_years_container").hide();
                $("#climate_mode0_controls").hide();
                $("#climate_mode5_controls").hide();
                $("#observed_years_container").hide();
                $("#future_years_container").hide();
                $("#climate_mode4_controls").hide();
                $("#climate_mode6_controls").hide();
                $("#climate_mode7_controls").hide();
                $("#climate_mode8_controls").hide();
                $("#climate_mode10_controls").hide();
                $("#climate_mode13_controls").hide();
                $("#climate_mode14_controls").show();
                $("#btn_build_climate_container").show();
            } else if (mode === 5) {
                // prism
                $("#climate_spatialmode2").prop("disabled", true);
                $("#climate_spatialmode_controls").show();
                $("#input_years_container").show();
                $("#climate_mode0_controls").hide();
                $("#climate_mode5_controls").show();
                $("#observed_years_container").hide();
                $("#future_years_container").hide();
                $("#climate_mode4_controls").hide();
                $("#climate_mode6_controls").hide();
                $("#climate_mode7_controls").hide();
                $("#climate_mode8_controls").hide();
                $("#climate_mode10_controls").hide();
                $("#climate_mode13_controls").hide();
                $("#climate_mode14_controls").hide();
                $("#btn_build_climate_container").show();
            } else if (mode === 6) {
                // observed database
                $("#climate_spatialmode2").prop("disabled", true);
                $("#climate_spatialmode_controls").show();
                $("#input_years_container").hide();
                $("#climate_mode0_controls").hide();
                $("#climate_mode5_controls").hide();
                $("#observed_years_container").hide();
                $("#future_years_container").hide();
                $("#climate_mode4_controls").hide();
                $("#climate_mode6_controls").show();
                $("#climate_mode7_controls").hide();
                $("#climate_mode8_controls").hide();
                $("#climate_mode10_controls").hide();
                $("#climate_mode13_controls").hide();
                $("#climate_mode14_controls").hide();
                $("#btn_build_climate_container").show();
            } else if (mode === 7) {
                // future database
                $("#climate_spatialmode2").prop("disabled", true);
                $("#climate_spatialmode_controls").show();
                $("#input_years_container").hide();
                $("#climate_mode0_controls").hide();
                $("#climate_mode5_controls").hide();
                $("#observed_years_container").hide();
                $("#future_years_container").hide();
                $("#climate_mode4_controls").hide();
                $("#climate_mode6_controls").hide();
                $("#climate_mode7_controls").show();
                $("#climate_mode8_controls").hide();
                $("#climate_mode10_controls").hide();
                $("#climate_mode13_controls").hide();
                $("#climate_mode14_controls").hide();
                $("#btn_build_climate_container").show();
            } else if (mode === 8) {
                // EOBS (EU)
                $("#climate_spatialmode2").prop("disabled", true);
                $("#climate_spatialmode_controls").show();
                $("#input_years_container").show();
                $("#climate_mode0_controls").hide();
                $("#climate_mode5_controls").hide();
                $("#observed_years_container").hide();
                $("#future_years_container").hide();
                $("#climate_mode4_controls").hide();
                $("#climate_mode6_controls").hide();
                $("#climate_mode7_controls").hide();
                $("#climate_mode8_controls").show();
                $("#climate_mode10_controls").hide();
                $("#climate_mode13_controls").hide();
                $("#climate_mode14_controls").hide();
                $("#btn_build_climate_container").show();
            } else if (mode === 9) {
                // observed PRISM
                $("#climate_spatialmode2").prop("disabled", false);
                $("#climate_spatialmode_controls").show();
                $("#input_years_container").hide();
                $("#climate_mode0_controls").hide();
                $("#climate_mode5_controls").hide();
                $("#observed_years_container").show();
                $("#future_years_container").hide();
                $("#climate_mode4_controls").hide();
                $("#climate_mode6_controls").hide();
                $("#climate_mode7_controls").hide();
                $("#climate_mode8_controls").hide();
                $("#climate_mode10_controls").hide();
                $("#climate_mode13_controls").hide();
                $("#climate_mode14_controls").hide();
                $("#btn_build_climate_container").show();
            } else if (mode === 10) {
                // AGDC (AU)
                $("#climate_spatialmode2").prop("disabled", true);
                $("#climate_spatialmode_controls").show();
                $("#input_years_container").show();
                $("#climate_mode0_controls").hide();
                $("#climate_mode5_controls").hide();
                $("#observed_years_container").hide();
                $("#future_years_container").hide();
                $("#climate_mode4_controls").hide();
                $("#climate_mode6_controls").hide();
                $("#climate_mode7_controls").hide();
                $("#climate_mode8_controls").hide();
                $("#climate_mode10_controls").show();
                $("#climate_mode13_controls").hide();
                $("#climate_mode14_controls").hide();
                $("#btn_build_climate_container").show();
            } else if (mode === 13) {
                // NEXRAD
                $("#climate_spatialmode2").prop("disabled", true);
                $("#climate_spatialmode_controls").show();
                $("#input_years_container").hide();
                $("#climate_mode0_controls").hide();
                $("#climate_mode5_controls").hide();
                $("#observed_years_container").show();
                $("#future_years_container").hide();
                $("#climate_mode4_controls").hide();
                $("#climate_mode6_controls").hide();
                $("#climate_mode7_controls").hide();
                $("#climate_mode8_controls").hide();
                $("#climate_mode10_controls").hide();
                $("#climate_mode13_controls").show();
                $("#climate_mode14_controls").hide();
                $("#btn_build_climate_container").show();
            }
            //              else {
            //                throw "ValueError: unknown mode";
            //            }
        };

        that.setSpatialMode = function (mode) {
            var self = instance;
            // mode is an optional parameter
            // if it isn't provided then we get the checked value
            if (mode === undefined) {
                mode = $("input[name='climate_spatialmode']:checked").val();
            }
            var task_msg = "Setting SpatialMode to " + mode;

            self.info.text("");
            self.stacktrace.text("");

            // sync climate with nodb
            $.post({
                url: "tasks/set_climate_spatialmode/",
                data: { "spatialmode": mode },
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
            var task_msg = "Setting " + routine + " (" + state + ")";

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
