/** @jest-environment jsdom */
/* eslint-env node */

const fs = require("node:fs");
const path = require("node:path");

const templatePath = path.resolve(
    __dirname,
    "../../templates/controls/edit_csv.htm"
);

function inlineScript() {
    const source = fs.readFileSync(templatePath, "utf8");
    const scripts = [...source.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];
    return scripts.at(-1)[1]
        .replace(
            'document.addEventListener("DOMContentLoaded", function () {',
            "window.__editCsvInit = function () {"
        )
        .replace(
            '});\n\nwindow.addEventListener("beforeunload"',
            '};\n\nwindow.addEventListener("beforeunload"'
        );
}

function installDom() {
    document.head.innerHTML = '<meta name="csrf-token" content="csrf-1">';
    document.body.innerHTML = `
      <div id="edit-csv-config"
           data-save-url="/runs/run-1/cfg/tasks/modify_disturbed?lookup=base"
           data-lookup-meta-url="/runs/run-1/cfg/api/disturbed/lookup_meta?lookup=base"
           data-lookup-snapshot-url="/runs/run-1/cfg/api/disturbed/lookup_snapshot?lookup=base"
           data-session-token-url="/rq-engine/api/runs/run-1/cfg/session-token"
           data-freeze-columns="4"
           data-loading-message="Loading table..."
           data-ready-message="Ready."
           data-save-success-message="Saved."></div>
      <div id="status-banner" class="wc-alert"><p class="wc-alert__body"></p></div>
      <button id="save" type="button" disabled>Save</button>
      <div id="stale-actions" style="display:none">
        <button id="reload-current" type="button">Load Current Table</button>
      </div>
      <div id="spreadsheet1"></div>
    `;
    Object.defineProperty(
        document.querySelector("#spreadsheet1"),
        "getBoundingClientRect",
        { value: () => ({ top: 100, width: 900 }) }
    );
}

function response({ ok = true, status = 200, body = {}, headers = {} } = {}) {
    return {
        ok,
        status,
        headers: { get: (name) => headers[name] || null },
        json: async () => body,
        text: async () => JSON.stringify(body),
    };
}

async function settle() {
    for (let index = 0; index < 24; index += 1) {
        await Promise.resolve();
    }
}

describe("shared CSV editor inline contract", () => {
    beforeEach(() => {
        jest.useFakeTimers();
        installDom();
        window.fetch = jest.fn();
        window.URL.createObjectURL = jest.fn(() => "blob:lookup");
        window.jspreadsheet = jest.fn(() => ({
            getData: jest.fn(() => [
                ["forest", "loam", "1"],
                ["", " ", null],
            ]),
            destroy: jest.fn(),
        }));
    });

    afterEach(() => {
        jest.useRealTimers();
        jest.restoreAllMocks();
        delete window.jspreadsheet;
    });

    test("authorizes, loads one atomic snapshot, and saves nonblank rows with its fingerprint", async () => {
        window.fetch
            .mockResolvedValueOnce(response())
            .mockResolvedValueOnce(response({
                body: {
                    Content: {
                        csv_text: "luse,stext,ki\nforest,loam,1\n",
                        lookup_sha256: "sha-before",
                    },
                },
            }))
            .mockResolvedValueOnce(response({
                headers: { "X-Lookup-Sha256": "sha-after" },
            }));

        window.eval(inlineScript());
        window.__editCsvInit();
        await settle();

        expect(window.fetch).toHaveBeenNthCalledWith(
            1,
            "/rq-engine/api/runs/run-1/cfg/session-token",
            expect.objectContaining({
                method: "POST",
                credentials: "same-origin",
                headers: { "X-CSRFToken": "csrf-1" },
            })
        );
        expect(window.fetch).toHaveBeenNthCalledWith(
            2,
            "/runs/run-1/cfg/api/disturbed/lookup_snapshot?lookup=base",
            { method: "GET", credentials: "same-origin", cache: "no-store" }
        );
        expect(document.querySelector("#save").disabled).toBe(false);

        document.querySelector("#save").click();
        await settle();

        expect(window.fetch).toHaveBeenNthCalledWith(
            3,
            "/runs/run-1/cfg/tasks/modify_disturbed?lookup=base",
            expect.objectContaining({
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": "csrf-1",
                },
                body: JSON.stringify({
                    rows: [["forest", "loam", "1"]],
                    if_match_sha256: "sha-before",
                }),
            })
        );
        expect(document.querySelector("#status-banner").textContent).toContain("Saved.");
        expect(document.querySelector("#save").disabled).toBe(false);
    });

    test("locks a stale page and retains recovery controls when reload fails", async () => {
        window.fetch
            .mockResolvedValueOnce(response())
            .mockResolvedValueOnce(response({
                body: {
                    Content: {
                        csv_text: "luse,stext,ki\nforest,loam,1\n",
                        lookup_sha256: "sha-before",
                    },
                },
            }))
            .mockResolvedValueOnce(response({
                body: { Content: { lookup_sha256: "sha-new" } },
            }))
            .mockRejectedValueOnce(new Error("session offline"));

        window.eval(inlineScript());
        window.__editCsvInit();
        await settle();
        jest.advanceTimersByTime(15000);
        await settle();

        expect(document.querySelector("#save").disabled).toBe(true);
        expect(document.querySelector("#spreadsheet1").getAttribute("aria-disabled")).toBe("true");
        expect(document.querySelector("#stale-actions").style.display).toBe("block");

        document.querySelector("#reload-current").click();
        await settle();

        expect(document.querySelector("#stale-actions").style.display).toBe("block");
        expect(document.querySelector("#status-banner").textContent).toContain(
            "Reload failed while page is stale"
        );
    });

    test("maps a stale save response to a locked visible recovery state", async () => {
        window.fetch
            .mockResolvedValueOnce(response())
            .mockResolvedValueOnce(response({
                body: {
                    Content: {
                        csv_text: "luse,stext,ki\nforest,loam,1\n",
                        lookup_sha256: "sha-before",
                    },
                },
            }))
            .mockResolvedValueOnce(response({
                ok: false,
                status: 409,
                body: {
                    error: {
                        code: "STALE_LOOKUP",
                        message: "Stale lookup.",
                        details: { current_sha256: "sha-current" },
                    },
                },
            }));

        window.eval(inlineScript());
        window.__editCsvInit();
        await settle();
        document.querySelector("#save").click();
        await settle();

        expect(document.querySelector("#save").disabled).toBe(true);
        expect(document.querySelector("#stale-actions").style.display).toBe("block");
        expect(document.querySelector("#status-banner").textContent).toContain(
            "Save blocked: table is stale"
        );
    });

    test("reports a missing spreadsheet CDN runtime and never enables saving", async () => {
        delete window.jspreadsheet;
        window.fetch
            .mockResolvedValueOnce(response())
            .mockResolvedValueOnce(response({
                body: {
                    Content: {
                        csv_text: "luse,stext,ki\nforest,loam,1\n",
                        lookup_sha256: "sha-before",
                    },
                },
            }));

        window.eval(inlineScript());
        window.__editCsvInit();
        await settle();

        expect(document.querySelector("#save").disabled).toBe(true);
        expect(document.querySelector("#status-banner").textContent).toContain(
            "Spreadsheet library failed to load"
        );
    });
});
