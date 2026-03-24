/**
 * @jest-environment jsdom
 */

const createControlBaseStub = require("./helpers/control_base_stub");

class FakeXMLHttpRequest {
    constructor() {
        this.headers = {};
        this.listeners = {};
        this.uploadListeners = {};
        this.upload = {
            addEventListener: (eventName, handler) => {
                this.uploadListeners[eventName] = handler;
            }
        };
        FakeXMLHttpRequest.instances.push(this);
    }

    open(method, url) {
        this.method = method;
        this.url = url;
    }

    setRequestHeader(name, value) {
        this.headers[name] = value;
    }

    addEventListener(eventName, handler) {
        this.listeners[eventName] = handler;
    }

    send(body) {
        this.body = body;
    }

    triggerUploadProgress(loaded, total) {
        if (!this.uploadListeners.progress) {
            return;
        }
        this.uploadListeners.progress({
            lengthComputable: true,
            loaded: loaded,
            total: total
        });
    }

    triggerLoad(status, payload) {
        this.status = status;
        this.responseText = JSON.stringify(payload || {});
        if (this.listeners.load) {
            this.listeners.load();
        }
    }

    triggerError() {
        if (this.listeners.error) {
            this.listeners.error();
        }
    }
}

FakeXMLHttpRequest.instances = [];

