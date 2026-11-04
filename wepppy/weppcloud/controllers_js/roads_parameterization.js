/* Dedicated Roads parameterization view; Roads NoDb remains the authority. */
(function (global) {
    "use strict";
    var root, state, saved, draft, editing = false, pending = false, repairing = false;
    var requestId = 0, selectedGroup = "", leaveHref = null, unsubscribers = [];
    var roles = ["road", "fill", "buffer"];
    var fields = ["ksat_mm_h", "ki_kg_s_m4", "kr_s_m", "critical_shear_pa"];
    var fieldLabels = {ksat_mm_h: "Baseline effective conductivity (mm/h)", ki_kg_s_m4: "Interrill erodibility Ki (kg s/m⁴)", kr_s_m: "Rill erodibility Kr (s/m)", critical_shear_pa: "Critical shear (Pa)"};
    function busy() { return Boolean(state && (state.busy || ["running", "preparing", "queued"].includes(state.status))); }
    function copy(value) { return JSON.parse(JSON.stringify(value)); }
    function defaults() {
        var result = {};
        roles.forEach(function (role) { result[role] = {}; fields.forEach(function (field) { result[role][field] = {mode: "default"}; }); });
        return result;
    }
    function qs(selector) { return global.WCDom.qs(selector, root); }
    function qsa(selector) { return global.WCDom.qsa(selector, root); }
    function text(selector, value) { var element = qs(selector); if (element) { element.textContent = value; } }
    function parameterization() { return state && state.parameterization; }
    function sameOverrides(left, right) {
        return roles.every(function (role) {
            return fields.every(function (field) {
                var a = left[role][field], b = right[role][field];
                return a.mode === b.mode && (a.mode === "default" || a.value === b.value);
            });
        });
    }
    function dirty() { return repairing || !sameOverrides(draft, saved); }
    function available() { return Boolean(state && state.enabled && !state.readonly && !busy() && parameterization()); }
    function writable() { return available() && (parameterization().status !== "invalid" || repairing); }
    function groups() { return parameterization() && parameterization().groups || []; }
    function activeGroup() { return groups().find(function (group) { return String(group.id) === selectedGroup; }) || groups()[0]; }
    function format(value) {
        if (typeof value !== "number" || !Number.isFinite(value)) { return "Unavailable"; }
        return Number(value.toPrecision(7)).toString();
    }
    function completedTime(value) {
        if (typeof value === "number" && Number.isFinite(value)) {
            var date = new Date(value * 1000);
            return Number.isFinite(date.getTime()) ? date.toISOString() : "Unavailable";
        }
        return value || "Unavailable";
    }
    function error(message) { var el = qs("[data-rp-errors]"); el.textContent = message || ""; el.hidden = !message; }
    function unwrap(response) { var body = response && response.body || response; return body && body.Content || body; }
    function validNumber(value, field) {
        var nativeValue = field === "ksat_mm_h" ? value / 3600000 : value;
        return Number.isFinite(value) && value > 0 && Math.fround(nativeValue) > 0 && Number.isFinite(Math.fround(nativeValue));
    }
    function resolved(row, entry) {
        if (!row) { return null; }
        if (entry.mode === "absolute") { return entry.value; }
        return entry.mode === "multiply" ? row.adjusted * entry.value : row.adjusted;
    }
    function validation() {
        var message = "";
        roles.forEach(function (role) { fields.forEach(function (field) {
            var entry = draft[role][field];
            if (entry.mode !== "default" && (!Number.isFinite(entry.value) || entry.value <= 0)) {
                message = "Override values must be positive finite numbers; zero is not an off switch.";
            }
            groups().forEach(function (group) {
                var row = group.roles && group.roles[role] && group.roles[role][field];
                if (row && !validNumber(resolved(row, entry), field)) {
                    message = "A resolved input overflows or underflows native numeric representation. Choose a positive representable value.";
                }
            });
        }); });
        return message;
    }
    function button(action, disabled, hidden) {
        var el = qs('[data-rp-action="' + action + '"]');
        if (el) { el.disabled = disabled; if (hidden !== undefined) { el.hidden = hidden; } }
    }
    function controls() {
        var invalid = validation();
        button("edit", !writable() || pending, editing);
        button("save", !editing || !writable() || pending || Boolean(invalid) || (!dirty() && parameterization().status !== "unbound"));
        button("cancel", !editing || pending);
        button("reset", !editing || pending || !writable());
        button("repair", !available() || pending, !parameterization() || parameterization().status !== "invalid" || repairing);
        qsa("[data-rp-row]").forEach(function (row) {
            var role = row.dataset.role, field = row.dataset.field;
            row.querySelector("[data-rp-mode]").disabled = !editing || pending || !writable() || repairing;
            row.querySelector("[data-rp-value]").disabled = !editing || pending || !writable() || repairing || draft[role][field].mode === "default";
        });
        if (editing && invalid) { error(invalid); }
        if (busy()) { text("[data-rp-status]", "Roads has an active operation. Editing is unavailable until it completes."); }
    }
    function appendText(parent, tag, value) { var el = document.createElement(tag); el.textContent = value; parent.appendChild(el); return el; }
    function renderReadback() {
        var el = qs("[data-rp-readback]"), p = parameterization(); el.replaceChildren();
        var completed = p && p.last_completed_run;
        if (!completed) { appendText(el, "p", "No completed-run parameter readback is available. Prepare and run Roads to create native inputs and results."); return; }
        appendText(el, "p", "Run configuration: " + (completed.configuration_hash || "unavailable") + ". Baseline: " + (completed.baseline_id || "unavailable") + ". Completed: " + completedTime(completed.completed_at));
        if (completed.historical === true || completed.current === false || completed.configuration_hash !== p.configuration_hash) { appendText(el, "p", "Historical settings: this readback does not describe the currently saved configuration."); }
        var records = completed.records || [completed];
        appendText(el, "p", records.length + " profile readbacks. Expand a profile to inspect actual native input values.");
        records.forEach(function (record) {
            var details = appendText(el, "details", "");
            appendText(details, "summary", "Profile " + (record.segment_run_id || record.segment_id || "(see input paths)"));
            appendText(details, "p", "Inputs: " + (record.input_files || []).map(function (file) { return file.relpath; }).join(", "));
            (record.ofes || []).forEach(function (ofe) {
                var values = ofe.emitted || {};
                appendText(details, "h3", (ofe.role || "Role") + " · OFE " + (ofe.ofe_index || "?"));
                var list = appendText(details, "dl", "");
                fields.forEach(function (field) { appendText(list, "dt", fieldLabels[field]); appendText(list, "dd", format(values[field])); });
            });
        });
    }
    function renderComparison() {
        var el = qs("[data-rp-comparison]"), p = parameterization(); el.replaceChildren();
        var comparison = p && p.comparisons;
        if (!comparison || comparison.status !== "available") { appendText(el, "p", comparison && comparison.reason || "No compatible baseline/custom runs are available."); return; }
        appendText(el, "p", "Modeled-profile PASS EVENT exports, not watershed outlet totals. Sediment outside EVENT support is reported separately.");
        var wrapper = appendText(el, "div", ""); wrapper.className = "rp-table-wrap";
        var table = appendText(wrapper, "table", ""); table.className = "pure-table pure-table-horizontal";
        var head = appendText(table, "thead", ""), heading = appendText(head, "tr", "");
        ["Quantity", "Baseline", "Custom", "Custom − baseline"].forEach(function (label) { var th = appendText(heading, "th", label); th.scope = "col"; });
        var body = appendText(table, "tbody", "");
        var metrics = {annual_runoff_m3: "Annual runoff (m³/year)", annual_sediment_kg: "Annual sediment (kg/year)", annual_runoff_mm: "Annual runoff depth (mm/year)", annual_sediment_kg_m2: "Annual sediment density (kg/m²/year)"};
        Object.keys(metrics).forEach(function (key) {
            var row = appendText(body, "tr", ""), th = appendText(row, "th", metrics[key]); th.scope = "row";
            appendText(row, "td", format(comparison.baseline.metrics[key]));
            appendText(row, "td", format(comparison.custom.metrics[key]));
            appendText(row, "td", format(comparison.difference[key]));
        });
        ["baseline", "custom"].forEach(function (kind) {
            var run = comparison[kind];
            appendText(el, "h3", kind === "baseline" ? "Baseline execution" : "Custom execution");
            appendText(el, "p", "Run: " + run.run_id + "; completed: " + completedTime(run.completed_at) + "; years: " + (run.calendar_years || []).join(", ") + "; modeled area: " + format(run.metrics.modeled_area_m2) + " m²; profiles: " + run.profile_count + (run.historical ? "; historical" : ""));
            appendText(el, "p", "Parameter snapshot: " + run.configuration_hash + "; baseline: " + run.baseline_id + "; evidence: " + run.snapshot_relpath);
        });
    }
    function render() {
        var p = parameterization(), group = activeGroup(), selector = qs("[data-rp-group]");
        selector.replaceChildren();
        groups().forEach(function (item) { var option = document.createElement("option"); option.value = String(item.id); option.textContent = (item.label || String(item.id)) + " · " + (item.routing_mode || "preview") + " · " + (item.segment_ids || []).length + " segments"; selector.appendChild(option); });
        if (group) { selectedGroup = String(group.id); selector.value = selectedGroup; }
        selector.disabled = !group || pending;
        text("[data-rp-state]", busy() ? "Roads is busy. Parameterization is temporarily unavailable while inputs or results are being updated. Reload this page after the operation finishes." : state && !state.enabled ? "Roads is disabled. Retained configuration is read-only here; return to the project to enable Roads." : !p ? "Roads is absent or disabled. Return to the project to enable Roads; viewing this page does not create settings." : p.status === "unbound" ? "Unbound repository preview. Save or Prepare binds this project’s baseline." : p.status === "invalid" ? "Saved parameterization is invalid. Inspect diagnostics and explicitly repair before execution." : "Bound project baseline · " + (state.readonly ? "Read-only · " : "") + (sameOverrides(saved, defaults()) ? "Default inputs" : "Custom overrides"));
        text("[data-rp-baseline]", p ? "Baseline: " + (p.baseline_id || "unavailable") : "");
        var repository = p && p.repository_baseline;
        text("[data-rp-repository]", !repository ? "" : repository.status === "different" ? "Repository defaults differ from this project’s retained baseline. Saved values remain unchanged; adopting newer defaults is not available." : repository.status === "matching" ? "Repository defaults match this baseline." : "Repository defaults could not be checked. This project continues using its retained baseline.");
        text("[data-rp-management]", group ? "Management: " + (group.management_asset || "See provenance") + ". " + (group.management_note || "") : "");
        text("[data-rp-members-summary]", "Segment membership (" + (group && group.segment_ids || []).length + ")");
        text("[data-rp-members]", group ? "Segments: " + (group.segment_ids || []).join(", ") + (group.segment_ids && group.segment_ids.length ? "" : "No executed segment membership; preview only.") : "No resolved groups are available.");
        qsa("[data-rp-row]").forEach(function (element) {
            var role = element.dataset.role, field = element.dataset.field;
            var row = group && group.roles && group.roles[role] && group.roles[role][field];
            if (!p || p.status === "invalid" && !repairing) { row = null; }
            var entry = draft[role][field];
            element.querySelector("[data-rp-source]").textContent = row ? format(row.source) + " · " + (row.source_asset || group.source_asset || "Source unavailable") : "Unavailable";
            element.querySelector("[data-rp-adjustment]").textContent = row ? String(row.adjustment || "Unchanged") + " → " + format(row.adjusted) : "Unavailable";
            element.querySelector("[data-rp-resolved]").textContent = row ? format(resolved(row, entry)) : "Unavailable";
            element.querySelector("[data-rp-mode]").value = entry.mode;
            element.querySelector("[data-rp-value]").value = entry.mode === "default" || entry.value === null ? "" : entry.value;
        });
        qsa("[data-rp-role]").forEach(function (section) {
            var applicable = group && (group.applicable_roles || []).includes(section.dataset.rpRole);
            section.querySelector("[data-rp-applicability]").textContent = !group ? "No resolved role information is available." : group.applicability !== "last_completed_run" ? (applicable ? "Potential template role; Run establishes actual use. Overrides apply to all template-owned rows of this role." : "Not in this preview’s template arrangement; saved overrides remain available for later configurations.") : (applicable ? "Used in the last completed run’s template-owned rows." : "Not used in the last completed run; any saved override remains available for this role.");
        });
        text("[data-rp-details]", p ? JSON.stringify({baseline_id: p.baseline_id, repository_baseline: p.repository_baseline, configuration_hash: p.configuration_hash, diagnostics: p.diagnostics, groups: p.groups, last_completed_run: p.last_completed_run}, null, 2) : "No parameterization state.");
        renderReadback(); renderComparison(); controls();
    }
    function hydrate(payload) {
        if (!payload || typeof payload.enabled !== "boolean" || !Object.prototype.hasOwnProperty.call(payload, "parameterization")) {
            throw new Error(payload && payload.error && payload.error.message || "Reload did not return authoritative Roads state.");
        }
        state = payload; var p = parameterization();
        saved = p && p.status !== "invalid" && p.overrides ? copy(p.overrides) : defaults();
        draft = copy(saved); repairing = false; editing = false;
        error(p && p.diagnostics && p.diagnostics.join("; ")); render();
    }
    function refresh(payload) { if (root && !dirty() && !pending) { hydrate(unwrap(payload)); } }
    function save() {
        if (!editing || pending || !writable() || validation()) { return Promise.resolve(false); }
        var token = ++requestId, snapshot = copy(draft), payload = {overrides: snapshot};
        if (repairing) { payload.repair = true; }
        pending = true; error(""); text("[data-rp-status]", "Saving settings…"); controls();
        return global.WCHttp.postJson(root.dataset.saveUrl, {parameterization: payload}).then(function (response) {
            if (!root || token !== requestId) { return false; }
            var body = unwrap(response);
            if (!body || body.Success === false || !body.parameterization) { throw new Error(body && (body.Error || body.error && body.error.message) || "Save did not return authoritative parameterization."); }
            pending = false; hydrate(Object.assign({}, state, {parameterization: body.parameterization}));
            text("[data-rp-status]", "Settings saved. Prepare and run Roads to generate results."); return true;
        }).catch(function (failure) {
            if (!root || token !== requestId) { return false; }
            pending = false; error(failure.message || "Save failed."); text("[data-rp-status]", "Settings were not confirmed saved; your draft is retained."); controls(); return false;
        });
    }
    function cancel() {
        if (pending) { return; }
        var token = ++requestId; pending = true; text("[data-rp-status]", "Loading saved settings…"); controls();
        global.WCHttp.getJson(root.dataset.queryUrl).then(function (response) {
            if (!root || token !== requestId) { return; }
            pending = false; hydrate(unwrap(response)); text("[data-rp-status]", "Saved settings reloaded.");
        }).catch(function (failure) { if (root && token === requestId) { pending = false; error(failure.message || "Reload failed; retry Cancel."); controls(); } });
    }
    function onInput(event, element) {
        if (!editing || pending || !writable() || repairing) { return; }
        var row = element.closest("[data-rp-row]"), mode = row.querySelector("[data-rp-mode]").value;
        var rawValue = row.querySelector("[data-rp-value]").value;
        var value = rawValue.trim() === "" ? null : Number(rawValue);
        draft[row.dataset.role][row.dataset.field] = mode === "default" ? {mode: mode} : {mode: mode, value: value};
        if (mode === "default") { row.querySelector("[data-rp-value]").value = ""; }
        var group = activeGroup(), baseline = group && group.roles && group.roles[row.dataset.role] && group.roles[row.dataset.role][row.dataset.field];
        row.querySelector("[data-rp-resolved]").textContent = baseline && (mode === "default" || value !== null) ? format(resolved(baseline, draft[row.dataset.role][row.dataset.field])) : "Enter a value";
        error(""); controls();
    }
    function onAction(event, element) {
        event.preventDefault(); var action = element.dataset.rpAction;
        if (element.disabled || pending) { return; }
        if (action === "edit" && writable()) { editing = true; error(""); controls(); }
        if (action === "reset" && editing && writable()) { draft = defaults(); error(""); render(); }
        if (action === "repair" && available() && parameterization().status === "invalid") {
            repairing = true; editing = true; draft = defaults();
            error("Repair will retain the invalid state as history, bind current repository defaults and remove all overrides. Save explicitly to confirm."); render();
        }
        if (action === "save") { save(); }
        if (action === "cancel") { cancel(); }
    }
    function beforeUnload(event) { if (root && (dirty() || pending)) { event.preventDefault(); event.returnValue = ""; } }
    function destroy() {
        requestId += 1; unsubscribers.forEach(function (unsubscribe) { unsubscribe(); }); unsubscribers = [];
        global.removeEventListener("beforeunload", beforeUnload); root = null;
    }
    function init() {
        var found = document.getElementById("roads_parameterization"); if (!found || found === root) { return; }
        destroy(); root = found; pending = false; editing = false; repairing = false;
        hydrate(JSON.parse(qs("[data-parameterization-seed]").textContent));
        unsubscribers.push(global.WCDom.delegate(root, "click", "[data-rp-action]", onAction));
        unsubscribers.push(global.WCDom.delegate(root, "input", "[data-rp-value]", onInput));
        unsubscribers.push(global.WCDom.delegate(root, "change", "[data-rp-mode]", onInput));
        unsubscribers.push(global.WCDom.delegate(root, "change", "[data-rp-group]", function (event, el) { selectedGroup = el.value; render(); }));
        unsubscribers.push(global.WCDom.delegate(root, "click", "[data-rp-navigate]", function (event, el) {
            if (pending || dirty()) { event.preventDefault(); if (!pending) { leaveHref = el.href; qs("[data-rp-leave]").showModal(); } }
        }));
        unsubscribers.push(global.WCDom.delegate(root, "click", "[data-rp-leave-action]", function (event, el) {
            var action = el.dataset.rpLeaveAction, dialog = qs("[data-rp-leave]");
            if (action === "stay") { dialog.close(); }
            if (action === "discard") { saved = copy(draft); dialog.close(); global.location.assign(leaveHref); }
            if (action === "save") { dialog.close(); save().then(function (success) { if (success) { global.location.assign(leaveHref); } }); }
        }));
        global.addEventListener("beforeunload", beforeUnload);
    }
    global.RoadsParameterization = {init: init, destroy: destroy, refresh: refresh};
    if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", init, {once: true}); } else { init(); }
})(window);
