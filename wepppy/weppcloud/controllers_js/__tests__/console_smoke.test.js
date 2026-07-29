/**
 * @jest-environment jsdom
 */

const flushPromises = () => new Promise((resolve) => setTimeout(resolve, 0));

describe("Archive console smoke", () => {
    let originalReadyStateDescriptor;
    let fetchMock;
    let statusStreamInstance;
    let poller;

    beforeEach(async () => {
        jest.resetModules();

        originalReadyStateDescriptor = Object.getOwnPropertyDescriptor(document, "readyState");
        Object.defineProperty(document, "readyState", {
            configurable: true,
            value: "complete",
        });

        statusStreamInstance = {
            append: jest.fn(),
            disconnect: jest.fn(),
        };
        global.StatusStream = {
            attach: jest.fn(() => statusStreamInstance),
            disconnect: jest.fn(),
        };
        poller = {
            set_rq_job_id: jest.fn((self, jobId) => {
                self.rq_job_id = jobId;
            }),
        };
        global.controlBase = jest.fn(() => poller);

        fetchMock = jest.fn((url, options = {}) => {
            if (url === "/runs/demo/config/archive-list") {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ archives: [] }),
                });
            }
            if (url === "/rq-engine/api/runs/demo/config/session-token") {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ token: "session-token" }),
                });
            }
            if (url === "/rq-engine/api/runs/demo/config/archive") {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ job_id: "job-123" }),
                });
            }
            throw new Error(`Unexpected fetch: ${url} (${JSON.stringify(options)})`);
        });
        global.fetch = fetchMock;

        document.body.innerHTML = `
            <section data-controller="archive-dashboard" data-user-anonymous="false">
                <div
                    data-archive-dashboard-config
                    data-runid="demo"
                    data-config="config"
                    data-archives-url="/runs/demo/config/archive-list"
                    data-archive-api-url="/rq-engine/api/runs/demo/config/archive"
                    data-restore-api-url="/rq-engine/api/runs/demo/config/restore-archive"
                    data-delete-api-url="/rq-engine/api/runs/demo/config/delete-archive"
                    data-project-path="/runs/demo/config"
                    data-user-anonymous="false"
                    hidden>
                </div>
                <div id="archive_status_panel">
                    <div id="archive_status_log" data-status-log></div>
                </div>
                <div id="archive_stacktrace_panel"><pre data-stacktrace-body></pre></div>
                <input id="archive_comment" />
                <button id="archive_button" type="button">Create archive</button>
                <button id="refresh_button" type="button">Refresh</button>
                <div id="archive_empty" hidden></div>
                <table id="archives_table"><tbody></tbody></table>
                <div id="restore_link"></div>
            </section>
            <p id="project_label"></p>
        `;

        await import("../../static/js/console_utils.js");
        await import("../../static/js/archive_console.js");
        await flushPromises();
        fetchMock.mockClear();
        statusStreamInstance.append.mockClear();
    });

    afterEach(() => {
        if (originalReadyStateDescriptor) {
            Object.defineProperty(document, "readyState", originalReadyStateDescriptor);
        } else {
            delete document.readyState;
        }
        document.body.innerHTML = "";
        delete global.StatusStream;
        delete global.controlBase;
        delete global.fetch;
        delete global.confirm;
    });

    test("clicking create archive posts the archive job", async () => {
        const comment = document.getElementById("archive_comment");
        comment.value = "Smoke test comment";

        document.getElementById("archive_button").click();
        await flushPromises();

        expect(fetchMock).toHaveBeenCalledTimes(2);
        const [tokenUrl, tokenOptions] = fetchMock.mock.calls[0];
        expect(tokenUrl).toBe("/rq-engine/api/runs/demo/config/session-token");
        expect(tokenOptions).toMatchObject({
            method: "POST",
            headers: { Accept: "application/json" },
        });
        const [url, options] = fetchMock.mock.calls[1];
        expect(url).toBe("/rq-engine/api/runs/demo/config/archive");
        expect(options).toMatchObject({
            method: "POST",
            headers: { "Content-Type": "application/json", Authorization: "Bearer session-token" },
            body: JSON.stringify({ comment: "Smoke test comment" }),
        });

        expect(statusStreamInstance.append).toHaveBeenCalledWith("Submitting archive job...");
        expect(statusStreamInstance.append).toHaveBeenCalledWith("Archive job submitted: job-123");
        expect(poller.set_rq_job_id).toHaveBeenCalledWith(poller, "job-123");
    });

    test("renders hostile archive metadata as text with server-owned download URL", async () => {
        fetchMock.mockImplementation((url) => {
            if (url === "/runs/demo/config/archive-list") {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        archives: [{
                            name: 'snapshot"><img data-injected src=x>.zip',
                            comment: '<script data-comment>alert(1)</script>',
                            size: 1024,
                            modified: "2026-07-29 12:00:00",
                            download_url: "/runs/demo/config/download/archives/snapshot.zip",
                        }],
                        in_progress: false,
                    }),
                });
            }
            throw new Error(`Unexpected fetch: ${url}`);
        });

        document.getElementById("refresh_button").click();
        await flushPromises();

        const row = document.querySelector("#archives_table tbody tr");
        expect(row.textContent).toContain('snapshot"><img data-injected src=x>.zip');
        expect(row.textContent).toContain("<script data-comment>alert(1)</script>");
        expect(row.querySelector("[data-injected]")).toBeNull();
        expect(row.querySelector("[data-comment]")).toBeNull();
        expect(row.querySelector("a").getAttribute("href")).toBe(
            "/runs/demo/config/download/archives/snapshot.zip"
        );
        expect(row.querySelector('button[data-role="restore"]').disabled).toBe(false);
        expect(row.querySelector('button[data-role="delete"]').disabled).toBe(false);
    });

    test("restore confirms and submits the exact listed archive with one active job", async () => {
        global.confirm = jest.fn(() => true);
        fetchMock.mockImplementation((url, options = {}) => {
            if (url === "/runs/demo/config/archive-list") {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        archives: [{
                            name: "snapshot.zip",
                            comment: "",
                            size: 1,
                            modified: "now",
                            download_url: "/download/snapshot.zip",
                        }],
                        in_progress: false,
                    }),
                });
            }
            if (url === "/rq-engine/api/runs/demo/config/session-token") {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ token: "session-token" }),
                });
            }
            if (url === "/rq-engine/api/runs/demo/config/restore-archive") {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ job_id: "restore-job" }),
                });
            }
            throw new Error(`Unexpected fetch: ${url} (${JSON.stringify(options)})`);
        });

        document.getElementById("refresh_button").click();
        await flushPromises();
        fetchMock.mockClear();
        document.querySelector('button[data-role="restore"]').click();
        await flushPromises();

        expect(global.confirm).toHaveBeenCalledWith(
            'Restore archive "snapshot.zip"?\nThis replaces current project files.'
        );
        expect(fetchMock.mock.calls[1]).toEqual([
            "/rq-engine/api/runs/demo/config/restore-archive",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: "Bearer session-token",
                },
                body: JSON.stringify({ archive_name: "snapshot.zip" }),
            },
        ]);
        expect(poller.poll_completion_event).toBe("RESTORE_COMPLETE");
        expect(poller.set_rq_job_id).toHaveBeenCalledWith(poller, "restore-job");
        expect(document.getElementById("archive_button").disabled).toBe(true);
        expect(document.querySelector('button[data-role="delete"]').disabled).toBe(true);
    });

    test("delete confirms, submits the exact listed archive, and refreshes", async () => {
        global.confirm = jest.fn(() => true);
        let listCalls = 0;
        fetchMock.mockImplementation((url) => {
            if (url === "/runs/demo/config/archive-list") {
                listCalls += 1;
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        archives: listCalls === 1 ? [{
                            name: "snapshot.zip",
                            comment: "",
                            size: 1,
                            modified: "now",
                            download_url: "/download/snapshot.zip",
                        }] : [],
                        in_progress: false,
                    }),
                });
            }
            if (url === "/rq-engine/api/runs/demo/config/session-token") {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ token: "session-token" }),
                });
            }
            if (url === "/rq-engine/api/runs/demo/config/delete-archive") {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ status: "ok" }),
                });
            }
            throw new Error(`Unexpected fetch: ${url}`);
        });

        document.getElementById("refresh_button").click();
        await flushPromises();
        fetchMock.mockClear();
        document.querySelector('button[data-role="delete"]').click();
        await flushPromises();

        expect(fetchMock.mock.calls[1][0]).toBe(
            "/rq-engine/api/runs/demo/config/delete-archive"
        );
        expect(fetchMock.mock.calls[1][1].body).toBe(
            JSON.stringify({ archive_name: "snapshot.zip" })
        );
        expect(listCalls).toBe(2);
        expect(document.getElementById("archive_empty").hidden).toBe(false);
    });

    test("delete disables all mutation controls until the request settles", async () => {
        global.confirm = jest.fn(() => true);
        let resolveDelete;
        fetchMock.mockImplementation((url) => {
            if (url === "/runs/demo/config/archive-list") {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        archives: [{
                            name: "snapshot.zip",
                            comment: "",
                            size: 1,
                            modified: "now",
                            download_url: "/download/snapshot.zip",
                        }],
                        in_progress: false,
                    }),
                });
            }
            if (url === "/rq-engine/api/runs/demo/config/session-token") {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ token: "session-token" }),
                });
            }
            if (url === "/rq-engine/api/runs/demo/config/delete-archive") {
                return new Promise((resolve) => {
                    resolveDelete = resolve;
                });
            }
            throw new Error(`Unexpected fetch: ${url}`);
        });

        document.getElementById("refresh_button").click();
        await flushPromises();
        document.querySelector('button[data-role="delete"]').click();
        await flushPromises();

        expect(document.getElementById("archive_button").disabled).toBe(true);
        expect(document.querySelector('button[data-role="restore"]').disabled).toBe(true);
        expect(document.querySelector('button[data-role="delete"]').disabled).toBe(true);

        resolveDelete({
            ok: true,
            json: () => Promise.resolve({ status: "ok" }),
        });
        await flushPromises();
        await flushPromises();

        expect(document.getElementById("archive_button").disabled).toBe(false);
        expect(document.querySelector('button[data-role="restore"]').disabled).toBe(false);
        expect(document.querySelector('button[data-role="delete"]').disabled).toBe(false);
    });

    test("declining restore confirmation performs no mutation", async () => {
        global.confirm = jest.fn(() => false);
        fetchMock.mockImplementation((url) => {
            if (url === "/runs/demo/config/archive-list") {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        archives: [{
                            name: "snapshot.zip",
                            comment: "",
                            size: 1,
                            modified: "now",
                            download_url: "/download/snapshot.zip",
                        }],
                    }),
                });
            }
            throw new Error(`Unexpected fetch: ${url}`);
        });

        document.getElementById("refresh_button").click();
        await flushPromises();
        fetchMock.mockClear();
        document.querySelector('button[data-role="restore"]').click();

        expect(global.confirm).toHaveBeenCalledTimes(1);
        expect(fetchMock).not.toHaveBeenCalled();
    });

    test("poll terminal completion refreshes the list and enables actions", async () => {
        document.getElementById("archive_button").click();
        await flushPromises();
        fetchMock.mockClear();

        poller.triggerEvent("ARCHIVE_COMPLETE", { source: "poll" });
        await flushPromises();

        expect(statusStreamInstance.append).toHaveBeenCalledWith("Archive job completed.");
        expect(fetchMock).toHaveBeenCalledWith(
            "/runs/demo/config/archive-list",
            { cache: "no-store" }
        );
        expect(document.getElementById("archive_button").disabled).toBe(false);
    });

    test("submission failure is visible and restores available actions", async () => {
        fetchMock.mockImplementation((url) => {
            if (url === "/rq-engine/api/runs/demo/config/session-token") {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ token: "session-token" }),
                });
            }
            if (url === "/rq-engine/api/runs/demo/config/archive") {
                return Promise.resolve({
                    ok: false,
                    json: () => Promise.resolve({
                        error: { message: "Archive is locked" },
                    }),
                });
            }
            throw new Error(`Unexpected fetch: ${url}`);
        });

        document.getElementById("archive_button").click();
        await flushPromises();

        expect(statusStreamInstance.append).toHaveBeenCalledWith("ERROR: Archive is locked");
        expect(document.getElementById("archive_button").disabled).toBe(false);
    });

    test("repeated script execution retains one create owner", async () => {
        jest.resetModules();
        await import("../../static/js/archive_console.js");

        document.getElementById("archive_button").click();
        await flushPromises();

        expect(fetchMock).toHaveBeenCalledTimes(2);
    });
});

