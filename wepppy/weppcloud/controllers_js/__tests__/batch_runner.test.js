/**
 * @jest-environment jsdom
 */

const TestFile = typeof File === "undefined"
    ? class TestFile extends Blob {
          constructor(chunks, name, options) {
              super(chunks, options);
              this.name = name;
          }
      }
    : File;

describe("BatchRunner controller", () => {
    let controller;
    let requestMock;
    let postJsonMock;
    let delegateTeardowns;
    let wsClientMock;

    function flushPromises() {
        return Promise.resolve().then(() => Promise.resolve());
    }

    function resolveTarget(target) {
        if (!target) {
            return null;
        }
        if (target instanceof Element) {
            return target;
        }
        if (typeof target === "string") {
            return document.querySelector(target);
        }
        return null;
    }

    beforeEach(async () => {
        jest.resetModules();

        document.body.innerHTML = `
            <form id="batch_runner_form">
                <div id="status"></div>
                <div id="stacktrace"></div>
                <div id="info"></div>
                <div id="rq_job"></div>
            </form>
            <div id="batch-runner-root">
                <section id="batch-runner-resource-card">
                    <div data-role="upload-form">
                        <input type="file" data-role="geojson-input">
                        <button type="button" data-role="upload-button" data-action="batch-upload">Upload GeoJSON</button>
                    </div>
                    <div data-role="upload-status"></div>
                    <div data-role="resource-empty"></div>
                    <div data-role="resource-details" hidden>
                        <dl data-role="resource-meta"></dl>
                    </div>
                    <div data-role="resource-schema" hidden>
                        <tbody data-role="resource-schema-body"></tbody>
                    </div>
                    <div data-role="resource-samples" hidden>
                        <tbody data-role="resource-samples-body"></tbody>
                    </div>
                </section>
                <section id="batch-runner-template-card">
                    <textarea data-role="template-input"></textarea>
                    <button type="button" data-role="validate-button" data-action="batch-validate">Validate Template</button>
                    <div data-role="template-status"></div>
                    <div data-role="validation-summary" hidden>
                        <ul data-role="validation-summary-list"></ul>
                    </div>
                    <div data-role="validation-issues" hidden>
                        <div data-role="validation-issues-list"></div>
                    </div>
                    <div data-role="validation-preview" hidden>
                        <tbody data-role="preview-body"></tbody>
                    </div>
                </section>
                <div data-role="run-directive-list"></div>
                <div data-role="run-directive-status"></div>
            </div>
            <div class="form-group" id="batch_runner_run_container">
                <button id="btn_run_batch" data-action="batch-run" type="button">Run Batch</button>
                <small id="hint_run_batch"></small>
                <img id="run_batch_lock" style="display:none;">
            </div>
        `;

        global.site_prefix = "";

        delegateTeardowns = [];

        global.WCDom = {
            qs: jest.fn((selector, context) => {
                if (context && context.querySelector) {
                    return context.querySelector(selector);
                }
                return document.querySelector(selector);
            }),
            show: jest.fn((target) => {
                var element = resolveTarget(target);
                if (!element) {
                    return;
                }
                element.hidden = false;
                element.style.display = "";
            }),
            hide: jest.fn((target) => {
                var element = resolveTarget(target);
                if (!element) {
                    return;
                }
                element.hidden = true;
                element.style.display = "none";
            }),
            toggle: jest.fn((target, force) => {
                var element = resolveTarget(target);
                if (!element) {
                    return;
                }
                var shouldShow = typeof force === "boolean" ? force : element.hidden || element.style.display === "none";
                if (shouldShow) {
                    global.WCDom.show(element);
                } else {
                    global.WCDom.hide(element);
                }
            }),
            delegate: jest.fn((root, eventName, selector, handler) => {
                var element;
                if (root && root.addEventListener) {
                    element = root;
                } else if (typeof root === "string") {
                    element = document.querySelector(root);
                } else {
                    element = document;
                }
                if (!element) {
                    throw new Error("Delegate root not found for selector: " + selector);
                }
                var listener = function (event) {
                    var matched = event.target && event.target.closest(selector);
                    if (matched && element.contains(matched)) {
                        handler.call(matched, event, matched);
                    }
                };
                element.addEventListener(eventName, listener);
                var unsubscribe = function () {
                    element.removeEventListener(eventName, listener);
                };
                delegateTeardowns.push(unsubscribe);
                return unsubscribe;
            })
        };

        global.WCForms = {
            serializeForm: jest.fn(() => new URLSearchParams())
        };

        requestMock = jest.fn(() => Promise.resolve({ body: { success: true } }));
        postJsonMock = jest.fn(() => Promise.resolve({ body: { success: true } }));

        global.WCHttp = {
            request: requestMock,
            postJson: postJsonMock,
            isHttpError: jest.fn((error) => Boolean(error && error.name === "HttpError"))
        };

        wsClientMock = {
            attachControl: jest.fn(),
            connect: jest.fn(),
            disconnect: jest.fn(),
            resetSpinner: jest.fn()
        };

        global.WSClient = jest.fn(() => wsClientMock);

        global.controlBase = jest.fn(() => ({
            command_btn_id: null,
            render_job_status: jest.fn(),
            update_command_button_state: jest.fn(),
            should_disable_command_button: jest.fn(() => false),
            set_rq_job_id: function (self, jobId) {
                this.rq_job_id = jobId;
            },
            handle_job_status_response: jest.fn(),
            triggerEvent: jest.fn(),
            pushResponseStacktrace: jest.fn(),
            stacktrace: { show: jest.fn(), text: jest.fn() }
        }));

        await import("../events.js");
        await import("../batch_runner.js");
        controller = window.BatchRunner.getInstance();
        controller.init({
            enabled: true,
            batchName: "demo",
            geojsonLimitMb: 16,
            state: {
                run_directives: [
                    { slug: "fetch_dem", label: "Fetch DEM", enabled: true },
                    { slug: "build_channels", label: "Build Channels", enabled: false }
                ],
                metadata: {},
                resources: {}
            }
        });
    });

    afterEach(() => {
        delegateTeardowns.forEach((fn) => fn());
        jest.clearAllMocks();

        delete window.BatchRunner;
        delete global.WCDom;
        delete global.WCForms;
        delete global.WCHttp;
        delete global.WSClient;
        delete global.controlBase;
        delete global.site_prefix;

        document.body.innerHTML = "";
    });

    test("init disables run button until prerequisites satisfied", () => {
        expect(controller.runBatchButton.disabled).toBe(true);
        expect(document.getElementById("hint_run_batch").textContent).toContain("Upload a watershed");
    });

    test("uploadGeojson posts FormData and emits completion event", async () => {
        const file = new TestFile([JSON.stringify({ type: "FeatureCollection", features: [] })], "demo.geojson", {
            type: "application/geo+json"
        });
        Object.defineProperty(controller.uploadInput, "files", {
            value: [file],
            writable: false
        });

        requestMock.mockResolvedValueOnce({
            body: {
                success: true,
                snapshot: {
                    resources: {
                        watershed_geojson: {
                            filename: "demo.geojson",
                            feature_count: 2
                        }
                    },
                    metadata: {
                        template_validation: {
                            status: "ok",
                            summary: { is_valid: true }
                        }
                    }
                }
            }
        });

        const completed = jest.fn();
        controller.emitter.on("batch:upload:completed", completed);

        controller.uploadButton.dispatchEvent(new Event("click", { bubbles: true }));
        await flushPromises();

        expect(requestMock).toHaveBeenCalledWith("/batch/_/demo/upload-geojson", expect.objectContaining({
            method: "POST",
            body: expect.any(FormData)
        }));
        expect(completed).toHaveBeenCalled();
        expect(controller.resourceDetails.hidden).toBe(false);
        expect(controller.runBatchButton.disabled).toBe(false);
    });

    test("uploadGeojson emits failure event when request rejects", async () => {
        const file = new TestFile(["{}"], "demo.geojson", { type: "application/json" });
        Object.defineProperty(controller.uploadInput, "files", {
            value: [file],
            writable: false
        });

        requestMock.mockRejectedValueOnce(new Error("Upload failed."));

        const failed = jest.fn();
        controller.emitter.on("batch:upload:failed", failed);

        controller.uploadButton.dispatchEvent(new Event("click", { bubbles: true }));
        await flushPromises();

        expect(failed).toHaveBeenCalledWith(expect.objectContaining({ error: "Upload failed." }));
        expect(controller.uploadStatus.textContent).toBe("Upload failed.");
    });

    test("validateTemplate updates validation state and emits completion", async () => {
        controller.templateInput.value = "{slug(properties['Name'])}";

        postJsonMock.mockResolvedValueOnce({
            body: {
                validation: {
                    status: "ok",
                    summary: { is_valid: true, feature_count: 2, unique_runids: 2 },
                    errors: [],
                    preview: []
                },
                stored: {
                    status: "ok"
                },
                snapshot: {
                    metadata: {
                        template_validation: {
                            status: "ok",
                            summary: { is_valid: true }
                        }
                    }
                }
            }
        });

        const completed = jest.fn();
        controller.emitter.on("batch:template:validate-completed", completed);

        controller.validateButton.dispatchEvent(new Event("click", { bubbles: true }));
        await flushPromises();

        expect(postJsonMock).toHaveBeenCalledWith("/batch/_/demo/validate-template", {
            template: "{slug(properties['Name'])}"
        });
        expect(completed).toHaveBeenCalled();
        expect(controller.state.validation).not.toBeNull();
    });

    test("toggle run directive posts selection", async () => {
        postJsonMock.mockResolvedValueOnce({
            body: {
                success: true,
                run_directives: [
                    { slug: "fetch_dem", label: "Fetch DEM", enabled: true },
                    { slug: "build_channels", label: "Build Channels", enabled: true }
                ],
                snapshot: {
                    run_directives: [
                        { slug: "fetch_dem", label: "Fetch DEM", enabled: true },
                        { slug: "build_channels", label: "Build Channels", enabled: true }
                    ],
                    metadata: {},
                    resources: {}
                }
            }
        });

        const directive = controller.runDirectiveList.querySelector('input[data-run-directive="build_channels"]');
        directive.checked = true;
        directive.dispatchEvent(new Event("change", { bubbles: true }));

        await flushPromises();

        expect(postJsonMock).toHaveBeenCalledWith("/batch/_/demo/run-directives", {
            run_directives: {
                fetch_dem: true,
                build_channels: true
            }
        });
    });

    test("runBatch posts to RQ endpoint and emits start event", async () => {
        postJsonMock.mockResolvedValueOnce({
            body: {
                success: true,
                job_id: "job-42",
                message: "Batch run submitted."
            }
        });

        const started = jest.fn();
        controller.emitter.on("batch:run:started", started);

        controller.runBatchButton.disabled = false;
        controller.runBatchButton.dispatchEvent(new Event("click", { bubbles: true }));
        await flushPromises();

        expect(postJsonMock).toHaveBeenCalledWith("/batch/_/demo/rq/api/run-batch", {});
        expect(started).toHaveBeenCalledWith(expect.objectContaining({ jobId: "job-42" }));
        expect(wsClientMock.connect).toHaveBeenCalled();
    });

    test("refreshJobInfo posts job info request when forced", async () => {
        controller.rq_job_id = "job-10";
        postJsonMock.mockResolvedValueOnce({ body: { jobs: [] } });

        controller.refreshJobInfo({ force: true });
        await flushPromises();

        expect(postJsonMock).toHaveBeenCalledWith(
            "/weppcloud/rq/api/jobinfo",
            { job_ids: ["job-10"] },
            expect.objectContaining({ signal: expect.any(Object) })
        );
    });
});
