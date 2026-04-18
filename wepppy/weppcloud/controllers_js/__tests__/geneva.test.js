/**
 * @jest-environment jsdom
 */

const createControlBaseStub = require("./helpers/control_base_stub");

function buildStatePayload(overrides) {
    return Object.assign({
        run_state_revision: "runstate:test:abc123",
        enabled: true,
        config_snapshot: {
            enabled: true,
            lambda_mode: "0.05",
            uh_method: "scs_curvilinear",
            default_hsg_code: 4,
            unresolved_hsg_policy: "assume_d",
            strict_burn_nodata: true,
            allow_cross_hsg_merge: true,
            hydrophobic_forest_high: false,
            hydrophobic_forest_moderate: true,
            hydrophobic_shrub_high: false,
            hydrophobic_shrub_moderate: true,
            min_hru_area_ha: 3.5
        },
        status: "prepared",
        status_message: "Frequency panel ready.",
        progress: {
            completed: 0,
            total: 0,
            unit: "storms",
            percent: 0,
            updated_at: "2026-04-16T00:00:00Z"
        },
        active_job_id: null,
        last_job_id: "last-job-1",
        warnings: [],
        errors: [],
        last_prepare_summary: { hru_count: 5 },
        last_run_summary: {},
        artifacts: {
            hru_table_ready: true,
            frequency_panel_ready: true,
            batch_summary_ready: false
        },
        updated_at: "2026-04-16T00:00:00Z"
    }, overrides || {});
}

