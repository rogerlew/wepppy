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
                <button id="path_ce_save" type="button" data-pathce-action="save-config"></button>
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
                        treatment_options: [
                            {
                                label: "Mulch",
                                scenario: "sbs_map",
                                quantity: 1,
                                unit_cost: 100,
                                fixed_cost: 200
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
            return Promise.resolve({ body: { Success: true, url: url } });
        });
    }

    function getController() {
        return window.PathCE.getInstance();
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

    test("saveConfig posts serialized payload and emits config saved", async () => {
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
        row.querySelector('[data-pathce-field="label"]').value = "Straw Mulch";
        row.querySelector('[data-pathce-field="scenario"]').value = "mulch_15_sbs_map";
        row.querySelector('[data-pathce-field="quantity"]').value = "3";
        row.querySelector('[data-pathce-field="unit_cost"]').value = "120";
        row.querySelector('[data-pathce-field="fixed_cost"]').value = "45";

        httpPostJson.mockImplementationOnce((url, payload) => {
            expect(url).toBe("api/path_ce/config");
            expect(payload.sddc_threshold).toBe(15);
            expect(payload.sdyd_threshold).toBe(5);
            expect(payload.slope_range).toEqual([2, 8]);
            expect(payload.severity_filter).toEqual(["Moderate"]);
            expect(payload.treatment_options).toEqual(
                expect.arrayContaining([
                    expect.objectContaining({
                        label: "Straw Mulch",
                        scenario: "mulch_15_sbs_map",
                        quantity: 3,
                        unit_cost: 120,
                        fixed_cost: 45
                    })
                ])
            );
            return Promise.resolve({ body: { Success: true, config: payload } });
        });

        await controller.saveConfig();

        expect(httpPostJson).toHaveBeenCalledWith(
            "api/path_ce/config",
            expect.any(Object),
            expect.objectContaining({ form: document.querySelector("#path_ce_form") })
        );
        expect(emitter.emit).toHaveBeenCalledWith(
            "pathce:config:saved",
            expect.objectContaining({ config: expect.any(Object) })
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
                    return Promise.resolve({ status: "idle", status_message: "", progress: 0 });
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
            return Promise.resolve({ body: { Success: true, job_id: "job-42" } });
        });

        const controller = getController();
        await Promise.resolve();
        await Promise.resolve();

        await controller.run();
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
        const hint = document.querySelector("#path_ce_hint");
        expect(hint.classList.contains("wc-field__help--error")).toBe(true);
    });
});
