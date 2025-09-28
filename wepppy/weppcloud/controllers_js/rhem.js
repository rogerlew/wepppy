/* ----------------------------------------------------------------------------
 * Rhem
 * ----------------------------------------------------------------------------
 */
var Rhem = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#rhem_form");
        that.info = $("#rhem_form #info");
        that.status = $("#rhem_form  #status");
        that.stacktrace = $("#rhem_form #stacktrace");
        that.ws_client = new WSClient('rhem_form', 'rhem');
        that.ws_client.attachControl(that);
        that.rq_job_id = null;
        that.rq_job = $("#rhem_form #rq_job");
        that.command_btn_id = 'btn_run_rhem';

        const baseTriggerEvent = that.triggerEvent.bind(that);
        that.triggerEvent = function (eventName, payload) {
            if (eventName === 'RHEM_RUN_TASK_COMPLETED') {
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
            var task_msg = "Submitting rhem run";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");
            self.ws_client.connect();

            $.post({
                url: "rq_api/run_rhem/",
                data: self.form.serialize(),
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(`run_rhem_rq job submitted: ${response.job_id}`);
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

            $.get({
                url: url_for_run("report/rhem/results/"),
                cache: false,
                success: function success(response) {
                    $('#rhem-results').html(response);
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });

            $.get({
                url: url_for_run("report/rhem/run_summary/"),
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
