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
            if (url === "/runs/demo/config/rq/api/archive") {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({ Success: true, job_id: "job-123" }),
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
                    data-archive-api-url="/runs/demo/config/rq/api/archive"
                    data-restore-api-url="/runs/demo/config/rq/api/restore"
                    data-delete-api-url="/runs/demo/config/rq/api/delete"
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

        expect(fetchMock).toHaveBeenCalledTimes(1);
        const [url, options] = fetchMock.mock.calls[0];
        expect(url).toBe("/runs/demo/config/rq/api/archive");
        expect(options).toMatchObject({
            method: "POST",
            headers: { "Content-Type": "application/json" },
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
            if (url === "http://localhost/weppcloud/runs/demo-run/cfg/rq/api/fork") {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        Success: true,
                        job_id: "job-456",
                        new_runid: "demo-run-new",
                        undisturbify: false,
                    }),
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

        expect(fetchMock).toHaveBeenCalledTimes(1);
        const [url, options] = fetchMock.mock.calls[0];
        expect(url).toBe("http://localhost/weppcloud/runs/demo-run/cfg/rq/api/fork");
        expect(options).toMatchObject({
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: "undisturbify=false",
        });

        expect(statusStreamInstance.append).toHaveBeenCalledWith("Submitting fork job...");
        expect(statusStreamInstance.append).toHaveBeenCalledWith("Fork job submitted: job-456");

        const consoleBlock = document.getElementById("the_console");
        expect(consoleBlock.dataset.state).toBe("attention");
        expect(consoleBlock.innerHTML).toContain('Fork job submitted:');
        expect(global.StatusStream.attach).toHaveBeenCalledWith(expect.objectContaining({
            channel: "fork",
            runId: "demo-run",
        }));
    });

    test("failed fork surfaces stacktrace", async () => {
        fetchMock.mockImplementation((url) => {
            if (url === "http://localhost/weppcloud/runs/demo-run/cfg/rq/api/fork") {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        Success: false,
                        Error: "Error forking project",
                        StackTrace: ["trace line 1", "trace line 2"],
                    }),
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
});
