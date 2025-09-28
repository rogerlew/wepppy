/* ----------------------------------------------------------------------------
 * Ash
 * ----------------------------------------------------------------------------
 */
var Ash = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        const DEPTH_MODE_SECTIONS = {
            0: '#ash_depth_mode0_controls',
            1: '#ash_depth_mode1_controls',
            2: '#ash_depth_mode2_controls'
        };

        function parseDepthMode(value, fallback) {
            var parsed = parseInt(value, 10);
            return Number.isNaN(parsed) ? fallback : parsed;
        }

        that.form = $("#ash_form");
        that.info = $("#ash_form #info");
        that.status = $("#ash_form  #status");
        that.stacktrace = $("#ash_form #stacktrace");
        that.ws_client = new WSClient('ash_form', 'ash');
        that.ws_client.attachControl(that);
        that.rq_job_id = null;
        that.rq_job = $("#ash_form #rq_job");
        that.command_btn_id = 'btn_run_ash';

        const baseTriggerEvent = that.triggerEvent.bind(that);
        that.triggerEvent = function (eventName, payload) {
            if (eventName === 'ASH_RUN_TASK_COMPLETED') {
                that.ws_client.disconnect();
                that.report();
            }

            baseTriggerEvent(eventName, payload);
        };

        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.run = function () {
            var self = instance;

            var task_msg = "Running ash model";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");
            self.ws_client.connect();

            var formData = new FormData($('#ash_form')[0]);

            $.post({
                url: "rq/api/run_ash",
                data: formData,
                contentType: false,
                cache: false,
                processData: false,
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(`run_ash job submitted: ${response.job_id}`);
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

        that.setAshDepthMode = function (mode) {
            var self = instance;

            if (mode === undefined) {
                mode = $("input[name='ash_depth_mode']:checked").val();
            }

            self.ash_depth_mode = parseDepthMode(mode, 0);
            self.showHideControls();
        };

        that.handleDepthModeChange = function (mode) {
            that.setAshDepthMode(mode);
        };

        that.set_wind_transport = function (state) {
            var self = instance;
            var task_msg = "Setting wind_transport(" + state + ")";

            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.post({
                url: "tasks/set_ash_wind_transport/",
                data: JSON.stringify({ run_wind_transport: state }),
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

        that.showHideControls = function () {
            var self = instance;
            var active = DEPTH_MODE_SECTIONS.hasOwnProperty(self.ash_depth_mode)
                ? DEPTH_MODE_SECTIONS[self.ash_depth_mode]
                : DEPTH_MODE_SECTIONS[0];

            Object.values(DEPTH_MODE_SECTIONS).forEach(function (selector) {
                if (selector === active) {
                    $(selector).show();
                } else {
                    $(selector).hide();
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

            $.get({
                url: url_for_run("report/run_ash/"),
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
