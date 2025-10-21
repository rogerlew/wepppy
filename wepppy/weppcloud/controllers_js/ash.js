/* ----------------------------------------------------------------------------
 * Ash
 * ----------------------------------------------------------------------------
 */
var Ash = function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        var depthModeContainers = {};
        var depthModeInputs = [];
        var modelSelectEl = null;
        var transportModeEl = null;
        var windCheckboxEl = null;
        var runButtonEl = null;
        var hintEl = null;
        var modelParams = {};
        var modelValuesCache = {};
        var currentModel = null;

        const DEPTH_MODE_IDS = {
            0: 'ash_depth_mode0_controls',
            1: 'ash_depth_mode1_controls',
            2: 'ash_depth_mode2_controls'
        };

        function parseDepthMode(value, fallback) {
            var parsed = parseInt(value, 10);
            return Number.isNaN(parsed) ? fallback : parsed;
        }

        that.form = $("#ash_form");
        that.info = $("#ash_form #info");
        that.status = $("#ash_form  #status");
        that.stacktrace = $("#ash_form #stacktrace");
        that.ws_client = new WSClient('ash_form', 'ash');
        that.ws_client.attachControl(that);
        that.rq_job_id = null;
        that.rq_job = $("#ash_form #rq_job");
        that.command_btn_id = 'btn_run_ash';

        function getFormElement() {
            return document.getElementById('ash_form');
        }

        function applyReadonlyMarkers() {
            var elements = getFormElement();
            if (!elements) {
                return;
            }
            elements.querySelectorAll('[data-disable-readonly]').forEach(function (node) {
                node.classList.add('disable-readonly');
                node.removeAttribute('data-disable-readonly');
            });
        }

        function readModelParams() {
            var scriptNode = document.getElementById('ash-model-params-data');
            if (scriptNode && scriptNode.textContent) {
                try {
                    return JSON.parse(scriptNode.textContent);
                } catch (err) {
                    console.warn('Unable to parse ash model params payload', err);
                }
            }
            if (typeof window.modelParams !== 'undefined') {
                return window.modelParams;
            }
            return {};
        }

        function ensureModelCache(model) {
            if (!modelValuesCache[model]) {
                modelValuesCache[model] = {
                    white: {},
                    black: {}
                };
            }
            return modelValuesCache[model];
        }

        function storeModelValueFromInput(input) {
            if (!input || !input.id || !currentModel) {
                return;
            }
            var separator = input.id.indexOf('_');
            if (separator <= 0) {
                return;
            }
            var color = input.id.slice(0, separator);
            if (color !== 'white' && color !== 'black') {
                return;
            }
            var key = input.id.slice(separator + 1);
            var cache = ensureModelCache(currentModel);
            cache[color][key] = input.value;
        }

        function captureModelValues(model) {
            var formEl = getFormElement();
            if (!formEl || !model) {
                return;
            }
            var cache = ensureModelCache(model);
            if (transportModeEl && model === 'alex') {
                cache.transport_mode = transportModeEl.value;
            }
            formEl.querySelectorAll('input[type="number"]').forEach(function (input) {
                storeModelValueFromInput(input);
            });
        }

        function mergeModelValues(base, overrides) {
            var result = {};
            Object.keys(base || {}).forEach(function (key) {
                result[key] = base[key];
            });
            Object.keys(overrides || {}).forEach(function (key) {
                if (overrides[key] !== undefined) {
                    result[key] = overrides[key];
                }
            });
            return result;
        }

        const baseTriggerEvent = that.triggerEvent.bind(that);
        that.triggerEvent = function (eventName, payload) {
            if (eventName === 'ASH_RUN_TASK_COMPLETED') {
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

            var task_msg = "Running ash model";

            self.info.text("");
            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            if (!self.validateBeforeRun()) {
                return;
            }

            self.ws_client.connect();

            var formEl = getFormElement();
            if (!formEl) {
                self.status.html("Unable to locate ash form");
                return;
            }
            var formData = new FormData(formEl);

            $.post({
                url: "rq/api/run_ash",
                data: formData,
                contentType: false,
                cache: false,
                processData: false,
                success: function success(response) {
                    if (response.Success === true) {
                        self.status.html(`run_ash job submitted: ${response.job_id}`);
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

        that.setAshDepthMode = function (mode) {
            var self = instance;

            if (mode === undefined) {
                var checked = document.querySelector('#ash_form input[name="ash_depth_mode"]:checked');
                mode = checked ? checked.value : undefined;
            }

            self.ash_depth_mode = parseDepthMode(mode, 0);
            self.clearHint();

            depthModeInputs.forEach(function (input) {
                input.checked = parseInt(input.value, 10) === self.ash_depth_mode;
            });

            self.showHideControls();
        };

        that.handleDepthModeChange = function (mode) {
            that.setAshDepthMode(mode);
        };

        that.set_wind_transport = function (state) {
            var self = instance;
            var task_msg = "Setting wind_transport(" + state + ")";

            self.status.html(task_msg + "...");
            self.stacktrace.text("");

            $.post({
                url: "tasks/set_ash_wind_transport/",
                data: JSON.stringify({ run_wind_transport: state }),
                contentType: "application/json; charset=utf-8",
                dataType: "json",
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
                fail: function fail(error) {
                    self.pushErrorStacktrace(self, jqXHR, textStatus, errorThrown);
                }
            });

        };

        that.showHideControls = function () {
            var self = instance;
            var activeMode = Object.prototype.hasOwnProperty.call(DEPTH_MODE_IDS, self.ash_depth_mode)
                ? self.ash_depth_mode
                : 0;

            Object.keys(DEPTH_MODE_IDS).forEach(function (key) {
                var container = depthModeContainers[key];
                if (!container) {
                    var selector = '#' + DEPTH_MODE_IDS[key];
                    var $node = $(selector);
                    if ($node.length) {
                        if (parseInt(key, 10) === activeMode) {
                            $node.show();
                        } else {
                            $node.hide();
                        }
                    }
                    return;
                }
                container.style.display = parseInt(key, 10) === activeMode ? '' : 'none';
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
                url: url_for_run("report/run_ash/"),
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

        that.clearHint = function () {
            if (hintEl) {
                hintEl.textContent = '';
            }
        };

        that.showHint = function (message) {
            if (hintEl) {
                hintEl.textContent = message;
            }
        };

        that.validateBeforeRun = function () {
            var self = instance;
            self.clearHint();

            var mode = self.ash_depth_mode;
            if (mode === undefined) {
                var checked = document.querySelector('#ash_form input[name="ash_depth_mode"]:checked');
                mode = checked ? checked.value : undefined;
            }
            self.ash_depth_mode = parseDepthMode(mode, 0);

            if (self.ash_depth_mode === 2) {
                var errors = [];
                var allowedExtensions = ['.tif', '.tiff', '.img'];
                var inputs = [
                    document.getElementById('input_upload_ash_load'),
                    document.getElementById('input_upload_ash_type_map')
                ].filter(Boolean);

                inputs.forEach(function (input) {
                    if (!input.files || !input.files.length) {
                        return;
                    }
                    var file = input.files[0];
                    var name = (file.name || '').toLowerCase();
                    var hasAllowedExt = allowedExtensions.some(function (ext) {
                        return name.endsWith(ext);
                    });
                    if (!hasAllowedExt) {
                        errors.push(file.name + " must be a .tif, .tiff, or .img file.");
                    }
                    if (file.size > 100 * 1024 * 1024) {
                        errors.push(file.name + " exceeds the 100 MB upload limit.");
                    }
                });

                if (errors.length) {
                    self.showHint(errors.join(' '));
                    return false;
                }
            }

            return true;
        };

        that.updateModelForm = function (options) {
            options = options || {};
            if (!modelSelectEl) {
                return;
            }

            var selectedModel = modelSelectEl.value || 'multi';
            if (options.capturePrevious !== false && currentModel && currentModel !== selectedModel) {
                captureModelValues(currentModel);
            }
            currentModel = selectedModel;

            var isAlex = selectedModel === 'alex';
            var paramsForModel = modelParams[selectedModel] || {};
            var cache = ensureModelCache(selectedModel);

            if (isAlex && transportModeEl && cache.transport_mode) {
                transportModeEl.value = cache.transport_mode;
            }

            document.querySelectorAll('.anu-only-param').forEach(function (node) {
                node.style.display = isAlex ? 'none' : '';
            });
            document.querySelectorAll('.alex-only-param').forEach(function (node) {
                node.style.display = isAlex ? '' : 'none';
            });

            var dynamicDesc = document.getElementById('dynamic_description');
            var staticDesc = document.getElementById('static_description');
            var dynamicParams = document.querySelectorAll('.alex-dynamic-param');
            var staticParams = document.querySelectorAll('.alex-static-param');

            if (isAlex && transportModeEl) {
                var mode = transportModeEl.value || 'dynamic';
                dynamicParams.forEach(function (node) {
                    node.style.display = mode === 'dynamic' ? '' : 'none';
                });
                staticParams.forEach(function (node) {
                    node.style.display = mode === 'static' ? '' : 'none';
                });
                if (dynamicDesc) {
                    dynamicDesc.style.display = mode === 'dynamic' ? '' : 'none';
                }
                if (staticDesc) {
                    staticDesc.style.display = mode === 'static' ? '' : 'none';
                }
            } else {
                dynamicParams.forEach(function (node) {
                    node.style.display = 'none';
                });
                staticParams.forEach(function (node) {
                    node.style.display = 'none';
                });
                if (dynamicDesc) {
                    dynamicDesc.style.display = 'none';
                }
                if (staticDesc) {
                    staticDesc.style.display = 'none';
                }
            }

            ['white', 'black'].forEach(function (color) {
                var mergedValues = mergeModelValues(paramsForModel[color] || {}, cache[color] || {});
                Object.keys(mergedValues).forEach(function (key) {
                    var inputId = color + '_' + key;
                    var input = document.getElementById(inputId);
                    if (input) {
                        input.value = mergedValues[key];
                    }
                });
            });
        };

        that.initializeForm = function () {
            var formEl = getFormElement();
            if (!formEl) {
                return;
            }

            modelParams = readModelParams();
            modelValuesCache = {};

            Object.keys(DEPTH_MODE_IDS).forEach(function (key) {
                depthModeContainers[key] = document.getElementById(DEPTH_MODE_IDS[key]);
            });

            depthModeInputs = Array.prototype.slice.call(
                formEl.querySelectorAll('input[name="ash_depth_mode"]')
            );
            modelSelectEl = document.getElementById('ash_model_select');
            transportModeEl = document.getElementById('ash_transport_mode_select');
            windCheckboxEl = document.getElementById('checkbox_run_wind_transport');
            runButtonEl = formEl.querySelector('[data-ash-action="run"]');
            hintEl = document.getElementById('hint_run_ash');

            applyReadonlyMarkers();

            depthModeInputs.forEach(function (input) {
                input.addEventListener('change', function () {
                    that.setAshDepthMode(this.value);
                });
            });

            if (runButtonEl) {
                runButtonEl.addEventListener('click', function () {
                    that.run();
                });
            }

            if (windCheckboxEl) {
                windCheckboxEl.addEventListener('change', function () {
                    that.set_wind_transport(this.checked);
                });
            }

            if (modelSelectEl) {
                modelSelectEl.addEventListener('change', function () {
                    that.updateModelForm();
                });
            }

            if (transportModeEl) {
                transportModeEl.addEventListener('change', function () {
                    ensureModelCache(currentModel).transport_mode = transportModeEl.value;
                    that.updateModelForm({ capturePrevious: false });
                });
            }

            formEl.querySelectorAll('input[type="number"]').forEach(function (input) {
                input.addEventListener('change', function () {
                    storeModelValueFromInput(this);
                });
            });

            formEl.querySelectorAll('input[type="file"][data-ash-upload]').forEach(function (input) {
                input.addEventListener('change', function () {
                    that.clearHint();
                });
            });

            currentModel = modelSelectEl ? modelSelectEl.value : 'multi';
            ensureModelCache(currentModel);
            that.setAshDepthMode();
            that.updateModelForm({ capturePrevious: false });

            window.updateAshModelForm = function () {
                Ash.getInstance().updateModelForm();
            };
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
