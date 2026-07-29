/** @jest-environment jsdom */
/* eslint-env node */

const fs = require("node:fs");
const path = require("node:path");

const templatePath = path.resolve(
    __dirname,
    "../../templates/reports/deval_loading.htm"
);

function inlineScript({ jobId = "job-1", initialStatus = "queued" } = {}) {
    const source = fs.readFileSync(templatePath, "utf8");
    const scripts = [...source.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];
    return scripts.at(-1)[1]
        .replace("{{ job_id|tojson }}", JSON.stringify(jobId))
        .replace("{{ job_status|tojson }}", JSON.stringify(initialStatus))
        .replace("{{ refresh_url|tojson }}", JSON.stringify("/runs/run-1/cfg/report/deval_details"))
        .replace(
            "window.location.replace(refreshUrl)",
            "window.__replaceLocation(refreshUrl)"
        );
}

function installDom() {
    document.body.innerHTML = `
      <div id="statusChip" data-state="queued">QUEUED</div>
      <div id="statusNote" data-state="active"></div>
      <span id="statusSpinner"></span>
      <span id="statusText"></span>
      <div id="errorPanel" hidden><div id="errorMessage"></div></div>
    `;
    window.__replaceLocation = jest.fn();
}

function jsonResponse(payload, { ok = true, status = 200 } = {}) {
    return {
        ok,
        status,
        headers: { get: () => "application/json" },
        json: async () => payload,
    };
}

async function settle() {
    for (let index = 0; index < 16; index += 1) {
        await Promise.resolve();
    }
}

describe("DEVAL loading inline contract", () => {
    beforeEach(() => {
        jest.useFakeTimers();
        installDom();
        window.fetch = jest.fn();
    });

    afterEach(() => {
        jest.useRealTimers();
        jest.restoreAllMocks();
        delete window.__replaceLocation;
    });

    test("polls active work and refreshes only on canonical finished", async () => {
        window.fetch
            .mockResolvedValueOnce(jsonResponse({ status: "started" }))
            .mockResolvedValueOnce(jsonResponse({ status: "finished" }));

        window.eval(inlineScript());
        jest.advanceTimersByTime(800);
        await settle();
        expect(window.fetch).toHaveBeenNthCalledWith(
            1,
            "/rq-engine/api/jobstatus/job-1",
            { headers: { Accept: "application/json" } }
        );
        expect(document.querySelector("#statusChip").dataset.state).toBe("started");

        jest.advanceTimersByTime(800);
        await settle();
        jest.advanceTimersByTime(400);
        expect(window.__replaceLocation).toHaveBeenCalledWith(
            "/runs/run-1/cfg/report/deval_details"
        );
    });

    test.each([
        [{ status: "mystery" }, "Unexpected job status"],
        [{}, "missing job status"],
    ])("fails closed for malformed successful payload %#", async (payload, message) => {
        window.fetch.mockResolvedValue(jsonResponse(payload));

        window.eval(inlineScript());
        jest.advanceTimersByTime(800);
        await settle();
        jest.runOnlyPendingTimers();

        expect(window.__replaceLocation).not.toHaveBeenCalled();
        expect(document.querySelector("#errorPanel").hidden).toBe(false);
        expect(document.querySelector("#errorMessage").textContent).toContain(message);
    });

    test("renders canonical nested failure message as text", async () => {
        window.fetch.mockResolvedValue(
            jsonResponse({
                status: "failed",
                error: { message: "<strong>renderer failed</strong>" },
            })
        );

        window.eval(inlineScript());
        jest.advanceTimersByTime(800);
        await settle();

        expect(document.querySelector("#errorMessage").textContent).toBe(
            "<strong>renderer failed</strong>"
        );
        expect(document.querySelector("#errorMessage").innerHTML).not.toContain(
            "<strong>"
        );
    });

    test("backs off 429 responses and stops after bounded ordinary errors", async () => {
        window.fetch
            .mockResolvedValueOnce(
                jsonResponse(
                    { error: { code: "rate_limited", message: "Too many polling requests" } },
                    { ok: false, status: 429 }
                )
            )
            .mockRejectedValue(new Error("offline"));

        window.eval(inlineScript());
        await jest.advanceTimersByTimeAsync(800);
        expect(document.querySelector("#statusText").textContent).toContain(
            "Retrying in 2s"
        );

        for (let attempt = 0; attempt < 5; attempt += 1) {
            await jest.advanceTimersByTimeAsync(1600);
        }

        expect(window.fetch).toHaveBeenCalledTimes(6);
        expect(document.querySelector("#errorPanel").hidden).toBe(false);
        expect(document.querySelector("#statusText").textContent).toBe("Render failed.");
        expect(document.querySelector("#errorMessage").textContent).toBe(
            "Unable to reach the job status endpoint after 5 attempts."
        );
    });
});
