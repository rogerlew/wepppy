/* ----------------------------------------------------------------------------
 * Treatments
 * ----------------------------------------------------------------------------
 */
var Treatments = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#treatments_form");
        that.info = $("#treatments_form #info");
        that.status = $("#treatments_form  #status");
        that.stacktrace = $("#treatments_form #stacktrace");
        that.ws_client = new WSClient('treatments_form', 'treatments');
        that.rq_job_id = null;
        that.rq_job = $("#treatments_form #rq_job");
        that.command_btn_id = 'btn_build_treatments';


        that.hideStacktrace = function () {
            var self = instance;
            self.stacktrace.hide();
        };

        that.build = function () {
            var self = instance;
            var task_msg = "Building treatments";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");
            self.ws_client.connect();

            var formData = new FormData($('#treatments_form')[0]);

            $.post({
                url: "rq/api/build_treatments",
                data: formData,
                contentType: false,
                cache: false,
                processData: false,
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(`build_treatments job submitted: ${response.job_id}`);
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
                url: url_for_run("report/treatments/"),
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

        that.restore = function (treatments_mode, treatments_single_selection) {
            console.log("restore treatments mode: " + treatments_mode);
            var self = instance;
            $("#treatments_mode" + treatments_mode).prop("checked", true);

            $('#treatments_single_selection').val('{{ treatments.single_selection }}').prop('selected', true);

            self.showHideControls(treatments_mode);
        };

        that.setMode = function (mode) {
            var self = instance;
            // mode is an optional parameter
            // if it isn't provided then we get the checked value
            if (mode === undefined) {
                mode = $("input[name='treatments_mode']:checked").val();
            }
            mode = parseInt(mode, 10);
            var treatments_single_selection = $("#treatments_single_selection").val();

            var task_msg = "Setting Mode to " + mode + " (" + treatments_single_selection + ")";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            // sync treatments with nodb
            $.post({
                url: "tasks/set_treatments_mode/",
                data: { "mode": mode, "treatments_single_selection": treatments_single_selection },
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
                // undefined
                $("#treatments_mode1_controls").hide();
                $("#treatments_mode4_controls").hide();
            } else if (mode === 1) {
                // selection
                $("#treatments_mode1_controls").show();
                $("#treatments_mode4_controls").hide();
            } else if (mode === 4) {
                // map
                $("#treatments_mode1_controls").hide();
                $("#treatments_mode4_controls").show();
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
