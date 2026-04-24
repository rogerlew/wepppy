/**
 * @jest-environment jsdom
 */

const createControlBaseStub = require("./helpers/control_base_stub");

describe("Landuse controller", () => {
    let httpRequestMock;
    let httpPostJsonMock;
    let baseInstance;
    let statusStreamMock;
    let landuse;
    let unitizerClient;

    const flushPromises = () => Promise.resolve().then(() => Promise.resolve());

    beforeEach(async () => {
        jest.resetModules();
        document.body.innerHTML = `
            <form id="landuse_form">
                <div id="info"></div>
                <div id="status"></div>
                <div id="stacktrace"></div>
                <div id="rq_job"></div>
                <div id="landuse_mode0_controls"></div>
                <div id="landuse_mode1_controls" hidden></div>
                <div id="landuse_mode2_controls" hidden></div>
                <div id="landuse_mode3_controls" hidden></div>
                <div id="landuse_mode4_controls" hidden></div>
                <input type="radio" id="landuse_mode0" name="landuse_mode" value="0" data-landuse-role="mode" data-landuse-mode="0" checked>
                <input type="radio" id="landuse_mode1" name="landuse_mode" value="1" data-landuse-role="mode" data-landuse-mode="1">
                <select id="landuse_db" data-landuse-role="db">
                    <option value="nlcd">NLCD</option>
                </select>
                <select id="landuse_single_selection" data-landuse-role="single-selection">
                    <option value="101">Option 101</option>
                    <option value="202">Option 202</option>
                </select>
                <button type="button" id="btn_build_landuse" data-landuse-action="build">Build</button>
            </form>
            <div id="hint_build_landuse"></div>
        `;

        await import("../dom.js");

        global.WCForms = {
            serializeForm: jest.fn((form) => {
                const modeInput = form.querySelector('input[name="landuse_mode"]:checked');
                const singleSelect = form.querySelector("#landuse_single_selection");
                return {
                    landuse_mode: modeInput ? modeInput.value : null,
                    landuse_single_selection: singleSelect ? singleSelect.value : null,
                };
            }),
        };

        function createEmitter() {
            const listeners = {};
            return {
                on(event, handler) {
                    (listeners[event] = listeners[event] || []).push(handler);
                    return () => {
                        listeners[event] = (listeners[event] || []).filter((fn) => fn !== handler);
                    };
                },
                once(event, handler) {
                    const unsubscribe = this.on(event, (payload) => {
                        unsubscribe();
                        handler(payload);
                    });
                    return unsubscribe;
                },
                off(event, handler) {
                    if (!listeners[event]) {
                        return;
                    }
                    if (!handler) {
                        listeners[event] = [];
                        return;
                    }
                    listeners[event] = listeners[event].filter((fn) => fn !== handler);
                },
                emit(event, payload) {
                    const bucket = listeners[event] || [];
                    bucket.slice().forEach((fn) => fn(payload));
                    return bucket.length > 0;
                },
                listenerCount(event) {
                    if (event) {
                        return (listeners[event] || []).length;
                    }
                    return Object.values(listeners).reduce((total, bucket) => total + bucket.length, 0);
                },
            };
        }

        global.WCEvents = {
            createEmitter,
            useEventMap: jest.fn((events, emitter) => emitter),
        };

        unitizerClient = {
            updateNumericFields: jest.fn(),
        };

        global.UnitizerClient = {
            ready: jest.fn(() => Promise.resolve(unitizerClient)),
        };

        httpRequestMock = jest.fn((url) => {
            if (url === "/rq-engine/api/runs/test/cfg/build-landuse") {
                return Promise.resolve({ body: { job_id: "job-1" } });
            }
            if (url === "/rq-engine/api/runs/test/cfg/modify-landuse-mapping") {
                return Promise.resolve({ body: { job_id: "job-map-1" } });
            }
            if (url === "report/landuse/") {
                return Promise.resolve({ body: "<div>report</div>" });
            }
            return Promise.resolve({ body: {} });
        });

        httpPostJsonMock = jest.fn(() => Promise.resolve({ body: {} }));

        global.WCHttp = {
            request: httpRequestMock,
            requestWithSessionToken: httpRequestMock,
            postJson: httpPostJsonMock,
            postForm: jest.fn(),
            getJson: jest.fn(),
            isHttpError: jest.fn().mockReturnValue(false),
        };

        ({ base: baseInstance, statusStreamMock } = createControlBaseStub({
            pushResponseStacktrace: jest.fn(),
            pushErrorStacktrace: jest.fn(),
            set_rq_job_id: jest.fn(),
            triggerEvent: jest.fn(),
        }));
        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));
        const colorMapMock = { enableColorMap: jest.fn() };
        global.SubcatchmentDelineation = {
            getInstance: jest.fn(() => colorMapMock),
        };
        global.url_for_run = jest.fn((path, options) => {
            if (options && options.prefix) {
                return `${options.prefix}/runs/test/cfg/${path}`;
            }
            return path;
        });

        await import("../landuse.js");
        landuse = window.Landuse.getInstance();
    });

    afterEach(() => {
        jest.clearAllMocks();
        delete window.Landuse;
        delete global.WCHttp;
        delete global.WCForms;
        delete global.controlBase;
        delete global.SubcatchmentDelineation;
        delete global.url_for_run;
        delete global.WCEvents;
        delete global.UnitizerClient;
        delete global.Project;
        if (global.WCDom) {
            delete global.WCDom;
        }
        document.body.innerHTML = "";
    });

    test("build submits form data and records job id", async () => {
        const pollCompletionValues = [];
        baseInstance.set_rq_job_id.mockImplementationOnce((self) => {
            pollCompletionValues.push(self.poll_completion_event);
        });

        landuse.build();
        await flushPromises();

        expect(httpRequestMock).toHaveBeenCalledWith("/rq-engine/api/runs/test/cfg/build-landuse", expect.objectContaining({
            method: "POST",
        }));
        const requestOptions = httpRequestMock.mock.calls[0][1];
        expect(requestOptions.body).toBeInstanceOf(FormData);
        expect(baseInstance.connect_status_stream).toHaveBeenCalledWith(expect.any(Object));
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(landuse, "job-1");
        expect(pollCompletionValues).toEqual(["LANDUSE_BUILD_TASK_COMPLETED"]);
        expect(baseInstance.append_status_message).toHaveBeenCalledWith(
            expect.any(Object),
            expect.stringContaining("build_landuse job submitted")
        );
    });

    test("poll failure pushes stacktrace and emits job error", async () => {
        global.WCHttp.getJson.mockResolvedValueOnce({ exc_info: "trace line" });
        landuse.rq_job_id = "job-123";

        landuse.handle_job_status_response(landuse, { status: "failed" });
        await Promise.resolve();
        await Promise.resolve();
        await Promise.resolve();

        expect(global.WCHttp.getJson).toHaveBeenCalledWith("/rq-engine/api/jobinfo/job-123", { params: undefined });
        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalledWith(
            landuse,
            expect.objectContaining({
                error: expect.objectContaining({ message: expect.stringContaining("failed") }),
                stacktrace: expect.any(Array)
            })
        );
        const jobErrorCalls = baseInstance.triggerEvent.mock.calls.filter((call) => call[0] === "job:error");
        expect(jobErrorCalls).toHaveLength(1);
        expect(jobErrorCalls[0][1]).toEqual(expect.objectContaining({ job_id: "job-123", status: "failed", source: "poll" }));
    });

    test("modify_mapping enqueues rq job for async completion", async () => {
        jest.spyOn(landuse, "report").mockImplementation(() => {});

        landuse.modify_mapping("100", "200");
        await flushPromises();
        await flushPromises();

        expect(httpRequestMock).toHaveBeenCalledWith(
            "/rq-engine/api/runs/test/cfg/modify-landuse-mapping",
            expect.objectContaining({
                method: "POST",
                headers: expect.objectContaining({ "Content-Type": "application/json" }),
                form: expect.any(HTMLFormElement),
            })
        );
        const options = httpRequestMock.mock.calls.find((call) => call[0] === "/rq-engine/api/runs/test/cfg/modify-landuse-mapping")[1];
        expect(JSON.parse(options.body)).toEqual({ mappings: [{ dom: "100", newdom: "200" }] });
        expect(baseInstance.connect_status_stream).toHaveBeenCalledWith(expect.any(Object));
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(landuse, "job-map-1");
        expect(baseInstance.append_status_message).toHaveBeenCalledWith(
            landuse,
            expect.stringContaining("modify_landuse_mapping job submitted")
        );
        expect(landuse.poll_completion_event).toBe("LANDUSE_MODIFY_MAPPING_TASK_COMPLETED");
        expect(landuse.report).not.toHaveBeenCalled();
    });

    test("modify_mapping handles response error payload without refreshing report", async () => {
        jest.spyOn(landuse, "report").mockImplementation(() => {});
        httpRequestMock.mockResolvedValueOnce({ body: { error: { message: "Failed to modify landuse mapping" } } });

        landuse.modify_mapping("100", "200");
        await flushPromises();
        await flushPromises();

        expect(landuse.report).not.toHaveBeenCalled();
        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalledWith(
            landuse,
            { error: { message: "Failed to modify landuse mapping" } }
        );
        expect(baseInstance.disconnect_status_stream).toHaveBeenCalledWith(landuse);
    });

    test("mapping select delegate stages updates until submit", async () => {
        landuse.infoElement.innerHTML = `
            <div class="wc-landuse-report__controls">
                <button type="button" data-landuse-action="submit-mapping" disabled aria-disabled="true">Apply Mapping Edits</button>
                <span data-landuse-role="mapping-pending-status">No pending mapping edits.</span>
            </div>
            <table>
                <tbody>
                    <tr data-landuse-row="5">
                        <td>
                            <select data-landuse-role="mapping-select" data-landuse-dom="5">
                                <option value="alpha" selected>Alpha</option>
                                <option value="beta">Beta</option>
                            </select>
                        </td>
                    </tr>
                </tbody>
            </table>
        `;
        landuse.bindReportEvents();
        jest.spyOn(landuse, "report").mockImplementation(() => {});
        httpRequestMock.mockClear();

        const select = landuse.infoElement.querySelector("select");
        const submitButton = landuse.infoElement.querySelector("[data-landuse-action=\"submit-mapping\"]");
        const pendingStatus = landuse.infoElement.querySelector("[data-landuse-role=\"mapping-pending-status\"]");
        const row = landuse.infoElement.querySelector("[data-landuse-row=\"5\"]");

        select.value = "beta";
        select.dispatchEvent(new Event("change", { bubbles: true }));
        await flushPromises();
        await flushPromises();

        expect(httpRequestMock).not.toHaveBeenCalled();
        expect(submitButton.disabled).toBe(false);
        expect(submitButton.textContent).toContain("Apply 1 Mapping Edit");
        expect(pendingStatus.textContent).toContain("1 mapping edit staged.");
        expect(row.getAttribute("data-landuse-mapping-pending")).toBe("true");

        submitButton.dispatchEvent(new Event("click", { bubbles: true }));
        await flushPromises();
        await flushPromises();

        expect(httpRequestMock).toHaveBeenCalledWith(
            "/rq-engine/api/runs/test/cfg/modify-landuse-mapping",
            expect.objectContaining({
                method: "POST",
                headers: expect.objectContaining({ "Content-Type": "application/json" }),
            })
        );
        const requestOptions = httpRequestMock.mock.calls[0][1];
        expect(JSON.parse(requestOptions.body)).toEqual({ mappings: [{ dom: "5", newdom: "beta" }] });
    });

    test("staged multi-edit submit posts one batch request", async () => {
        landuse.infoElement.innerHTML = `
            <div class="wc-landuse-report__controls">
                <button type="button" data-landuse-action="submit-mapping" disabled aria-disabled="true">Apply Mapping Edits</button>
                <span data-landuse-role="mapping-pending-status">No pending mapping edits.</span>
            </div>
            <table>
                <tbody>
                    <tr data-landuse-row="44">
                        <td>
                            <select data-landuse-role="mapping-select" data-landuse-dom="44">
                                <option value="71" selected>Forest</option>
                                <option value="42">Range</option>
                            </select>
                        </td>
                    </tr>
                    <tr data-landuse-row="55">
                        <td>
                            <select data-landuse-role="mapping-select" data-landuse-dom="55">
                                <option value="91" selected>Urban</option>
                                <option value="11">Water</option>
                            </select>
                        </td>
                    </tr>
                </tbody>
            </table>
        `;
        landuse.bindReportEvents();
        httpRequestMock.mockClear();

        const selects = Array.from(landuse.infoElement.querySelectorAll("select"));
        const submitButton = landuse.infoElement.querySelector("[data-landuse-action=\"submit-mapping\"]");
        const pendingStatus = landuse.infoElement.querySelector("[data-landuse-role=\"mapping-pending-status\"]");

        selects[0].value = "42";
        selects[0].dispatchEvent(new Event("change", { bubbles: true }));
        selects[1].value = "11";
        selects[1].dispatchEvent(new Event("change", { bubbles: true }));
        await flushPromises();

        expect(httpRequestMock).not.toHaveBeenCalled();
        expect(submitButton.disabled).toBe(false);
        expect(submitButton.textContent).toContain("Apply 2 Mapping Edits");
        expect(pendingStatus.textContent).toContain("2 mapping edits staged.");

        submitButton.dispatchEvent(new Event("click", { bubbles: true }));
        await flushPromises();
        await flushPromises();

        expect(httpRequestMock).toHaveBeenCalledTimes(1);
        expect(httpRequestMock).toHaveBeenCalledWith(
            "/rq-engine/api/runs/test/cfg/modify-landuse-mapping",
            expect.objectContaining({
                method: "POST",
                headers: expect.objectContaining({ "Content-Type": "application/json" }),
            })
        );
        const requestOptions = httpRequestMock.mock.calls[0][1];
        expect(JSON.parse(requestOptions.body)).toEqual({
            mappings: [
                { dom: "44", newdom: "42" },
                { dom: "55", newdom: "11" },
            ],
        });
    });

    test("staged submit remains disabled in readonly mode", async () => {
        global.Project = {
            getInstance: jest.fn(() => ({ state: { readonly: true } })),
        };
        landuse.infoElement.innerHTML = `
            <div class="wc-landuse-report__controls">
                <button type="button" data-landuse-action="submit-mapping" disabled aria-disabled="true">Apply Mapping Edits</button>
                <span data-landuse-role="mapping-pending-status">No pending mapping edits.</span>
            </div>
            <table>
                <tbody>
                    <tr data-landuse-row="5">
                        <td>
                            <select data-landuse-role="mapping-select" data-landuse-dom="5">
                                <option value="alpha" selected>Alpha</option>
                                <option value="beta">Beta</option>
                            </select>
                        </td>
                    </tr>
                </tbody>
            </table>
        `;
        landuse.bindReportEvents();

        const select = landuse.infoElement.querySelector("select");
        const submitButton = landuse.infoElement.querySelector("[data-landuse-action=\"submit-mapping\"]");
        select.value = "beta";
        select.dispatchEvent(new Event("change", { bubbles: true }));
        await flushPromises();

        expect(submitButton.disabled).toBe(true);
        expect(submitButton.getAttribute("aria-disabled")).toBe("true");
    });

    test("mapping submit inflight disables selects and ignores additional staging", async () => {
        const deferred = () => {
            let resolve;
            let reject;
            const promise = new Promise((res, rej) => {
                resolve = res;
                reject = rej;
            });
            return { promise, resolve, reject };
        };

        const mappingRequest = deferred();
        httpRequestMock.mockImplementation((url) => {
            if (url === "/rq-engine/api/runs/test/cfg/modify-landuse-mapping") {
                return mappingRequest.promise;
            }
            if (url === "/rq-engine/api/runs/test/cfg/build-landuse") {
                return Promise.resolve({ body: { job_id: "job-1" } });
            }
            if (url === "report/landuse/") {
                return Promise.resolve({ body: "<div>report</div>" });
            }
            return Promise.resolve({ body: {} });
        });

        landuse.infoElement.innerHTML = `
            <div class="wc-landuse-report__controls">
                <button type="button" data-landuse-action="submit-mapping" disabled aria-disabled="true">Apply Mapping Edits</button>
                <span data-landuse-role="mapping-pending-status">No pending mapping edits.</span>
            </div>
            <table>
                <tbody>
                    <tr data-landuse-row="5">
                        <td>
                            <select data-landuse-role="mapping-select" data-landuse-dom="5">
                                <option value="alpha" selected>Alpha</option>
                                <option value="beta">Beta</option>
                            </select>
                        </td>
                    </tr>
                </tbody>
            </table>
        `;
        landuse.bindReportEvents();

        const select = landuse.infoElement.querySelector("select");
        const submitButton = landuse.infoElement.querySelector("[data-landuse-action=\"submit-mapping\"]");
        const pendingStatus = landuse.infoElement.querySelector("[data-landuse-role=\"mapping-pending-status\"]");

        select.value = "beta";
        select.dispatchEvent(new Event("change", { bubbles: true }));
        await flushPromises();
        await flushPromises();

        submitButton.dispatchEvent(new Event("click", { bubbles: true }));
        await flushPromises();
        await flushPromises();

        expect(httpRequestMock).toHaveBeenCalledTimes(1);
        expect(submitButton.disabled).toBe(true);
        expect(submitButton.textContent).toContain("Applying Mapping Edits...");
        expect(select.disabled).toBe(true);
        expect(pendingStatus.textContent).toContain("Submitting mapping edits...");

        select.value = "alpha";
        select.dispatchEvent(new Event("change", { bubbles: true }));
        await flushPromises();
        await flushPromises();

        expect(httpRequestMock).toHaveBeenCalledTimes(1);
        expect(submitButton.textContent).toContain("Applying Mapping Edits...");

        mappingRequest.resolve({ body: { job_id: "job-map-1" } });
        await flushPromises();
        await flushPromises();

        expect(select.disabled).toBe(false);
        expect(submitButton.disabled).toBe(true);
        expect(submitButton.textContent).toContain("Apply Mapping Edits");
        expect(pendingStatus.textContent).toContain("No pending mapping edits.");
    });

    test("toggle button expands details panel", () => {
        landuse.infoElement.innerHTML = `
            <button type="button" data-landuse-toggle="panel-1" aria-expanded="false">Toggle</button>
            <table><tr><td>
                <details id="panel-1"></details>
            </td></tr></table>
        `;
        landuse.bindReportEvents();
        const button = landuse.infoElement.querySelector("button");
        button.dispatchEvent(new Event("click", { bubbles: true }));

        const details = landuse.infoElement.querySelector("#panel-1");
        expect(details.open).toBe(true);
        expect(button.getAttribute("aria-expanded")).toBe("true");
    });

    test("network errors surface via pushResponseStacktrace", async () => {
        const error = new Error("boom");
        global.WCHttp.isHttpError.mockReturnValue(true);
        httpRequestMock.mockRejectedValueOnce(error);

        landuse.modify_mapping("10", "11");
        await flushPromises();
        await flushPromises();

        expect(baseInstance.pushResponseStacktrace).toHaveBeenCalledWith(landuse, { error: { message: "boom" } });
        expect(baseInstance.disconnect_status_stream).toHaveBeenCalledWith(landuse);
    });

    test("emits lifecycle events", async () => {
        const started = jest.fn();
        const completed = jest.fn();
        landuse.events.on("landuse:build:started", started);
        landuse.events.on("landuse:build:completed", completed);

        landuse.build();
        await Promise.resolve();
        landuse.triggerEvent("LANDUSE_BUILD_TASK_COMPLETED");

        expect(started).toHaveBeenCalled();
        expect(completed).toHaveBeenCalled();
    });

    test("completion trigger is idempotent", () => {
        const enableColorMap = global.SubcatchmentDelineation.getInstance().enableColorMap;
        jest.spyOn(landuse, "report").mockImplementation(() => {});

        landuse.triggerEvent("LANDUSE_BUILD_TASK_COMPLETED");
        landuse.triggerEvent("LANDUSE_BUILD_TASK_COMPLETED");

        expect(baseInstance.disconnect_status_stream).toHaveBeenCalledTimes(1);
        expect(enableColorMap).toHaveBeenCalledTimes(1);
        expect(landuse.report).toHaveBeenCalledTimes(1);
    });

    test("mapping completion trigger is idempotent", () => {
        jest.spyOn(landuse, "report").mockImplementation(() => {});

        landuse.triggerEvent("LANDUSE_MODIFY_MAPPING_TASK_COMPLETED");
        landuse.triggerEvent("LANDUSE_MODIFY_MAPPING_TASK_COMPLETED");

        expect(baseInstance.disconnect_status_stream).toHaveBeenCalledTimes(1);
        expect(landuse.report).toHaveBeenCalledTimes(1);
    });

    test("mapping completion ignores stale job trigger when newer mapping job is active", () => {
        jest.spyOn(landuse, "report").mockImplementation(() => {});
        landuse._mapping_job_id = "job-new";

        landuse.triggerEvent("LANDUSE_MODIFY_MAPPING_TASK_COMPLETED", {
            tokens: ["rq:job-old", "TRIGGER", "landuse", "LANDUSE_MODIFY_MAPPING_TASK_COMPLETED"]
        });

        expect(landuse.report).not.toHaveBeenCalled();

        landuse.triggerEvent("LANDUSE_MODIFY_MAPPING_TASK_COMPLETED", {
            tokens: ["rq:job-new", "TRIGGER", "landuse", "LANDUSE_MODIFY_MAPPING_TASK_COMPLETED"]
        });

        expect(landuse.report).toHaveBeenCalledTimes(1);
    });

    test("mapping completion handles poll payload job_id and ignores stale poll completion", () => {
        jest.spyOn(landuse, "report").mockImplementation(() => {});
        landuse._mapping_job_id = "job-new";

        landuse.triggerEvent("LANDUSE_MODIFY_MAPPING_TASK_COMPLETED", {
            job_id: "job-old",
            status: { status: "finished", job_id: "job-old" }
        });
        expect(landuse.report).not.toHaveBeenCalled();

        landuse.triggerEvent("LANDUSE_MODIFY_MAPPING_TASK_COMPLETED", {
            job_id: "job-new",
            status: { status: "finished", job_id: "job-new" }
        });
        expect(landuse.report).toHaveBeenCalledTimes(1);
    });

    test("mapping job failure refreshes report for the active mapping job", () => {
        jest.spyOn(landuse, "report").mockImplementation(() => {});
        landuse.poll_completion_event = "LANDUSE_MODIFY_MAPPING_TASK_COMPLETED";
        landuse._mapping_job_id = "job-map";

        landuse.triggerEvent("job:error", {
            job_id: "job-map",
            status: "failed",
            source: "poll"
        });

        expect(baseInstance.disconnect_status_stream).toHaveBeenCalledWith(landuse);
        expect(landuse.report).toHaveBeenCalledTimes(1);
    });

    test("mapping job failure ignores stale job ids when a newer mapping job is active", () => {
        jest.spyOn(landuse, "report").mockImplementation(() => {});
        landuse.poll_completion_event = "LANDUSE_MODIFY_MAPPING_TASK_COMPLETED";
        landuse._mapping_job_id = "job-new";

        landuse.triggerEvent("job:error", {
            job_id: "job-old",
            status: "failed",
            source: "poll"
        });

        expect(landuse.report).not.toHaveBeenCalled();
    });

    test("out-of-order mapping enqueue responses keep latest job id", async () => {
        const deferred = () => {
            let resolve;
            let reject;
            const promise = new Promise((res, rej) => {
                resolve = res;
                reject = rej;
            });
            return { promise, resolve, reject };
        };

        const first = deferred();
        const second = deferred();
        let mappingRequestCount = 0;
        httpRequestMock.mockImplementation((url) => {
            if (url === "/rq-engine/api/runs/test/cfg/modify-landuse-mapping") {
                mappingRequestCount += 1;
                return mappingRequestCount === 1 ? first.promise : second.promise;
            }
            if (url === "/rq-engine/api/runs/test/cfg/build-landuse") {
                return Promise.resolve({ body: { job_id: "job-1" } });
            }
            if (url === "report/landuse/") {
                return Promise.resolve({ body: "<div>report</div>" });
            }
            return Promise.resolve({ body: {} });
        });

        landuse.modify_mapping("44", "71");
        landuse.modify_mapping("44", "42");

        second.resolve({ body: { job_id: "job-new" } });
        await flushPromises();
        await flushPromises();

        first.resolve({ body: { job_id: "job-old" } });
        await flushPromises();
        await flushPromises();

        expect(landuse._mapping_job_id).toBe("job-new");
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(landuse, "job-new");
        expect(baseInstance.set_rq_job_id).not.toHaveBeenCalledWith(landuse, "job-old");
    });

    test("report emits event and updates unitizer", async () => {
        const listener = jest.fn();
        landuse.events.on("landuse:report:loaded", listener);

        landuse.report();
        await Promise.resolve();
        await Promise.resolve();

        expect(listener).toHaveBeenCalledWith({ html: "<div>report</div>" });
        expect(global.UnitizerClient.ready).toHaveBeenCalled();
        expect(unitizerClient.updateNumericFields).toHaveBeenCalledWith(expect.any(HTMLElement));
    });

    test("mode change delegate posts payload and emits event", async () => {
        const listener = jest.fn();
        landuse.events.on("landuse:mode:change", listener);

        const modeOne = document.getElementById("landuse_mode1");
        modeOne.checked = true;
        modeOne.dispatchEvent(new Event("change", { bubbles: true }));
        await Promise.resolve();

        expect(httpRequestMock).toHaveBeenCalledWith(
            "/rq-engine/api/runs/test/cfg/set-landuse-mode",
            expect.objectContaining({
                method: "POST",
                headers: expect.objectContaining({ "Content-Type": "application/json" }),
                form: expect.any(HTMLFormElement),
            })
        );
        const requestOptions = httpRequestMock.mock.calls.find(
            (call) => call[0] === "/rq-engine/api/runs/test/cfg/set-landuse-mode"
        )[1];
        expect(JSON.parse(requestOptions.body)).toEqual({ mode: 1, landuse_single_selection: "101" });
        expect(listener).toHaveBeenCalledWith(expect.objectContaining({ mode: 1 }));
    });

    test("bootstrap sets job id and triggers build completion", () => {
        const triggerSpy = jest.spyOn(landuse, "triggerEvent");
        landuse.report = jest.fn();

        landuse.bootstrap({
            jobIds: { build_landuse_rq: "job-abc" },
            data: { landuse: { hasLanduse: true, mode: 3, singleSelection: 202 } }
        });

        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(landuse, "job-abc");
        expect(triggerSpy).toHaveBeenCalledWith("LANDUSE_BUILD_TASK_COMPLETED");
    });

    test("bootstrap restores mapping job id when mapping update is active", () => {
        const triggerSpy = jest.spyOn(landuse, "triggerEvent");
        landuse.report = jest.fn();

        landuse.bootstrap({
            jobIds: { modify_landuse_mapping_rq: "job-map", build_landuse_rq: "job-abc" },
            data: { landuse: { hasLanduse: true, mode: 3, singleSelection: 202 } }
        });

        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(landuse, "job-map");
        expect(landuse.poll_completion_event).toBe("LANDUSE_MODIFY_MAPPING_TASK_COMPLETED");
        expect(landuse._mapping_job_id).toBe("job-map");
        expect(triggerSpy).not.toHaveBeenCalledWith("LANDUSE_BUILD_TASK_COMPLETED");
    });
});
