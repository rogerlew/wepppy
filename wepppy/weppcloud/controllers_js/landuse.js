/* ----------------------------------------------------------------------------
 * Landuse
 * ----------------------------------------------------------------------------
 */
var Landuse = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#landuse_form");
        that.info = $("#landuse_form #info");
        that.status = $("#landuse_form  #status");
        that.stacktrace = $("#landuse_form #stacktrace");
        that.ws_client = new WSClient('landuse_form', 'landuse');
        that.ws_client.attachControl(that);
        that.rq_job_id = null;
        that.rq_job = $("#landuse_form #rq_job");
        that.command_btn_id = 'btn_build_landuse';

        const baseTriggerEvent = that.triggerEvent.bind(that);
        that.triggerEvent = function (eventName, payload) {
            if (eventName === 'LANDUSE_BUILD_TASK_COMPLETED') {
                that.ws_client.disconnect();
                that.report();
                SubcatchmentDelineation.getInstance().enableColorMap('dom_lc');
            }

            baseTriggerEvent(eventName, payload);
        };


        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.build = function () {
            var self = instance;
            var task_msg = "Building landuse";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");
            self.ws_client.connect();

            var formData = new FormData($('#landuse_form')[0]);

            $.post({
                url: "rq/api/build_landuse",
                data: formData,
                contentType: false,
                cache: false,
                processData: false,
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(`build_landuse job submitted: ${response.job_id}`);
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

        that.modify_coverage = function (dom, cover, value) {
            var data = {
                dom: dom,
                cover: cover,
                value: value
            };

            $.post({
                url: "tasks/modify_landuse_coverage/",
                data: JSON.stringify(data),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                success: function success(response) {
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.modify_mapping = function (dom, newdom) {
            var self = instance;

            var data = {
                dom: dom,
                newdom: newdom
            };

            $.post({
                url: "tasks/modify_landuse_mapping/",
                data: JSON.stringify(data),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                success: function success(response) {
                    self.report();
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
                url: url_for_run("report/landuse/"),
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

        that.restore = function (landuse_mode, landuse_single_selection) {
            console.log("restore landuse mode: " + landuse_mode);
            var self = instance;
            $("#landuse_mode" + landuse_mode).prop("checked", true);

            $('#landuse_single_selection').val('{{ landuse.single_selection }}').prop('selected', true);

            self.showHideControls(landuse_mode);
        };

        that.setMode = function (mode) {
            var self = instance;
            // mode is an optional parameter
            // if it isn't provided then we get the checked value
            if (mode === undefined) {
                mode = $("input[name='landuse_mode']:checked").val();
            }
            mode = parseInt(mode, 10);
            var landuse_single_selection = $("#landuse_single_selection").val();

            var task_msg = "Setting Mode to " + mode + " (" + landuse_single_selection + ")";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            // sync landuse with nodb
            $.post({
                url: "tasks/set_landuse_mode/",
                data: { "mode": mode, "landuse_single_selection": landuse_single_selection },
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

        that.setLanduseDb = function (db) {
            var self = instance;
            // mode is an optional parameter
            // if it isn't provided then we get the checked value
            if (db === undefined) {
                db = $("input[name='landuse_db']:checked").val();
            }

            var task_msg = "Setting Landuse Db to " + db;

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            // sync landuse with nodb
            $.post({
                url: "tasks/set_landuse_db/",
                data: { "landuse_db": db },
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
            self.showHideControls(self.mode);
        };

        that.showHideControls = function (mode) {
            // show the appropriate controls
            if (mode === -1) {
                // neither
                $("#landuse_mode0_controls").hide();
                $("#landuse_mode1_controls").hide();
                $("#landuse_mode2_controls").hide();
                $("#landuse_mode3_controls").hide();
                $("#landuse_mode4_controls").hide();
            } else if (mode === 0) {
                // gridded
                $("#landuse_mode0_controls").show();
                $("#landuse_mode1_controls").hide();
                $("#landuse_mode2_controls").hide();
                $("#landuse_mode3_controls").hide();
                $("#landuse_mode4_controls").hide();
            } else if (mode === 1) {
                // single
                $("#landuse_mode0_controls").hide();
                $("#landuse_mode1_controls").show();
                $("#landuse_mode2_controls").hide();
                $("#landuse_mode3_controls").hide();
                $("#landuse_mode4_controls").hide();
            } else if (mode === 2) {
                // single
                $("#landuse_mode0_controls").hide();
                $("#landuse_mode1_controls").hide();
                $("#landuse_mode2_controls").show();
                $("#landuse_mode3_controls").hide();
                $("#landuse_mode4_controls").hide();
            } else if (mode === 3) {
                // single
                $("#landuse_mode0_controls").hide();
                $("#landuse_mode1_controls").hide();
                $("#landuse_mode2_controls").hide();
                $("#landuse_mode3_controls").show();
                $("#landuse_mode4_controls").hide();
            } else if (mode === 4) {
                // single
                $("#landuse_mode0_controls").hide();
                $("#landuse_mode1_controls").hide();
                $("#landuse_mode2_controls").hide();
                $("#landuse_mode3_controls").hide();
                $("#landuse_mode4_controls").show();
            } else {
                throw "ValueError: unknown mode";
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
