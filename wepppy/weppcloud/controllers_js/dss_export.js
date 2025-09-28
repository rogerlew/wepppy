/* ----------------------------------------------------------------------------
 * DSS Export
 * ----------------------------------------------------------------------------
 */
var DssExport = function () {
    var instance;

    function createInstance() {
        var that = controlBase();

        that.form = $("#dss_export_form");
        that.container = that.form.closest(".controller-section");
        if (!that.container.length) {
            that.container = that.form;
        }
        that.info = $("#dss_export_form #info");
        that.status = $("#dss_export_form  #status");
        that.stacktrace = $("#dss_export_form #stacktrace");
        that.ws_client = new WSClient('dss_export_form', 'dss_export');
        that.ws_client.attachControl(that);
        that.rq_job_id = null;
        that.rq_job = $("#dss_export_form #rq_job");
        that.command_btn_id = 'btn_export_dss';

        const baseTriggerEvent = that.triggerEvent.bind(that);
        that.triggerEvent = function (eventName, payload) {
            if (eventName === 'DSS_EXPORT_TASK_COMPLETED') {
                that.ws_client.disconnect();
                that.report();

                if (typeof Omni !== 'undefined') {
                    var omni = Omni.getInstance();
                    if (omni && omni.ws_client && typeof omni.ws_client.disconnect === 'function') {
                        omni.ws_client.disconnect();
                    }
                    if (omni && typeof omni.report_scenarios === 'function') {
                        omni.report_scenarios();
                    }
                }
            }

            baseTriggerEvent(eventName, payload);
        };

        that.show = function () {
            that.container.show();
            $('a[href="#partitioned-dss-export-for-hec"]').parent().show()
        };

        that.hide = function () {
            that.container.hide();
            $('a[href="#partitioned-dss-export-for-hec"]').parent().hide()
        };

        that.setMode = function (mode) {
            var self = instance;

            // verify mode is 1 or 2
            if (mode !== 1 && mode !== 2) {
                throw "ValueError: unknown mode";
            }

            if (mode === 1) {
                $("#dss_export_mode1_controls").show();
                $("#dss_export_mode2_controls").hide();
            }
            else if (mode === 2) {
                $("#dss_export_mode1_controls").hide();
                $("#dss_export_mode2_controls").show();
            }

        };

        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.export = function () {
            var self = instance;

            var task_msg = "Exporting to DSS";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");
            self.ws_client.connect();

            $.post({
                url: "rq/api/post_dss_export_rq",
                data: self.form.serialize(),
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(`post_dss_export_rq job submitted: ${response.job_id}`);
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
            self.info.html("<a href='browse/export/dss.zip' target='_blank'>Download DSS Export Results (.zip)</a>");
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
