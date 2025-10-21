/* ----------------------------------------------------------------------------
 * Omni
 * ----------------------------------------------------------------------------
 */
var Omni = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        that.form = $("#omni_form");
        that.info = $("#omni_form #info");
        that.status = $("#omni_form  #status");
        that.stacktrace = $("#omni_form #stacktrace");
        that.ws_client = new WSClient('omni_form', 'omni');
        that.ws_client.attachControl(that);
        that.rq_job_id = null;
        that.rq_job = $("#omni_form #rq_job");
        that.command_btn_id = 'btn_run_omni';
        const MAX_SBS_FILE_BYTES = 100 * 1024 * 1024;
        const ALLOWED_SBS_FILE_EXTENSIONS = new Set(['tif', 'tiff', 'img']);

        const baseTriggerEvent = that.triggerEvent.bind(that);
        that.triggerEvent = function (eventName, payload) {
            if (eventName === 'OMNI_SCENARIO_RUN_TASK_COMPLETED') {
                that.report_scenarios();
            }
            else if (eventName === 'END_BROADCAST') {
                that.ws_client.disconnect();
            }

            baseTriggerEvent(eventName, payload);
        };

        that.serializeScenarios = function () {
            const formData = new FormData();
            const scenarioItems = document.querySelectorAll('#omni_form #scenario-container .scenario-item');
            const scenariosList = [];

            scenarioItems.forEach((item, index) => {
                const scenarioSelect = item.querySelector('select[name="scenario"]');
                if (!scenarioSelect || !scenarioSelect.value) return;

                const scenarioType = scenarioSelect.value;
                const scenario = {
                    type: scenarioType
                };

                const controls = item.querySelectorAll('.scenario-controls [name]');
                controls.forEach(control => {
                    if (control.type === 'file' && control.files.length > 0) {
                        const file = control.files[0];
                        if (scenarioType === 'sbs_map') {
                            const extension = file.name.includes('.') ? file.name.split('.').pop().toLowerCase() : '';
                            if (!ALLOWED_SBS_FILE_EXTENSIONS.has(extension)) {
                                throw new Error("SBS maps must be .tif, .tiff, or .img files.");
                            }
                            if (file.size > MAX_SBS_FILE_BYTES) {
                                throw new Error("SBS maps must be 100 MB or smaller.");
                            }
                        }
                        formData.append(`scenarios[${index}][${control.name}]`, file);
                        scenario[control.name] = file.name;
                    } else if (control.value) {
                        scenario[control.name] = control.value;
                    }
                });

                scenariosList.push(scenario);
            });

            formData.append('scenarios', JSON.stringify(scenariosList));
            return formData;
        };


        that.run_omni_scenarios = function () {
            var self = instance;
            var task_msg = "Submitting omni run";

            self.info.text("");
            self.stacktrace.text("");

            let data;
            try {
                data = self.serializeScenarios();
            } catch (err) {
                const message = (err && err.message) ? err.message : "Validation failed. Check SBS uploads.";
                self.status.html(message);
                return;
            }

            self.status.html(task_msg + "...");
            self.ws_client.connect();

            $.post({
                url: "rq/api/run_omni",
                data: data,
                contentType: false,
                processData: false,
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(`run_omni_rq job submitted: ${response.job_id}`);
                        self.set_rq_job_id(self, response.job_id);
                    } else {
                        self.pushResponseStacktrace(self, response);
                    }
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON || { error: "Unknown error occurred" });
                }
            });
        };

        that.load_scenarios_from_backend = function () {
            fetch("api/omni/get_scenarios")
                .then(response => {
                    if (!response.ok) throw new Error("Failed to fetch scenarios");
                    return response.json();
                })
                .then(data => {
                    if (!Array.isArray(data)) throw new Error("Invalid scenario format");

                    data.forEach(scenario => {
                        const scenarioItem = addScenario(scenario);
                        if (!scenarioItem) {
                            return;
                        }
                        const scenarioSelect = scenarioItem.querySelector('select[name="scenario"]');
                        if (scenarioSelect && scenario.type && scenarioSelect.value !== scenario.type) {
                            scenarioSelect.value = scenario.type;
                            updateControls(scenarioSelect, scenario);
                        }

                        Object.entries(scenario).forEach(([key, value]) => {
                            if (key === "type") {
                                return;
                            }
                            const input = scenarioItem.querySelector(`[name="${key}"]`);
                            if (input && input.type !== 'file') {
                                input.value = value;
                            }
                        });
                    });
                })
                .catch(err => {
                    console.error("Error loading scenarios:", err);
                });
        };

        that.report_scenarios = function () {
            var self = instance;
            self.status.html("Omni Scenarios Completed")
        };



        that.report_scenarios = function () {
            var self = instance;

            $.get({
                url: url_for_run("report/omni_scenarios/"),
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
