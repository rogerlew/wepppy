/** @jest-environment jsdom */
/* eslint-env node */

const fs = require("node:fs");
const path = require("node:path");

const templatePath = path.resolve(
    __dirname,
    "../../routes/rq/job_dashboard/templates/dashboard_pure.htm"
);

function inlineScript() {
    const source = fs.readFileSync(templatePath, "utf8");
    const scripts = [...source.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];
    return scripts.at(-1)[1]
        .replace("{{ job_id | tojson }}", JSON.stringify("job-123"))
        .replace("{{ site_prefix | tojson }}", JSON.stringify("/weppcloud"));
}

function response(status, payload) {
    return {
        ok: status >= 200 && status < 300,
        status,
        text: jest.fn().mockResolvedValue(JSON.stringify(payload)),
    };
}

function installDom() {
    document.body.innerHTML = `
      <span id="job-id">job-123</span><span id="run-id">--</span>
      <span id="job-summary">Waiting for data...</span>
      <span id="query-count">0</span><span id="query-interval">--</span>
      <button id="cancel-job" type="button">Cancel job</button>
      <div><canvas id="job-dashboard-qr"></canvas></div>
      <span class="job-dashboard__qr-label"></span>
      <div id="job-overall-progress"></div><div id="job-dashboard"></div>
    `;
    global.QRCode = {
        generate: jest.fn(() => ({ size: 1 })),
        render: jest.fn(),
    };
    global.url_for_run = jest.fn(() => "/rq-engine/api/runs/run-1/cfg/session-token");
    global.confirm = jest.fn(() => true);
    global.alert = jest.fn();
}

async function settle() {
    for (let index = 0; index < 24; index += 1) {
        await Promise.resolve();
    }
}

function executeDashboard() {
    const originalAddEventListener = document.addEventListener.bind(document);
    let initialize;
    const listenerSpy = jest
        .spyOn(document, "addEventListener")
        .mockImplementation((eventName, callback, options) => {
            if (eventName === "DOMContentLoaded") {
                initialize = callback;
                return;
            }
            originalAddEventListener(eventName, callback, options);
        });
    window.eval(inlineScript());
    listenerSpy.mockRestore();
    initialize();
}

describe("RQ job dashboard inline contract", () => {
    beforeEach(() => {
        jest.resetModules();
        installDom();
    });

    afterEach(() => {
        jest.restoreAllMocks();
        delete global.fetch;
        delete global.QRCode;
        delete global.url_for_run;
        delete global.confirm;
        delete global.alert;
    });

    test("escapes metadata and stops polling for a terminal tree", async () => {
        global.fetch = jest.fn().mockResolvedValue(
            response(200, {
                id: "job-123", runid: "run-1", status: "finished",
                description: "<img src=x onerror=alert(1)>", elapsed_s: 3, children: {},
            })
        );
        const timeoutSpy = jest.spyOn(window, "setTimeout");

        executeDashboard();
        await settle();

        expect(global.fetch).toHaveBeenCalledWith(
            "/rq-engine/api/jobinfo/job-123",
            { credentials: "same-origin" }
        );
        expect(document.querySelector("#job-dashboard").innerHTML).toContain(
            "&lt;img src=x onerror=alert(1)&gt;"
        );
        expect(document.querySelector("#job-dashboard img")).toBeNull();
        expect(document.querySelector("#run-id a").getAttribute("href")).toBe(
            "/weppcloud/runs/run-1/cfg"
        );
        expect(timeoutSpy).not.toHaveBeenCalled();
    });

    test("backs off after a canonical rate limit", async () => {
        global.fetch = jest.fn().mockResolvedValue(
            response(429, {
                error: { code: "rate_limited", message: "Too many polling requests" },
            })
        );
        const timeoutSpy = jest.spyOn(window, "setTimeout").mockImplementation(() => 42);

        executeDashboard();
        await settle();

        expect(document.querySelector("#job-dashboard").textContent).toContain("Rate limited");
        expect(document.querySelector("#query-interval").textContent).toBe("2000");
        expect(timeoutSpy).toHaveBeenCalledWith(expect.any(Function), 2000);
    });

    test("retries polling with a fallback token when auth is required", async () => {
        global.fetch = jest.fn()
            .mockResolvedValueOnce(response(401, {
                error: { code: "auth_required", message: "Bearer token required" },
            }))
            .mockResolvedValueOnce(response(200, {
                token: "status-token", expires_at: 4102444800,
            }))
            .mockResolvedValueOnce(response(200, {
                id: "job-123", runid: "run-1", status: "finished",
                description: "Done", elapsed_s: 1, children: {},
            }));

        executeDashboard();
        await settle();

        expect(global.fetch).toHaveBeenNthCalledWith(
            2,
            "/weppcloud/api/auth/rq-engine-token",
            { method: "POST", credentials: "same-origin" }
        );
        expect(global.fetch).toHaveBeenNthCalledWith(
            3,
            "/rq-engine/api/jobinfo/job-123",
            {
                credentials: "same-origin",
                headers: { Authorization: "Bearer status-token" },
            }
        );
        expect(document.querySelector("#job-summary").textContent).toContain("Finished");
    });

    test("confirms one authorized cancellation and refreshes", async () => {
        const terminal = {
            id: "job-123", runid: "run-1", status: "finished",
            description: "Done", elapsed_s: 1, children: {},
        };
        global.fetch = jest.fn()
            .mockResolvedValueOnce(response(200, terminal))
            .mockResolvedValueOnce(response(200, {
                token: "session-token", expires_at: 4102444800,
            }))
            .mockResolvedValueOnce(response(200, { status: "canceled" }))
            .mockResolvedValueOnce(response(200, { ...terminal, status: "canceled" }));

        executeDashboard();
        await settle();
        document.querySelector("#cancel-job").click();
        await settle();

        expect(global.confirm).toHaveBeenCalledTimes(1);
        expect(global.fetch).toHaveBeenNthCalledWith(
            3,
            "/rq-engine/api/canceljob/job-123",
            {
                method: "POST",
                credentials: "same-origin",
                headers: { Authorization: "Bearer session-token" },
            }
        );
        expect(global.alert).toHaveBeenCalledWith("Job canceled");
        expect(document.querySelector("#cancel-job").disabled).toBe(false);
        expect(global.fetch).toHaveBeenCalledTimes(4);
    });
});
