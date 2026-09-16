/** @jest-environment jsdom */
/* global __dirname */
const fs = require("fs");
const path = require("path");

const attempt = "a".repeat(32);
const eventId = "b".repeat(64) + ":0";
const row = (duration = 15) => ({event_id: eventId, row_ordinal: 0, duration_minutes: duration,
    year: 1, month: 2, day_of_month: 3, date_status: "simulation_labels",
    intensity_mm_per_hour: 52, rainfall_mm: 13, precipitation_mm: 20,
    probability: 0.99999, reason: null, return_interval_years: 1});
const seed = () => ({schema_version: 1, status: "available", attempt_id: attempt,
    summary: {model: "M1", completed_at: "2026-09-15", assessment_id: "c".repeat(32),
        current: false, climate_mode: "CLIGEN", date_semantics: "simulation_labels", frequency_source: "noaa",
        frequency: {represented_years: 10, year_min: 1, year_max: 10}, area_km2: 41,
        coverage: {total_cells: 100, valid_cells: 90, excluded_cells: 10, valid_fraction: 0.9}, warnings: [], predictors: []},
    design: [row(), {...row(), return_interval_years: 2, probability: 0.00001}, row(30)],
    inverse: [15, 30, 60].map(d => ({...row(d), probability: null, target_probability: 0.5})),
    events: {rows: [row()], total: 101, unfiltered_total: 101},
    query: {duration_minutes: 15, min_probability: null, year: null, sort: "row_ordinal", descending: false, limit: 100, offset: 0},
    urls: {query: "/query/", event: "/event", control: "/run/#postfire", artifacts: {"events.parquet": "/files/events?attempt_id=" + attempt}}});

function markup(payload) {
    // Use the actual report's markup, with only its Jinja shell/seed expressions removed.
    const template = fs.readFileSync(path.join(__dirname, "../../templates/reports/postfire_debris_flow/report.htm"), "utf8");
    document.body.innerHTML = template.replace(/\{%[\s\S]*?%\}/g, "").replace(/\{\{[\s\S]*?\}\}/g, "");
    document.getElementById("postfire-report-seed").textContent = JSON.stringify(payload);
}
const flush = () => new Promise(resolve => setTimeout(resolve, 0));
const click = selector => document.querySelector(selector).click();
let unitHandler;
let client;

beforeEach(async () => {
    jest.resetModules();
    delete window.PostfireReport;
    markup(seed());
    require("../dom.js");
    window.WCHttp = {getJson: jest.fn()};
    client = {getPreferencePayload: () => ({rain: "mm", intensity: "mm/hour", area: "km^2"}),
        getCategory: key => ({units: [{key: {rain: "mm", intensity: "mm/hour", area: "km^2"}[key], precision: 2}, {key: "in", precision: 3}]}),
        syncPreferencesFromDom: jest.fn(), convert: (value, from, to) => to === "in" ? value / 25.4 : value};
    window.UnitizerClient = {getClientSync: () => client, ready: () => Promise.resolve(client)};
    const add = document.addEventListener.bind(document);
    jest.spyOn(document, "addEventListener").mockImplementation((name, handler, ...args) => {
        if (name === "unitizer:preferences-changed") unitHandler = handler;
        else add(name, handler, ...args);
    });
    require("../postfire_report.js");
    window.PostfireReport.getInstance().bootstrap();
    await flush();
});
afterEach(() => {
    jest.restoreAllMocks();
    delete window.__unitizerMapModule;
    delete window.__unitizerMap;
});

test("accepted model, stale warning, fixed likelihood scale and all three thresholds", () => {
    expect(document.querySelector("[data-pfr-summary]").textContent).toContain("M1");
    expect(document.querySelector("[data-pfr-current]").textContent).toContain("Inputs have changed");
    expect(document.querySelector("[data-pfr-chart]").textContent).toContain("100%");
    expect(document.querySelector("[data-pfr-body=design]").textContent).toContain(">99.9%");
    expect(document.querySelector("[data-pfr-body=design]").textContent).toContain("<0.1%");
    expect(document.querySelectorAll("[data-pfr-body=inverse] tr")).toHaveLength(4);
    expect(document.querySelector("[data-pfr-count]").textContent).toContain("of 101 matching storm events");
});

test("scenario buttons link to accessible markers, bootstrap does not duplicate listeners", () => {
    window.PostfireReport.getInstance().bootstrap();
    click("button[data-pfr-scenario='0']");
    expect(document.querySelectorAll("[data-pfr-scenario='0'][aria-pressed=true]")).toHaveLength(2);
    const marker = document.querySelector("circle[data-pfr-scenario='1']");
    marker.dispatchEvent(new KeyboardEvent("keydown", {key: " ", bubbles: true}));
    expect(marker.getAttribute("aria-pressed")).toBe("true");
});

