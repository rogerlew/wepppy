/** @jest-environment jsdom */
/* eslint-env node */

const fs = require("node:fs");
const path = require("node:path");

const templatePath = path.resolve(
    __dirname,
    "../../routes/run_0/templates/run_0/rq-migration-status.htm"
);

function inlineScript() {
    const source = fs.readFileSync(templatePath, "utf8");
    const scripts = [...source.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];
    return scripts.at(-1)[1]
        .replace("{{ runid | tojson }}", JSON.stringify("run-1"))
        .replace("{{ config | tojson }}", JSON.stringify("cfg"))
        .replace(
            "{{ url_for('run_0.runs0', runid=runid, config=config, skip_migration_check='true') }}",
            "/weppcloud/runs/run-1/cfg/?skip_migration_check=true"
        );
}

function installDom() {
    document.body.innerHTML = `
      <input type="checkbox" id="create-archive">
      <button type="button" id="run-migrations-btn">
        <span id="btn-text">Run Migrations</span>
        <span id="btn-spinner" class="spinner hidden"></span>
      </button>
      <div id="migration-result" class="hidden"></div>
    `;
    window.url_for_run = jest.fn(() => "/rq-engine/api/runs/run-1/cfg/migrate-run");
}

async function settle() {
    for (let index = 0; index < 24; index += 1) {
        await Promise.resolve();
    }
}