describe("Fork console smoke", () => {
    let originalReadyStateDescriptor;
    let fetchMock;
    let statusStreamInstance;
    let poller;

    beforeEach(async () => {
        jest.resetModules();

        originalReadyStateDescriptor = Object.getOwnPropertyDescriptor(document, "readyState");
        Object.defineProperty(document, "readyState", {
            configurable: true,
            value: "complete",
        });

        statusStreamInstance = {
            append: jest.fn(),
            connect: jest.fn(),
            disconnect: jest.fn(),
        };
        global.StatusStream = {
            attach: jest.fn(() => statusStreamInstance),
            disconnect: jest.fn(),
        };

        poller = {
            set_rq_job_id: jest.fn((self, jobId) => {
                self.rq_job_id = jobId;
            }),
            fetch_job_status: jest.fn(),
        };
        global.controlBase = jest.fn(() => poller);

        fetchMock = jest.fn((url, options = {}) => {
            if (url === "http://localhost/rq-engine/api/runs/demo-run/cfg/session-token") {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ token: "session-token" }),
                });
            }
            if (url === "http://localhost/rq-engine/api/runs/demo-run/cfg/fork") {
                const payload = {
                    job_id: "job-456",
                    new_runid: "demo-run-new",
                    undisturbify: false,
                };
                return Promise.resolve({
                    ok: true,
                    text: () => Promise.resolve(JSON.stringify(payload)),
                });
            }
            if (url === "http://localhost/weppcloud/rq/job-dashboard/job-456") {
                return Promise.resolve({ ok: true, text: () => Promise.resolve("") });
            }
            if (url === "http://localhost/weppcloud/runs/demo-run/cfg/rq-fork-console/readiness/job-456/demo-run-new") {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ ready: true, missing: [] }),
                });
            }
            return Promise.reject(new Error(`Unexpected fetch: ${url} (${JSON.stringify(options)})`));
        });
        global.fetch = fetchMock;
        global.alert = jest.fn();

        document.body.innerHTML = `
            <section data-controller="fork-console">
                <div data-fork-console-config
                     data-runid="demo-run"
                     data-config="cfg"
                     data-undisturbify="false"
                     data-skip-wepp-runs-output="false"
                     hidden></div>
                <div id="fork_status_panel">
                    <div id="fork_status_log" data-status-log></div>
                </div>
                <div data-fork-progress hidden></div>
                <div id="fork_stacktrace_panel"><pre data-stacktrace-body></pre></div>
                <form id="fork_form">
                    <input id="runid_input" value="demo-run" />
                    <input id="undisturbify_checkbox" type="checkbox" />
                    <input id="skip_wepp_runs_output_checkbox" type="checkbox" />
                    <button id="submit_button" type="submit">Fork project</button>
                    <button id="cancel_button" type="button" hidden>Cancel</button>
                </form>
                <div id="the_console" data-state=""></div>
            </section>
        `;

        await import("../../static/js/console_utils.js");
        await import("../../static/js/fork_console.js");
        await flushPromises();
        fetchMock.mockClear();
        statusStreamInstance.append.mockClear();
    });

    afterEach(() => {
        if (originalReadyStateDescriptor) {
            Object.defineProperty(document, "readyState", originalReadyStateDescriptor);
        } else {
            delete document.readyState;
        }
        document.body.innerHTML = "";
        window.sessionStorage.clear();
        delete global.StatusStream;
        delete global.controlBase;
        delete global.fetch;
        delete global.alert;
    });

    test("submitting fork form posts the fork job", async () => {
        expect(global.StatusStream.attach).not.toHaveBeenCalled();
        const undisturbifyCheckbox = document.getElementById("undisturbify_checkbox");
        expect(undisturbifyCheckbox.checked).toBe(false);

        const form = document.getElementById("fork_form");

        form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        await flushPromises();

        expect(fetchMock).toHaveBeenCalledTimes(2);
        const [tokenUrl, tokenOptions] = fetchMock.mock.calls[0];
        expect(tokenUrl).toBe("http://localhost/rq-engine/api/runs/demo-run/cfg/session-token");
        expect(tokenOptions).toMatchObject({
            method: "POST",
            headers: { Accept: "application/json" },
        });
        const [url, options] = fetchMock.mock.calls[1];
        expect(url).toBe("http://localhost/rq-engine/api/runs/demo-run/cfg/fork");
        expect(options).toMatchObject({
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                Authorization: "Bearer session-token",
            },
            body: "undisturbify=false&skip_wepp_runs_output=false",
        });

        expect(statusStreamInstance.append).toHaveBeenCalledWith("Submitting fork job...");
     
        const consoleBlock = document.getElementById("the_console");
        expect(consoleBlock.dataset.state).toBe("attention");
        expect(global.StatusStream.attach).toHaveBeenCalledWith(expect.objectContaining({
            channel: "fork",
            runId: "demo-run",
            autoConnect: false,
        }));
        expect(statusStreamInstance.connect).toHaveBeenCalledTimes(1);
        expect(poller.set_rq_job_id).toHaveBeenCalledWith(poller, "job-456");

        const stored = JSON.parse(window.sessionStorage.getItem("weppcloud:fork-console:demo-run:cfg"));
        expect(Object.keys(stored).sort()).toEqual([
            "config",
            "jobId",
            "newRunId",
            "runId",
            "version",
        ]);
        expect(stored).toEqual(expect.objectContaining({
            runId: "demo-run",
            config: "cfg",
            jobId: "job-456",
            newRunId: "demo-run-new",
        }));
    });

    test("propagates rendered true option defaults into the exact submit payload", async () => {
        document.body.innerHTML = `
            <section data-controller="fork-console">
                <div data-fork-console-config
                     data-runid="demo-run"
                     data-config="cfg"
                     data-undisturbify="true"
                     data-skip-wepp-runs-output="true"
                     hidden></div>
                <div id="fork_status_panel"><div id="fork_status_log"></div></div>
                <div id="fork_stacktrace_panel"><pre data-stacktrace-body></pre></div>
                <form id="fork_form">
                    <input id="runid_input" value="demo-run" />
                    <input id="undisturbify_checkbox" type="checkbox" />
                    <input id="skip_wepp_runs_output_checkbox" type="checkbox" />
                    <button id="submit_button" type="submit">Fork project</button>
                    <button id="cancel_button" type="button" hidden>Cancel</button>
                </form>
                <div id="the_console"></div>
            </section>
        `;
        jest.resetModules();
        await import("../../static/js/console_utils.js");
        await import("../../static/js/fork_console.js");
        await flushPromises();
        fetchMock.mockClear();

        expect(document.getElementById("undisturbify_checkbox").checked).toBe(true);
        expect(document.getElementById("skip_wepp_runs_output_checkbox").checked).toBe(true);

        document.getElementById("fork_form").dispatchEvent(
            new Event("submit", { bubbles: true, cancelable: true })
        );
        await flushPromises();

        expect(fetchMock.mock.calls[1][1].body).toBe(
            "undisturbify=true&skip_wepp_runs_output=true"
        );
    });

    test("repeated script execution retains one submit owner", async () => {
        jest.resetModules();
        await import("../../static/js/fork_console.js");

        document.getElementById("fork_form").dispatchEvent(
            new Event("submit", { bubbles: true, cancelable: true })
        );
        await flushPromises();

        expect(fetchMock).toHaveBeenCalledTimes(2);
    });

    test("removes a cross-scope tracked record instead of restoring it", async () => {
        window.sessionStorage.setItem("weppcloud:fork-console:demo-run:cfg", JSON.stringify({
            version: 1,
            runId: "other-run",
            config: "cfg",
            jobId: "job-other",
            newRunId: "other-new",
        }));
        document.querySelector('[data-controller="fork-console"]').__forkConsoleInit = false;
        jest.resetModules();
        await import("../../static/js/fork_console.js");
        await flushPromises();

        expect(window.sessionStorage.getItem("weppcloud:fork-console:demo-run:cfg")).toBeNull();
        expect(poller.set_rq_job_id).not.toHaveBeenCalledWith(poller, "job-other");
    });

    test("anonymous CAP blocks before solve and submits the solved token directly", async () => {
        document.body.innerHTML = `
            <section data-controller="fork-console">
                <div data-fork-console-config
                     data-runid="demo-run"
                     data-config="cfg"
                     data-undisturbify="false"
                     data-skip-wepp-runs-output="true"
                     data-cap-required="true"
                     data-cap-section="fork"
                     hidden></div>
                <div class="wc-cap-prompt" data-cap-section="fork">
                    <button type="button" data-cap-trigger></button>
                    <span data-cap-status></span>
                </div>
                <cap-widget data-cap-section="fork"></cap-widget>
                <div id="fork_status_panel"><div id="fork_status_log"></div></div>
                <div id="fork_stacktrace_panel"><pre data-stacktrace-body></pre></div>
                <form id="fork_form">
                    <input id="runid_input" value="demo-run" />
                    <input id="undisturbify_checkbox" type="checkbox" />
                    <input id="skip_wepp_runs_output_checkbox" type="checkbox" />
                    <input name="cap_token" value="" data-cap-token />
                    <button id="submit_button" type="submit" disabled>Fork project</button>
                    <button id="cancel_button" type="button" hidden>Cancel</button>
                </form>
                <div id="the_console"></div>
            </section>
        `;
        const trigger = document.querySelector("[data-cap-trigger]");
        trigger.click = jest.fn();
        document.querySelector('[data-controller="fork-console"]').__forkConsoleInit = false;
        jest.resetModules();
        await import("../../static/js/fork_console.js");
        await flushPromises();
        fetchMock.mockClear();

        document.getElementById("fork_form").dispatchEvent(
            new Event("submit", { bubbles: true, cancelable: true })
        );
        expect(trigger.click).toHaveBeenCalledTimes(1);
        expect(fetchMock).not.toHaveBeenCalled();

        document.querySelector("cap-widget").dispatchEvent(
            new CustomEvent("solve", { detail: { token: "<cap-token>" } })
        );
        document.getElementById("fork_form").dispatchEvent(
            new Event("submit", { bubbles: true, cancelable: true })
        );
        await flushPromises();

        expect(fetchMock).toHaveBeenCalledTimes(1);
        expect(fetchMock.mock.calls[0][0]).toBe(
            "http://localhost/rq-engine/api/runs/demo-run/cfg/fork"
        );
        expect(fetchMock.mock.calls[0][1]).toMatchObject({
            method: "POST",
            body: "undisturbify=false&skip_wepp_runs_output=true&cap_token=%3Ccap-token%3E",
        });
    });

    test("stream completion requests authoritative status before completing", async () => {
        document.getElementById("fork_form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        await flushPromises();

        const streamOptions = global.StatusStream.attach.mock.calls[0][0];
        streamOptions.onTrigger({ event: "FORK_COMPLETE", raw: "TRIGGER fork FORK_COMPLETE" });

        expect(poller.fetch_job_status).toHaveBeenCalledWith(poller);
        expect(document.getElementById("the_console").dataset.state).toBe("attention");
        expect(window.sessionStorage.getItem("weppcloud:fork-console:demo-run:cfg")).not.toBeNull();

        poller.triggerEvent("FORK_COMPLETE", { source: "poll", status: { status: "finished" } });
        await flushPromises();

        expect(document.getElementById("the_console").dataset.state).toBe("positive");
        expect(window.sessionStorage.getItem("weppcloud:fork-console:demo-run:cfg")).toBeNull();
    });

    test("waits for destination readiness before exposing the load link", async () => {
        let readinessCalls = 0;
        let scheduledRetry = null;
        fetchMock.mockImplementation((url) => {
            if (url === "http://localhost/rq-engine/api/runs/demo-run/cfg/session-token") {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ token: "session-token" }),
                });
            }
            if (url === "http://localhost/rq-engine/api/runs/demo-run/cfg/fork") {
                return Promise.resolve({
                    ok: true,
                    text: () => Promise.resolve(JSON.stringify({
                        job_id: "job-456",
                        new_runid: "demo-run-new",
                    })),
                });
            }
            if (url === "http://localhost/weppcloud/runs/demo-run/cfg/rq-fork-console/readiness/job-456/demo-run-new") {
                readinessCalls += 1;
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        ready: readinessCalls >= 2,
                        missing: readinessCalls >= 2 ? [] : ["ron.nodb"],
                    }),
                });
            }
            return Promise.reject(new Error(`Unexpected fetch: ${url}`));
        });

        document.getElementById("fork_form").dispatchEvent(
            new Event("submit", { bubbles: true, cancelable: true })
        );
        await flushPromises();
        expect(document.getElementById("the_console").querySelector("a")).toBeNull();
        const timeoutSpy = jest.spyOn(window, "setTimeout").mockImplementation((callback) => {
            scheduledRetry = callback;
            return 1;
        });
        try {
            poller.triggerEvent("FORK_COMPLETE", {
                source: "poll",
                status: { status: "finished" },
            });
            for (let index = 0; index < 20 && scheduledRetry === null; index += 1) {
                await Promise.resolve();
            }

            expect(document.getElementById("the_console").querySelector("a")).toBeNull();
            expect(window.sessionStorage.getItem("weppcloud:fork-console:demo-run:cfg")).not.toBeNull();
            expect(scheduledRetry).not.toBeNull();
            expect(document.getElementById("cancel_button").hidden).toBe(true);
            expect(document.getElementById("cancel_button").disabled).toBe(true);

            scheduledRetry();
            for (
                let index = 0;
                index < 20 && document.getElementById("the_console").dataset.state !== "positive";
                index += 1
            ) {
                await Promise.resolve();
            }

            expect(readinessCalls).toBe(2);
            expect(document.getElementById("the_console").dataset.state).toBe("positive");
            expect(document.getElementById("the_console").querySelector("a").textContent).toContain(
                "Load demo-run-new project"
            );
            expect(window.sessionStorage.getItem("weppcloud:fork-console:demo-run:cfg")).toBeNull();
        } finally {
            timeoutSpy.mockRestore();
        }
    });

    test("bounds unavailable-destination checks and keeps a manual retry", async () => {
        let readinessCalls = 0;
        let destinationReady = false;
        fetchMock.mockImplementation((url) => {
            if (url === "http://localhost/rq-engine/api/runs/demo-run/cfg/session-token") {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ token: "session-token" }),
                });
            }
            if (url === "http://localhost/rq-engine/api/runs/demo-run/cfg/fork") {
                return Promise.resolve({
                    ok: true,
                    text: () => Promise.resolve(JSON.stringify({
                        job_id: "job-456",
                        new_runid: "demo-run-new",
                    })),
                });
            }
            if (url === "http://localhost/weppcloud/runs/demo-run/cfg/rq-fork-console/readiness/job-456/demo-run-new") {
                readinessCalls += 1;
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        ready: destinationReady,
                        missing: destinationReady ? [] : ["ron.nodb"],
                    }),
                });
            }
            return Promise.reject(new Error(`Unexpected fetch: ${url}`));
        });

        document.getElementById("fork_form").dispatchEvent(
            new Event("submit", { bubbles: true, cancelable: true })
        );
        await flushPromises();
        const timeoutSpy = jest.spyOn(window, "setTimeout").mockImplementation((callback) => {
            callback();
            return 1;
        });
        try {
            poller.triggerEvent("FORK_COMPLETE", {
                source: "poll",
                status: { status: "finished" },
            });
            for (
                let index = 0;
                index < 300
                    && document.getElementById("the_console").querySelector("button") === null;
                index += 1
            ) {
                await Promise.resolve();
            }

            const consoleBlock = document.getElementById("the_console");
            const retryButton = consoleBlock.querySelector("button");
            expect(readinessCalls).toBe(30);
            expect(consoleBlock.querySelector("a")).toBeNull();
            expect(retryButton.textContent).toBe("Check project readiness");
            expect(window.sessionStorage.getItem("weppcloud:fork-console:demo-run:cfg")).not.toBeNull();
            expect(document.getElementById("cancel_button").hidden).toBe(true);
            expect(document.getElementById("cancel_button").disabled).toBe(true);

            destinationReady = true;
            retryButton.click();
            for (
                let index = 0;
                index < 20 && consoleBlock.dataset.state !== "positive";
                index += 1
            ) {
                await Promise.resolve();
            }

            expect(readinessCalls).toBe(31);
            expect(consoleBlock.querySelector("a").textContent).toContain(
                "Load demo-run-new project"
            );
            expect(window.sessionStorage.getItem("weppcloud:fork-console:demo-run:cfg")).toBeNull();
        } finally {
            timeoutSpy.mockRestore();
        }
    });

    test("readiness authorization failure retains tracking and prompts reload", async () => {
        fetchMock.mockImplementation((url) => {
            if (url === "http://localhost/rq-engine/api/runs/demo-run/cfg/session-token") {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ token: "session-token" }),
                });
            }
            if (url === "http://localhost/rq-engine/api/runs/demo-run/cfg/fork") {
                return Promise.resolve({
                    ok: true,
                    text: () => Promise.resolve(JSON.stringify({
                        job_id: "job-456",
                        new_runid: "demo-run-new",
                    })),
                });
            }
            if (url === "http://localhost/weppcloud/runs/demo-run/cfg/rq-fork-console/readiness/job-456/demo-run-new") {
                return Promise.resolve({
                    ok: false,
                    status: 403,
                    json: () => Promise.resolve({
                        error: { code: "forbidden", message: "Destination access denied" },
                    }),
                });
            }
            return Promise.reject(new Error(`Unexpected fetch: ${url}`));
        });

        document.getElementById("fork_form").dispatchEvent(
            new Event("submit", { bubbles: true, cancelable: true })
        );
        await flushPromises();
        poller.triggerEvent("FORK_COMPLETE", {
            source: "poll",
            status: { status: "finished" },
        });
        await flushPromises();

        const consoleBlock = document.getElementById("the_console");
        expect(consoleBlock.dataset.state).toBe("critical");
        expect(consoleBlock.textContent).toContain("Destination access denied");
        expect(consoleBlock.querySelector("a")).toBeNull();
        expect(global.alert).toHaveBeenCalledTimes(1);
        expect(window.sessionStorage.getItem("weppcloud:fork-console:demo-run:cfg")).not.toBeNull();
        expect(document.getElementById("cancel_button").hidden).toBe(true);
    });

    test("readiness transport failure retains tracking and offers manual retry", async () => {
        fetchMock.mockImplementation((url) => {
            if (url === "http://localhost/rq-engine/api/runs/demo-run/cfg/session-token") {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ token: "session-token" }),
                });
            }
            if (url === "http://localhost/rq-engine/api/runs/demo-run/cfg/fork") {
                return Promise.resolve({
                    ok: true,
                    text: () => Promise.resolve(JSON.stringify({
                        job_id: "job-456",
                        new_runid: "demo-run-new",
                    })),
                });
            }
            if (url === "http://localhost/weppcloud/runs/demo-run/cfg/rq-fork-console/readiness/job-456/demo-run-new") {
                return Promise.reject(new Error("readiness offline"));
            }
            return Promise.reject(new Error(`Unexpected fetch: ${url}`));
        });

        document.getElementById("fork_form").dispatchEvent(
            new Event("submit", { bubbles: true, cancelable: true })
        );
        await flushPromises();
        poller.triggerEvent("FORK_COMPLETE", {
            source: "poll",
            status: { status: "finished" },
        });
        await flushPromises();

        const consoleBlock = document.getElementById("the_console");
        expect(consoleBlock.dataset.state).toBe("critical");
        expect(consoleBlock.textContent).toContain("readiness offline");
        expect(consoleBlock.querySelector("a")).toBeNull();
        expect(consoleBlock.querySelector("button").textContent).toBe(
            "Check project readiness"
        );
        expect(window.sessionStorage.getItem("weppcloud:fork-console:demo-run:cfg")).not.toBeNull();
        expect(document.getElementById("cancel_button").hidden).toBe(true);
    });

    test("heartbeat updates replaceable progress instead of the log", async () => {
        document.getElementById("fork_form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        await flushPromises();

        const streamOptions = global.StatusStream.attach.mock.calls[0][0];
        const formatted = streamOptions.formatter("FORK_HEARTBEAT Copy in progress - elapsed 00:10:00");

        expect(formatted).toBe("");
        expect(document.querySelector("[data-fork-progress]").textContent).toBe("Copy in progress - elapsed 00:10:00");
        expect(document.querySelector("[data-fork-progress]").hidden).toBe(false);
    });

    test("restores a tracked job and reconciles on focus", async () => {
        window.sessionStorage.setItem("weppcloud:fork-console:demo-run:cfg", JSON.stringify({
            version: 1,
            runId: "demo-run",
            config: "cfg",
            jobId: "job-restored",
            newRunId: "restored-run",
        }));
        document.querySelector('[data-controller="fork-console"]').__forkConsoleInit = false;
        jest.resetModules();
        await import("../../static/js/console_utils.js");
        await import("../../static/js/fork_console.js");
        await flushPromises();

        expect(poller.set_rq_job_id).toHaveBeenCalledWith(poller, "job-restored");
        expect(global.StatusStream.attach).toHaveBeenCalledWith(expect.objectContaining({
            channel: "fork",
            runId: "demo-run",
        }));
        poller.fetch_job_status.mockClear();

        window.dispatchEvent(new Event("focus"));

        expect(poller.fetch_job_status).toHaveBeenCalledWith(poller);
        expect(document.getElementById("the_console").textContent).toContain("Restored fork job");
    });

    test("renders restored identifiers as text", async () => {
        window.sessionStorage.setItem("weppcloud:fork-console:demo-run:cfg", JSON.stringify({
            version: 1,
            runId: "demo-run",
            config: "cfg",
            jobId: "job-restored",
            newRunId: 'restored-run"><img data-injected src=x>',
        }));
        document.querySelector('[data-controller="fork-console"]').__forkConsoleInit = false;
        jest.resetModules();
        await import("../../static/js/console_utils.js");
        await import("../../static/js/fork_console.js");
        await flushPromises();

        const consoleBlock = document.getElementById("the_console");
        expect(consoleBlock.textContent).toContain('restored-run"><img data-injected src=x>');
        expect(consoleBlock.querySelector("[data-injected]")).toBeNull();
        expect(consoleBlock.querySelector("a")).toBeNull();
    });

    test("submitting fork form uses rq-engine token when provided", async () => {
        document.body.innerHTML = `
            <section data-controller="fork-console">
                <div data-fork-console-config
                     data-runid="demo-run"
                     data-config="cfg"
                     data-undisturbify="false"
                     data-rq-engine-token="rq-token-123"
                     hidden></div>
                <div id="fork_status_panel">
                    <div id="fork_status_log" data-status-log></div>
                </div>
                <div id="fork_stacktrace_panel"><pre data-stacktrace-body></pre></div>
                <form id="fork_form">
                    <input id="runid_input" value="demo-run" />
                    <input id="undisturbify_checkbox" type="checkbox" />
                    <button id="submit_button" type="submit">Fork project</button>
                    <button id="cancel_button" type="button" hidden>Cancel</button>
                </form>
                <div id="the_console" data-state=""></div>
            </section>
        `;

        jest.resetModules();
        await import("../../static/js/console_utils.js");
        await import("../../static/js/fork_console.js");
        await flushPromises();
        fetchMock.mockClear();

        const form = document.getElementById("fork_form");
        form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        await flushPromises();

        expect(fetchMock).toHaveBeenCalledTimes(1);
        const [url, options] = fetchMock.mock.calls[0];
        expect(url).toBe("http://localhost/rq-engine/api/runs/demo-run/cfg/fork");
        expect(options).toMatchObject({
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                Authorization: "Bearer rq-token-123",
            },
            body: "undisturbify=false&skip_wepp_runs_output=false",
        });
    });

    test("failed fork surfaces stacktrace", async () => {
        fetchMock.mockImplementation((url) => {
            if (url === "http://localhost/rq-engine/api/runs/demo-run/cfg/session-token") {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ token: "session-token" }),
                });
            }
            if (url === "http://localhost/rq-engine/api/runs/demo-run/cfg/fork") {
                const payload = {
                    error: { message: "Error forking project", details: ["trace line 1", "trace line 2"] },
                };
                return Promise.resolve({
                    ok: false,
                    text: () => Promise.resolve(JSON.stringify(payload)),
                });
            }
            return Promise.reject(new Error(`Unexpected fetch: ${url}`));
        });

        document.getElementById("fork_form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        await flushPromises();

        const consoleBlock = document.getElementById("the_console");
        expect(consoleBlock.dataset.state).toBe("critical");
        expect(consoleBlock.textContent).toContain("Error forking project");

        const stacktraceBody = document.querySelector("#fork_stacktrace_panel [data-stacktrace-body]");
        expect(stacktraceBody.textContent).toContain("trace line 1");
        expect(stacktraceBody.textContent).toContain("trace line 2");

        expect(document.getElementById("submit_button").disabled).toBe(false);
        expect(document.getElementById("submit_button").hidden).toBe(false);
    });

    test("cancel targets only the accepted tracked job with renewable authorization", async () => {
        fetchMock.mockImplementation((url) => {
            if (url === "http://localhost/rq-engine/api/runs/demo-run/cfg/session-token") {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ token: "session-token" }),
                });
            }
            if (url === "http://localhost/rq-engine/api/runs/demo-run/cfg/fork") {
                return Promise.resolve({
                    ok: true,
                    text: () => Promise.resolve(JSON.stringify({
                        job_id: "job-456",
                        new_runid: "demo-run-new",
                        undisturbify: false,
                        skip_wepp_runs_output: false,
                    })),
                });
            }
            if (url === "/rq-engine/api/canceljob/job-456") {
                return Promise.resolve({
                    ok: true,
                    text: () => Promise.resolve(JSON.stringify({ status: "ok" })),
                });
            }
            return Promise.reject(new Error(`Unexpected fetch: ${url}`));
        });

        document.getElementById("fork_form").dispatchEvent(
            new Event("submit", { bubbles: true, cancelable: true })
        );
        await flushPromises();
        fetchMock.mockClear();

        document.getElementById("cancel_button").click();
        await flushPromises();

        expect(fetchMock).toHaveBeenCalledTimes(2);
        expect(fetchMock.mock.calls[0][0]).toBe(
            "http://localhost/rq-engine/api/runs/demo-run/cfg/session-token"
        );
        expect(fetchMock.mock.calls[1]).toEqual([
            "/rq-engine/api/canceljob/job-456",
            {
                method: "POST",
                headers: { Authorization: "Bearer session-token" },
            },
        ]);
        expect(global.alert).toHaveBeenCalledWith("Job canceled");
    });

    test("stale auth prompts reload when fork returns unauthorized", async () => {
        fetchMock.mockImplementation((url) => {
            if (url === "http://localhost/rq-engine/api/runs/demo-run/cfg/session-token") {
                const payload = {
                    error: { code: "unauthorized", message: "Session not authorized for run" },
                };
                return Promise.resolve({
                    ok: false,
                    status: 401,
                    json: () => Promise.resolve(payload),
                });
            }
            if (url === "http://localhost/rq-engine/api/runs/demo-run/cfg/fork") {
                const payload = {
                    error: { code: "unauthorized", message: "Session not authorized for run" },
                };
                return Promise.resolve({
                    ok: false,
                    status: 401,
                    text: () => Promise.resolve(JSON.stringify(payload)),
                });
            }
            return Promise.reject(new Error(`Unexpected fetch: ${url}`));
        });

        document.body.innerHTML = `
            <section data-controller="fork-console">
                <div data-fork-console-config
                     data-runid="demo-run"
                     data-config="cfg"
                     data-undisturbify="false"
                     data-rq-engine-token="rq-token-123"
                     hidden></div>
                <div id="fork_status_panel">
                    <div id="fork_status_log" data-status-log></div>
                </div>
                <div id="fork_stacktrace_panel"><pre data-stacktrace-body></pre></div>
                <form id="fork_form">
                    <input id="runid_input" value="demo-run" />
                    <input id="undisturbify_checkbox" type="checkbox" />
                    <button id="submit_button" type="submit">Fork project</button>
                    <button id="cancel_button" type="button" hidden>Cancel</button>
                </form>
                <div id="the_console" data-state=""></div>
            </section>
        `;

        jest.resetModules();
        await import("../../static/js/console_utils.js");
        await import("../../static/js/fork_console.js");
        await flushPromises();
        fetchMock.mockClear();

        const form = document.getElementById("fork_form");
        form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        await flushPromises();

        const consoleBlock = document.getElementById("the_console");
        expect(consoleBlock.dataset.state).toBe("critical");
        expect(consoleBlock.textContent).toContain("Session not authorized for run");
        expect(global.alert).toHaveBeenCalledTimes(1);
        expect(global.alert.mock.calls[0][0]).toContain("Reload this page and sign in again.");
        expect(document.getElementById("submit_button").disabled).toBe(true);
    });

    test("stale auth prompts reload when cancel returns unauthorized", async () => {
        let tokenCalls = 0;
        fetchMock.mockImplementation((url) => {
            if (url === "http://localhost/rq-engine/api/runs/demo-run/cfg/session-token") {
                tokenCalls += 1;
                if (tokenCalls === 1) {
                    return Promise.resolve({
                        ok: true,
                        json: () => Promise.resolve({ token: "session-token" }),
                    });
                }
                const payload = {
                    error: { code: "unauthorized", message: "Session not authorized for run" },
                };
                return Promise.resolve({
                    ok: false,
                    status: 401,
                    json: () => Promise.resolve(payload),
                });
            }
            if (url === "http://localhost/rq-engine/api/runs/demo-run/cfg/fork") {
                const payload = {
                    job_id: "job-456",
                    new_runid: "demo-run-new",
                    undisturbify: false,
                };
                return Promise.resolve({
                    ok: true,
                    text: () => Promise.resolve(JSON.stringify(payload)),
                });
            }
            return Promise.reject(new Error(`Unexpected fetch: ${url}`));
        });

        document.getElementById("fork_form").dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
        await flushPromises();

        fetchMock.mockClear();
        global.alert.mockClear();

        const cancelButton = document.getElementById("cancel_button");
        expect(cancelButton.hidden).toBe(false);
        cancelButton.click();
        await flushPromises();

        const consoleBlock = document.getElementById("the_console");
        expect(consoleBlock.dataset.state).toBe("critical");
        expect(consoleBlock.textContent).toContain("Session not authorized for run");
        expect(global.alert).toHaveBeenCalledTimes(1);
        expect(global.alert.mock.calls[0][0]).toContain("Reload this page and sign in again.");
    });
});