test("details are directly after selected event with preserved activating focus", async () => {
    window.WCHttp.getJson.mockResolvedValue({attempt_id: attempt, rows: [row(), row(30), row(60)]});
    const button = document.querySelector("[data-pfr-event]");
    button.focus(); button.click(); await flush();
    expect(document.activeElement).toBe(button);
    expect(button.getAttribute("aria-expanded")).toBe("true");
    expect(button.closest("tr").nextElementSibling.matches("[data-pfr-detail]")).toBe(true);
    expect(document.querySelector("[data-pfr-detail]").textContent).toContain("60");
});

test("duration/filter queries are typed, reset page and ignore out-of-order responses", async () => {
    let first;
    window.WCHttp.getJson.mockImplementationOnce(() => new Promise(resolve => {first = resolve;}));
    const next = seed(); next.query.duration_minutes = 60; next.events.rows = [row(60)];
    window.WCHttp.getJson.mockResolvedValueOnce(next);
    const duration = document.querySelector("[data-pfr-field=duration]");
    duration.value = "30"; duration.dispatchEvent(new Event("change", {bubbles: true}));
    duration.value = "60"; duration.dispatchEvent(new Event("change", {bubbles: true}));
    await flush(); first(seed()); await flush();
    expect(document.querySelector("[data-pfr-window]").textContent).toContain("60");
    expect(window.WCHttp.getJson.mock.calls[1][0]).toContain("duration_minutes=60");
    expect(window.WCHttp.getJson.mock.calls[1][0]).toContain("offset=0");
});

test("replacement disables exports and clears details, including later unit events", async () => {
    window.WCHttp.getJson.mockRejectedValueOnce({body: {error: {code: "assessment_replaced"}}});
    click("[data-pfr-action=next]"); await flush();
    expect(document.querySelector("[data-pfr-status]").textContent).toContain("Reload");
    expect(document.querySelector("[data-pfr-export=events]").disabled).toBe(true);
    unitHandler();
    expect(document.querySelector("[data-pfr-downloads]").children).toHaveLength(0);
    expect(document.querySelector("[data-pfr-event]").disabled).toBe(true);
});

test("CSV retains full precision, labels scope and neutralizes formula text", () => {
    const csv = window.PostfireReport.getInstance().csv("events");
    expect(csv).toContain("0.99999");
    expect(csv).toContain("attempt_id");
    expect(csv).toContain("simulation");
    expect(csv).toContain("probability_fraction");
    expect(csv).toContain("target_probability_fraction");
    expect(csv).toContain("min_probability_fraction");
    expect(csv).toContain("fraction (0–1)");
    const payload = seed(); payload.events.rows[0].reason = " \t=HYPERLINK(\"bad\")";
    markup(payload); window.PostfireReport.getInstance().bootstrap();
    expect(window.PostfireReport.getInstance().csv("events")).toContain("' \t=HYPERLINK");
    expect(document.querySelector("[data-pfr-body=events]").textContent).not.toContain("HYPERLINK");
});

test("unit changes preserve selection and change chart, all tables and precise exports together", () => {
    click("button[data-pfr-scenario='0']");
    client.getPreferencePayload = () => ({rain: "in", intensity: "in", area: "km^2"});
    unitHandler();
    expect(document.querySelector("[data-pfr-body=design]").textContent).toContain("0.51");
    expect(document.querySelector("[data-pfr-chart]").textContent).toContain("in");
    expect(document.querySelectorAll("[data-pfr-scenario='0'][aria-pressed=true]")).toHaveLength(2);
    expect(window.PostfireReport.getInstance().csv("events")).toContain(String(13 / 25.4));
});

test("absent and unknown currentness never invent zero probabilities", () => {
    const payload = seed(); payload.summary.current = null;
    markup(payload); window.PostfireReport.getInstance().bootstrap();
    expect(document.querySelector("[data-pfr-current]").textContent).toContain("Could not check");
    markup({...payload, status: "absent", summary: null, attempt_id: null});
    window.PostfireReport.getInstance().bootstrap();
    expect(document.querySelector("[data-pfr-empty]").hidden).toBe(false);
    expect(document.querySelector("[data-pfr-results]").hidden).toBe(true);
});