describe("run migration status inline contract", () => {
    beforeEach(() => {
        jest.resetModules();
        installDom();
    });

    afterEach(() => {
        jest.restoreAllMocks();
        delete window.WCHttp;
        delete window.url_for_run;
    });

    test("submits one native archive choice and finishes through authenticated polling", async () => {
        const postJsonWithSessionToken = jest.fn().mockResolvedValue({
            body: {
                job_id: "job-1",
                status_url: "https://attacker.invalid/steal-token",
                result: { was_readonly: true },
            },
        });
        const requestWithSessionToken = jest.fn()
            .mockResolvedValueOnce({ body: { status: "finished" } })
            .mockResolvedValueOnce({
                body: {
                    result: {
                        applied: ["<migration-one>"],
                        skipped: ["migration-two"],
                    },
                },
            });
        window.WCHttp = { postJsonWithSessionToken, requestWithSessionToken };
        document.querySelector("#create-archive").checked = true;
        let pollCallback;
        jest.spyOn(window, "setTimeout").mockImplementation((callback) => {
            pollCallback = callback;
            return 11;
        });

        window.eval(inlineScript());
        await window.eval("runMigrations()");
        await settle();

        expect(postJsonWithSessionToken).toHaveBeenCalledTimes(1);
        expect(postJsonWithSessionToken).toHaveBeenCalledWith(
            "/rq-engine/api/runs/run-1/cfg/migrate-run",
            { create_archive: true },
            { runId: "run-1", config: "cfg" }
        );
        expect(document.querySelector("#run-migrations-btn").disabled).toBe(true);
        await pollCallback();
        await settle();

        expect(requestWithSessionToken).toHaveBeenNthCalledWith(
            1,
            "/rq-engine/api/jobstatus/job-1",
            expect.objectContaining({ runId: "run-1", config: "cfg" })
        );
        expect(requestWithSessionToken).toHaveBeenNthCalledWith(
            2,
            "/rq-engine/api/jobinfo/job-1",
            expect.objectContaining({ runId: "run-1", config: "cfg" })
        );
        expect(document.querySelector("#migration-result").textContent).toContain(
            "<migration-one>"
        );
        expect(document.querySelector("#migration-result script")).toBeNull();
        expect(document.querySelector("#btn-text").textContent).toBe("Complete!");
        expect(requestWithSessionToken).not.toHaveBeenCalledWith(
            "https://attacker.invalid/steal-token",
            expect.anything()
        );
    });

    test("backs off boundedly on canonical rate limiting", async () => {
        window.WCHttp = {
            postJsonWithSessionToken: jest.fn().mockResolvedValue({
                body: { job_id: "job-1", status_url: "/rq-engine/api/jobstatus/job-1" },
            }),
            requestWithSessionToken: jest.fn().mockResolvedValue({
                body: {
                    _http_status: 429,
                    error: {
                        code: "rate_limited",
                        message: "Too many polling requests",
                        details: "Limit is one request per 40 seconds",
                    },
                },
            }),
        };
        const callbacks = [];
        const timeoutSpy = jest.spyOn(window, "setTimeout").mockImplementation((callback) => {
            callbacks.push(callback);
            return callbacks.length;
        });

        window.eval(inlineScript());
        await window.eval("runMigrations()");
        await callbacks.shift()();
        await settle();

        expect(document.querySelector("#status-text").textContent).toContain("30s");
        expect(timeoutSpy).toHaveBeenLastCalledWith(expect.any(Function), 30000);
        expect(document.querySelector("#run-migrations-btn").disabled).toBe(true);
    });

    test("stops on failure, safely renders traceback, and enables retry", async () => {
        window.WCHttp = {
            postJsonWithSessionToken: jest.fn().mockResolvedValue({
                body: { job_id: "job-1", status_url: "/rq-engine/api/jobstatus/job-1" },
            }),
            requestWithSessionToken: jest.fn()
                .mockResolvedValueOnce({ body: { status: "failed" } })
                .mockResolvedValueOnce({
                    body: { exc_info: "<img src=x onerror=alert(1)>" },
                }),
        };
        let pollCallback;
        jest.spyOn(window, "setTimeout").mockImplementation((callback) => {
            pollCallback = callback;
            return 11;
        });

        window.eval(inlineScript());
        await window.eval("runMigrations()");
        await pollCallback();
        await settle();

        expect(document.querySelector("#migration-result").textContent).toContain(
            "<img src=x onerror=alert(1)>"
        );
        expect(document.querySelector("#migration-result img")).toBeNull();
        expect(document.querySelector("#run-migrations-btn").disabled).toBe(false);
        expect(document.querySelector("#btn-text").textContent).toBe("Retry Migrations");
    });

    test("treats a finished job with a failed migration result as retryable", async () => {
        window.WCHttp = {
            postJsonWithSessionToken: jest.fn().mockResolvedValue({
                body: { job_id: "job-1", status_url: "/rq-engine/api/jobstatus/job-1" },
            }),
            requestWithSessionToken: jest.fn()
                .mockResolvedValueOnce({ body: { status: "finished" } })
                .mockResolvedValueOnce({
                    body: {
                        result: {
                            success: false,
                            errors: { archive: "<archive failed>" },
                        },
                    },
                }),
        };
        let pollCallback;
        jest.spyOn(window, "setTimeout").mockImplementation((callback) => {
            pollCallback = callback;
            return 11;
        });

        window.eval(inlineScript());
        await window.eval("runMigrations()");
        await pollCallback();
        await settle();

        expect(document.querySelector("#migration-result").textContent).toContain(
            "<archive failed>"
        );
        expect(document.querySelector("#migration-result").querySelector("archive")).toBeNull();
        expect(document.querySelector("#run-migrations-btn").disabled).toBe(false);
        expect(document.querySelector("#btn-text").textContent).toBe("Retry Migrations");
    });

    test.each(["stopped", "canceled", "not_found"])(
        "stops polling and enables retry for %s",
        async (status) => {
            window.WCHttp = {
                postJsonWithSessionToken: jest.fn().mockResolvedValue({
                    body: { job_id: "job-1", status_url: "/rq-engine/api/jobstatus/job-1" },
                }),
                requestWithSessionToken: jest.fn()
                    .mockResolvedValueOnce({ body: { status } })
                    .mockResolvedValueOnce({ body: { exc_info: `${status} detail` } }),
            };
            let pollCallback;
            const timeoutSpy = jest.spyOn(window, "setTimeout").mockImplementation((callback) => {
                pollCallback = callback;
                return 11;
            });

            window.eval(inlineScript());
            await window.eval("runMigrations()");
            await pollCallback();
            await settle();

            expect(document.querySelector("#run-migrations-btn").disabled).toBe(false);
            expect(document.querySelector("#btn-text").textContent).toBe("Retry Migrations");
            expect(timeoutSpy).toHaveBeenCalledTimes(1);
        }
    );
});
