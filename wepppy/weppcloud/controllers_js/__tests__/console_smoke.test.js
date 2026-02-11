/**
 * @jest-environment jsdom
 */

const flushPromises = () => new Promise((resolve) => setTimeout(resolve, 0));

describe("Archive console smoke", () => {
    let originalReadyStateDescriptor;
    let fetchMock;
    let statusStreamInstance;

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
        delete global.fetch;
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
    });
});

describe("Fork console smoke", () => {
    let originalReadyStateDescriptor;
    let fetchMock;
    let statusStreamInstance;

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

        await import("../../static/js/console_utils.js");
        await import("../../static/js/fork_console.js");
        await flushPromises();
        fetchMock.mockClear();
        statusStreamInstance.append.mockClear();
        global.StatusStream.attach.mockClear();
    });

    afterEach(() => {
        if (originalReadyStateDescriptor) {
            Object.defineProperty(document, "readyState", originalReadyStateDescriptor);
        } else {
            delete document.readyState;
        }
        document.body.innerHTML = "";
        delete global.StatusStream;
        delete global.fetch;
        delete global.alert;
    });

    test("submitting fork form posts the fork job", async () => {
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
            body: "undisturbify=false",
        });

        expect(statusStreamInstance.append).toHaveBeenCalledWith("Submitting fork job...");
     
        const consoleBlock = document.getElementById("the_console");
        expect(consoleBlock.dataset.state).toBe("attention");
        expect(global.StatusStream.attach).toHaveBeenCalledWith(expect.objectContaining({
            channel: "fork",
            runId: "demo-run",
        }));
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
            body: "undisturbify=false",
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
