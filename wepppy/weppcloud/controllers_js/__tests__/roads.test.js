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
    let roadsTaskStatus;

    beforeEach(async () => {
        jest.resetModules();
        FakeXMLHttpRequest.instances = [];
        roadsTaskStatus = "running";

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
                <fieldset id="roads_attribute_mapping_section">
                    <div id="roads_attribute_catalog_preview"></div>
                    <select id="roads_design_field" data-roads-map-field="design"></select>
                    <select id="roads_surface_field" data-roads-map-field="surface"></select>
                    <select id="roads_surface_default" data-roads-default-field="surface_default"></select>
                    <select id="roads_traffic_field" data-roads-map-field="traffic"></select>
                    <select id="roads_traffic_default" data-roads-default-field="traffic_default"></select>
                    <button id="roads_apply_mapping" type="button" data-roads-action="apply-attribute-mapping">Apply</button>
                    <p id="roads_mapping_message"></p>
                </fieldset>
                <button id="roads_prepare_segments" type="button" data-roads-action="prepare-segments">Prepare</button>
                <button id="run_roads_wepp" type="button" data-roads-action="run">Run</button>
            </form>
            <div id="roads-results"></div>
            <p id="hint_run_roads"></p>
            <section id="roads_status_panel"><span id="braille"></span><div data-status-log></div></section>
            <section id="roads_stacktrace_panel"><div data-stacktrace-body></div></section>
        `;

        await import("../dom.js");
        await import("../events.js");

        httpMock = {
            request: jest.fn((path, options) => {
                if (!options && path === "/runs/test-run/test-config/report/roads/results/") {
                    return Promise.resolve({ body: "<div data-roads-results-panel>Roads Run Results</div>" });
                }
                if (path === "/runs/test-run/test-config/tasks/roads/set_params") {
                    return Promise.resolve({
                        body: {
                            roads_params: {
                                surface_default: "paved",
                                traffic_default: "none",
                                attribute_field_map: {
                                    design: "ROADTYPE",
                                    surface: "SURF_MAIN",
                                    traffic: "TRAF_MAIN"
                                }
                            },
                            attribute_field_map: {
                                design: "ROADTYPE",
                                surface: "SURF_MAIN",
                                traffic: "TRAF_MAIN"
                            },
                            discovered_attribute_catalog: {
                                field_names: ["ROADTYPE", "SURF_MAIN", "TRAF_MAIN"],
                                field_profiles: [],
                                field_count: 3,
                                total_feature_count: 1,
                                profiled_feature_count: 1,
                                profile_truncated: false
                            }
                        }
                    });
                }
                return Promise.resolve({ body: { job_id: "roads-job-1" } });
            }),
            getJson: jest.fn((path) => {
                if (path === "/runs/test-run/test-config/api/roads/status") {
                    return Promise.resolve({ body: { status: roadsTaskStatus } });
                }
                if (path === "/runs/test-run/test-config/api/roads/config") {
                    return Promise.resolve({
                        body: {
                            roads_params: {
                                surface_default: "gravel",
                                traffic_default: "low",
                                attribute_field_map: {
                                    design: "DESIGN",
                                    surface: "SURFACE",
                                    traffic: "TRAFFIC"
                                }
                            },
                            attribute_field_map: {
                                design: "DESIGN",
                                surface: "SURFACE",
                                traffic: "TRAFFIC"
                            },
                            discovered_attribute_catalog: {
                                field_names: ["DESIGN", "SURFACE", "ROAD_SURFACE", "TRAFFIC", "CONDITION"],
                                field_profiles: [],
                                field_count: 5,
                                total_feature_count: 2,
                                profiled_feature_count: 2,
                                profile_truncated: false
                            }
                        }
                    });
                }
                return Promise.resolve({ body: {} });
            }),
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
                feature_count: 7,
                attribute_field_map: {
                    design: "DESIGN",
                    surface: "SURFACE",
                    traffic: "TRAFFIC"
                },
                discovered_attribute_catalog: {
                    field_names: ["DESIGN", "SURFACE", "ROAD_SURFACE", "TRAFFIC", "CONDITION"],
                    field_profiles: [],
                    field_count: 5,
                    total_feature_count: 7,
                    profiled_feature_count: 7,
                    profile_truncated: false
                }
            }
        });
        await uploadPromise;

        expect(document.getElementById("roads_upload_message").textContent).toContain("uploaded successfully");
        expect(document.querySelector(".wc-upload-progress__fill").style.width).toBe("100%");
        expect(document.getElementById("roads_info").innerHTML).toContain("roads.uploaded.geojson");
        expect(document.getElementById("roads_design_field").value).toBe("DESIGN");
        expect(document.getElementById("roads_surface_default").value).toBe("gravel");
        expect(document.getElementById("roads_traffic_default").value).toBe("low");
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
        await Promise.resolve();

        expect(httpMock.request).toHaveBeenCalledTimes(4);
        expect(httpMock.request).toHaveBeenNthCalledWith(
            1,
            "/runs/test-run/test-config/tasks/roads/prepare_segments",
            expect.objectContaining({ method: "POST", form: expect.any(HTMLFormElement) })
        );
        expect(httpMock.request).toHaveBeenNthCalledWith(2, "/runs/test-run/test-config/report/roads/results/");
        expect(httpMock.request).toHaveBeenNthCalledWith(
            3,
            "/runs/test-run/test-config/tasks/roads/run",
            expect.objectContaining({ method: "POST", form: expect.any(HTMLFormElement) })
        );
        expect(httpMock.request).toHaveBeenNthCalledWith(4, "/runs/test-run/test-config/report/roads/results/");
        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(roads, "roads-job-1");
        expect(pollEvents).toEqual(["ROADS_PREPARE_TASK_COMPLETED", "ROADS_RUN_TASK_COMPLETED"]);
    });

    test("roads run completion is idempotent", async () => {
        await roads.runRoads();
        await Promise.resolve();

        roads.triggerEvent("ROADS_RUN_TASK_COMPLETED", { source: "test", job_id: "roads-job-1" });
        roads.triggerEvent("ROADS_RUN_TASK_COMPLETED", { source: "test", job_id: "roads-job-1" });
        await Promise.resolve();
        await Promise.resolve();

        expect(baseInstance.disconnect_status_stream).toHaveBeenCalledTimes(1);
        expect(document.getElementById("roads-results").innerHTML).toContain("Roads Run Results");
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

    test("queueTask clears stale active roads task after terminal status", async () => {
        await roads.runRoads();
        await Promise.resolve();

        roadsTaskStatus = "idle";
        await roads.prepareSegments();
        await Promise.resolve();

        expect(httpMock.getJson).toHaveBeenCalledWith("/runs/test-run/test-config/api/roads/status");
        expect(httpMock.request).toHaveBeenCalledTimes(2);
        expect(httpMock.request).toHaveBeenNthCalledWith(
            2,
            "/runs/test-run/test-config/tasks/roads/prepare_segments",
            expect.objectContaining({ method: "POST", form: expect.any(HTMLFormElement) })
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

    test("bootstrap fetches roads results panel", async () => {
        roads.bootstrap({});
        await Promise.resolve();
        await Promise.resolve();

        expect(httpMock.getJson).toHaveBeenCalledWith("/runs/test-run/test-config/api/roads/config");
        expect(httpMock.getJson).toHaveBeenCalledWith("/runs/test-run/test-config/api/roads/results");
        expect(httpMock.request).toHaveBeenCalledWith("/runs/test-run/test-config/report/roads/results/");
        expect(document.getElementById("roads-results").innerHTML).toContain("Roads Run Results");
        expect(document.getElementById("roads_traffic_field").value).toBe("TRAFFIC");
    });

    test("bootstrap job hint does not lock prepare/run actions", async () => {
        roads.bootstrap({ jobIds: { run_roads_rq: "stale-roads-job" } });
        await Promise.resolve();
        await Promise.resolve();

        await roads.prepareSegments();
        await Promise.resolve();

        expect(baseInstance.set_rq_job_id).toHaveBeenCalledWith(roads, "stale-roads-job");
        expect(httpMock.request).toHaveBeenNthCalledWith(
            2,
            "/runs/test-run/test-config/tasks/roads/prepare_segments",
            expect.objectContaining({ method: "POST", form: expect.any(HTMLFormElement) })
        );
    });

    test("apply mapping posts attribute_field_map payload", async () => {
        roads.bootstrap({});
        await Promise.resolve();
        await Promise.resolve();

        document.getElementById("roads_design_field").value = "DESIGN";
        document.getElementById("roads_surface_field").value = "SURFACE";
        document.getElementById("roads_traffic_field").value = "TRAFFIC";
        document.getElementById("roads_surface_default").value = "paved";
        document.getElementById("roads_traffic_default").value = "none";

        await roads.applyAttributeMapping();
        await Promise.resolve();

        expect(httpMock.request).toHaveBeenCalledWith(
            "/runs/test-run/test-config/tasks/roads/set_params",
            expect.objectContaining({
                method: "POST",
                json: {
                    attribute_field_map: {
                        design: "DESIGN",
                        surface: "SURFACE",
                        traffic: "TRAFFIC"
                    },
                    surface_default: "paved",
                    traffic_default: "none"
                }
            })
        );
        expect(document.getElementById("roads_mapping_message").textContent).toContain("applied");
    });
});
