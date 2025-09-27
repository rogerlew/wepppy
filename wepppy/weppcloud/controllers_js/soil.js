/* ----------------------------------------------------------------------------
 * Soil
 * ----------------------------------------------------------------------------
 */
var Soil = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#soil_form");
        that.info = $("#soil_form #info");
        that.status = $("#soil_form  #status");
        that.stacktrace = $("#soil_form #stacktrace");
        that.ws_client = new WSClient('soil_form', 'soils');
        that.rq_job_id = null;
        that.rq_job = $("#soil_form #rq_job");
        that.command_btn_id = 'btn_build_soil';

        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.build = function () {
            var self = instance;
            var task_msg = "Building soil";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");
            self.ws_client.connect();

            $.post({
                url: "rq/api/build_soils",
                data: self.form.serialize(),
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(`build_soils_rq job submitted: ${response.job_id}`);
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
            $.get({
                url: url_for_run("report/soils/"),
                cache: false,
                success: function success(response) {
                    self.info.html(response);
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.restore = function (soil_mode) {
            var self = instance;
            $("#soil_mode" + soil_mode).prop("checked", true);

            self.showHideControls(soil_mode);
        };

        that.set_ksflag = function (state) {
            var self = instance;
            var task_msg = "Setting ksflag (" + state + ")";

            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.post({
                url: "tasks/set_soils_ksflag/",
                data: JSON.stringify({ ksflag: state }),
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

        that.setMode = function (mode) {
            var self = instance;
            // mode is an optional parameter
            // if it isn't provided then we get the checked value
            if (mode === undefined) {
                mode = $("input[name='soil_mode']:checked").val();
            }
            mode = parseInt(mode, 10);
            var soil_single_selection = $("#soil_single_selection").val();
            var soil_single_dbselection = $("#soil_single_dbselection").val();

            var task_msg = "Setting Mode to " + mode;

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            // sync soil with nodb
            $.post({
                url: "tasks/set_soil_mode/",
                data: {
                    "mode": mode,
                    "soil_single_selection": soil_single_selection,
                    "soil_single_dbselection": soil_single_dbselection
                },
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
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
            self.showHideControls(mode);
        };

        that.showHideControls = function (mode) {
            // show the appropriate controls
            if (mode === -1) {
                // neither
                $("#soil_mode0_controls").hide();
                $("#soil_mode1_controls").hide();
                $("#soil_mode2_controls").hide();
                $("#soil_mode3_controls").hide();
                $("#soil_mode4_controls").hide();
            } else if (mode === 0) {
                // gridded
                $("#soil_mode0_controls").show();
                $("#soil_mode1_controls").hide();
                $("#soil_mode2_controls").hide();
                $("#soil_mode3_controls").hide();
                $("#soil_mode4_controls").hide();
            } else if (mode === 1) {
                // single
                $("#soil_mode0_controls").hide();
                $("#soil_mode1_controls").show();
                $("#soil_mode2_controls").hide();
                $("#soil_mode3_controls").hide();
                $("#soil_mode4_controls").hide();
            } else if (mode === 2) {
                // singledb
                $("#soil_mode0_controls").hide();
                $("#soil_mode1_controls").hide();
                $("#soil_mode2_controls").show();
                $("#soil_mode3_controls").hide();
                $("#soil_mode4_controls").hide();
            } else if (mode === 3) {
                // RRED Unburned
                $("#soil_mode0_controls").hide();
                $("#soil_mode1_controls").hide();
                $("#soil_mode2_controls").hide();
                $("#soil_mode3_controls").show();
                $("#soil_mode4_controls").hide();
            } else if (mode === 4) {
                // RRED Burned
                $("#soil_mode0_controls").hide();
                $("#soil_mode1_controls").hide();
                $("#soil_mode2_controls").hide();
                $("#soil_mode3_controls").hide();
                $("#soil_mode4_controls").show();
            } else {
                throw "ValueError: Landuse unknown mode";
            }
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