describe("Geneva controller", () => {
    let httpMock;
    let baseInstance;
    let geneva;

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = `
            <form id="geneva_form">
                <div id="info"></div>
                <div id="status"></div>
                <div id="stacktrace"></div>
                <div id="rq_job"></div>
                <p id="geneva_config_message"></p>
                <select id="geneva_lambda_mode" name="geneva_lambda_mode" data-geneva-field="lambda_mode">
                    <option value="0.20">0.20</option>
                    <option value="0.05">0.05</option>
                </select>
                <select id="geneva_uh_method" name="geneva_uh_method" data-geneva-field="uh_method">
                    <option value="scs_triangular">tri</option>
                    <option value="scs_curvilinear">curv</option>
                </select>
                <select id="geneva_default_hsg_code" name="geneva_default_hsg_code" data-geneva-field="default_hsg_code">
                    <option value="">Auto</option>
                    <option value="4">D</option>
                </select>
                <select id="geneva_unresolved_hsg_policy" name="geneva_unresolved_hsg_policy" data-geneva-field="unresolved_hsg_policy">
                    <option value="error">error</option>
                    <option value="assume_d">assume_d</option>
                </select>
                <input id="geneva_min_hru_area_ha" name="geneva_min_hru_area_ha" type="number" value="2.0" data-geneva-field="min_hru_area_ha">
                <input id="geneva_allow_cross_hsg_merge" name="geneva_allow_cross_hsg_merge" type="checkbox" data-geneva-field="allow_cross_hsg_merge">
                <input id="geneva_hydrophobic_forest_high" name="geneva_hydrophobic_forest_high" type="checkbox" data-geneva-field="hydrophobic_forest_high">
                <input id="geneva_hydrophobic_forest_moderate" name="geneva_hydrophobic_forest_moderate" type="checkbox" data-geneva-field="hydrophobic_forest_moderate">
                <input id="geneva_hydrophobic_shrub_high" name="geneva_hydrophobic_shrub_high" type="checkbox" data-geneva-field="hydrophobic_shrub_high">
                <input id="geneva_hydrophobic_shrub_moderate" name="geneva_hydrophobic_shrub_moderate" type="checkbox" data-geneva-field="hydrophobic_shrub_moderate">
                <input id="geneva_panel_durations_minutes" name="geneva_panel_durations_minutes" value="5, 30">
                <input id="geneva_panel_ari_years" name="geneva_panel_ari_years" value="2, 10">
                <input id="geneva_panel_source_cligen" name="geneva_panel_source_cligen" value="">
                <input id="geneva_panel_source_noaa14" name="geneva_panel_source_noaa14" value="">
                <input id="geneva_run_batch_id" name="geneva_run_batch_id" value="batch-ui-1">
                <input id="geneva_run_datasource_ids" name="geneva_run_datasource_ids" value="cligen_freq, noaa14_pds">
                <input id="geneva_run_durations_minutes" name="geneva_run_durations_minutes" value="30, 60">
                <input id="geneva_run_ari_years" name="geneva_run_ari_years" value="10, 25">
                <input id="geneva_run_time_step_minutes" name="geneva_run_time_step_minutes" value="1.5">
                <select id="geneva_run_lambda_mode" name="geneva_run_lambda_mode">
                    <option value="">Use saved</option>
                    <option value="0.20">0.20</option>
                    <option value="0.05">0.05</option>
                </select>
                <select id="geneva_run_uh_method" name="geneva_run_uh_method">
                    <option value="">Use saved</option>
                    <option value="scs_triangular">tri</option>
                    <option value="scs_curvilinear">curv</option>
                </select>
                <select id="geneva_run_timing_method" name="geneva_run_timing_method">
                    <option value="kirpich">kirpich</option>
                    <option value="kent">kent</option>
                </select>
                <input id="geneva_run_tc_hours" name="geneva_run_tc_hours" value="">
                <button id="geneva_run_batch" type="button" data-geneva-action="run-workflow">Run</button>
                <a data-geneva-link="cn-table" href="/runs//cfg/modify_geneva_cn_table">CN Table</a>
                <a data-geneva-link="query-summary" href="/runs//cfg/query/geneva/summary">Query</a>
                <a data-geneva-link="report-summary" href="/runs//cfg/report/geneva/summary">Report</a>
                <script type="application/json" id="geneva_controller_data">
                    {"config_url":"/runs/test/cfg/api/geneva/config","state_url":"/rq-engine/api/runs/test/cfg/geneva/state","run_workflow_url":"/rq-engine/api/runs/test/cfg/geneva/run-workflow"}
                </script>
            </form>
            <p id="hint_run_geneva_run_workflow"></p>
            <p id="hint_run_geneva_run_batch"></p>
            <div id="geneva_status_panel"><span id="braille"></span></div>
            <div id="geneva_stacktrace_panel"></div>
            <div id="geneva-results"></div>
        `;

        window.runid = "demo-run";
        window.runId = "demo-run";
        window.config = "cfg";
        window.site_prefix = "";

        await import("../dom.js");
        await import("../events.js");
        await import("../forms.js");

        httpMock = {
            postJson: jest.fn(() => Promise.resolve({ body: {} })),
            postJsonWithSessionToken: jest.fn(() => Promise.resolve({ body: { job_id: "geneva-job-9" } })),
            requestWithSessionToken: jest.fn(() => Promise.resolve({ body: buildStatePayload() })),
            isHttpError: jest.fn(() => false)
        };
        global.WCHttp = httpMock;

        ({ base: baseInstance } = createControlBaseStub({
            pushResponseStacktrace: jest.fn(),
            set_rq_job_id: jest.fn(),
            connect_status_stream: jest.fn(),
            disconnect_status_stream: jest.fn(),
            triggerEvent: jest.fn()
        }));
        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));

        window.WCControllerBootstrap = {
            getControllerContext: jest.fn(() => ({})),
            resolveJobId: jest.fn(() => "bootstrap-job-ignored")
        };

        await import("../geneva.js");
        geneva = window.Geneva.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.Geneva;
        delete global.WCHttp;
        delete global.controlBase;
        delete window.WCControllerBootstrap;
        delete window.runid;
        delete window.runId;
        delete window.config;
        delete window.site_prefix;
        if (global.WCDom) {
            delete global.WCDom;
        }
        if (global.WCEvents) {
            delete global.WCEvents;
        }
        if (global.WCForms) {
            delete global.WCForms;
        }
        document.body.innerHTML = "";
    });

    function flushPromises() {
        return Promise.resolve().then(() => Promise.resolve());
    }

    test("bootstrap hydrates from rq-engine state instead of bootstrap job hints", async () => {
        httpMock.requestWithSessionToken.mockResolvedValueOnce({
            body: buildStatePayload({ active_job_id: "state-job-3" })
        });

        geneva.bootstrap({ jobIds: { geneva_prepare_hrus_rq: "bootstrap-job-ignored" } });
        await flushPromises();

        expect(httpMock.requestWithSessionToken).toHaveBeenCalledWith(
            "/rq-engine/api/runs/test/cfg/geneva/state",
            expect.objectContaining({ method: "GET", form: expect.any(HTMLFormElement) })
        );
        expect(document.getElementById("geneva_lambda_mode").value).toBe("0.05");
        expect(document.getElementById("geneva_uh_method").value).toBe("scs_curvilinear");
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(geneva, "state-job-3");
        expect(baseInstance.set_rq_job_id).not.toHaveBeenCalledWith(geneva, "bootstrap-job-ignored");
        expect(geneva.hint.element && geneva.hint.element.id).toBe("hint_run_geneva_run_workflow");
    });

    test("bootstrap keeps last_job_id as the visible job hint when no active job is running", async () => {
        httpMock.requestWithSessionToken.mockResolvedValueOnce({
            body: buildStatePayload({ active_job_id: null, last_job_id: "last-job-visible-5" })
        });

        geneva.bootstrap({});
        await flushPromises();

        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(geneva, "last-job-visible-5");
    });

    test("save-config posts the normalized Flask config payload", async () => {
        httpMock.requestWithSessionToken.mockResolvedValueOnce({ body: buildStatePayload() });
        geneva.bootstrap({});
        await flushPromises();

        document.getElementById("geneva_lambda_mode").value = "0.20";
        document.getElementById("geneva_uh_method").value = "scs_triangular";
        document.getElementById("geneva_default_hsg_code").value = "";
        document.getElementById("geneva_min_hru_area_ha").value = "4.2";

        httpMock.requestWithSessionToken.mockResolvedValueOnce({ body: buildStatePayload() });
        await geneva.saveConfig();
        await flushPromises();

        expect(httpMock.postJson).toHaveBeenCalledWith(
            "/runs/test/cfg/api/geneva/config",
            expect.objectContaining({
                schema_version: 1,
                lambda_mode: "0.20",
                uh_method: "scs_triangular",
                default_hsg_code: null,
                min_hru_area_ha: 4.2,
                strict_burn_nodata: true
            }),
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
        expect(document.getElementById("geneva_config_message").textContent).toContain("saved");
    });

    test("terminal snapshots keep workflow button enabled even when artifacts are missing", async () => {
        httpMock.requestWithSessionToken.mockResolvedValueOnce({
            body: buildStatePayload({
                active_job_id: "stale-active-1",
                status: "failed",
                status_message: "Geneva batch failed.",
                artifacts: {
                    hru_table_ready: false,
                    frequency_panel_ready: false,
                    batch_summary_ready: false
                }
            })
        });

        geneva.bootstrap({});
        await flushPromises();

        expect(document.getElementById("geneva_run_batch").disabled).toBe(false);
    });

    test("bootstrap rewrites malformed panel links to resolved run-scoped URLs", async () => {
        const priorUrlForRun = global.url_for_run;
        global.url_for_run = jest.fn((path, options) => {
            const normalizedPath = String(path || "").replace(/^\/+/, "");
            if (options && options.prefix) {
                return String(options.prefix).replace(/\/+$/, "") + "/runs/demo-run/cfg/" + normalizedPath;
            }
            return "/runs/demo-run/cfg/" + normalizedPath;
        });

        httpMock.requestWithSessionToken.mockResolvedValueOnce({ body: buildStatePayload() });
        geneva.bootstrap({});
        await flushPromises();

        expect(document.querySelector('[data-geneva-link="cn-table"]').getAttribute("href")).toBe(
            "/runs/demo-run/cfg/modify_geneva_cn_table"
        );
        expect(document.querySelector('[data-geneva-link="query-summary"]').getAttribute("href")).toBe(
            "/runs/demo-run/cfg/query/geneva/summary"
        );
        expect(document.querySelector('[data-geneva-link="report-summary"]').getAttribute("href")).toBe(
            "/runs/demo-run/cfg/report/geneva/summary"
        );

        global.url_for_run = priorUrlForRun;
    });

    test("run-workflow posts chained payload with forced prepare/panel rebuild and tc override", async () => {
        httpMock.requestWithSessionToken.mockResolvedValueOnce({ body: buildStatePayload() });
        geneva.bootstrap({});
        await flushPromises();

        document.getElementById("geneva_run_lambda_mode").value = "0.20";
        document.getElementById("geneva_run_uh_method").value = "scs_triangular";
        document.getElementById("geneva_run_timing_method").value = "kent";
        document.getElementById("geneva_run_tc_hours").value = "3.5";

        httpMock.requestWithSessionToken.mockResolvedValueOnce({
            body: buildStatePayload({
                active_job_id: "geneva-job-9",
                status: "running",
                status_message: "Running Geneva storm batch..."
            })
        });
        document.getElementById("geneva_run_batch").dispatchEvent(new MouseEvent("click", { bubbles: true }));
        await flushPromises();

        expect(httpMock.postJsonWithSessionToken).toHaveBeenCalledWith(
            "/rq-engine/api/runs/test/cfg/geneva/run-workflow",
            {
                schema_version: 1,
                prepare: {
                    schema_version: 1,
                    force_rebuild: true
                },
                panel: {
                    schema_version: 1,
                    durations_minutes: [5, 30],
                    ari_years: [2, 10],
                    rebuild: true
                },
                run_batch: {
                    schema_version: 1,
                    batch_id: "batch-ui-1",
                    event_filter: {
                        datasource_ids: ["cligen_freq", "noaa14_pds"],
                        durations_minutes: [30, 60],
                        ari_years: [10, 25]
                    },
                    hyetograph: {
                        distribution_type: "neh4_type_b",
                        time_step_minutes: 1.5
                    },
                    runoff_model: {
                        lambda_mode: "0.20",
                        uh_method: "scs_triangular",
                        tc_hours: 3.5
                    }
                }
            },
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
        expect(baseInstance.connect_status_stream).toHaveBeenCalledWith(geneva);
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(geneva, "geneva-job-9");
        expect(geneva.hint.element && geneva.hint.element.id).toBe("hint_run_geneva_run_workflow");
    });

    test("workflow action keeps the workflow hint target active", async () => {
        httpMock.requestWithSessionToken.mockResolvedValueOnce({ body: buildStatePayload() });
        geneva.bootstrap({});
        await flushPromises();

        httpMock.requestWithSessionToken.mockResolvedValueOnce({
            body: buildStatePayload({ active_job_id: "prepare-job-1", status_message: "Preparing Geneva HRUs..." })
        });
        document.getElementById("geneva_run_batch").dispatchEvent(new MouseEvent("click", { bubbles: true }));
        await flushPromises();

        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(geneva, "geneva-job-9");
        expect(geneva.hint.element && geneva.hint.element.id).toBe("hint_run_geneva_run_workflow");
    });

    test("config edits show unsaved warning and auto-save before queue actions", async () => {
        httpMock.requestWithSessionToken.mockResolvedValueOnce({ body: buildStatePayload() });
        geneva.bootstrap({});
        await flushPromises();

        const unresolvedPolicy = document.getElementById("geneva_unresolved_hsg_policy");
        unresolvedPolicy.value = "error";
        unresolvedPolicy.dispatchEvent(new Event("change", { bubbles: true }));

        expect(document.getElementById("geneva_config_message").textContent).toContain("Unsaved Geneva settings");

        httpMock.requestWithSessionToken.mockResolvedValueOnce({
            body: buildStatePayload({
                config_snapshot: Object.assign({}, buildStatePayload().config_snapshot, {
                    unresolved_hsg_policy: "error"
                })
            })
        });
        document.getElementById("geneva_run_batch").dispatchEvent(new MouseEvent("click", { bubbles: true }));
        await flushPromises();
        await flushPromises();

        expect(httpMock.postJson).toHaveBeenCalledWith(
            "/runs/test/cfg/api/geneva/config",
            expect.objectContaining({
                unresolved_hsg_policy: "error"
            }),
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
        expect(httpMock.postJsonWithSessionToken).toHaveBeenCalledWith(
            "/rq-engine/api/runs/test/cfg/geneva/run-workflow",
            expect.objectContaining({
                schema_version: 1,
                prepare: expect.objectContaining({ force_rebuild: true }),
                panel: expect.objectContaining({ rebuild: true }),
                run_batch: expect.objectContaining({ schema_version: 1 })
            }),
            expect.objectContaining({ form: expect.any(HTMLFormElement) })
        );
    });
});