test("percent and year filters normalize, numeric filters show unique unfiltered denominator", async () => {
    const next = seed(); next.events = {rows: [], total: 0, unfiltered_total: 101};
    next.query.min_probability = 0.75; next.query.year = 2;
    window.WCHttp.getJson.mockResolvedValue(next);
    document.querySelector("[data-pfr-field=min_probability]").value = "75";
    document.querySelector("[data-pfr-field=year]").value = "2";
    document.querySelector("[data-pfr-filters]").dispatchEvent(new Event("submit", {bubbles: true, cancelable: true}));
    await flush();
    expect(window.WCHttp.getJson.mock.calls[0][0]).toContain("min_probability=0.75");
    expect(window.WCHttp.getJson.mock.calls[0][0]).toContain("year=2");
    expect(document.querySelector("[data-pfr-count]").textContent).toContain("101 storm events before filters");
    expect(document.querySelector("[data-pfr-count]").textContent).toContain("No storms match these filters");
    window.WCHttp.getJson.mockResolvedValue(seed());
    click("[data-pfr-action=reset]"); await flush();
    expect(window.WCHttp.getJson.mock.calls[1][0]).not.toContain("min_probability");
    expect(document.querySelector("[data-pfr-field=year]").value).toBe("");
});

test("transient failure retains coherent values, marks CSV previous view, and retries same page", async () => {
    window.WCHttp.getJson.mockRejectedValueOnce(new Error("network"));
    click("[data-pfr-action=next]"); await flush();
    expect(document.querySelector("[data-pfr-status]").textContent).toContain("Could not update results");
    expect(document.querySelector("[data-pfr-pagination] [data-pfr-event-status]").textContent).toContain("Could not update results");
    expect(document.querySelector("[data-pfr-pagination] [data-pfr-action=retry]").hidden).toBe(false);
    expect(window.PostfireReport.getInstance().csv("events")).toContain("previous view");
    const next = seed(); next.query.offset = 100;
    window.WCHttp.getJson.mockResolvedValueOnce(next);
    click("[data-pfr-pagination] [data-pfr-action=retry]"); await flush();
    expect(window.WCHttp.getJson.mock.calls[0][0]).toBe(window.WCHttp.getJson.mock.calls[1][0]);
    expect(document.querySelector("[data-pfr-count]").textContent).toContain("Showing 101–101");
});

test("last-page-row inline detail is discoverable; response from an old selection is ignored", async () => {
    const payload = seed();
    const second = {...row(), event_id: "b".repeat(64) + ":1", row_ordinal: 1, day_of_month: 4};
    payload.events.rows.push(second);
    markup(payload); window.PostfireReport.getInstance().bootstrap();
    await flush();
    let first;
    window.WCHttp.getJson.mockImplementationOnce(() => new Promise(resolve => {first = resolve;}));
    window.WCHttp.getJson.mockResolvedValueOnce({attempt_id: attempt, rows: [{...second, probability: 0.25}]});
    const buttons = document.querySelectorAll("[data-pfr-event]");
    buttons[0].click(); buttons[1].focus(); buttons[1].click(); await flush();
    first({attempt_id: attempt, rows: [row()]}); await flush();
    expect(document.activeElement).toBe(buttons[1]);
    expect(buttons[1].closest("tr").nextElementSibling.matches("[data-pfr-detail]")).toBe(true);
    expect(document.querySelector("[data-pfr-detail]").textContent).toContain("25%");
    expect(document.querySelectorAll("[data-pfr-detail]")).toHaveLength(1);
});

test("failed event details keep a local retry beside the selected event and recover", async () => {
    window.WCHttp.getJson.mockRejectedValueOnce(new Error("offline"));
    const button = document.querySelector("[data-pfr-event]"); button.focus(); button.click(); await flush();
    expect(button.getAttribute("aria-expanded")).toBe("true");
    expect(document.activeElement).toBe(button);
    expect(document.querySelector("[data-pfr-detail]").textContent).toContain("Could not load this storm");
    window.WCHttp.getJson.mockResolvedValueOnce({attempt_id: attempt, rows: [row()]});
    click("[data-pfr-detail-retry]"); await flush();
    expect(document.activeElement).toBe(button);
    expect(document.querySelector("[data-pfr-detail]").textContent).toContain(">99.9%");
    expect(document.querySelector("[data-pfr-event-status]").textContent).toBe("");
});

test("query in flight prevents detail requests canceling the selected page generation", async () => {
    let resolve;
    window.WCHttp.getJson.mockImplementation(() => new Promise(done => {resolve = done;}));
    click("[data-pfr-action=next]");
    unitHandler(); // Re-rendering while loading must not revive competing event requests.
    const button = document.querySelector("[data-pfr-event]");
    expect(button.disabled).toBe(true); button.click();
    expect(window.WCHttp.getJson).toHaveBeenCalledTimes(1);
    resolve(seed()); await flush();
    expect(document.querySelector("[data-pfr-event]").disabled).toBe(false);
});

