/** @jest-environment jsdom */
/* eslint-env node */

function installDom(token = "rq-token") {
    document.body.innerHTML = `
      <main data-controller="run-sync-dashboard">
        <div id="run_sync_config"
             data-api-url="/rq-engine/api/run-sync"
             data-status-url="/rq-engine/api/run-sync/status"
             data-default-host="wepp.cloud"
             data-default-root="/wc1/runs"
             data-status-channel="run_sync"
             data-rq-engine-token="${token}"></div>
        <form id="run_sync_form">
          <input id="source_host" name="source_host" value="source.example">
          <input id="runid" name="runid" value="run one">
          <input id="config" name="config" value="cfg special">
          <input id="target_root" name="target_root" value="/wc1/runs">
          <input id="owner_email" name="owner_email" value="owner@example.com">
          <input id="source_run_token" name="source_run_token" value="source-secret">
          <input id="run_migrations" name="run_migrations" type="checkbox" checked>
          <input id="archive_before" name="archive_before" type="checkbox">
          <button id="run_sync_submit" type="submit">Start sync</button>
          <section id="run_sync_status_panel"><pre id="run_sync_status_log"></pre></section>
          <section data-stacktrace-panel hidden><div id="stacktrace" data-stacktrace-body></div></section>
          <div id="run_sync_summary"></div>
        </form>
        <table id="run_sync_jobs_table"><tbody></tbody></table>
        <table id="run_sync_migrations_table"><tbody></tbody></table>
      </main>`;
}

async function settle() {
    for (let index = 0; index < 16; index += 1) {
        await Promise.resolve();
    }
}

