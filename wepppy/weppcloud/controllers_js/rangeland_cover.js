/* ----------------------------------------------------------------------------
 * Rangeland Cover
 * ----------------------------------------------------------------------------
 */

var RangelandCover = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#rangeland_cover_form");
        that.info = $("#rangeland_cover_form #info");
        that.status = $("#rangeland_cover_form  #status");
        that.stacktrace = $("#rangeland_cover_form #stacktrace");
        that.ws_client = new WSClient('rangeland_cover_form', 'rangeland_cover');
        that.ws_client.attachControl(that);
        that.rq_job_id = null;
        that.rq_job = $("#rangeland_cover_form #rq_job");

        const baseTriggerEvent = that.triggerEvent.bind(that);
        that.triggerEvent = function (eventName, payload) {
            if (eventName === 'RANGELAND_COVER_BUILD_TASK_COMPLETED') {
                SubcatchmentDelineation.getInstance().enableColorMap("rangeland_cover");
                that.report();
            }

            baseTriggerEvent(eventName, payload);
        };

        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.handleModeChange = function (mode) {
            if (mode === undefined) {
                that.setMode();
                return;
            }
            that.setMode(parseInt(mode, 10));
        };

        that.handleRapYearChange = function () {
            that.setMode();
        };

        that.build = function () {
            var self = instance;

            var task_msg = "Building rangeland_cover";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.post({
                url: "tasks/build_rangeland_cover/",
                data: self.form.serialize(),
                success: function success(response) {
                    if (response.Success === true) {
                        self.triggerEvent('RANGELAND_COVER_BUILD_TASK_COMPLETED');
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
        };

        that.report = function () {
            var self = instance;
            $.get({
                url: url_for_run("report/rangeland_cover/"),
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

        that.setMode = function (mode) {
            var self = instance;
            // mode is an optional parameter
            // if it isn't provided then we get the checked value
            if (mode === undefined) {
                mode = $("input[name='rangeland_cover_mode']:checked").val();
            }
            mode = parseInt(mode, 10);
            var rangeland_rap_year = $("#rangeland_cover_form #rap_year").val();

            var task_msg = "Setting Mode to " + mode + " (" + rangeland_rap_year + ")";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            // sync rangeland_cover with nodb
            $.post({
                url: "tasks/set_rangeland_cover_mode/",
                data: { "mode": mode, "rap_year": rangeland_rap_year },
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
            if (mode == 2) {
                $("#rangeland_cover_form #rangeland_cover_rap_year_div").show();
            } else {
                $("#rangeland_cover_form #rangeland_cover_rap_year_div").hide();
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
