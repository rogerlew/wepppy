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
        that.statusPanelEl = document.getElementById("treatments_status_panel");
        that.stacktracePanelEl = document.getElementById("treatments_stacktrace_panel");
        that.statusStream = null;
        that.ws_client = null;
        that.rq_job_id = null;
        that.rq_job = $("#treatments_form #rq_job");
        that.command_btn_id = 'btn_build_treatments';
        that.hint = $("#hint_build_treatments");

        that.appendStatus = function (message, meta) {
            if (!message) {
                return;
            }
            if (that.statusStream && typeof that.statusStream.append === "function") {
                that.statusStream.append(message, meta || null);
            }
            if (that.status && that.status.length) {
                that.status.html(message);
            }
            if (that.hint && that.hint.length) {
                that.hint.text(message);
            }
        };

        if (typeof StatusStream !== "undefined" && that.statusPanelEl) {
            var stacktraceConfig = null;
            if (that.stacktracePanelEl) {
                stacktraceConfig = { element: that.stacktracePanelEl };
            }
            that.statusStream = StatusStream.attach({
                element: that.statusPanelEl,
                channel: "treatments",
                runId: window.runid || window.runId || null,
                logLimit: 200,
                stacktrace: stacktraceConfig,
                onTrigger: function (detail) {
                    if (detail && detail.event) {
                        that.triggerEvent(detail.event, detail);
                    }
                }
            });
        } else {
            that.ws_client = new WSClient('treatments_form', 'treatments');
            that.ws_client.attachControl(that);
        }

        that.hideStacktrace = function () {
            if (that.stacktrace && that.stacktrace.length) {
                that.stacktrace.hide();
            }
        };

        function getFormElement() {
            return document.getElementById('treatments_form');
        }

        function normalizeMode(mode, fallback) {
            var parsed = parseInt(mode, 10);
            return Number.isNaN(parsed) ? fallback : parsed;
        }

        function getSelectedMode() {
            var formEl = getFormElement();
            if (!formEl) {
                return undefined;
            }
            var checked = formEl.querySelector('input[name="treatments_mode"]:checked');
            return checked ? checked.value : undefined;
        }

        function getTreatmentsSelectValue() {
            var formEl = getFormElement();
            if (!formEl) {
                return undefined;
            }
            var selectEl = formEl.querySelector('#treatments_single_selection');
            return selectEl ? selectEl.value : undefined;
        }

        that.build = function () {
            var self = instance || that;
            var task_msg = "Building treatments";

            self.info.text("");
            self.appendStatus(task_msg + "...");
            if (self.stacktrace && self.stacktrace.length) {
                self.stacktrace.text("");
            }
            if (self.ws_client) {
                self.ws_client.connect();
            }

            var formEl = getFormElement();
            if (!formEl) {
                self.appendStatus("Unable to locate treatments form.");
                return;
            }

            var formData = new FormData(formEl);

            $.post({
                url: "rq/api/build_treatments",
                data: formData,
                contentType: false,
                cache: false,
                processData: false,
                success: function success(response) {
                    if (response.Success === true) {
                        self.appendStatus("build_treatments job submitted: " + response.job_id);
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
            var self = instance || that;
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
            var formEl = getFormElement();
            if (!formEl) {
                return;
            }

            if (treatments_mode !== undefined && treatments_mode !== null) {
                var normalized = normalizeMode(treatments_mode, null);
                if (normalized !== null) {
                    var radio = formEl.querySelector('input[name="treatments_mode"][value="' + normalized + '"]');
                    if (radio) {
                        radio.checked = true;
                    }
                }
            }

            if (typeof treatments_single_selection !== 'undefined' && treatments_single_selection !== null) {
                var selectEl = formEl.querySelector('#treatments_single_selection');
                if (selectEl) {
                    selectEl.value = treatments_single_selection;
                }
            }

            that.updateModeUI(getSelectedMode());
        };

        that.setMode = function (mode) {
            var self = instance || that;
            var selectedMode = mode !== undefined ? mode : getSelectedMode();
            var normalizedMode = normalizeMode(selectedMode, -1);

            var formEl = getFormElement();
            if (formEl) {
                var targetRadio = formEl.querySelector('input[name="treatments_mode"][value="' + normalizedMode + '"]');
                if (targetRadio) {
                    targetRadio.checked = true;
                }
            }

            var treatments_single_selection = getTreatmentsSelectValue();
            if (treatments_single_selection === undefined || treatments_single_selection === null) {
                treatments_single_selection = '';
            }

            var task_msg = "Setting Mode to " + normalizedMode + " (" + treatments_single_selection + ")";

            self.info.text("");
            self.appendStatus(task_msg + "...");
            if (self.stacktrace && self.stacktrace.length) {
                self.stacktrace.text("");
            }

            $.post({
                url: "tasks/set_treatments_mode/",
                data: { "mode": normalizedMode, "treatments_single_selection": treatments_single_selection },
                success: function success(response) {
                    if (response.Success === true) {
                        self.appendStatus(task_msg + "... Success");
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

            self.updateModeUI(normalizedMode);
        };

        that.updateModeUI = function (mode) {
            var normalized = normalizeMode(mode !== undefined ? mode : getSelectedMode(), -1);
            var selectionControls = document.getElementById('treatments_mode1_controls');
            var uploadControls = document.getElementById('treatments_mode4_controls');

            if (selectionControls) {
                selectionControls.style.display = normalized === 1 ? '' : 'none';
            }
            if (uploadControls) {
                uploadControls.style.display = normalized === 4 ? '' : 'none';
            }
        };

        that.initializeForm = function () {
            var formEl = getFormElement();
            if (!formEl) {
                return;
            }
            if (formEl.dataset.treatmentsHandlersBound === "true") {
                return;
            }
            formEl.dataset.treatmentsHandlersBound = "true";

            formEl.querySelectorAll('input[name="treatments_mode"]').forEach(function (radio) {
                radio.addEventListener('change', function () {
                    that.setMode(this.value);
                });
            });

            var selectEl = formEl.querySelector('#treatments_single_selection');
            if (selectEl) {
                selectEl.addEventListener('change', function () {
                    that.setMode();
                });
            }

            var buildButton = document.getElementById('btn_build_treatments');
            if (buildButton) {
                buildButton.addEventListener('click', function () {
                    that.build();
                });
            }

            that.updateModeUI(getSelectedMode());
        };

        return that;
    }

    return {
        getInstance: function getInstance() {
            if (!instance) {
                instance = createInstance();
                instance.initializeForm();
            }
            return instance;
        }
    };
}();