describe("Run Sync dashboard contract", () => {
    let http;
    let poller;
    let statusStream;
    let formPayload;

    beforeEach(async () => {
        jest.resetModules();
        jest.useFakeTimers();
        installDom();

        formPayload = {
            source_host: "source.example",
            runid: " run one ",
            config: " cfg special ",
            target_root: "/wc1/runs",
            owner_email: "owner@example.com",
            source_run_token: " source-secret ",
            run_migrations: true,
            archive_before: false,
        };
        http = {
            request: jest.fn(),
            getJson: jest.fn().mockResolvedValue({ jobs: [], migrations: [] }),
            postJson: jest.fn().mockResolvedValue({
                body: { sync_job_id: "sync-job", migration_job_id: "migration-job" },
            }),
        };
        window.WCHttp = global.WCHttp = http;
        window.WCDom = global.WCDom = {
            ensureElement: jest.fn(),
            qs: jest.fn((selector) => document.querySelector(selector)),
        };
        window.WCForms = global.WCForms = {
            formToJSON: jest.fn(() => ({ ...formPayload })),
        };
        statusStream = {
            append: jest.fn(),
            clear: jest.fn(),
            disconnect: jest.fn(),
        };
        poller = {
            attach_status_stream: jest.fn(() => statusStream),
            connect_status_stream: jest.fn(),
            detach_status_stream: jest.fn(),
            set_rq_job_id: jest.fn(),
        };
        window.controlBase = global.controlBase = jest.fn(() => poller);

        await import("../run_sync_dashboard.js");
        window.RunSyncDashboard.bootstrap();
        await settle();
    });

    afterEach(() => {
        jest.useRealTimers();
        document.body.innerHTML = "";
        delete window.WCHttp;
        delete global.WCHttp;
        delete window.WCDom;
        delete global.WCDom;
        delete window.WCForms;
        delete global.WCForms;
        delete window.RunSyncDashboard;
        delete window.controlBase;
        delete global.controlBase;
    });

    test("submits the exact normalized payload with rendered authorization", async () => {
        document.getElementById("run_sync_form").dispatchEvent(
            new Event("submit", { bubbles: true, cancelable: true })
        );
        await settle();

        expect(http.postJson).toHaveBeenCalledWith(
            "/rq-engine/api/run-sync",
            {
                source_host: "source.example",
                runid: "run one",
                config: "cfg special",
                target_root: "/wc1/runs",
                owner_email: "owner@example.com",
                source_run_token: "source-secret",
                run_migrations: true,
                archive_before: false,
            },
            { headers: { Authorization: "Bearer rq-token" } }
        );
        expect(poller.set_rq_job_id).toHaveBeenCalledWith(poller, "sync-job");
        expect(poller.attach_status_stream).toHaveBeenCalledWith(
            poller,
            expect.objectContaining({ channel: "run_sync", runId: "run one" })
        );
    });

    test("renders hostile job and migration metadata as text", async () => {
        http.getJson.mockResolvedValueOnce({
            jobs: [{
                id: '<img data-job src=x>',
                runid: '<script data-run>alert(1)</script>',
                source_host: "source.example",
                status: "REGISTERED",
                job_status: "finished",
            }],
            migrations: [{
                runid: '<img data-migration src=x>',
                source_host: "source.example",
                owner_email: "owner@example.com",
                last_status: "REGISTERED",
                version_at_pull: 999,
                local_path: '/wc1/runs"><script data-path>alert(1)</script>',
            }],
        });

        jest.advanceTimersByTime(10000);
        await settle();

        expect(document.querySelector("#run_sync_jobs_table tbody").textContent).toContain(
            "<script data-run>alert(1)</script>"
        );
        expect(document.querySelector("#run_sync_migrations_table tbody").textContent).toContain(
            '<img data-migration src=x>'
        );
        expect(document.querySelector("[data-job]")).toBeNull();
        expect(document.querySelector("[data-run]")).toBeNull();
        expect(document.querySelector("[data-migration]")).toBeNull();
        expect(document.querySelector("[data-path]")).toBeNull();
    });

    test("rejects a missing run id without submitting", async () => {
        formPayload.runid = " ";
        document.getElementById("run_sync_form").dispatchEvent(
            new Event("submit", { bubbles: true, cancelable: true })
        );
        await settle();

        expect(http.postJson).not.toHaveBeenCalled();
        expect(document.getElementById("run_sync_status_log").textContent).toContain(
            "runid is required."
        );
    });

    test("blocks duplicate submission while the first request is pending", async () => {
        let resolveSubmit;
        http.postJson.mockImplementation(() => new Promise((resolve) => {
            resolveSubmit = resolve;
        }));
        const form = document.getElementById("run_sync_form");
        form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        await settle();

        expect(http.postJson).toHaveBeenCalledTimes(1);
        expect(document.getElementById("run_sync_submit").disabled).toBe(true);

        resolveSubmit({ body: { sync_job_id: "sync-job" } });
        await settle();
        poller.triggerEvent("RUN_SYNC_COMPLETE");
        await settle();

        expect(document.getElementById("run_sync_submit").disabled).toBe(false);
    });

    test("restores submission after a visible request failure", async () => {
        const consoleError = jest.spyOn(console, "error").mockImplementation(() => {});
        http.postJson.mockRejectedValueOnce(new Error("remote unavailable"));
        document.getElementById("run_sync_form").dispatchEvent(
            new Event("submit", { bubbles: true, cancelable: true })
        );
        await settle();

        expect(document.getElementById("run_sync_status_log").textContent).toContain(
            "Run sync submit failed: remote unavailable"
        );
        expect(document.getElementById("run_sync_submit").disabled).toBe(false);
        consoleError.mockRestore();
    });

    test("encodes terminal navigation and handles completion idempotently", async () => {
        document.getElementById("run_sync_form").dispatchEvent(
            new Event("submit", { bubbles: true, cancelable: true })
        );
        await settle();

        poller.triggerEvent("RUN_SYNC_COMPLETE");
        poller.triggerEvent("RUN_SYNC_COMPLETE");
        await settle();

        const link = document.querySelector("#run_sync_summary a");
        expect(link.getAttribute("href")).toBe(
            "/weppcloud/runs/run%20one/cfg%20special/"
        );
        expect(statusStream.append.mock.calls.filter(
            ([message]) => message === "Sync job completed."
        )).toHaveLength(1);
    });

    test("polling failure is visible, idempotent, and restores submission", async () => {
        document.getElementById("run_sync_form").dispatchEvent(
            new Event("submit", { bubbles: true, cancelable: true })
        );
        await settle();

        poller.triggerEvent("RUN_SYNC_FAILED");
        poller.triggerEvent("RUN_SYNC_FAILED");
        await settle();

        expect(document.getElementById("run_sync_summary").textContent).toContain(
            "Sync failed"
        );
        expect(statusStream.append.mock.calls.filter(
            ([message]) => message.startsWith("Sync job failed:")
        )).toHaveLength(1);
        expect(document.getElementById("run_sync_submit").disabled).toBe(false);
    });

    test("repeated module execution retains one submit owner and timer", async () => {
        await import("../run_sync_dashboard.js?second-owner");
        window.RunSyncDashboard.bootstrap();
        await settle();
        http.postJson.mockClear();

        document.getElementById("run_sync_form").dispatchEvent(
            new Event("submit", { bubbles: true, cancelable: true })
        );
        await settle();

        expect(http.postJson).toHaveBeenCalledTimes(1);
        expect(jest.getTimerCount()).toBe(1);
    });
});
