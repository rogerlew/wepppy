/* Saved assessment explorer: no model execution or scientific recomputation. */
(function (global) {
    "use strict";
    var instance;
    var reasons = {
        missing_duration: "Rainfall window not recorded", missing_intensity: "Rainfall intensity not recorded",
        nonfinite_intensity: "Rainfall intensity is invalid", negative_intensity: "Rainfall intensity is invalid",
        missing_noaa: "NOAA rainfall is unavailable", unsupported_combination: "Rainfall combination not available",
        zero_placeholder: "Rainfall estimate not available", insufficient_positive_samples: "Insufficient positive rainfall samples",
        invalid_year_labels: "Climate year labels are invalid", missing_predictor: "Required model input is unavailable",
        missing_predictors: "Required model inputs are unavailable; inspect the input explanations in Methods",
        zero_valid_support: "No common valid input cells; check the coverage of the accepted input maps",
        terrain_potentially_truncated: "Upstream terrain may extend beyond the elevation map; check terrain coverage in the run control",
        watershed_area_mismatch: "Upstream terrain does not match the watershed area; check watershed delineation in the run control",
        unresolved_intersection: "Input overlap could not be resolved; inspect the saved assessment manifest",
        zero_relief: "Watershed relief is zero; check the accepted terrain inputs",
        zero_area: "Watershed area is zero; check the accepted watershed delineation",
        zero_valid_cells: "No valid input cells", no_valid_cells: "No valid input cells"
    };
    function reason(code) {
        return reasons[code] || "Not available; see the saved assessment manifest for support details";
    }
    function finite(value) { return typeof value === "number" && Number.isFinite(value); }
    function recorded(value) { return value === null || value === undefined ? "Not recorded" : String(value); }
    function probability(value) {
        if (!finite(value)) return "Unavailable";
        if (value > 0 && value < 0.0005) return "<0.1%";
        if (value < 1 && value >= 0.9995) return ">99.9%";
        return String(Math.round(value * 1000) / 10) + "%";
    }
    function node(tag, text, attrs) {
        var element = document.createElement(tag);
        if (text !== undefined) element.textContent = text;
        Object.keys(attrs || {}).forEach(function (key) { element.setAttribute(key, attrs[key]); });
        return element;
    }
    function csvCell(value) {
        if (value === null || value === undefined) return "";
        if (typeof value === "number") return String(value);
        var text = String(value);
        // Quoting alone does not stop spreadsheet evaluation of untrusted labels.
        // eslint-disable-next-line no-control-regex -- spreadsheet prefixes may follow ASCII controls.
        if (/^[\s\x00-\x1f]*[=+@-]/.test(text)) text = "'" + text;
        return '"' + text.replace(/"/g, '""') + '"';
    }
    function Controller() {
        var dom = global.WCDom;
        var http = global.WCHttp;
        if (!dom || !http) throw new Error("PostfireReport requires WCDom and WCHttp");
        var root, payload, generation = 0, selectedScenario = null, selectedEvent = null;
        var detailRows = null, detailError = false, replaced = false, previousView = false, pendingQuery = null, retryAction = null, loadingQuery = false;
        var unitListener;
        function qs(selector) { return dom.qs(selector, root); }
        function field(name) { return qs('[data-pfr-field="' + name + '"]'); }
        function setText(selector, value) { qs(selector).textContent = value; }
        function unit(base) {
            var client = global.UnitizerClient.getClientSync();
            if (!client) return {base: base, key: base, precision: 2, client: null};
            var preferences = client.getPreferencePayload();
            var keys = Object.keys(preferences);
            for (var index = 0; index < keys.length; index += 1) {
                var category = client.getCategory(keys[index]);
                if (category && category.units.some(function (entry) { return entry.key === base; })) {
                    var key = preferences[keys[index]];
                    var selected = category.units.find(function (entry) { return entry.key === key; });
                    return {base: base, key: key, precision: selected.precision, client: client};
                }
            }
            throw new Error("PostfireReport requires the Unitizer category for " + base);
        }
        function converted(value, info) {
            if (!finite(value)) return null;
            return info.client ? info.client.convert(value, info.base, info.key) : value;
        }
        function quantity(value, base, code) {
            if (!finite(value)) return "Unavailable — " + reason(code);
            var info = unit(base);
            return converted(value, info).toFixed(info.precision);
        }
        function dateLabel(row) {
            if (row.date_status === "invalid_or_missing" || ![row.year, row.month, row.day_of_month].every(finite)) {
                return "Date unavailable (event " + (row.row_ordinal + 1) + ")";
            }
            var prefix = payload.summary.date_semantics === "simulation_labels" ? "Simulation " : "";
            return prefix + row.year + " / " + row.month + " / " + row.day_of_month;
        }
        function status(message, canRetry, reload) {
            setText("[data-pfr-status]", message);
            dom.qsa("[data-pfr-event-status]", root).forEach(function (element) { element.textContent = message; });
            dom.qsa('[data-pfr-action="retry"]', root).forEach(function (button) { button.hidden = !canRetry; });
            qs('[data-pfr-action="reload"]').hidden = !reload;
        }
        function scenarioRows() {
            return payload.design.filter(function (row) { return row.duration_minutes === payload.query.duration_minutes; });
        }
        function unitsRow(body, values) {
            var tr = node("tr", undefined, {"data-sort-position": "top"});
            values.forEach(function (value) { tr.appendChild(node("td", value)); });
            body.appendChild(tr);
        }
        function likelihood(row) {
            return finite(row.probability) ? probability(row.probability) : "Unavailable — " + reason(row.reason);
        }
        function renderSummary() {
            var summary = payload.summary;
            setText("[data-pfr-summary]", "Accepted model " + recorded(summary.model) + " · Completed " + recorded(summary.completed_at) +
                " · Watershed area: " + (finite(summary.area_km2) ? quantity(summary.area_km2, "km^2") + " " + unit("km^2").key : "Not recorded"));
            var current = summary.current === true ? "Results match the current inputs." : summary.current === false ?
                "Inputs have changed; these are previous results." : "Could not check whether these results match the current inputs.";
            if (summary.newer_attempt) current += " A newer " + recorded(summary.newer_attempt.model) + " attempt is " + recorded(summary.newer_attempt.phase) + "; the accepted results shown have not been replaced.";
            setText("[data-pfr-current]", current);
            var coverage = summary.coverage;
            setText("[data-pfr-coverage]", coverage ? "Usable input coverage: " + coverage.valid_cells + " of " + coverage.total_cells +
                " cells (" + probability(coverage.valid_fraction) + "); " + coverage.excluded_cells + " excluded. Coverage is not confidence." :
                "Common input coverage: Not recorded. Legacy independent input support is described in Methods.");
            var notices = [];
            if (finite(summary.area_km2) && (summary.area_km2 < 0.2 || summary.area_km2 > 8)) notices.push("Watershed area is outside the published study range of 0.2–8 km²; interpret applicability with care.");
            if (summary.warnings.indexOf("partial_dnbr_coverage") !== -1) notices.push("The dNBR map covers only part of the watershed; inspect input coverage before interpreting results.");
            if (summary.warnings.indexOf("unrecorded_warning") !== -1) notices.push("The accepted assessment has an additional input or applicability warning; see the saved manifest for support details.");
            summary.predictors.filter(function (predictor) { return !finite(predictor.value); }).forEach(function (predictor) {
                notices.push("Unavailable input " + predictor.name + ": " + reason(predictor.reason) + ".");
            });
            setText("[data-pfr-warnings]", notices.join(" "));
            var frequency = summary.frequency;
            setText("[data-pfr-source]", "Saved rainfall-frequency source: " + (summary.frequency_source === "noaa" ? "NOAA Atlas 14 PDS" : summary.frequency_source === "cli" ? "Project climate PDS" : "Not recorded") + ".");
            setText("[data-pfr-climate]", "Accepted climate mode: " + recorded(summary.climate_mode) + ". Years represented: " + recorded(frequency.represented_years) +
                " (original labels " + recorded(frequency.year_min) + "–" + recorded(frequency.year_max) + "; not necessarily a continuous record)." +
                (summary.date_semantics === "simulation_labels" ? " Dates below are simulation labels, not observed calendar dates." : " Dates retain the accepted climate provenance."));
            setText("[data-pfr-date-heading]", summary.date_semantics === "simulation_labels" ? "Simulation year / month / day" : "Date label (year / month / day)");
            var methods = qs("[data-pfr-methods]"); methods.replaceChildren();
            methods.appendChild(node("p", "Assessment ID: " + recorded(summary.assessment_id) + ". Accepted attempt ID: " + payload.attempt_id + "."));
            methods.appendChild(node("p", "Wet years: " + recorded(frequency.wet_years) + ". " + (coverage ? "Inputs use the saved common-valid support." : "Legacy v1 M1 inputs have independent support; no common-valid fraction or mask is inferred.")));
            summary.predictors.forEach(function (predictor) {
                methods.appendChild(node("p", predictor.name + ": " + (finite(predictor.value) ? predictor.value + " " + predictor.unit : "Unavailable — " + reason(predictor.reason))));
            });
        }
        function renderDesign() {
            var body = qs('[data-pfr-body="design"]'); body.replaceChildren();
            unitsRow(body, ["years", unit("mm/hour").key, unit("mm").key, "%"]);
            scenarioRows().forEach(function (row, index) {
                var tr = node("tr");
                var cell = node("td");
                cell.appendChild(node("button", String(row.return_interval_years), {type: "button", "class": "pure-button pure-button-link", "data-pfr-scenario": index,
                    "aria-label": "Select " + row.return_interval_years + "-year rainfall scenario", "aria-pressed": "false"}));
                tr.appendChild(cell);
                [quantity(row.intensity_mm_per_hour, "mm/hour", row.reason), quantity(row.rainfall_mm, "mm", row.reason), likelihood(row)].forEach(function (value) { tr.appendChild(node("td", value)); });
                body.appendChild(tr);
            });
            var inverse = qs('[data-pfr-body="inverse"]'); inverse.replaceChildren();
            unitsRow(inverse, ["minutes", unit("mm/hour").key, unit("mm").key]);
            payload.inverse.forEach(function (row) {
                var tr = node("tr");
                [row.duration_minutes, quantity(row.intensity_mm_per_hour, "mm/hour", row.reason), quantity(row.rainfall_mm, "mm", row.reason)].forEach(function (value) { tr.appendChild(node("td", value)); });
                inverse.appendChild(tr);
            });
        }
        function svgNode(tag, attrs, text) {
            var element = document.createElementNS("http://www.w3.org/2000/svg", tag);
            Object.keys(attrs).forEach(function (key) { element.setAttribute(key, attrs[key]); });
            if (text !== undefined) element.textContent = text;
            return element;
        }
        function renderChart() {
            var chart = qs("[data-pfr-chart]"); chart.replaceChildren();
            var rows = scenarioRows(); var intensity = unit("mm/hour");
            var points = rows.filter(function (row) { return finite(row.probability) && finite(row.intensity_mm_per_hour); });
            if (!points.length) { chart.appendChild(node("p", "No available rainfall scenario points; see the table for reasons.")); return; }
            var maximum = Math.max.apply(null, points.map(function (row) { return converted(row.intensity_mm_per_hour, intensity); }));
            if (maximum === 0) maximum = 1;
            var svg = svgNode("svg", {viewBox: "0 0 680 300", width: "100%", style: "max-width:56rem", "aria-label": payload.query.duration_minutes + "-minute rainfall scenarios; likelihood scale zero to one hundred percent", role: "group"});
            [0, 25, 50, 75, 100].forEach(function (percent) {
                var y = 250 - percent * 2;
                svg.appendChild(svgNode("line", {x1: 65, y1: y, x2: 630, y2: y, stroke: "currentColor", "stroke-opacity": ".2"}));
                svg.appendChild(svgNode("text", {x: 55, y: y + 5, "text-anchor": "end", fill: "currentColor", "font-size": 13}, percent + "%"));
            });
            [0, 0.25, 0.5, 0.75, 1].forEach(function (fraction) {
                svg.appendChild(svgNode("text", {x: 65 + fraction * 565, y: 270, "text-anchor": "middle", fill: "currentColor", "font-size": 13}, (fraction * maximum).toFixed(intensity.precision)));
            });
            svg.appendChild(svgNode("text", {x: 345, y: 294, "text-anchor": "middle", fill: "currentColor", "font-size": 14}, "Peak rainfall intensity (" + intensity.key + ")"));
            svg.appendChild(svgNode("text", {x: 65, y: 22, fill: "currentColor", "font-size": 14}, "Modeled likelihood · " + payload.query.duration_minutes + "-minute window"));
            rows.forEach(function (row, index) {
                if (!finite(row.probability) || !finite(row.intensity_mm_per_hour)) return;
                var x = 65 + converted(row.intensity_mm_per_hour, intensity) / maximum * 565;
                var y = 250 - row.probability * 200;
                var label = payload.query.duration_minutes + " minutes, " + row.return_interval_years + "-year rainfall recurrence, intensity " + quantity(row.intensity_mm_per_hour, "mm/hour") + " " + intensity.key +
                    ", window rainfall " + quantity(row.rainfall_mm, "mm") + " " + unit("mm").key + ", likelihood " + probability(row.probability);
                svg.appendChild(svgNode("circle", {cx: x, cy: y, r: 7, fill: "currentColor", stroke: "currentColor", tabindex: 0, role: "button", "aria-label": label, "aria-pressed": "false", "data-pfr-scenario": index}));
            });
            chart.appendChild(svg);
        }
        function syncScenario() {
            dom.qsa("[data-pfr-scenario]", root).forEach(function (element) {
                var selected = Number(element.dataset.pfrScenario) === selectedScenario;
                element.setAttribute("aria-pressed", String(selected));
                if (element.tagName.toLowerCase() === "circle") {
                    element.setAttribute("r", selected ? "10" : "7");
                    element.setAttribute("stroke-width", selected ? "3" : "1");
                } else {
                    element.textContent = (selected ? "Selected: " : "") + scenarioRows()[Number(element.dataset.pfrScenario)].return_interval_years;
                }
            });
        }
        function renderDetail() {
            dom.qsa("[data-pfr-detail]", root).forEach(function (element) { element.remove(); });
            dom.qsa("[data-pfr-event]", root).forEach(function (button) {
                var selected = button.dataset.pfrEvent === selectedEvent;
                button.setAttribute("aria-expanded", String(selected));
                if (!selected) { button.removeAttribute("aria-controls"); return; }
                button.setAttribute("aria-controls", "pfr-event-detail");
                var tr = node("tr", undefined, {"data-pfr-detail": "", id: "pfr-event-detail"});
                var td = node("td", undefined, {colspan: 5});
                td.appendChild(node("p", "All three rainfall windows for " + button.textContent));
                if (detailError) {
                    td.appendChild(node("p", "Could not load this storm's details. The event table above is unchanged.", {role: "status"}));
                    td.appendChild(node("button", "Retry event details", {type: "button", "class": "pure-button", "data-pfr-detail-retry": ""}));
                } else if (!detailRows) td.appendChild(node("p", "Loading event details…"));
                else {
                    var table = node("table", undefined, {"class": "wc-table wc-table--compact wc-table--dense"});
                    var head = node("thead"); var header = node("tr");
                    ["Window (minutes)", "Peak intensity (" + unit("mm/hour").key + ")", "Window rainfall (" + unit("mm").key + ")", "Modeled likelihood"].forEach(function (text) { header.appendChild(node("th", text, {scope: "col"})); });
                    head.appendChild(header); table.appendChild(head);
                    var body = node("tbody");
                    detailRows.forEach(function (row) {
                        var line = node("tr");
                        [row.duration_minutes, quantity(row.intensity_mm_per_hour, "mm/hour", row.reason), quantity(row.rainfall_mm, "mm", row.reason), likelihood(row)].forEach(function (text) { line.appendChild(node("td", text)); });
                        body.appendChild(line);
                    });
                    table.appendChild(body); td.appendChild(table);
                }
                tr.appendChild(td); button.closest("tr").after(tr);
            });
        }
        function renderEvents() {
            var body = qs('[data-pfr-body="events"]'); body.replaceChildren();
            unitsRow(body, ["", unit("mm/hour").key, unit("mm").key, unit("mm").key, "%"]);
            payload.events.rows.forEach(function (row) {
                var tr = node("tr"); var cell = node("td");
                cell.appendChild(node("button", dateLabel(row), {type: "button", "class": "pure-button pure-button-link", "data-pfr-event": row.event_id, "aria-expanded": "false"}));
                cell.firstChild.disabled = loadingQuery;
                tr.appendChild(cell);
                [quantity(row.intensity_mm_per_hour, "mm/hour", row.reason), quantity(row.rainfall_mm, "mm", row.reason), quantity(row.precipitation_mm, "mm", row.reason), likelihood(row)].forEach(function (text) { tr.appendChild(node("td", text)); });
                body.appendChild(tr);
            });
            var total = payload.events.total, start = payload.events.rows.length ? payload.query.offset + 1 : 0;
            var text = "Showing " + start + "–" + (start ? payload.query.offset + payload.events.rows.length : 0) + " of " + total + " matching storm events. " + payload.events.unfiltered_total + " storm events before filters.";
            if (!payload.events.rows.length) text += payload.events.unfiltered_total ? " No storms match these filters." : " No storm events in this climate record.";
            setText("[data-pfr-count]", text);
            qs('[data-pfr-action="previous"]').disabled = payload.query.offset === 0 || replaced;
            qs('[data-pfr-action="next"]').disabled = payload.query.offset + payload.query.limit >= total || payload.query.offset + payload.query.limit > 200000 || replaced;
            renderDetail();
        }
        function renderDownloads() {
            var list = qs("[data-pfr-downloads]"); list.replaceChildren();
            var labels = {"events.parquet": "All saved events (canonical units)", "design.parquet": "All saved design scenarios (canonical units)", "inverse.parquet": "All saved thresholds (canonical units)", "manifest.json": "Saved assessment manifest", "valid_mask.tif": "Saved validity mask"};
            Object.keys(payload.urls.artifacts).forEach(function (name) {
                var item = node("li"); item.appendChild(node("a", labels[name], {href: payload.urls.artifacts[name]})); list.appendChild(item);
            });
        }
        function hydrateFields() {
            field("duration").value = String(payload.query.duration_minutes);
            field("min_probability").value = payload.query.min_probability === null ? "" : payload.query.min_probability * 100;
            field("year").value = payload.query.year === null ? "" : payload.query.year;
            field("sort").value = payload.query.sort; field("descending").checked = payload.query.descending;
        }
        function render() {
            if (!payload || payload.status !== "available" || replaced) return;
            dom.qsa("[data-pfr-window]", root).forEach(function (element) { element.textContent = payload.query.duration_minutes + " minutes"; });
            renderSummary(); renderDesign(); renderChart(); syncScenario(); renderEvents(); renderDownloads();
        }
        function requestUrl(base, query) {
            var url = new URL(base, global.location.href);
            Object.keys(query).forEach(function (key) {
                if (query[key] !== null && query[key] !== undefined && query[key] !== "") url.searchParams.set(key, String(query[key]));
            });
            return url.pathname + url.search;
        }
        function fail(error, detailFailure) {
            dom.qsa("[data-pfr-event]", root).forEach(function (button) { button.disabled = false; });
            var body = error && (error.body || error.response);
            var code = body && body.error && body.error.code;
            if (code === "assessment_replaced") {
                replaced = true; selectedEvent = null; detailRows = null; renderDetail();
                dom.qsa("[data-pfr-export], [data-pfr-event], [data-pfr-field], [data-pfr-action=apply], [data-pfr-action=reset], [data-pfr-action=next], [data-pfr-action=previous]", root).forEach(function (element) { element.disabled = true; });
                qs("[data-pfr-downloads]").replaceChildren();
                status("This assessment was replaced. Reload the report to inspect the new results; downloads are disabled.", false, true);
            } else {
                if (!detailFailure) previousView = true;
                status(previousView ? "Could not update results. Showing the previous coherent view; displayed-row exports also contain that previous view." :
                    "Could not update event details. The displayed event table is unchanged; retry beside the selected storm.", true, false);
            }
        }
        function queryFromFields(offset) {
            return {duration_minutes: Number(field("duration").value), min_probability: field("min_probability").value === "" ? null : Number(field("min_probability").value) / 100,
                year: field("year").value === "" ? null : Number(field("year").value), sort: field("sort").value,
                descending: field("descending").checked, limit: 100, offset: offset};
        }
        function selectedMatches(rows, query) {
            var row = rows.find(function (entry) { return entry.duration_minutes === query.duration_minutes; });
            return row && (query.year === null || row.year === query.year) &&
                (query.min_probability === null || (finite(row.probability) && row.probability >= query.min_probability));
        }
        function selectionNotice() {
            if (!selectedEvent || payload.events.rows.some(function (row) { return row.event_id === selectedEvent; })) return "";
            return detailRows ? "Selected storm retained; it is outside this page. Its details will appear when its row is shown again." :
                "Checking whether the selected storm still matches these filters…";
        }
        async function refresh(query) {
            if (replaced) return;
            pendingQuery = query; retryAction = function () { return refresh(pendingQuery); };
            loadingQuery = true;
            var requestGeneration = ++generation;
            dom.qsa("[data-pfr-event]", root).forEach(function (button) { button.disabled = true; });
            status("Loading results… The previous view remains visible until the new page is ready.", false, false);
            try {
                var next = await http.getJson(requestUrl(payload.urls.query, Object.assign({attempt_id: payload.attempt_id}, query)));
                if (requestGeneration !== generation) return;
                loadingQuery = false;
                if (next.attempt_id !== payload.attempt_id) { fail({body: {error: {code: "assessment_replaced"}}}); return; }
                if (next.query.duration_minutes !== payload.query.duration_minutes) selectedScenario = null;
                // Pagination is not filter eligibility: retain a matching selection even off-page.
                var cleared = selectedEvent && detailRows && !selectedMatches(detailRows, next.query);
                if (cleared) { selectedEvent = null; detailRows = null; }
                payload = next; previousView = false; hydrateFields(); render();
                status(cleared ? "The selected storm no longer matches these filters; its detail was cleared." : selectionNotice(), false, false);
                if (selectedEvent && !detailRows) loadDetail(selectedEvent);
            } catch (error) { if (requestGeneration === generation) { loadingQuery = false; hydrateFields(); fail(error); } }
        }
        async function loadDetail(eventId) {
            if (replaced || loadingQuery) return;
            var requestGeneration = ++generation;
            selectedEvent = eventId; detailRows = null; detailError = false; renderDetail();
            retryAction = function () { return loadDetail(eventId); };
            try {
                var response = await http.getJson(requestUrl(payload.urls.event, {attempt_id: payload.attempt_id, event_id: eventId}));
                if (requestGeneration !== generation || eventId !== selectedEvent) return;
                if (response.attempt_id !== payload.attempt_id) { fail({body: {error: {code: "assessment_replaced"}}}); return; }
                detailRows = response.rows;
                if (!selectedMatches(detailRows, payload.query)) {
                    selectedEvent = null; detailRows = null; renderDetail();
                    status("The selected storm no longer matches these filters; its detail was cleared.", false, false);
                    return;
                }
                renderDetail();
                if (previousView) {
                    retryAction = function () { return refresh(pendingQuery); };
                    status("Could not update results. Showing the previous coherent view; displayed-row exports also contain that previous view.", true, false);
                } else status(selectionNotice(), false, false);
            } catch (error) {
                if (requestGeneration === generation) {
                    detailError = true; renderDetail(); fail(error, true);
                }
            }
        }
        function csv(kind) {
            if (replaced || !payload || payload.status !== "available") return "";
            var rows = kind === "events" ? payload.events.rows : kind === "design" ? scenarioRows() : payload.inverse;
            var intensity = unit("mm/hour"), rain = unit("mm");
            var contextKeys = ["model", "assessment_id", "attempt_id", "view", "selected_window_minutes", "min_probability_fraction", "year_filter", "sort", "descending", "offset", "limit", "intensity_unit", "rainfall_unit", "probability_unit"];
            var context = [payload.summary.model, payload.summary.assessment_id, payload.attempt_id, previousView ? "previous view" : "displayed view", payload.query.duration_minutes, payload.query.min_probability,
                payload.query.year, payload.query.sort, payload.query.descending, payload.query.offset, payload.query.limit, intensity.key, rain.key, "fraction (0–1)"];
            var columns = ["event_id", "date_label", "date_semantics", "return_interval_years", "duration_minutes", "peak_intensity", "window_rainfall", "total_event_rainfall", "probability_fraction", "target_probability_fraction", "reason"];
            var lines = [contextKeys.concat(columns).map(csvCell).join(",")];
            rows.forEach(function (row) {
                lines.push(context.concat([row.event_id, kind === "events" ? dateLabel(row) : null, payload.summary.date_semantics, row.return_interval_years, row.duration_minutes,
                    converted(row.intensity_mm_per_hour, intensity), converted(row.rainfall_mm, rain), converted(row.precipitation_mm, rain), row.probability, row.target_probability, row.reason]).map(csvCell).join(","));
            });
            return lines.join("\r\n");
        }
        function download(kind) {
            var content = csv(kind); if (!content) return;
            var url = URL.createObjectURL(new Blob([content], {type: "text/csv;charset=utf-8"}));
            var link = node("a", "", {href: url, download: "postfire-" + payload.attempt_id + "-" + kind + ".csv"});
            root.appendChild(link); link.click(); link.remove();
            global.setTimeout(function () { URL.revokeObjectURL(url); }, 0);
        }
        function bootstrap() {
            var nextRoot = dom.qs("[data-postfire-report]");
            if (!nextRoot || nextRoot === root) return;
            root = nextRoot;
            dom.delegate(root, "click", '[data-pfr-action="reload"]', function () { global.location.reload(); });
            payload = JSON.parse(qs("#postfire-report-seed").textContent);
            selectedScenario = null; selectedEvent = null; detailRows = null; detailError = false; replaced = false; previousView = false; loadingQuery = false; generation += 1;
            if (!payload) { status("Results are unavailable. Reload the report or inspect the existing run control.", false, true); return; }
            qs("[data-pfr-control]").href = payload.urls.control;
            qs("[data-pfr-empty]").hidden = payload.status !== "absent";
            qs("[data-pfr-results]").hidden = payload.status !== "available";
            dom.delegate(root, "click", "[data-pfr-action]", function (event, button) {
                var action = button.dataset.pfrAction;
                if (action === "reload") return;
                if (action === "retry") { if (retryAction) retryAction(); return; }
                if (action === "apply") return; // The form submit owns validation and Enter-key behavior.
                if (action === "reset") { field("min_probability").value = ""; field("year").value = ""; field("sort").value = "row_ordinal"; field("descending").checked = false; refresh(queryFromFields(0)); }
                if (action === "previous" || action === "next") refresh(Object.assign({}, payload.query, {offset: payload.query.offset + (action === "next" ? 100 : -100)}));
            });
            dom.delegate(root, "submit", "[data-pfr-filters]", function (event) { event.preventDefault(); refresh(queryFromFields(0)); });
            dom.delegate(root, "change", '[data-pfr-field="duration"]', function () { refresh(queryFromFields(0)); });
            dom.delegate(root, "click", "[data-pfr-scenario]", function (event, target) { selectedScenario = Number(target.dataset.pfrScenario); syncScenario(); });
            dom.delegate(root, "keydown", "circle[data-pfr-scenario]", function (event, target) {
                if (event.key === "Enter" || event.key === " ") { event.preventDefault(); selectedScenario = Number(target.dataset.pfrScenario); syncScenario(); }
            });
            dom.delegate(root, "click", "[data-pfr-event]", function (event, target) {
                if (selectedEvent === target.dataset.pfrEvent) { generation += 1; selectedEvent = null; detailRows = null; renderDetail(); }
                else loadDetail(target.dataset.pfrEvent);
            });
            dom.delegate(root, "click", "[data-pfr-detail-retry]", function () {
                if (!selectedEvent) return;
                dom.qsa("[data-pfr-event]", root).find(function (button) { return button.dataset.pfrEvent === selectedEvent; }).focus();
                loadDetail(selectedEvent);
            });
            dom.delegate(root, "click", "[data-pfr-export]", function (event, target) { download(target.dataset.pfrExport); });
            if (payload.status !== "available") return;
            if (!global.UnitizerClient) throw new Error("PostfireReport requires UnitizerClient");
            hydrateFields(); render();
            if (unitListener) document.removeEventListener("unitizer:preferences-changed", unitListener);
            unitListener = render;
            document.addEventListener("unitizer:preferences-changed", unitListener);
            global.UnitizerClient.ready().then(function (client) {
                // Hydrate saved display preferences locally; passive report reads must not persist them.
                client.syncPreferencesFromDom(document);
                render();
            }).catch(function () {
                status("Unit preferences could not be loaded. Reload before changing units or exporting results.", false, true);
                dom.qsa("[data-pfr-export]", root).forEach(function (button) { button.disabled = true; });
            });
        }
        return {bootstrap: bootstrap, csv: csv};
    }
    global.PostfireReport = {getInstance: function () { if (!instance) instance = Controller(); return instance; }};
    function initialize() { if (global.WCDom.qs("[data-postfire-report]")) global.PostfireReport.getInstance().bootstrap(); }
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize, {once: true});
    else initialize();
}(window));
