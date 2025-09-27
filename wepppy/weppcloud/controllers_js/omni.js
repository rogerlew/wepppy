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
        that.rq_job_id = null;
        that.rq_job = $("#omni_form #rq_job");
        that.command_btn_id = 'btn_run_omni';

        function escapeHtml(value) {
            if (value === null || value === undefined) {
                return '';
            }
            const div = document.createElement('div');
            div.textContent = value;
            return div.innerHTML;
        }

        that.serializeScenarios = function () {
            const formData = new FormData();
            const scenarioItems = document.querySelectorAll('#omni_form #scenario-container .scenario-item');
            const scenariosList = [];

            scenarioItems.forEach((item, index) => {
                const scenarioSelect = item.querySelector('select[name="scenario"]');
                if (!scenarioSelect || !scenarioSelect.value) return;

                const scenario = {
                    type: scenarioSelect.value
                };

                const controls = item.querySelectorAll('.scenario-controls [name]');
                controls.forEach(control => {
                    if (control.type === 'file' && control.files.length > 0) {
                        formData.append(`scenarios[${index}][${control.name}]`, control.files[0]);
                        scenario[control.name] = control.files[0].name;
                    } else if (control.value) {
                        scenario[control.name] = control.value;
                    }
                });

                scenariosList.push(scenario);
            });

            formData.append('scenarios', JSON.stringify(scenariosList));
            return formData;
        };

        that.render_run_state = function (payload) {
            const container = document.getElementById('scenario-run-state');
            if (!container) {
                return;
            }

            const runState = (payload && Array.isArray(payload.run_state)) ? payload.run_state : [];

            if (runState.length === 0) {
                container.innerHTML = '<span class="text-muted">No recent scenario runs.</span>';
                return;
            }

            const entries = runState.map((entry) => {
                const statusExecuted = entry.status === 'executed';
                const statusLabel = statusExecuted ? 'Ran' : 'Skipped';
                const cssClass = statusExecuted ? 'text-success' : 'text-secondary';
                const reason = entry.reason === 'dependency_unchanged' ? 'dependency unchanged' : 'dependency changed';
                const dependency = entry.dependency_target ? ` · depends on ${escapeHtml(entry.dependency_target)}` : '';
                const timestamp = entry.timestamp ? new Date(entry.timestamp * 1000).toLocaleString() : '';
                const when = timestamp ? ` · ${escapeHtml(timestamp)}` : '';
                return `<div class="${cssClass}"><strong>${escapeHtml(entry.scenario)}</strong> — ${statusLabel}${dependency}${when}<span class="text-muted small"> (${escapeHtml(reason)})</span></div>`;
            }).join('');

            container.innerHTML = entries;
        };

        that.fetch_run_state = function () {
            fetch("api/omni/get_scenario_run_state")
                .then(response => {
                    if (!response.ok) {
                        throw new Error("Failed to fetch scenario run state");
                    }
                    return response.json();
                })
                .then(data => {
                    that.render_run_state(data);
                })
                .catch(err => {
                    console.error("Error fetching scenario run state:", err);
                });
        };


        that.run_omni_scenarios = function () {
            var self = instance;
            var task_msg = "Submitting omni run";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");
            self.ws_client.connect();

            const stateContainer = document.getElementById('scenario-run-state');
            if (stateContainer) {
                stateContainer.innerHTML = '<span class="text-info">Running scenarios...</span>';
            }

            const data = self.serializeScenarios();
            for (let [key, value] of data.entries()) {
                console.log(`${key}: ${value instanceof File ? value.name : value}`);
            }

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
                        addScenario();
                        const container = document.querySelectorAll('#scenario-container .scenario-item');
                        const latestItem = container[container.length - 1];
                        const scenarioSelect = latestItem.querySelector('select[name="scenario"]');
                        scenarioSelect.value = scenario.type;

                        // Trigger controls to be rendered
                        updateControls(scenarioSelect);

                        // Populate the controls with values
                        Object.entries(scenario).forEach(([key, value]) => {
                            if (key === "type") return;
                            const input = latestItem.querySelector(`[name="${key}"]`);
                            if (input) {
                                input.value = value;
                            }
                        });
                    });
                })
                .catch(err => {
                    console.error("Error loading scenarios:", err);
                })
                .then(() => {
                    that.fetch_run_state();
                });
        };

        that.report_scenarios = function () {
            var self = instance;
            self.status.html("Omni Scenarios Completed")
        };



        that.report_scenarios = function () {
            var self = instance;

            $.get({
                url: "report/omni_scenarios/",
                cache: false,
                success: function success(response) {
                    self.info.html(response);
                    self.fetch_run_state();
                },
                error: function error(jqXHR) {
                    self.pushResponseStacktrace(self, jqXHR.responseJSON);
                },
                fail: function fail(jqXHR, textStatus, errorThrown) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });
        };

        that.render_run_state({ run_state: [] });
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
