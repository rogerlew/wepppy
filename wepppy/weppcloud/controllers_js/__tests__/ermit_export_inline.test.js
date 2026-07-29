/**
 * @jest-environment jsdom
 */

const fs = require("fs");
const path = require("path");

const TEMPLATE_PATH = path.resolve("..", "templates", "reports", "ermit_export_download.htm");
const SUBMIT_URL = "/rq-engine/api/runs/test-run/test-config/export/ermit";
const TOKEN_URL = "/rq-engine/api/runs/test-run/test-config/session-token";
const STATUS_URL = "/rq-engine/api/jobstatus/ermit-job-1";
const DOWNLOAD_URL = "/rq-engine/api/runs/test-run/test-config/export/ermit/job/ermit-job-1/download";

function extractInlineScriptSource() {
    const template = fs.readFileSync(TEMPLATE_PATH, "utf8");
    const start = template.lastIndexOf("<script>");
    const end = template.indexOf("</script>", start);
    if (start === -1 || end === -1) {
        throw new Error("Unable to locate ERMiT export inline script.");
    }
    return template
        .slice(start + "<script>".length, end)
        .replace("{{ ermit_export_submit_url|tojson }}", JSON.stringify(SUBMIT_URL))
        .replace("{{ ermit_export_session_token_url|tojson }}", JSON.stringify(TOKEN_URL));
}

function buildPageMarkup() {
    return `
        <div id="ermitExportStatusChip" data-state="queued">QUEUED</div>
        <div id="ermitExportStatusNote" data-state="active">
          <span id="ermitExportSpinner"></span>
          <span id="ermitExportStatusText">Preparing export request…</span>
        </div>
        <div id="ermitExportActions" hidden>
          <a id="ermitExportDownloadLink" href="#" download>Download</a>
        </div>
        <div id="ermitExportErrorPanel" data-state="error" hidden>
          <div id="ermitExportErrorMessage"></div>
          <button id="ermitExportRetry" type="button">Retry Export</button>
        </div>
    `;
}

function makeResponse(payload, status = 200, headers = {}) {
    return {
        ok: status >= 200 && status < 300,
        status,
        headers: {
            get: (name) => headers[String(name).toLowerCase()] || (
                String(name).toLowerCase() === "content-type" ? "application/json" : ""
            ),
        },
        json: () => Promise.resolve(payload),
        blob: () => Promise.resolve(new Blob(["ermit-zip"], { type: "application/zip" })),
    };
}

async function flushPromises(iterations = 10) {
    for (let idx = 0; idx < iterations; idx += 1) {
        // eslint-disable-next-line no-await-in-loop
        await Promise.resolve();
        // eslint-disable-next-line no-await-in-loop
        await new Promise((resolve) => setTimeout(resolve, 0));
    }
}

describe("ERMiT export inline lifecycle", () => {
    const scriptSource = extractInlineScriptSource();

    beforeEach(() => {
        jest.resetAllMocks();
        document.body.innerHTML = buildPageMarkup();
        global.URL.createObjectURL = jest.fn(() => "blob:ermit-export");
        jest.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    });

    afterEach(() => {
        delete global.fetch;
        delete global.URL.createObjectURL;
        jest.restoreAllMocks();
    });

    test("mints one token, submits, polls, and downloads the finished artifact", async () => {
        const fetchMock = jest.fn((url, options = {}) => {
            if (url === TOKEN_URL) {
                return Promise.resolve(makeResponse({ token: "session-token" }));
            }
            if (url === SUBMIT_URL) {
                return Promise.resolve(makeResponse({
                    job_id: "ermit-job-1",
                    status_url: STATUS_URL,
                    download_url: DOWNLOAD_URL,
                }, 202));
            }
            if (url === STATUS_URL) {
                return Promise.resolve(makeResponse({ status: "finished" }));
            }
            if (url === DOWNLOAD_URL) {
                return Promise.resolve(makeResponse({}, 200, {
                    "content-type": "application/zip",
                    "content-disposition": "attachment; filename=\"ERMiT_input_test.zip\"",
                }));
            }
            throw new Error("Unexpected fetch URL: " + url);
        });
        global.fetch = fetchMock;

        window.eval(scriptSource);
        await flushPromises();

        expect(fetchMock).toHaveBeenCalledWith(TOKEN_URL, expect.objectContaining({
            method: "POST",
            credentials: "same-origin",
        }));
        expect(fetchMock).toHaveBeenCalledWith(SUBMIT_URL, expect.objectContaining({
            method: "POST",
            headers: expect.objectContaining({ Authorization: "Bearer session-token" }),
        }));
        expect(fetchMock).toHaveBeenCalledWith(STATUS_URL, expect.objectContaining({
            headers: expect.objectContaining({ Authorization: "Bearer session-token" }),
        }));
        expect(fetchMock).toHaveBeenCalledWith(DOWNLOAD_URL, expect.objectContaining({
            headers: { Authorization: "Bearer session-token" },
        }));
        expect(fetchMock.mock.calls.filter(([url]) => url === TOKEN_URL)).toHaveLength(1);
        expect(document.getElementById("ermitExportStatusChip").dataset.state).toBe("finished");
        expect(document.getElementById("ermitExportStatusText").textContent).toBe("Export downloaded.");
        expect(document.getElementById("ermitExportActions").hidden).toBe(false);
        expect(document.getElementById("ermitExportDownloadLink").download).toBe("ERMiT_input_test.zip");
    });

    test("retry obtains a fresh token after the first token request fails", async () => {
        let tokenAttempts = 0;
        const fetchMock = jest.fn((url) => {
            if (url === TOKEN_URL) {
                tokenAttempts += 1;
                if (tokenAttempts === 1) {
                    return Promise.resolve(makeResponse({
                        error: { message: "Temporary token failure." },
                    }, 503));
                }
                return Promise.resolve(makeResponse({ token: "replacement-token" }));
            }
            if (url === SUBMIT_URL) {
                return Promise.resolve(makeResponse({
                    job_id: "ermit-job-1",
                    status_url: STATUS_URL,
                    download_url: DOWNLOAD_URL,
                }, 202));
            }
            if (url === STATUS_URL) {
                return Promise.resolve(makeResponse({ status: "failed", description: "Stop here." }));
            }
            throw new Error("Unexpected fetch URL: " + url);
        });
        global.fetch = fetchMock;

        window.eval(scriptSource);
        await flushPromises();
        expect(document.getElementById("ermitExportErrorMessage").textContent).toBe("Temporary token failure.");

        document.getElementById("ermitExportRetry").click();
        await flushPromises();

        expect(tokenAttempts).toBe(2);
        expect(fetchMock).toHaveBeenCalledWith(SUBMIT_URL, expect.objectContaining({
            headers: expect.objectContaining({ Authorization: "Bearer replacement-token" }),
        }));
    });
});
