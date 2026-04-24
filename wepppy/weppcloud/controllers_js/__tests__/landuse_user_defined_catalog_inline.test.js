/**
 * @jest-environment jsdom
 */

const fs = require("fs");
const path = require("path");

const TEMPLATE_PATH = path.resolve("..", "templates", "controls", "landuse_user_defined.htm");

function extractInlineScriptSource() {
    const template = fs.readFileSync(TEMPLATE_PATH, "utf8");
    const start = template.lastIndexOf("<script>");
    const end = template.indexOf("</script>", start);
    if (start === -1 || end === -1) {
        throw new Error("Unable to locate landuse_user_defined inline script.");
    }
    return template.slice(start + "<script>".length, end);
}

function buildPageMarkup(seedItems) {
    return `
        <meta name="csrf-token" content="csrf-token-123" />
        <div id="landuse-user-defined-config"
             data-list-url="/rq-engine/api/runs/test/cfg/landuse-user-defined/catalog"
             data-upload-url="/rq-engine/api/runs/test/cfg/landuse-user-defined/upload"
             data-delete-url="/rq-engine/api/runs/test/cfg/landuse-user-defined/delete"
             data-update-description-url="/rq-engine/api/runs/test/cfg/landuse-user-defined/update-description"
             data-session-token-url="/rq-engine/api/runs/test/cfg/session-token"></div>
        <script id="landuse-user-defined-seed" type="application/json">${JSON.stringify(seedItems || [])}</script>
        <div id="catalog-status" class="wc-alert wc-alert--info lu-catalog__status">
            <p class="wc-alert__body">Catalog ready.</p>
        </div>
        <form id="catalog-upload-form">
            <input id="catalog-upload-input" name="management_upload" type="file" />
            <input id="catalog-upload-replace" name="replace" type="checkbox" value="true" />
            <button type="submit">Upload</button>
            <button id="catalog-refresh" type="button">Refresh</button>
        </form>
        <table><tbody id="catalog-rows"></tbody></table>
        <div id="catalog-empty" hidden>No user-defined management files uploaded yet.</div>
    `;
}

function makeJsonResponse(payload, status = 200) {
    return {
        ok: status >= 200 && status < 300,
        status,
        text: () => Promise.resolve(JSON.stringify(payload)),
    };
}

describe("landuse_user_defined inline catalog script", () => {
    const scriptSource = extractInlineScriptSource();

    async function flushPromises(iterations = 6) {
        for (let idx = 0; idx < iterations; idx += 1) {
            // eslint-disable-next-line no-await-in-loop
            await Promise.resolve();
            // eslint-disable-next-line no-await-in-loop
            await new Promise((resolve) => setTimeout(resolve, 0));
        }
    }

    beforeEach(() => {
        jest.resetAllMocks();
        document.body.innerHTML = "";
    });

    afterEach(() => {
        delete global.fetch;
    });

    test("refresh button loads catalog rows from top-level items payload", async () => {
        document.body.innerHTML = buildPageMarkup([]);

        const fetchMock = jest.fn((url) => {
            if (url === "/rq-engine/api/runs/test/cfg/session-token") {
                return Promise.resolve(makeJsonResponse({ token: "rq-token" }));
            }
            if (url === "/rq-engine/api/runs/test/cfg/landuse-user-defined/catalog") {
                return Promise.resolve(makeJsonResponse({
                    items: [
                        {
                            filename: "custom_entry.man",
                            description: "Custom forest",
                            uploaded_at: "2026-04-24T06:54:00+00:00",
                            size_bytes: 42,
                            sha256: "deadbeef",
                        },
                    ],
                }));
            }
            throw new Error("Unexpected fetch URL: " + url);
        });
        global.fetch = fetchMock;

        window.eval(scriptSource);

        const refreshButton = document.getElementById("catalog-refresh");
        refreshButton.click();
        await flushPromises();

        expect(fetchMock).toHaveBeenCalledWith(
            "/rq-engine/api/runs/test/cfg/session-token",
            expect.objectContaining({ method: "POST" })
        );
        expect(fetchMock).toHaveBeenCalledWith(
            "/rq-engine/api/runs/test/cfg/landuse-user-defined/catalog",
            expect.objectContaining({ method: "GET" })
        );
        expect(document.getElementById("catalog-status").textContent).toContain("Catalog refreshed.");

        const rows = document.querySelectorAll("#catalog-rows tr");
        expect(rows).toHaveLength(1);
        expect(rows[0].textContent).toContain("custom_entry.man");
        const descriptionInput = rows[0].querySelector("[data-description-for='custom_entry.man']");
        expect(descriptionInput).toBeTruthy();
        expect(descriptionInput.value).toBe("Custom forest");
        expect(document.getElementById("catalog-empty").hidden).toBe(true);
    });

    test("save description keeps updated value from top-level items response", async () => {
        document.body.innerHTML = buildPageMarkup([
            {
                filename: "custom_entry.man",
                description: "Old description",
                uploaded_at: "2026-04-24T06:54:00+00:00",
                size_bytes: 42,
                sha256: "deadbeef",
            },
        ]);

        const fetchMock = jest.fn((url) => {
            if (url === "/rq-engine/api/runs/test/cfg/session-token") {
                return Promise.resolve(makeJsonResponse({ token: "rq-token" }));
            }
            if (url === "/rq-engine/api/runs/test/cfg/landuse-user-defined/update-description") {
                return Promise.resolve(makeJsonResponse({
                    message: "Landuse user-defined description updated",
                    items: [
                        {
                            filename: "custom_entry.man",
                            description: "New description",
                            uploaded_at: "2026-04-24T06:54:00+00:00",
                            size_bytes: 42,
                            sha256: "deadbeef",
                        },
                    ],
                }));
            }
            throw new Error("Unexpected fetch URL: " + url);
        });
        global.fetch = fetchMock;

        window.eval(scriptSource);

        const descriptionInput = document.querySelector("[data-description-for='custom_entry.man']");
        descriptionInput.value = "New description";
        const saveButton = document.querySelector("[data-action='save-description'][data-filename='custom_entry.man']");
        saveButton.click();
        await flushPromises();

        const refreshedInput = document.querySelector("[data-description-for='custom_entry.man']");
        expect(refreshedInput.value).toBe("New description");
        expect(document.getElementById("catalog-status").textContent).toContain("Description updated.");
    });
});
