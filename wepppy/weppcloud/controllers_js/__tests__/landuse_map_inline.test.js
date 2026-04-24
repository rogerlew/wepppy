/**
 * @jest-environment jsdom
 */

const fs = require("fs");
const path = require("path");

const TEMPLATE_PATH = path.resolve("..", "templates", "controls", "landuse_map.htm");

function extractInlineScriptSource() {
    const template = fs.readFileSync(TEMPLATE_PATH, "utf8");
    const start = template.lastIndexOf("<script>");
    const end = template.indexOf("</script>", start);
    if (start === -1 || end === -1) {
        throw new Error("Unable to locate landuse_map inline script.");
    }
    return template.slice(start + "<script>".length, end);
}

function buildPageMarkup(seedPayload) {
    return `
        <meta name="csrf-token" content="csrf-token-123" />
        <div id="landuse-map-config"
             data-snapshot-url="/rq-engine/api/runs/test/cfg/landuse-map/snapshot"
             data-save-url="/rq-engine/api/runs/test/cfg/landuse-map/save"
             data-clear-override-url="/rq-engine/api/runs/test/cfg/landuse-map/clear-override"
             data-session-token-url="/rq-engine/api/runs/test/cfg/session-token"></div>
        <script id="landuse-map-seed" type="application/json">${JSON.stringify(seedPayload || {})}</script>
        <div id="landuse-map-status" class="wc-alert wc-alert--info lu-map__status">
            <p class="wc-alert__body">Map snapshot loaded.</p>
        </div>
        <button id="landuse-map-save" type="button">Save Map</button>
        <button id="landuse-map-refresh" type="button">Refresh</button>
        <button id="landuse-map-clear" type="button">Clear Override</button>
        <table><tbody id="landuse-map-rows"></tbody></table>
        <div id="landuse-map-empty" hidden>No rows available.</div>
    `;
}

function makeJsonResponse(payload, status = 200) {
    return {
        ok: status >= 200 && status < 300,
        status,
        text: () => Promise.resolve(JSON.stringify(payload)),
    };
}

describe("landuse_map inline script", () => {
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

    test("save map submits rows with precondition header and refreshes snapshot", async () => {
        document.body.innerHTML = buildPageMarkup({
            rows: [
                {
                    key: "21",
                    description: "Low Intensity Residential",
                    disturbed_class: "developed low intensity",
                    management_file: "Developed_Low_Intensity.man",
                },
            ],
            management_options: [
                {
                    management_file: "Developed_Low_Intensity.man",
                    description: "Low",
                    source: "mapping",
                },
                {
                    management_file: "Developed_Moderate_Intensity.man",
                    description: "Moderate",
                    source: "mapping",
                },
            ],
            lookup_sha256: "sha-before-save",
        });

        const fetchMock = jest.fn((url, options) => {
            if (url === "/rq-engine/api/runs/test/cfg/session-token") {
                return Promise.resolve(makeJsonResponse({ token: "rq-token" }));
            }
            if (url === "/rq-engine/api/runs/test/cfg/landuse-map/save") {
                expect(options.method).toBe("POST");
                expect(options.headers.Authorization).toBe("Bearer rq-token");
                expect(options.headers["X-If-Match-Sha256"]).toBe("sha-before-save");
                const payload = JSON.parse(options.body);
                expect(payload.rows).toEqual([
                    { key: "21", management_file: "Developed_Moderate_Intensity.man" },
                ]);
                return Promise.resolve(makeJsonResponse({ message: "Landuse map saved", lookup_sha256: "sha-after-save" }));
            }
            if (url === "/rq-engine/api/runs/test/cfg/landuse-map/snapshot") {
                return Promise.resolve(
                    makeJsonResponse({
                        rows: [
                            {
                                key: "21",
                                description: "Low Intensity Residential",
                                disturbed_class: "developed low intensity",
                                management_file: "Developed_Moderate_Intensity.man",
                            },
                        ],
                        management_options: [
                            {
                                management_file: "Developed_Low_Intensity.man",
                                description: "Low",
                                source: "mapping",
                            },
                            {
                                management_file: "Developed_Moderate_Intensity.man",
                                description: "Moderate",
                                source: "mapping",
                            },
                        ],
                        lookup_sha256: "sha-after-save",
                    })
                );
            }
            throw new Error("Unexpected fetch URL: " + url);
        });
        global.fetch = fetchMock;

        window.eval(scriptSource);

        const select = document.querySelector("[data-row-key='21']");
        select.value = "Developed_Moderate_Intensity.man";
        document.getElementById("landuse-map-save").click();
        await flushPromises();

        expect(fetchMock).toHaveBeenCalledWith(
            "/rq-engine/api/runs/test/cfg/landuse-map/save",
            expect.objectContaining({ method: "POST" })
        );
        expect(fetchMock).toHaveBeenCalledWith(
            "/rq-engine/api/runs/test/cfg/landuse-map/snapshot",
            expect.objectContaining({ method: "GET" })
        );
        expect(document.getElementById("landuse-map-status").textContent).toContain("Map snapshot refreshed.");
    });

    test("save map warns when lookup hash is missing", async () => {
        document.body.innerHTML = buildPageMarkup({
            rows: [
                {
                    key: "21",
                    description: "Low Intensity Residential",
                    disturbed_class: "developed low intensity",
                    management_file: "Developed_Low_Intensity.man",
                },
            ],
            management_options: [
                {
                    management_file: "Developed_Low_Intensity.man",
                    description: "Low",
                    source: "mapping",
                },
            ],
            lookup_sha256: null,
        });

        const fetchMock = jest.fn(() => Promise.resolve(makeJsonResponse({ token: "rq-token" })));
        global.fetch = fetchMock;

        window.eval(scriptSource);

        document.getElementById("landuse-map-save").click();
        await flushPromises();

        expect(fetchMock).not.toHaveBeenCalledWith(
            "/rq-engine/api/runs/test/cfg/landuse-map/save",
            expect.anything()
        );
        expect(document.getElementById("landuse-map-status").textContent).toContain(
            "Snapshot hash unavailable. Reload the table first."
        );
    });
});