describe("Roads controller", () => {
    let baseInstance;
    let roads;
    let httpMock;
    let originalXmlHttpRequest;

    beforeEach(async () => {
        jest.resetModules();
        FakeXMLHttpRequest.instances = [];

        document.body.innerHTML = `
            <form id="roads_form" data-roads-max-upload-mb="50">
                <input id="roads_geojson_file" name="file" type="file">
                <div id="roads_geojson_file-progress" hidden>
                    <div class="wc-upload-progress__fill" style="width: 0%"></div>
                    <p class="wc-upload-progress__status">Uploading: 0%</p>
                </div>
                <p id="roads_upload_message"></p>
                <div id="roads_info"></div>
                <div id="roads_status"></div>
                <div id="roads_stacktrace" style="display:none;"></div>
                <div id="rq_job"></div>
                <button id="roads_upload_geojson" type="button" data-roads-action="upload">Upload</button>
                <button id="roads_prepare_segments" type="button" data-roads-action="prepare-segments">Prepare</button>
                <button id="run_roads_wepp" type="button" data-roads-action="run">Run</button>
            </form>
            <p id="hint_run_roads"></p>
            <section id="roads_status_panel"><span id="braille"></span><div data-status-log></div></section>
            <section id="roads_stacktrace_panel"><div data-stacktrace-body></div></section>
        `;

        await import("../dom.js");
        await import("../events.js");

        httpMock = {
            request: jest.fn(() => Promise.resolve({ body: { job_id: "roads-job-1" } })),
            getJson: jest.fn(() => Promise.resolve({ body: {} })),
            isHttpError: jest.fn(() => false),
            getCsrfToken: jest.fn(() => "csrf-token")
        };
        global.WCHttp = httpMock;
        global.WCForms = {
            serializeForm: jest.fn(() => ({}))
        };
        global.url_for_run = jest.fn((path) => "/runs/test-run/test-config/" + path.replace(/^\/+/, ""));

        ({ base: baseInstance } = createControlBaseStub({
            pushResponseStacktrace: jest.fn(),
            set_rq_job_id: jest.fn(),
            triggerEvent: jest.fn(),
            disconnect_status_stream: jest.fn(),
            append_status_message: jest.fn(),
            reset_panel_state: jest.fn()
        }));
        global.controlBase = jest.fn(() => Object.assign({}, baseInstance));

        originalXmlHttpRequest = global.XMLHttpRequest;
        global.XMLHttpRequest = FakeXMLHttpRequest;

        await import("../roads.js");
        roads = window.Roads.getInstance();
    });

    afterEach(() => {
        delete global.WCHttp;
        delete global.WCForms;
        delete global.url_for_run;
        delete global.controlBase;
        delete window.Roads;
        delete window.WCDom;
        delete window.WCEvents;
        global.XMLHttpRequest = originalXmlHttpRequest;
        document.body.innerHTML = "";
        jest.clearAllMocks();
    });

    test("upload action validates missing file before posting", async () => {
        await roads.uploadGeojson();

        expect(FakeXMLHttpRequest.instances).toHaveLength(0);
        expect(document.getElementById("roads_upload_message").textContent).toContain("Select a .geojson file");
    });

    test("upload action posts geojson with progress UI", async () => {
        const file = new File(['{"type":"FeatureCollection","features":[]}'], "roads.geojson", {
            type: "application/geo+json"
        });
        const input = document.getElementById("roads_geojson_file");
        Object.defineProperty(input, "files", {
            configurable: true,
            value: [file]
        });

        const uploadPromise = roads.uploadGeojson();
        expect(FakeXMLHttpRequest.instances).toHaveLength(1);

        const xhr = FakeXMLHttpRequest.instances[0];
        expect(xhr.method).toBe("POST");
        expect(xhr.url).toBe("/runs/test-run/test-config/tasks/roads/upload_geojson");
        expect(xhr.headers["X-CSRFToken"]).toBe("csrf-token");

        xhr.triggerUploadProgress(5, 10);
        expect(document.querySelector(".wc-upload-progress__fill").style.width).toBe("50%");

        xhr.triggerLoad(200, {
            Content: {
                uploaded_geojson_relpath: "roads/roads.uploaded.geojson",
                feature_count: 7
            }
        });
        await uploadPromise;

        expect(document.getElementById("roads_upload_message").textContent).toContain("uploaded successfully");
        expect(document.querySelector(".wc-upload-progress__fill").style.width).toBe("100%");
        expect(document.getElementById("roads_info").innerHTML).toContain("roads.uploaded.geojson");
    });

    test("prepare and run actions enqueue roads jobs with matching completion events", async () => {
        const pollEvents = [];
        baseInstance.set_rq_job_id.mockImplementation((self, jobId) => {
            self.rq_job_id = jobId || null;
            if (jobId) {
                pollEvents.push(self.poll_completion_event);
            }
        });

        await roads.prepareSegments();
        await Promise.resolve();
        roads.triggerEvent("ROADS_PREPARE_TASK_COMPLETED", { source: "test", job_id: "roads-job-1" });
        await roads.runRoads();
        await Promise.resolve();
        roads.triggerEvent("ROADS_RUN_TASK_COMPLETED", { source: "test", job_id: "roads-job-1" });

        expect(httpMock.request).toHaveBeenNthCalledWith(
            1,
            "/runs/test-run/test-config/tasks/roads/prepare_segments",
            expect.objectContaining({ method: "POST", form: expect.any(HTMLFormElement) })
        );
        expect(httpMock.request).toHaveBeenNthCalledWith(
            2,
            "/runs/test-run/test-config/tasks/roads/run",
            expect.objectContaining({ method: "POST", form: expect.any(HTMLFormElement) })
        );
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(roads, "roads-job-1");
        expect(pollEvents).toEqual(["ROADS_PREPARE_TASK_COMPLETED", "ROADS_RUN_TASK_COMPLETED"]);
    });

    test("roads run completion is idempotent", async () => {
        await roads.runRoads();
        await Promise.resolve();

        roads.triggerEvent("ROADS_RUN_TASK_COMPLETED", { source: "test", job_id: "roads-job-1" });
        roads.triggerEvent("ROADS_RUN_TASK_COMPLETED", { source: "test", job_id: "roads-job-1" });

        expect(baseInstance.disconnect_status_stream).toHaveBeenCalledTimes(1);
        expect(document.getElementById("roads_info").innerHTML).toContain("report/roads/summary");
    });

    test("queueTask blocks concurrent roads task submissions", async () => {
        await roads.prepareSegments();
        await Promise.resolve();

        await roads.runRoads();
        await Promise.resolve();

        expect(httpMock.request).toHaveBeenCalledTimes(1);
        expect(baseInstance.triggerEvent).toHaveBeenCalledWith(
            "job:error",
            expect.objectContaining({ task: "roads:run" })
        );
    });

    test("completion events must match active job id", async () => {
        await roads.runRoads();
        await Promise.resolve();

        roads.triggerEvent("ROADS_RUN_TASK_COMPLETED", { source: "poll", job_id: "stale-job-id" });
        expect(baseInstance.disconnect_status_stream).not.toHaveBeenCalled();

        roads.triggerEvent("ROADS_RUN_TASK_COMPLETED", { source: "poll", job_id: "roads-job-1" });
        expect(baseInstance.disconnect_status_stream).toHaveBeenCalledTimes(1);
    });
});
