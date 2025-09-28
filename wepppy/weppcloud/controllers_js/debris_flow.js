/* ----------------------------------------------------------------------------
 * DebrisFlow
 * ----------------------------------------------------------------------------
 */
var DebrisFlow = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#debris_flow_form");
        that.info = $("#debris_flow_form #info");
        that.status = $("#debris_flow_form  #status");
        that.stacktrace = $("#debris_flow_form #stacktrace");
        that.ws_client = new WSClient('debris_flow_form', 'debris_flow');
        that.ws_client.attachControl(that);
        that.rq_job_id = null;
        that.rq_job = $("#debris_flow_form #rq_job");
        that.command_btn_id = 'btn_run_debris_flow';

        const baseTriggerEvent = that.triggerEvent.bind(that);
        that.triggerEvent = function (eventName, payload) {
            if (eventName === 'DEBRIS_FLOW_RUN_TASK_COMPLETED') {
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

            var task_msg = "Running debris_flow model fit";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");
            self.ws_client.connect();

            $.post({
                url: "rq/api/run_debris_flow",
                contentType: "application/json; charset=utf-8",
                dataType: "json",
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(`run_debris_flow_rq job submitted: ${response.job_id}`);
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
            self.info.html(`<a href='${url_for_run("report/debris_flow/")}' target='_blank'>View Debris Flow Model Results</a>`);
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
