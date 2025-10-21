/* ----------------------------------------------------------------------------
 * RAP_TS
 * ----------------------------------------------------------------------------
 */
var RAP_TS = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#rap_ts_form");
        that.info = $("#rap_ts_form #info");
        that.status = $("#rap_ts_form  #status");
        that.stacktrace = $("#rap_ts_form #stacktrace");
        that.ws_client = new WSClient('rap_ts_form', 'rap_ts');
        that.ws_client.attachControl(that);
        that.rq_job_id = null;
        that.rq_job = $("#rap_ts_form #rq_job");
        that.command_btn_id = 'btn_build_rap_ts';

        that.bindHandlers = function () {
            if (!that.form || !that.form.length) {
                return;
            }

            if (that.form.data("rapTsHandlersBound")) {
                return;
            }
            that.form.data("rapTsHandlersBound", true);

            that.form.on("click", "#btn_build_rap_ts", function (event) {
                event.preventDefault();
                instance.acquire();
            });
        };

        const baseTriggerEvent = that.triggerEvent.bind(that);
        that.triggerEvent = function (eventName, payload) {
            if (eventName === 'RAP_TS_TASK_COMPLETED') {
                that.ws_client.disconnect();
                that.report();
            }

            baseTriggerEvent(eventName, payload);
        };

        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.acquire = function () {
            var self = instance;
            var task_msg = "Acquiring RAP TS maps";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");
            self.ws_client.connect();

            $.post({
                url: "rq/api/acquire_rap_ts",
                cache: false,
                success: function success(response) {
                    self.status.html(`fetch_and_analyze_rap_ts_rq job submitted: ${response.job_id}`);
                    self.set_rq_job_id(self, response.job_id);
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
            self.status.html("RAP Timeseries fetched and analyzed")
        };

        that.bindHandlers();

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