test("invalid dates remain selectable and unknown reasons render safe support language", () => {
    const payload = seed();
    payload.events.rows[0].date_status = "invalid_or_missing";
    payload.events.rows[0].probability = null;
    payload.events.rows[0].reason = "<img src=x onerror=alert(1)>";
    markup(payload); window.PostfireReport.getInstance().bootstrap();
    const body = document.querySelector("[data-pfr-body=events]");
    expect(body.textContent).toContain("Date unavailable");
    expect(body.textContent).toContain("Unavailable — Not available; see the saved assessment manifest");
    expect(body.querySelector("img")).toBeNull();
});

test("zero wet events remain distinct from filtered empty pages and retain design results", () => {
    const payload = seed(); payload.events = {rows: [], total: 0, unfiltered_total: 0};
    markup(payload); window.PostfireReport.getInstance().bootstrap();
    expect(document.querySelector("[data-pfr-count]").textContent).toContain("No storm events in this climate record");
    expect(document.querySelectorAll("[data-pfr-body=design] tr")).toHaveLength(3);
});

test("full common coverage does not hide missing terrain and row explanations", () => {
    const payload = seed(); payload.summary.coverage.valid_fraction = 1;
    payload.summary.predictors = [{name: "ruggedness", value: null, unit: "1", reason: "terrain_potentially_truncated"}];
    payload.events.rows[0].probability = null; payload.events.rows[0].reason = "missing_predictors";
    markup(payload); window.PostfireReport.getInstance().bootstrap();
    expect(document.querySelector("[data-pfr-warnings]").textContent).toContain("Upstream terrain may extend beyond");
    expect(document.querySelector("[data-pfr-body=events]").textContent).toContain("Required model inputs are unavailable");
});

test("real Unitizer public API hydrates values, chart and detail without a private precision method", async () => {
    window.__unitizerMap = {categories: [
        {key: "rain", defaultIndex: 0, units: [{key: "mm", token: "mm", precision: 2}, {key: "in", token: "in", precision: 3}], conversions: [{from: "mm", to: "in", scale: 1 / 25.4, offset: 0}]},
        {key: "intensity", defaultIndex: 0, units: [{key: "mm/hour", token: "mmhr", precision: 2}], conversions: []},
        {key: "area", defaultIndex: 0, units: [{key: "km^2", token: "km2", precision: 2}], conversions: []}
    ]};
    require("../unitizer_client.js");
    markup(seed()); window.PostfireReport.getInstance().bootstrap();
    const realClient = await window.UnitizerClient.ready(); await flush();
    expect(realClient.getPrecision).toBeUndefined();
    expect(document.querySelector("[data-pfr-status]").textContent).toBe("");
    realClient.setPreference("rain", "in"); unitHandler();
    window.WCHttp.getJson.mockResolvedValue({attempt_id: attempt, rows: [row(), row(30), row(60)]});
    click("[data-pfr-event]"); await flush();
    expect(document.querySelector("[data-pfr-detail]").textContent).toContain("0.512");
    expect(window.PostfireReport.getInstance().csv("events")).toContain(String(13 / 25.4));
});

test("already initialized real Unitizer hydrates saved English radios locally without persistence", async () => {
    window.__unitizerMap = {categories: [
        {key: "rain", defaultIndex: 0, units: [{key: "mm", token: "mm", precision: 2}, {key: "in", token: "in", precision: 3}], conversions: [{from: "mm", to: "in", scale: 1 / 25.4, offset: 0}]},
        {key: "intensity", defaultIndex: 0, units: [{key: "mm/hour", token: "mmhr", precision: 2}], conversions: []},
        {key: "area", defaultIndex: 0, units: [{key: "km^2", token: "km2", precision: 2}], conversions: []}
    ]};
    require("../unitizer_client.js");
    const realClient = await window.UnitizerClient.ready();
    expect(realClient.getPreferencePayload().rain).toBe("mm");
    markup(seed());
    const radio = document.createElement("input");
    radio.type = "radio"; radio.name = "unitizer_rain_radio"; radio.value = "in"; radio.checked = true;
    document.body.appendChild(radio);
    window.WCHttp.postJson = jest.fn();
    window.PostfireReport.getInstance().bootstrap(); await flush();
    expect(realClient.getPreferencePayload().rain).toBe("in");
    expect(document.querySelector("[data-pfr-body=design]").textContent).toContain("0.512");
    expect(window.PostfireReport.getInstance().csv("events")).toContain(String(13 / 25.4));
    expect(window.WCHttp.postJson).not.toHaveBeenCalled();
    expect(window.WCHttp.getJson).not.toHaveBeenCalled();
});

