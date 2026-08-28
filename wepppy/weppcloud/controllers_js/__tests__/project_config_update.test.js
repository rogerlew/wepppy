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
            <p data-project-config-update-availability-error hidden></p>
          </div>
          <div id="projectConfigUpdateModal" hidden>
            <p data-project-config-update-error hidden tabindex="-1"></p>
            <p data-project-config-update-status tabindex="-1"></p>
            <div data-project-config-update-review hidden>
              <div data-project-config-update-additions><table><tbody data-project-config-update-rows></tbody></table></div>
              <div data-project-config-update-capability-changes hidden><table><tbody data-project-config-update-capability-rows></tbody></table></div>
              <div data-project-config-update-capability-details hidden><table><tbody data-project-config-update-capability-detail-rows></tbody></table></div>
              <div data-project-config-update-acknowledgment hidden>
                <label><input type="checkbox" data-project-config-update-acknowledgment-checkbox>Capability warning</label>
              </div>
            </div>
            <button data-project-config-update-refresh></button>
            <button data-project-config-update-apply disabled></button>
            <button data-modal-dismiss></button>
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
                    current_digest: "a".repeat(64),
                    resulting_digest: "b".repeat(64),
                    additions: [{
                        section: "new<section>", option: "enabled", value: "true",
                        source_id: "preset", source_revision: "rev-2"
                    }]
                } });
            }
            return Promise.resolve({ body: { job_id: "job-1" } });
        });
        request = jest.fn((url) => {
            if (url === "/rq-engine/api/jobstatus/job-1") {
                return Promise.resolve({ body: { status: "finished" } });
            }
            if (url === "/rq-engine/api/jobinfo/job-1") {
                return Promise.resolve({ body: { result: {
                    applied: true,
                    recovered: false,
                    sequence: 7,
                    prior_digest: "a".repeat(64),
                    resulting_digest: "b".repeat(64)
                } } });
            }
            return Promise.reject(new Error("unexpected request"));
        });
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
        expect(request).toHaveBeenCalledWith("/rq-engine/api/jobinfo/job-1");
        expect(document.querySelector("[data-project-config-update-status]").textContent).toContain("Sequence 7");
        expect(document.querySelector("[data-project-config-update-status]").textContent).toContain("Prior digest " + "a".repeat(64));
        expect(document.querySelector("[data-project-config-update-status]").textContent).toContain("Resulting digest " + "b".repeat(64));
        expect(document.querySelector("[data-project-config-update-status]").textContent).toContain("complete");
    });

    test("terminal recovered success reports the established project pair", async () => {
        await window.ProjectConfigUpdate.loadPreview();
        request.mockImplementation((url) => {
            if (url === "/rq-engine/api/jobstatus/job-recovered") {
                return Promise.resolve({ body: { status: "finished" } });
            }
            if (url === "/rq-engine/api/jobinfo/job-recovered") {
                return Promise.resolve({ body: { result: {
                    applied: true,
                    recovered: true,
                    sequence: 8,
                    prior_digest: "a".repeat(64),
                    resulting_digest: "b".repeat(64)
                } } });
            }
            return Promise.reject(new Error("unexpected request"));
        });
        requestWithSessionToken.mockImplementation((url) => {
            if (url === "/apply") {
                return Promise.resolve({ body: { job_id: "job-recovered" } });
            }
            if (url === "/preview") {
                return Promise.resolve({ body: {
                    preview_id: "pcu1-a",
                    current_digest: "a".repeat(64),
                    resulting_digest: "b".repeat(64),
                    additions: [{ section: "new", option: "enabled", value: "true" }]
                } });
            }
            return Promise.reject(new Error("unexpected request"));
        });

        await window.ProjectConfigUpdate.apply();

        const status = document.querySelector("[data-project-config-update-status]").textContent;
        expect(status).toContain("committed and was recovered");
        expect(status).toContain("Sequence 8");
        expect(status).toContain("Prior digest " + "a".repeat(64));
        expect(status).toContain("Resulting digest " + "b".repeat(64));
    });

    test("immediate recovered apply reports only the reviewed project pair", async () => {
        await window.ProjectConfigUpdate.loadPreview();
        requestWithSessionToken.mockImplementation((url) => {
            if (url === "/apply") {
                return Promise.resolve({ body: {
                    applied: true,
                    recovered: true,
                    sequence: 8,
                    prior_digest: "a".repeat(64),
                    resulting_digest: "b".repeat(64)
                } });
            }
            return Promise.reject(new Error("unexpected request"));
        });

        await window.ProjectConfigUpdate.apply();

        const status = document.querySelector("[data-project-config-update-status]").textContent;
        expect(status).toContain("already committed and recovered");
        expect(status).toContain("Sequence 8");
        expect(document.querySelector("[data-project-config-update-open]").hidden).toBe(true);
    });

    test("immediate recovered apply with a different pair is indeterminate", async () => {
        await window.ProjectConfigUpdate.loadPreview();
        requestWithSessionToken.mockImplementation((url) => {
            if (url === "/apply") {
                return Promise.resolve({ body: {
                    applied: true,
                    recovered: true,
                    sequence: 8,
                    prior_digest: "b".repeat(64),
                    resulting_digest: "c".repeat(64)
                } });
            }
            return Promise.reject(new Error("unexpected request"));
        });

        await window.ProjectConfigUpdate.apply();

        expect(document.querySelector("[data-project-config-update-status]").textContent).toContain("indeterminate");
        expect(document.querySelector("[data-project-config-update-open]").hidden).toBe(false);
    });

    test("terminal success with a mismatched digest pair is indeterminate", async () => {
        await window.ProjectConfigUpdate.loadPreview();
        document.querySelector("[data-project-config-update-acknowledgment-checkbox]").checked = true;
        request.mockImplementation((url) => {
            if (url === "/rq-engine/api/jobstatus/job-1") {
                return Promise.resolve({ body: { status: "finished" } });
            }
            if (url === "/rq-engine/api/jobinfo/job-1") {
                return Promise.resolve({ body: { result: {
                    applied: true,
                    recovered: false,
                    sequence: 7,
                    prior_digest: "b".repeat(64),
                    resulting_digest: "c".repeat(64)
                } } });
            }
            return Promise.reject(new Error("unexpected request"));
        });

        await window.ProjectConfigUpdate.apply();

        expect(document.querySelector("[data-project-config-update-status]").textContent).toContain("indeterminate");
        expect(document.querySelector("[data-project-config-update-open]").hidden).toBe(false);
        expect(document.querySelector("[data-project-config-update-acknowledgment-checkbox]").checked).toBe(true);
    });

    test("terminal success remains bound to the immutable apply-time preview", async () => {
        await window.ProjectConfigUpdate.loadPreview();
        let finishStatus;
        request.mockImplementation((url) => {
            if (url === "/rq-engine/api/jobstatus/job-1") {
                return new Promise((resolve) => { finishStatus = resolve; });
            }
            if (url === "/rq-engine/api/jobinfo/job-1") {
                return Promise.resolve({ body: { result: {
                    applied: true,
                    recovered: false,
                    sequence: 7,
                    prior_digest: "a".repeat(64),
                    resulting_digest: "b".repeat(64)
                } } });
            }
            return Promise.reject(new Error("unexpected request"));
        });
        requestWithSessionToken.mockImplementation((url) => {
            if (url === "/apply") {
                return Promise.resolve({ body: { job_id: "job-1" } });
            }
            if (url === "/preview") {
                return Promise.resolve({ body: {
                    preview_id: "pcu1-b",
                    current_digest: "c".repeat(64),
                    resulting_digest: "d".repeat(64),
                    additions: [{ section: "later", option: "enabled", value: "true" }]
                } });
            }
            return Promise.reject(new Error("unexpected request"));
        });

        const applyPromise = window.ProjectConfigUpdate.apply();
        await Promise.resolve();
        await Promise.resolve();
        await window.ProjectConfigUpdate.loadPreview();
        expect(window.ProjectConfigUpdate.preview.preview_id).toBe("pcu1-b");
        finishStatus({ body: { status: "finished" } });
        await applyPromise;

        const status = document.querySelector("[data-project-config-update-status]").textContent;
        expect(status).toContain("complete");
        expect(status).toContain("Prior digest " + "a".repeat(64));
        expect(status).toContain("Resulting digest " + "b".repeat(64));
    });

    test("terminal success with a malformed result is indeterminate", async () => {
        await window.ProjectConfigUpdate.loadPreview();
        request.mockImplementation((url) => {
            if (url === "/rq-engine/api/jobstatus/job-1") {
                return Promise.resolve({ body: { status: "finished" } });
            }
            if (url === "/rq-engine/api/jobinfo/job-1") {
                return Promise.resolve({ body: { result: { applied: true, recovered: false } } });
            }
            return Promise.reject(new Error("unexpected request"));
        });

        await window.ProjectConfigUpdate.apply();

        expect(document.querySelector("[data-project-config-update-status]").textContent).toContain("indeterminate");
        expect(document.querySelector("[data-project-config-update-open]").hidden).toBe(false);
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

    test("incompatible refresh shows diagnostic details and error ID safely", async () => {
        await window.ProjectConfigUpdate.loadPreview();
        const checkbox = document.querySelector("[data-project-config-update-acknowledgment-checkbox]");
        checkbox.checked = true;
        requestWithSessionToken.mockRejectedValueOnce({ body: {
            error: {
                code: "config_update_unavailable",
                details: "Removed stable IDs: corine-2018 <script>"
            },
            error_id: "error-409"
        } });

        await window.ProjectConfigUpdate.apply();

        const error = document.querySelector("[data-project-config-update-error]");
        expect(error.textContent).toContain("corine-2018 <script>");
        expect(error.textContent).toContain("error-409");
        expect(error.querySelector("script")).toBeNull();
        expect(checkbox.checked).toBe(false);
    });

    test("availability registry failure remains visible and diagnostic", async () => {
        const root = document.querySelector("[data-project-config-update]");
        const error = document.querySelector("[data-project-config-update-availability-error]");
        requestWithSessionToken.mockRejectedValueOnce({ body: {
            error: {
                code: "builder_registry_error",
                details: "profiles registry could not be read"
            },
            error_id: "error-503"
        } });

        await window.ProjectConfigUpdate.checkAvailability();

        expect(root.hidden).toBe(false);
        expect(error.hidden).toBe(false);
        expect(error.textContent).toContain("temporarily unavailable");
        expect(error.textContent).toContain("profiles registry could not be read");
        expect(error.textContent).toContain("error-503");
    });

    test("unavailable refresh details from read-only availability remain visible", async () => {
        const error = document.querySelector("[data-project-config-update-availability-error]");
        requestWithSessionToken.mockResolvedValueOnce({ body: {
            available: false,
            digest_warning: false,
            reason: "config_update_unavailable",
            details: "Builder refresh requires general.dem_db"
        } });

        await window.ProjectConfigUpdate.checkAvailability();

        expect(error.hidden).toBe(false);
        expect(error.textContent).toContain("general.dem_db");
    });

    test("busy apply does not submit twice", async () => {
        await window.ProjectConfigUpdate.loadPreview();
        window.ProjectConfigUpdate.busy = true;
        await window.ProjectConfigUpdate.apply();
        expect(requestWithSessionToken.mock.calls.filter((call) => call[0] === "/apply")).toHaveLength(0);
    });

    test("capability refresh stays disabled until exact warning is acknowledged", async () => {
        request.mockImplementation((url) => {
            if (url === "/rq-engine/api/jobstatus/job-refresh") {
                return Promise.resolve({ body: { status: "finished" } });
            }
            if (url === "/rq-engine/api/jobinfo/job-refresh") {
                return Promise.resolve({ body: { result: {
                    applied: true,
                    recovered: false,
                    sequence: 9,
                    prior_digest: "a".repeat(64),
                    resulting_digest: "c".repeat(64)
                } } });
            }
            return Promise.reject(new Error("unexpected request"));
        });
        requestWithSessionToken.mockImplementation((url) => {
            if (url === "/preview") {
                return Promise.resolve({ body: {
                    preview_id: "pcu1-refresh",
                    current_digest: "a".repeat(64),
                    resulting_digest: "c".repeat(64),
                    additions: [],
                    capability_refresh: {
                        acknowledgment: {
                            required: true,
                            revision: "PC-24-capability-refresh-v1",
                            text: "Capability warning"
                        },
                        locale_profile: "europe",
                        locales: ["eu"],
                        preserved_project_selections: {
                            capability_defaults: { climate_dataset: "vanilla_cligen" },
                            nodb: { mods: [] },
                            climate: { cligen_db: "ghcn_stations.db" }
                        },
                        prior: {
                            graph_sha256: "prior-graph",
                            structure_sha256: "prior-structure",
                            provider_revision: "prior-provider",
                            wepp_binary_revisions: { wepp_260803: "prior-binary" },
                            selected_parent_chain: [{ kind: "locale", id: "europe", revision: "prior-locale" }]
                        },
                        resulting: {
                            graph_sha256: "result-graph",
                            structure_sha256: "result-structure",
                            provider_revision: "result-provider",
                            wepp_binary_revisions: { wepp_260803: "result-binary" },
                            selected_parent_chain: [{ kind: "locale", id: "europe", revision: "result-locale" }]
                        },
                        changes: [{
                            section: "capabilities",
                            option: "provider_revision",
                            kind: "changed",
                            before: "old",
                            after: "new",
                            added_ids: [],
                            removed_ids: [],
                            added_support: []
                        }]
                    }
                } });
            }
            if (url === "/apply") {
                return Promise.resolve({ body: { job_id: "job-refresh" } });
            }
            return Promise.resolve({ body: { available: true } });
        });

        await window.ProjectConfigUpdate.loadPreview();
        const apply = document.querySelector("[data-project-config-update-apply]");
        const checkbox = document.querySelector("[data-project-config-update-acknowledgment-checkbox]");
        expect(apply.disabled).toBe(true);
        expect(document.querySelector("[data-project-config-update-capability-changes]").hidden).toBe(false);
        expect(document.querySelector("[data-project-config-update-capability-details]").hidden).toBe(false);
        expect(document.querySelector("[data-project-config-update-capability-detail-rows]").textContent).toContain("prior-locale");
        expect(document.querySelector("[data-project-config-update-capability-detail-rows]").textContent).toContain("result-locale");
        checkbox.checked = true;
        checkbox.dispatchEvent(new Event("change"));
        expect(apply.disabled).toBe(false);

        await window.ProjectConfigUpdate.apply();

        expect(requestWithSessionToken).toHaveBeenLastCalledWith("/apply", {
            method: "POST",
            json: {
                preview_id: "pcu1-refresh",
                capability_acknowledgment: {
                    accepted: true,
                    revision: "PC-24-capability-refresh-v1"
                }
            }
        });
        expect(checkbox.checked).toBe(false);
        expect(apply.disabled).toBe(true);
    });

    test("closing the modal clears capability acknowledgment", async () => {
        await window.ProjectConfigUpdate.loadPreview();
        const checkbox = document.querySelector("[data-project-config-update-acknowledgment-checkbox]");
        checkbox.checked = true;
        document.querySelector("[data-modal-dismiss]").click();
        expect(checkbox.checked).toBe(false);
    });

    test("Escape clears capability acknowledgment", async () => {
        await window.ProjectConfigUpdate.loadPreview();
        const checkbox = document.querySelector("[data-project-config-update-acknowledgment-checkbox]");
        checkbox.checked = true;
        document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
        expect(checkbox.checked).toBe(false);
    });

    test("terminal failure reconciles the complete project pair", async () => {
        await window.ProjectConfigUpdate.loadPreview();
        request.mockResolvedValueOnce({ body: { status: "failed" } });
        requestWithSessionToken.mockImplementation((url) => {
            if (url === "/apply") {
                return Promise.resolve({ body: { job_id: "job-failed" } });
            }
            if (url === "/availability") {
                return Promise.resolve({ body: {
                    current_digest: "a".repeat(64),
                    last_update: null
                } });
            }
            return Promise.reject(new Error("unexpected request"));
        });

        await window.ProjectConfigUpdate.apply();

        expect(requestWithSessionToken).toHaveBeenLastCalledWith("/availability", {});
        expect(document.querySelector("[data-project-config-update-status]").textContent).toContain("not applied");
        expect(document.querySelector("[data-project-config-update-error]").hidden).toBe(true);
    });

    test("terminal failure clears the generic error when reconciliation proves recovery", async () => {
        await window.ProjectConfigUpdate.loadPreview();
        request.mockResolvedValueOnce({ body: { status: "failed" } });
        requestWithSessionToken.mockImplementation((url) => {
            if (url === "/apply") {
                return Promise.resolve({ body: { job_id: "job-recovered" } });
            }
            if (url === "/availability") {
                return Promise.resolve({ body: {
                    current_digest: "b".repeat(64),
                    last_update: { preview_id: "pcu1-a" }
                } });
            }
            return Promise.reject(new Error("unexpected request"));
        });

        await window.ProjectConfigUpdate.apply();

        expect(document.querySelector("[data-project-config-update-status]").textContent).toContain("committed and was recovered");
        expect(document.querySelector("[data-project-config-update-error]").hidden).toBe(true);
        expect(document.querySelector("[data-project-config-update-open]").hidden).toBe(true);
    });
});
