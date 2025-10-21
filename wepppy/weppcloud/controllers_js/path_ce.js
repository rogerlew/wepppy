/* ----------------------------------------------------------------------------
 * PATH Cost-Effective Control
 * ----------------------------------------------------------------------------
 */
var PathCE = (function () {
    var instance;

    function createInstance() {
        var that = controlBase();
        var endpoints = {
            config: "api/path_ce/config",
            status: "api/path_ce/status",
            results: "api/path_ce/results",
            run: "tasks/path_cost_effective_run"
        };

        var selectors = {
            sddcThreshold: "#path_ce_sddc_threshold",
            sdydThreshold: "#path_ce_sdyd_threshold",
            slopeMin: "#path_ce_slope_min",
            slopeMax: "#path_ce_slope_max",
            severity: "#path_ce_severity",
            treatmentsTable: "#path_ce_treatments_table tbody",
            addTreatmentBtn: "#path_ce_add_treatment",
            hint: "#path_ce_hint",
            rqJob: "#path_ce_rq_job",
            braille: "#path_ce_braille",
            summary: "#path_ce_summary"
        };

        var state = {
            config: null,
            pollingTimer: null,
            availableScenarios: []
        };

        /* --------------------------------------------
         * Utilities
         * -------------------------------------------- */
        function toFloat(value) {
            var num = parseFloat(value);
            return isNaN(num) ? null : num;
        }

        function readSeveritySelection() {
            var options = $(selectors.severity).val() || [];
            return options.length ? options : null;
        }

        function unique(list) {
            var seen = {};
            return list.filter(function (item) {
                if (!item) {
                    return false;
                }
                if (seen[item]) {
                    return false;
                }
                seen[item] = true;
                return true;
            });
        }

        function ensureScenarioOptions(config) {
            var defaults = [
                "mulch_15_sbs_map",
                "mulch_30_sbs_map",
                "mulch_60_sbs_map",
                "sbs_map",
                "undisturbed"
            ];
            var options = defaults.slice();
            if (config && Array.isArray(config.available_scenarios)) {
                options = options.concat(config.available_scenarios);
            }
            if (config && Array.isArray(config.treatment_options)) {
                config.treatment_options.forEach(function (opt) {
                    if (opt && opt.scenario) {
                        options.push(opt.scenario);
                    }
                });
            }
            state.availableScenarios = unique(options);
        }

        function renderTreatments(treatments) {
            var $tbody = $(selectors.treatmentsTable);
            $tbody.empty();

            (treatments || []).forEach(function (treatment, index) {
                var scenarioOptions = state.availableScenarios.length ? state.availableScenarios : [treatment.scenario || ""];
                var scenarioSelect = [
                    '<select class="pure-input-1 path-ce-scenario">'
                ];
                scenarioOptions.forEach(function (optionKey) {
                    var selected = optionKey === treatment.scenario ? ' selected' : '';
                    scenarioSelect.push('<option value="' + optionKey + '"' + selected + '>' + optionKey + '</option>');
                });
                scenarioSelect.push('</select>');

                var row = [
                    '<tr data-index="' + index + '">',
                    '  <td><input type="text" class="pure-input-1 path-ce-label" value="' + (treatment.label || '') + '" /></td>',
                    '  <td>' + scenarioSelect.join("") + '</td>',
                    '  <td><input type="number" class="pure-input-1 path-ce-quantity" step="any" value="' + (treatment.quantity || 0) + '" /></td>',
                    '  <td><input type="number" class="pure-input-1 path-ce-unit-cost" step="any" value="' + (treatment.unit_cost || 0) + '" /></td>',
                    '  <td><input type="number" class="pure-input-1 path-ce-fixed-cost" step="any" value="' + (treatment.fixed_cost || 0) + '" /></td>',
                    '  <td class="wc-table__actions">',
                    '    <button type="button" class="pure-button pure-button-secondary path-ce-remove">Remove</button>',
                    '  </td>',
                    '</tr>'
                ].join("");
                $tbody.append(row);
            });
        }

        function harvestTreatments() {
            var treatments = [];
            $(selectors.treatmentsTable).find("tr").each(function () {
                var $row = $(this);
                var label = $row.find(".path-ce-label").val().trim();
                var scenario = $row.find(".path-ce-scenario").val().trim();
                if (!label || !scenario) {
                    return;
                }
                treatments.push({
                    label: label,
                    scenario: scenario,
                    quantity: toFloat($row.find(".path-ce-quantity").val()) || 0,
                    unit_cost: toFloat($row.find(".path-ce-unit-cost").val()) || 0,
                    fixed_cost: toFloat($row.find(".path-ce-fixed-cost").val()) || 0
                });
            });
            return treatments;
        }

        function displaySummary(results) {
            var $summary = $(selectors.summary);
            $summary.empty();

            if (!results || !Object.keys(results).length) {
                $summary.append('<dt>No results yet.</dt>');
                return;
            }

            var fields = [
                ["Status", results.status || "unknown"],
                ["Used Secondary Solver", results.used_secondary ? "Yes" : "No"],
                ["Total Cost (variable)", results.total_cost != null ? results.total_cost.toFixed(2) : "—"],
                ["Total Fixed Cost", results.total_fixed_cost != null ? results.total_fixed_cost.toFixed(2) : "—"],
                ["Total Sddc Reduction", results.total_sddc_reduction != null ? results.total_sddc_reduction.toFixed(2) : "—"],
                ["Final Sddc", results.final_sddc != null ? results.final_sddc.toFixed(2) : "—"]
            ];

            fields.forEach(function (entry) {
                $summary.append("<dt>" + entry[0] + "</dt><dd>" + entry[1] + "</dd>");
            });
        }

        function showHint(message, isError) {
            var $hint = $(selectors.hint);
            $hint.text(message || "");
            $hint.toggleClass("wc-field__help--error", !!isError);
        }

        function updateStatusPanel(statusPayload) {
            var status = statusPayload || {};
            $(selectors.rqJob).text(status.job || "");
            $(selectors.braille).text(status.braille || "");
            displaySummary(status.results || {});
        }

        /* --------------------------------------------
         * API interactions
         * -------------------------------------------- */
        that.fetchConfig = function () {
            return $.get({
                url: endpoints.config,
                cache: false
            }).done(function (response) {
                state.config = response.config || {};
                ensureScenarioOptions(state.config);
                $(selectors.sddcThreshold).val(state.config.sddc_threshold || "");
                $(selectors.sdydThreshold).val(state.config.sdyd_threshold || "");

                if (state.config.slope_range && state.config.slope_range.length === 2) {
                    $(selectors.slopeMin).val(state.config.slope_range[0] != null ? state.config.slope_range[0] : "");
                    $(selectors.slopeMax).val(state.config.slope_range[1] != null ? state.config.slope_range[1] : "");
                } else {
                    $(selectors.slopeMin).val("");
                    $(selectors.slopeMax).val("");
                }

                if (state.config.severity_filter && state.config.severity_filter.length) {
                    $(selectors.severity).val(state.config.severity_filter);
                } else {
                    $(selectors.severity).val([]);
                }

                renderTreatments(state.config.treatment_options || []);
            }).fail(function (jqXHR) {
                console.warn("[PathCE] fetchConfig error", jqXHR);
                showHint("Failed to load configuration.", true);
            });
        };

        that.saveConfig = function () {
            var payload = {
                sddc_threshold: toFloat($(selectors.sddcThreshold).val()) || 0,
                sdyd_threshold: toFloat($(selectors.sdydThreshold).val()) || 0,
                slope_range: [
                    toFloat($(selectors.slopeMin).val()),
                    toFloat($(selectors.slopeMax).val())
                ],
                severity_filter: readSeveritySelection(),
                treatment_options: harvestTreatments()
            };

            return $.ajax({
                url: endpoints.config,
                method: "POST",
                contentType: "application/json",
                data: JSON.stringify(payload)
            }).done(function (response) {
                showHint("Configuration saved.");
                state.config = response.config || payload;
            }).fail(function (jqXHR) {
                console.warn("[PathCE] saveConfig error", jqXHR);
                showHint("Failed to save configuration.", true);
            });
        };

        function pollStatus() {
            $.get({
                url: endpoints.status,
                cache: false
            }).done(function (response) {
                var status = response || {};
                var statusMessage = status.status_message || "";

                $(selectors.rqJob).text(status.status || "");
                $(selectors.braille).text(status.progress != null ? "Progress: " + Math.round(status.progress * 100) + "%" : "");
                showHint(statusMessage);
            }).fail(function (jqXHR) {
                console.warn("[PathCE] status poll failed", jqXHR);
            });
        }

        function pollResults() {
            $.get({
                url: endpoints.results,
                cache: false
            }).done(function (response) {
                var results = response.results || {};
                displaySummary(results);
            }).fail(function (jqXHR) {
                console.warn("[PathCE] result poll failed", jqXHR);
            });
        }

        function startPolling() {
            stopPolling();
            state.pollingTimer = setInterval(function () {
                pollStatus();
                pollResults();
            }, 5000);
        }

        function stopPolling() {
            if (state.pollingTimer) {
                clearInterval(state.pollingTimer);
                state.pollingTimer = null;
            }
        }

        that.run = function () {
            showHint("Starting PATH Cost-Effective run…");
            startPolling();
            return $.post({
                url: endpoints.run,
                contentType: "application/json",
                data: JSON.stringify({})
            }).done(function (response) {
                showHint("PATH Cost-Effective job submitted. Monitoring status…");
                pollResults();
            }).fail(function (jqXHR) {
                stopPolling();
                console.warn("[PathCE] run error", jqXHR);
                showHint("Failed to enqueue PATH Cost-Effective run.", true);
            });
        };

        that.init = function () {
            $(selectors.addTreatmentBtn).on("click", function () {
                var treatments = harvestTreatments();
                var defaultScenario = state.availableScenarios.length ? state.availableScenarios[0] : "";
                treatments.push({
                    label: "New Treatment",
                    scenario: defaultScenario,
                    quantity: 0,
                    unit_cost: 0,
                    fixed_cost: 0
                });
                renderTreatments(treatments);
            });

            $(document).on("click", ".path-ce-remove", function () {
                $(this).closest("tr").remove();
            });

            that.fetchConfig().then(function () {
                pollStatus();
                pollResults();
            });
        };

        return that;
    }

    return {
        getInstance: function () {
            if (!instance) {
                instance = createInstance();
                instance.init();
            }
            return instance;
        }
    };
})();

window.PathCE = PathCE;
