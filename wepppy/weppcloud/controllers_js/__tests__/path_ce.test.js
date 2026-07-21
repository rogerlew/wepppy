/**
 * @jest-environment jsdom
 */

describe("PathCE controller", () => {
    let emitter;
    let httpGetJson;
    let httpPostJson;
    let baseInstance;

    beforeEach(async () => {
        jest.resetModules();
        document.body.innerHTML = `
            <form id="path_ce_form">
                <div id="info"></div>
                <small id="status"></small>
                <div id="path_ce_stacktrace"></div>
                <div id="path_ce_rq_job"></div>
                <span id="path_ce_braille"></span>
                <dl id="path_ce_summary"></dl>
                <p id="path_ce_message"></p>
                <p id="path_ce_hint"></p>
                <input id="path_ce_sddc_threshold" name="sddc_threshold" type="number">
                <input id="path_ce_sdyd_threshold" name="sdyd_threshold" type="number">
                <input id="path_ce_slope_min" name="slope_min" type="number">
                <input id="path_ce_slope_max" name="slope_max" type="number">
                <select id="path_ce_severity" name="severity_filter" multiple>
                    <option value="High">High</option>
                    <option value="Moderate">Moderate</option>
                    <option value="Low">Low</option>
                </select>
                <table id="path_ce_treatments_table">
                    <tbody></tbody>
                </table>
                <section id="path_ce_results_panel" hidden>
                    <div id="path_ce_links"></div>
                </section>
                <div id="path_ce_preconditions"></div>
                <button id="path_ce_run" type="button" data-pathce-action="run"></button>
                <button id="path_ce_add_treatment" type="button" data-pathce-action="add-treatment"></button>
            </form>
        `;

        await import("../dom.js");
        global.WCDom = window.WCDom;
        await import("../forms.js");
        global.WCForms = window.WCForms;

        emitter = {
            emit: jest.fn(),
            on: jest.fn(),
            once: jest.fn(),
            off: jest.fn()
        };

        global.WCEvents = {
            createEmitter: jest.fn(() => emitter),
            useEventMap: jest.fn((_, baseEmitter) => baseEmitter)
        };

        httpGetJson = jest.fn();
        httpPostJson = jest.fn();
        global.WCHttp = {
            getJson: httpGetJson,
            postJson: httpPostJson,
            isHttpError: jest.fn().mockReturnValue(false)
        };

        baseInstance = null;
        global.controlBase = jest.fn(() => {
            baseInstance = {
                pushErrorStacktrace: jest.fn(),
                pushResponseStacktrace: jest.fn(),
                set_rq_job_id: jest.fn(),
                triggerEvent: jest.fn(),
                job_status_poll_interval_ms: 0
            };
            return baseInstance;
        });

        jest.spyOn(window, "setInterval").mockImplementation(() => 1);
        jest.spyOn(window, "clearInterval").mockImplementation(() => {});

        global.url_for_run = jest.fn((path) => path);

        await import("../path_ce.js");
    });

    afterEach(() => {
        jest.clearAllMocks();
        if (window.setInterval.mockRestore) {
            window.setInterval.mockRestore();
        }
        if (window.clearInterval.mockRestore) {
            window.clearInterval.mockRestore();
        }
        delete window.PathCE;
        delete global.WCHttp;
        delete global.WCEvents;
        delete global.controlBase;
        if (global.WCForms) {
            delete global.WCForms;
        }
        if (global.WCDom) {
            delete global.WCDom;
        }
        delete global.url_for_run;
        document.body.innerHTML = "";
    });

    function primeHttpMocks() {
        httpGetJson.mockImplementation((url) => {
            if (url === "api/path_ce/config") {
                return Promise.resolve({
                    config: {
                        sddc_threshold: 10,
                        sdyd_threshold: 2,
                        slope_range: [1, 5],
                        severity_filter: ["High"],
                        treatments: [
                            {
                                label: "2 tons/acre",
                                scenario: "mulch_60_sbs_map",
                                quantity: 2,
                                unit_cost: 2475,
                                fixed_cost: 1500
                            }
                        ]
                    }
                });
            }
            if (url === "api/path_ce/status") {
                return Promise.resolve({ status: "idle", status_message: "", progress: 0 });
            }
            if (url === "api/path_ce/results") {
                return Promise.resolve({ results: {} });
            }
            throw new Error("Unexpected URL " + url);
        });
        httpPostJson.mockImplementation((url) => {
            return Promise.resolve({ body: { url: url } });
        });
    }

    function getController() {
        return window.PathCE.getInstance();
    }

    function flush() {
        return new Promise((resolve) => setTimeout(resolve, 0));
    }

    test("fetchConfig hydrates form and renders treatments", async () => {
        primeHttpMocks();
        const controller = getController();
        await Promise.resolve();
        await Promise.resolve();

        const sddcInput = document.querySelector("#path_ce_sddc_threshold");
        const severitySelect = document.querySelector("#path_ce_severity");
        const rows = document.querySelectorAll("#path_ce_treatments_table tbody tr");

        expect(sddcInput.value).toBe("10");
        expect(severitySelect.options[0].selected).toBe(true);
        expect(rows).toHaveLength(1);
        expect(emitter.emit).toHaveBeenCalledWith(
            "pathce:config:loaded",
            expect.objectContaining({ config: expect.any(Object) })
        );
        expect(baseInstance).not.toBeNull();
    });

    test("run posts the serialized form payload", async () => {
        primeHttpMocks();
        const controller = getController();
        await Promise.resolve();
        await Promise.resolve();

        document.querySelector("#path_ce_sddc_threshold").value = "15";
        document.querySelector("#path_ce_sdyd_threshold").value = "5";
        document.querySelector("#path_ce_slope_min").value = "2";
        document.querySelector("#path_ce_slope_max").value = "8";
        const severitySelect = document.querySelector("#path_ce_severity");
        severitySelect.options[0].selected = false;
        severitySelect.options[1].selected = true;

        document.querySelector("#path_ce_add_treatment").dispatchEvent(new Event("click", { bubbles: true }));
        const row = document.querySelector("#path_ce_treatments_table tbody tr:last-child");
        const scenarioSelect = row.querySelector('[data-pathce-field="scenario"]');
        scenarioSelect.value = "mulch_15_sbs_map";
        scenarioSelect.dispatchEvent(new Event("change", { bubbles: true }));
        // label/quantity are readonly and derived from the scenario; stale
        // values written directly must not survive the harvest
        row.querySelector('[data-pathce-field="label"]').value = "Straw Mulch";
        row.querySelector('[data-pathce-field="quantity"]').value = "3";
        row.querySelector('[data-pathce-field="unit_cost"]').value = "120";
        row.querySelector('[data-pathce-field="fixed_cost"]').value = "45";

        httpPostJson.mockImplementationOnce((url, payload) => {
            expect(url).toBe("tasks/path_cost_effective_run");
            expect(payload.sddc_threshold).toBe(15);
            expect(payload.sdyd_threshold).toBe(5);
            expect(payload.slope_range).toEqual([2, 8]);
            expect(payload.severity_filter).toEqual(["Moderate"]);
            expect(payload).not.toHaveProperty("render_reports");
            expect(payload.treatments).toEqual(
                expect.arrayContaining([
                    expect.objectContaining({
                        label: "0.5 tons/acre",
                        scenario: "mulch_15_sbs_map",
                        quantity: 0.5,
                        unit_cost: 120,
                        fixed_cost: 45
                    })
                ])
            );
            return Promise.resolve({ body: { job_id: "job-7" } });
        });

        await controller.run();

        expect(httpPostJson).toHaveBeenCalledWith(
            "tasks/path_cost_effective_run",
            expect.any(Object),
            expect.objectContaining({ form: document.querySelector("#path_ce_form") })
        );
        expect(emitter.emit).toHaveBeenCalledWith(
            "pathce:run:started",
            expect.objectContaining({ job_id: "job-7" })
        );
    });

    test("run enqueues job and emits lifecycle events", async () => {
        let statusCalls = 0;
        httpGetJson.mockImplementation((url) => {
            if (url === "api/path_ce/config") {
                return Promise.resolve({ config: {} });
            }
            if (url === "api/path_ce/status") {
                statusCalls += 1;
                if (statusCalls === 1) {
                    return Promise.resolve({ status: "completed", status_message: "Stale", progress: 1 });
                }
                return Promise.resolve({ status: "completed", status_message: "Done", progress: 1 });
            }
            if (url === "api/path_ce/results") {
                return Promise.resolve({ results: statusCalls >= 2 ? { status: "completed" } : {} });
            }
            throw new Error("Unexpected URL " + url);
        });
        httpPostJson.mockImplementationOnce((url) => {
            expect(url).toBe("tasks/path_cost_effective_run");
            return Promise.resolve({ body: { job_id: "job-42" } });
        });

        const stacktrace = document.querySelector("#path_ce_stacktrace");
        const status = document.querySelector("#status");
        stacktrace.textContent = "Old stacktrace";
        status.textContent = "Old status";

        const controller = getController();
        await Promise.resolve();
        await Promise.resolve();

        const runPromise = controller.run();
        expect(stacktrace.textContent).toBe("");
        expect(status.textContent).toBe("");
        await runPromise;
        await Promise.resolve();
        await Promise.resolve();

        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(expect.any(Object), "job-42");
        expect(emitter.emit).toHaveBeenCalledWith(
            "pathce:run:started",
            expect.objectContaining({ job_id: "job-42" })
        );
        expect(emitter.emit).toHaveBeenCalledWith(
            "job:started",
            expect.objectContaining({ job_id: "job-42" })
        );
        expect(httpGetJson).toHaveBeenCalledWith("api/path_ce/status", expect.any(Object));
        // Stale completed status should be ignored immediately after run
        const statusLog = document.querySelector("#status");
        expect(statusLog.textContent).toBe("");
    });

    test("fetchConfig failure records error hint and emits config error", async () => {
        httpGetJson.mockImplementation((url) => {
            if (url === "api/path_ce/config") {
                return Promise.reject(new Error("config-failure"));
            }
            if (url === "api/path_ce/status") {
                return Promise.resolve({ status: "idle", status_message: "", progress: 0 });
            }
            if (url === "api/path_ce/results") {
                return Promise.resolve({ results: {} });
            }
            throw new Error("Unexpected URL " + url);
        });

        getController();
        await Promise.resolve();
        await Promise.resolve();

        expect(baseInstance.pushErrorStacktrace).toHaveBeenCalled();
        expect(emitter.emit).toHaveBeenCalledWith(
            "pathce:config:error",
            expect.objectContaining({ error: expect.any(Error) })
        );
        const message = document.querySelector("#path_ce_message");
        expect(message.classList.contains("wc-field__help--error")).toBe(true);
    });

    test("results render report link and artifact downloads", async () => {
        httpGetJson.mockImplementation((url) => {
            if (url === "api/path_ce/config") {
                return Promise.resolve({ config: {} });
            }
            if (url === "api/path_ce/status") {
                return Promise.resolve({ status: "completed", status_message: "", progress: 1 });
            }
            if (url === "api/path_ce/results") {
                return Promise.resolve({
                    results: {
                        primary_status: 1,
                        total_cost: 513272.61,
                        report: { html: "path/report/PATH_CE_Report.html", skipped_reason: null },
                        artifacts: {
                            selection: "path/selection.parquet",
                            sweep: "path/sweep.parquet"
                        },
                        sweep: { n_cells: 6, n_errors: 0, reused: true }
                    }
                });
            }
            throw new Error("Unexpected URL " + url);
        });

        getController();
        await flush();
        await flush();

        const links = document.querySelectorAll("#path_ce_links a");
        const hrefs = Array.prototype.map.call(links, (a) => a.getAttribute("href"));
        expect(hrefs).toEqual(
            expect.arrayContaining([
                "report/path_ce/",
                "download/path/selection.parquet?as_csv=1",
                "download/path/sweep.parquet?as_csv=1"
            ])
        );
        // panel entries: styled link + description hint, panel unhidden
        expect(document.querySelector("#path_ce_results_panel").hidden).toBe(false);
        links.forEach((anchor) => {
            expect(anchor.className).toContain("wc-link");
            const hint = anchor.parentElement.querySelector("p.wc-field__help");
            expect(hint.textContent.length).toBeGreaterThan(0);
        });
        const linksText = document.querySelector("#path_ce_links").textContent;
        expect(linksText).toContain("cost surface");
        const summaryText = document.querySelector("#path_ce_summary").textContent;
        expect(summaryText).toContain("Optimal");
        expect(summaryText).toContain("513272.61");
    });

    test("results note skipped report with reason", async () => {
        httpGetJson.mockImplementation((url) => {
            if (url === "api/path_ce/config") {
                return Promise.resolve({ config: {} });
            }
            if (url === "api/path_ce/status") {
                return Promise.resolve({ status: "completed", status_message: "", progress: 1 });
            }
            if (url === "api/path_ce/results") {
                return Promise.resolve({
                    results: {
                        primary_status: 1,
                        report: { html: null, skipped_reason: "subcatchments.WGS.geojson not found" },
                        artifacts: {}
                    }
                });
            }
            throw new Error("Unexpected URL " + url);
        });

        getController();
        await flush();
        await flush();

        const linksText = document.querySelector("#path_ce_links").textContent;
        expect(linksText).toContain("subcatchments.WGS.geojson not found");
        expect(document.querySelectorAll("#path_ce_links a")).toHaveLength(0);
        // the skipped-report note keeps the panel visible
        expect(document.querySelector("#path_ce_results_panel").hidden).toBe(false);
    });

    test("summary renders Sddc values through the unitizer when present", async () => {
        httpGetJson.mockImplementation((url) => {
            if (url === "api/path_ce/config") {
                return Promise.resolve({ config: {} });
            }
            if (url === "api/path_ce/status") {
                return Promise.resolve({ status: "completed", status_message: "", progress: 1 });
            }
            if (url === "api/path_ce/results") {
                return Promise.resolve({
                    results: {
                        primary_status: 1,
                        total_sddc_reduction: 39.5,
                        final_sddc: 8.7,
                        artifacts: {}
                    }
                });
            }
            throw new Error("Unexpected URL " + url);
        });

        const renderValue = jest.fn((value, unit) => (
            `<div class="unitizer units-ton-yr">${value} converted ${unit}</div>`
        ));
        window.UnitizerClient = {
            ready: () => Promise.resolve({ renderValue })
        };
        try {
            getController();
            await flush();
            await flush();

            const unitized = document.querySelectorAll("#path_ce_summary [data-pathce-canonical]");
            expect(unitized).toHaveLength(2);
            expect(renderValue).toHaveBeenCalledWith("39.5", "tonne/yr", expect.objectContaining({ includeUnits: true }));
            expect(renderValue).toHaveBeenCalledWith("8.7", "tonne/yr", expect.objectContaining({ includeUnits: true }));
            expect(unitized[0].innerHTML).toContain("converted tonne/yr");
            // unit moved out of the term label and into the value blocks
            const summaryText = document.querySelector("#path_ce_summary").textContent;
            expect(summaryText).toContain("Total Sddc Reduction");
            expect(summaryText).not.toContain("Total Sddc Reduction (tonne/yr)");
        } finally {
            delete window.UnitizerClient;
        }
    });

    test("summary falls back to canonical tonne/yr text without the unitizer", async () => {
        httpGetJson.mockImplementation((url) => {
            if (url === "api/path_ce/config") {
                return Promise.resolve({ config: {} });
            }
            if (url === "api/path_ce/status") {
                return Promise.resolve({ status: "completed", status_message: "", progress: 1 });
            }
            if (url === "api/path_ce/results") {
                return Promise.resolve({
                    results: { primary_status: 1, total_sddc_reduction: 39.5, final_sddc: 8.7, artifacts: {} }
                });
            }
            throw new Error("Unexpected URL " + url);
        });

        getController();
        await flush();
        await flush();

        const unitized = document.querySelectorAll("#path_ce_summary [data-pathce-canonical]");
        expect(unitized).toHaveLength(2);
        expect(unitized[0].textContent).toBe("39.50 tonne/yr");
        expect(unitized[1].textContent).toBe("8.70 tonne/yr");
    });

    test("precondition failures render actionable messages", async () => {
        httpGetJson.mockImplementation((url) => {
            if (url === "api/path_ce/config") {
                return Promise.resolve({ config: {} });
            }
            if (url === "api/path_ce/status") {
                return Promise.resolve({
                    status: "failed",
                    status_message:
                        "Omni scenario summaries are missing treatment scenario(s) ['mulch_90_sbs_map'] — add them to Omni and run Omni scenarios.; Omni contrasts have no completed 'sbs_map'-control contrasts for treatment scenario(s) ['mulch_90_sbs_map'] — run Omni contrasts for each configured treatment.",
                    progress: 0
                });
            }
            if (url === "api/path_ce/results") {
                return Promise.resolve({ results: {} });
            }
            throw new Error("Unexpected URL " + url);
        });

        getController();
        await flush();
        await flush();

        const preconditions = document.querySelector("#path_ce_preconditions");
        expect(preconditions.classList.contains("wc-field__help--error")).toBe(true);
        const lines = preconditions.querySelectorAll("p");
        expect(lines).toHaveLength(2);
        expect(preconditions.textContent).toContain("run Omni scenarios");
        expect(preconditions.textContent).toContain("run Omni contrasts");
    });

    test("empty config renders default treatment rows", async () => {
        httpGetJson.mockImplementation((url) => {
            if (url === "api/path_ce/config") {
                return Promise.resolve({ config: {} });
            }
            if (url === "api/path_ce/status") {
                return Promise.resolve({ status: "idle", status_message: "", progress: 0 });
            }
            if (url === "api/path_ce/results") {
                return Promise.resolve({ results: {} });
            }
            throw new Error("Unexpected URL " + url);
        });

        getController();
        await Promise.resolve();
        await Promise.resolve();

        const rows = document.querySelectorAll("#path_ce_treatments_table tbody tr");
        expect(rows).toHaveLength(3);
        const firstScenario = rows[0].querySelector('[data-pathce-field="scenario"]');
        expect(firstScenario.tagName).toBe("SELECT");
        expect(firstScenario.value).toBe("mulch_15_sbs_map");
        const unitCostInput = rows[0].querySelector('[data-pathce-field="unit_cost"]');
        expect(unitCostInput.getAttribute("data-unitizer-unit")).toBe("$/acre");
        expect(unitCostInput.dataset.unitizerCanonicalValue).toBe("2475");
    });

    test("scenario select drives readonly label and rate", async () => {
        primeHttpMocks();
        getController();
        await flush();

        // config hydrates one mulch_60 row; a new row defaults to the first
        // unconfigured scenario with that tier's default costs
        document.querySelector("#path_ce_add_treatment").dispatchEvent(new Event("click", { bubbles: true }));
        const row = document.querySelector("#path_ce_treatments_table tbody tr:last-child");
        const scenarioSelect = row.querySelector('[data-pathce-field="scenario"]');
        const labelInput = row.querySelector('[data-pathce-field="label"]');
        const quantityInput = row.querySelector('[data-pathce-field="quantity"]');

        expect(scenarioSelect.tagName).toBe("SELECT");
        expect(scenarioSelect.value).toBe("mulch_15_sbs_map");
        expect(labelInput.readOnly).toBe(true);
        expect(quantityInput.readOnly).toBe(true);
        expect(labelInput.value).toBe("0.5 tons/acre");
        expect(quantityInput.value).toBe("0.5");
        expect(row.querySelector('[data-pathce-field="unit_cost"]').dataset.unitizerCanonicalValue).toBe("2475");
        expect(row.querySelector('[data-pathce-field="fixed_cost"]').value).toBe("500");

        scenarioSelect.value = "mulch_30_sbs_map";
        scenarioSelect.dispatchEvent(new Event("change", { bubbles: true }));

        expect(labelInput.value).toBe("1 tons/acre");
        expect(quantityInput.value).toBe("1");
    });

    test("run surfaces error_factory bodies as failures", async () => {
        primeHttpMocks();
        const controller = getController();
        await flush();

        httpPostJson.mockImplementationOnce(() => {
            return Promise.resolve({ body: { error: { message: "treatment label 'x' does not match scenario" } } });
        });

        await expect(controller.run()).rejects.toThrow("does not match scenario");
        const message = document.querySelector("#path_ce_message");
        expect(message.textContent).toContain("does not match scenario");
        expect(emitter.emit).toHaveBeenCalledWith(
            "pathce:run:error",
            expect.objectContaining({ error: expect.any(String) })
        );
    });

    test("run surfaces active-job rejection as error", async () => {
        primeHttpMocks();
        const controller = getController();
        await flush();

        httpPostJson.mockImplementationOnce(() => {
            return Promise.resolve({ body: { error: { message: "A PATH Cost-Effective run is already in progress (job live-1)." } } });
        });

        await expect(controller.run()).rejects.toThrow("already in progress");
        expect(emitter.emit).toHaveBeenCalledWith(
            "pathce:run:error",
            expect.objectContaining({ error: expect.stringContaining("already in progress") })
        );
        expect(baseInstance.set_rq_job_id).not.toHaveBeenCalledWith(expect.any(Object), expect.stringMatching(/live/));
    });

    test("structured precondition_errors render without prose parsing", async () => {
        httpGetJson.mockImplementation((url) => {
            if (url === "api/path_ce/config") {
                return Promise.resolve({ config: {} });
            }
            if (url === "api/path_ce/status") {
                return Promise.resolve({
                    status: "failed",
                    status_message: "boom",
                    progress: 0,
                    precondition_errors: [
                        "omni/contrasts.out.parquet is unreadable (ArrowInvalid) — regenerate it.",
                        "watershed/hillslopes.parquet not found — build the watershed before PATH-CE."
                    ]
                });
            }
            if (url === "api/path_ce/results") {
                return Promise.resolve({ results: {} });
            }
            throw new Error("Unexpected URL " + url);
        });

        getController();
        await flush();
        await flush();

        const preconditions = document.querySelector("#path_ce_preconditions");
        expect(preconditions.querySelectorAll("p")).toHaveLength(2);
        expect(preconditions.textContent).toContain("unreadable");
        expect(preconditions.textContent).toContain("build the watershed");
    });

    test("blank thresholds are omitted so server merge preserves them", async () => {
        primeHttpMocks();
        const controller = getController();
        await flush();

        document.querySelector("#path_ce_sddc_threshold").value = "";
        document.querySelector("#path_ce_sddc_threshold").dataset.unitizerCanonicalValue = "";
        document.querySelector("#path_ce_sdyd_threshold").value = "";

        httpPostJson.mockImplementationOnce((url, payload) => {
            expect(payload).not.toHaveProperty("sddc_threshold");
            expect(payload).not.toHaveProperty("sdyd_threshold");
            return Promise.resolve({ body: { job_id: "job-8" } });
        });

        await controller.run();
        expect(httpPostJson).toHaveBeenCalled();
    });

    test("bootstrap rehydrates job id from context", async () => {
        primeHttpMocks();
        const controller = getController();
        await Promise.resolve();
        await Promise.resolve();

        controller.bootstrap({ jobIds: { run_path_ce: "ce-job-1" } });

        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(expect.any(Object), "ce-job-1");
    });
});