test("page-two selection survives duration reset and expands again when its page returns", async () => {
    const secondId = "d".repeat(64) + ":100";
    const selectedRows = [15, 30, 60].map(duration => ({...row(duration), event_id: secondId, row_ordinal: 100}));
    const pageTwo = seed(); pageTwo.query.offset = 100; pageTwo.events.rows = [selectedRows[0]];
    window.WCHttp.getJson.mockResolvedValueOnce(pageTwo);
    click("[data-pfr-action=next]"); await flush();
    window.WCHttp.getJson.mockResolvedValueOnce({attempt_id: attempt, rows: selectedRows});
    click("[data-pfr-event]"); await flush();
    const pageOne30 = seed(); pageOne30.query.duration_minutes = 30; pageOne30.events.rows = [row(30)];
    window.WCHttp.getJson.mockResolvedValueOnce(pageOne30);
    const duration = document.querySelector("[data-pfr-field=duration]");
    duration.value = "30"; duration.dispatchEvent(new Event("change", {bubbles: true})); await flush();
    expect(window.WCHttp.getJson.mock.calls[2][0]).toContain("offset=0");
    expect(document.querySelector("[data-pfr-event-status]").textContent).toContain("Selected storm retained");
    expect(document.querySelector("[data-pfr-detail]")).toBeNull();
    const pageTwo30 = {...pageOne30, query: {...pageOne30.query, offset: 100}, events: {...pageOne30.events, rows: [selectedRows[1]]}};
    window.WCHttp.getJson.mockResolvedValueOnce(pageTwo30);
    click("[data-pfr-action=next]"); await flush();
    expect(document.querySelector("[data-pfr-event]").getAttribute("aria-expanded")).toBe("true");
    expect(document.querySelector("[data-pfr-detail]").textContent).toContain("60");
    expect(window.WCHttp.getJson).toHaveBeenCalledTimes(4); // The saved three-duration detail is reused.
});

test("duration change clears a selected event genuinely excluded by its new probability", async () => {
    const payload = seed(); payload.query.min_probability = 0.5;
    markup(payload); window.PostfireReport.getInstance().bootstrap(); await flush();
    const detail = [row(), {...row(30), probability: 0.25}, row(60)];
    window.WCHttp.getJson.mockResolvedValueOnce({attempt_id: attempt, rows: detail});
    click("[data-pfr-event]"); await flush();
    const filtered = seed(); filtered.query.duration_minutes = 30; filtered.query.min_probability = 0.5;
    filtered.events.rows = []; filtered.events.total = 0;
    window.WCHttp.getJson.mockResolvedValueOnce(filtered);
    const duration = document.querySelector("[data-pfr-field=duration]");
    duration.value = "30"; duration.dispatchEvent(new Event("change", {bubbles: true})); await flush();
    expect(document.querySelector("[data-pfr-event-status]").textContent).toContain("no longer matches these filters");
    expect(document.querySelector("[data-pfr-detail]")).toBeNull();
});

test("unknown off-page selection uses bounded detail and discards an older in-flight response", async () => {
    let oldDetail;
    window.WCHttp.getJson.mockImplementationOnce(() => new Promise(resolve => {oldDetail = resolve;}));
    click("[data-pfr-event]");
    const next = seed(); next.query.duration_minutes = 30;
    next.events.rows = [{...row(30), event_id: "e".repeat(64) + ":1", row_ordinal: 1}];
    window.WCHttp.getJson.mockResolvedValueOnce(next);
    window.WCHttp.getJson.mockResolvedValueOnce({attempt_id: attempt, rows: [row(), row(30), row(60)]});
    const duration = document.querySelector("[data-pfr-field=duration]");
    duration.value = "30"; duration.dispatchEvent(new Event("change", {bubbles: true})); await flush();
    expect(window.WCHttp.getJson.mock.calls[2][0]).toContain("event_id=" + encodeURIComponent(eventId));
    expect(document.querySelector("[data-pfr-event-status]").textContent).toContain("Selected storm retained");
    oldDetail({attempt_id: "f".repeat(32), rows: []}); await flush();
    expect(document.querySelector("[data-pfr-event-status]").textContent).toContain("Selected storm retained");
    expect(document.querySelector("[data-pfr-export=events]").disabled).toBe(false);
});
