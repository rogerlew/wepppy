/* ----------------------------------------------------------------------------
 * Wepp
 * ----------------------------------------------------------------------------
 */
var Wepp = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#wepp_form");
        that.info = $("#wepp_form #info");
        that.status = $("#wepp_form  #status");
        that.stacktrace = $("#wepp_form #stacktrace");
        that.ws_client = new WSClient('wepp_form', 'wepp');
        that.ws_client.attachControl(that);
        that.rq_job_id = null;
        that.rq_job = $("#wepp_form #rq_job");
        that.command_btn_id = 'btn_run_wepp';

        const baseTriggerEvent = that.triggerEvent.bind(that);
        that.triggerEvent = function (eventName, payload) {
            if (eventName === 'WEPP_RUN_TASK_COMPLETED') {
                that.ws_client.disconnect();
                that.report();
                Observed.getInstance().onWeppRunCompleted();
            }

            baseTriggerEvent(eventName, payload);
        };

        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.surf_runoff = $("#wepp_form #surf_runoff");
        that.lateral_flow = $("#wepp_form #lateral_flow");
        that.baseflow = $("#wepp_form #baseflow");
        that.sediment = $("#wepp_form #sediment");
        that.channel_critical_shear = $("#wepp_form #channel_critical_shear");

        that.addChannelCriticalShear = function (x) {
            var self = instance;
            self.channel_critical_shear.append(new Option('User Defined: CS = ' + x, x, true, true));
        };


        that.updatePhosphorus = function () {
            var self = instance;

            $.get({
                url: "query/wepp/phosphorus_opts/",
                cache: false,
                success: function success(response) {
                    if (response.surf_runoff !== null)
                        self.surf_runoff.val(response.surf_runoff.toFixed(4));

                    if (response.lateral_flow !== null)
                        self.lateral_flow.val(response.lateral_flow.toFixed(4));

                    if (response.baseflow !== null)
                        self.baseflow.val(response.baseflow.toFixed(4));

                    if (response.sediment !== null)
                        self.sediment.val(response.sediment.toFixed(0));
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.set_run_wepp_routine = function (routine, state) {
            var self = instance;
            var task_msg = "Setting " + routine + " (" + state + ")";

            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.post({
                url: "tasks/set_run_wepp_routine/",
                data: JSON.stringify({ routine: routine, state: state }),
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

        that.handleCoverTransformUpload = function (input) {
            if (!input || !input.files || input.files.length === 0) {
                return false;
            }

            var file = input.files[0];
            var formData = new FormData();
            formData.append('input_upload_cover_transform', file);

            $.post({
                url: "tasks/upload_cover_transform",
                data: formData,
                contentType: false,
                cache: false,
                processData: false,
                success: function success() {
                    console.log('upload cover transform successful');
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });

            return true;
        };

        that.run = function () {
            var self = instance;
            var task_msg = "Submitting wepp run";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");
            self.ws_client.connect();

            var data = self.form.serialize();

            $.post({
                url: "rq/api/run_wepp",
                data: data,
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(`run_wepp_rq job submitted: ${response.job_id}`);
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
            var task_msg = "Fetching Summary";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            try {
                SubcatchmentDelineation.getInstance().prefetchLossMetrics();
            } catch (err) {
                console.warn('Unable to prefetch loss metrics:', err);
            }

            $.get({
                url: url_for_run("report/wepp/results/"),
                cache: false,
                success: function success(response) {
                    $('#wepp-results').html(response);
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });

            $.get({
                url: url_for_run("report/wepp/run_summary/"),
                cache: false,
                success: function success(response) {
                    self.info.html(response);
                    self.status.html(task_msg + "... Success");
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
