/**
 * @jest-environment jsdom
 */

describe("Project config update controller", () => {
    let requestWithSessionToken;
    let request;

    function fixture() {
        document.body.innerHTML = `
          <div data-project-config-update
               data-availability-url="/availability"
               data-preview-url="/preview"
               data-apply-url="/apply" hidden>
            <button data-project-config-update-open>Update</button>
            <p data-project-config-digest-warning hidden></p>
          </div>
          <div id="projectConfigUpdateModal" hidden>
            <p data-project-config-update-error hidden tabindex="-1"></p>
            <p data-project-config-update-status tabindex="-1"></p>
            <div data-project-config-update-review hidden><table><tbody data-project-config-update-rows></tbody></table></div>
            <button data-project-config-update-refresh></button>
            <button data-project-config-update-apply disabled></button>
          </div>`;
    }

    beforeEach(async () => {
        jest.resetModules();
        jest.useFakeTimers();
        fixture();
        requestWithSessionToken = jest.fn((url) => {
            if (url === "/availability") {
                return Promise.resolve({ body: { available: true, preview_id: "pcu1-a", digest_warning: true } });
            }
            if (url === "/preview") {
                return Promise.resolve({ body: {
                    preview_id: "pcu1-a",
                    additions: [{
                        section: "new<section>", option: "enabled", value: "true",
                        source_id: "preset", source_revision: "rev-2"
                    }]
                } });
            }
            return Promise.resolve({ body: { job_id: "job-1" } });
        });
        request = jest.fn(() => Promise.resolve({ body: { status: "finished" } }));
        window.WCHttp = { requestWithSessionToken, request };
        await import("../project_config_update.js");
        if (!window.ProjectConfigUpdate) {
            document.dispatchEvent(new Event("DOMContentLoaded"));
        }
        await Promise.resolve();
    });

    afterEach(() => {
        jest.useRealTimers();
        delete window.WCHttp;
        delete window.ProjectConfigUpdate;
        delete window.ProjectConfigUpdateController;
        document.body.innerHTML = "";
    });

    test("page load performs only one read-only availability request", async () => {
        await Promise.resolve();
        expect(requestWithSessionToken).toHaveBeenCalledTimes(1);
        expect(requestWithSessionToken).toHaveBeenCalledWith("/availability", {});
        expect(document.querySelector("[data-project-config-update]").hidden).toBe(false);
        expect(document.querySelector("[data-project-config-digest-warning]").hidden).toBe(false);
    });

    test("opening renders the complete preview as text and enables explicit apply", async () => {
        await window.ProjectConfigUpdate.loadPreview();

        const cells = Array.from(document.querySelectorAll("[data-project-config-update-rows] td"));
        expect(cells.map((cell) => cell.textContent)).toEqual([
            "new<section>", "enabled", "true", "preset", "rev-2"
        ]);
        expect(document.querySelector("[data-project-config-update-rows] section")).toBeNull();
        expect(document.querySelector("[data-project-config-update-apply]").disabled).toBe(false);
    });

    test("apply submits the exact preview and trigger then announces completion", async () => {
        await window.ProjectConfigUpdate.loadPreview();
        await window.ProjectConfigUpdate.apply();

        expect(requestWithSessionToken).toHaveBeenLastCalledWith("/apply", {
            method: "POST",
            json: {
                preview_id: "pcu1-a",
                trigger: { section: "new<section>", option: "enabled" }
            }
        });
        expect(request).toHaveBeenCalledWith("/rq-engine/api/jobstatus/job-1");
        expect(document.querySelector("[data-project-config-update-status]").textContent).toContain("complete");
    });

    test("stale preview error is actionable and clears reviewed state", async () => {
        await window.ProjectConfigUpdate.loadPreview();
        requestWithSessionToken.mockRejectedValueOnce({
            body: { error: { code: "stale_config_preview" } }
        });

        await window.ProjectConfigUpdate.apply();

        expect(document.querySelector("[data-project-config-update-error]").textContent).toContain("stale");
        expect(window.ProjectConfigUpdate.preview).toBeNull();
    });

    test("busy apply does not submit twice", async () => {
        await window.ProjectConfigUpdate.loadPreview();
        window.ProjectConfigUpdate.busy = true;
        await window.ProjectConfigUpdate.apply();
        expect(requestWithSessionToken.mock.calls.filter((call) => call[0] === "/apply")).toHaveLength(0);
    });
});
