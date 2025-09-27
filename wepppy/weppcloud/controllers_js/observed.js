/* ----------------------------------------------------------------------------
 * Observed
 * ----------------------------------------------------------------------------
 */
var Observed = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#observed_form");
        that.textarea = $("#observed_form #observed_text");
        that.info = $("#observed_form #info");
        that.status = $("#observed_form  #status");
        that.stacktrace = $("#observed_form #stacktrace");
        that.ws_client = new WSClient('observed_form', 'observed');
        that.rq_job_id = null;
        that.rq_job = $("#observed_form #rq_job");

        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.hideControl = function () {
            var self = instance;
            self.form.hide();
        };

        that.showControl = function () {
            var self = instance;
            self.form.show();
        };

        that.onWeppRunCompleted = function () {
            var self = instance;

            $.get({
                url: "query/climate_has_observed/",
                success: function success(response) {
                    if (response === true) {
                        self.showControl();
                    } else {
                        self.hideControl();
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

        that.run_model_fit = function () {
            var self = instance;
            var textdata = self.textarea.val();

            var task_msg = "Running observed model fit";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.post({
                url: "tasks/run_model_fit/",
                data: JSON.stringify({ data: textdata }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(task_msg + "... done.");
                        self.report();
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
            self.info.html(`<a href='${url_for_run("report/observed/")}' target='_blank'>View Model Fit Results</a>`);
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
