/**
 * @jest-environment node
 */

const MockFormData = class {
    constructor(entries) {
        this._entries = [];
        if (Array.isArray(entries)) {
            entries.forEach(([key, value]) => {
                this.append(key, value);
            });
        }
    }

    append(key, value) {
        this._entries.push([key, value]);
    }

    forEach(callback) {
        this._entries.forEach(([key, value]) => {
            callback(value, key, this);
        });
    }
};

describe("recorder interceptor", () => {
    let dateNowSpy;
    let mathRandomSpy;

    function setupInterceptor(configOverrides, requestImpl) {
        const request = requestImpl || jest.fn(() => Promise.resolve({ status: 200, ok: true, url: "/resolved/url" }));
        global.WCHttp = {
            request: request
        };
        global.__WEPP_RECORDER_CONFIG = Object.assign({
            endpoint: "recorder/events",
            batchSize: 10,
            flushIntervalMs: 200,
            sessionId: "session-test"
        }, configOverrides || {});
        jest.resetModules();
        require("../recorder_interceptor.js");
        return request;
    }

    function parseEvents(callIndex = 0) {
        const args = global.fetch.mock.calls[callIndex];
        if (!args) {
            return [];
        }
        const body = args[1] && args[1].body;
        if (!body) {
            return [];
        }
        return JSON.parse(body).events || [];
    }

    beforeEach(() => {
        jest.resetModules();
        jest.useRealTimers();

        global.fetch = jest.fn(() => Promise.resolve({}));
        global.window = global;
        global.navigator = undefined;
        global.addEventListener = jest.fn();
        global.location = { origin: "https://example.test" };
        global.runId = "run-abc";
        global.config = "cfg-1";
        global.pup_relpath = "pup/test";
        global.FormData = MockFormData;
        global.Blob = class MockBlob {};
        global.File = class MockFile extends global.Blob {
            constructor(name) {
                super();
                this.name = name || "file.bin";
                this.size = (name || "").length;
            }
        };
        let perfTick = 0;
        global.performance = {
            now: jest.fn(() => {
                perfTick += 5;
                return perfTick;
            })
        };

        let current = 0;
        dateNowSpy = jest.spyOn(Date, "now").mockImplementation(() => {
            current += 100;
            return current;
        });
        mathRandomSpy = jest.spyOn(Math, "random").mockReturnValue(0.123456789);
    });

    afterEach(() => {
        jest.restoreAllMocks();
        jest.useRealTimers();

        delete global.WCHttp;
        delete global.WCRecorder;
        delete global.__WEPP_RECORDER_CONFIG;
        delete global.fetch;
        delete global.navigator;
        delete global.addEventListener;
        delete global.location;
        delete global.runId;
        delete global.config;
        delete global.pup_relpath;
        delete global.FormData;
        delete global.File;
        delete global.Blob;
        delete global.performance;
        delete global.window;
    });

    it("wraps WCHttp.request once and records request/response events", async () => {
        const wrappedFetch = jest.fn(() => Promise.resolve({}));
        global.fetch = wrappedFetch;

        const originalRequest = jest.fn(() => Promise.resolve({ status: 201, ok: true, url: "/runs/test/ok" }));
        setupInterceptor({ batchSize: 1 }, originalRequest);

        const wrappedRequest = global.WCHttp.request;

        expect(wrappedRequest).not.toBe(originalRequest);
        expect(wrappedRequest.__wcRecorderWrapped).toBe(true);

        await wrappedRequest("tasks/run", {
            method: "post",
            json: { foo: "bar" },
            params: { foo: "bar" }
        });

        expect(originalRequest).toHaveBeenCalledWith("tasks/run", expect.objectContaining({ method: "post" }));
        expect(wrappedFetch).toHaveBeenCalledTimes(2);

        const requestEvent = parseEvents(0)[0];
        expect(requestEvent).toEqual(expect.objectContaining({
            stage: "request",
            method: "POST",
            endpoint: "tasks/run",
            category: "http_request",
            sessionId: "session-test",
            runId: "run-abc",
            config: "cfg-1",
            pup: "pup/test",
            rootUrl: "https://example.test"
        }));
        expect(typeof requestEvent.timestamp).toBe("string");
        expect(requestEvent.requestMeta).toEqual(expect.objectContaining({
            hasBody: true,
            bodyType: "json",
            jsonPayload: JSON.stringify({ foo: "bar" })
        }));
        expect(requestEvent.params).toEqual(["foo"]);

        const responseEvent = parseEvents(1)[0];
        expect(responseEvent).toEqual(expect.objectContaining({
            stage: "response",
            method: "POST",
            endpoint: "/runs/test/ok",
            status: 201,
            ok: true,
            category: "http_request"
        }));
        expect(typeof responseEvent.durationMs).toBe("number");
        expect(responseEvent.durationMs).toBeGreaterThanOrEqual(0);
    });

    it("bypasses logging when __skipRecorder flag is provided", async () => {
        const wrappedFetch = jest.fn(() => Promise.resolve({}));
        global.fetch = wrappedFetch;

        const originalRequest = jest.fn(() => Promise.resolve({}));
        setupInterceptor({ batchSize: 1 }, originalRequest);

        await global.WCHttp.request("tasks/skip", { __skipRecorder: true });

        expect(originalRequest).toHaveBeenCalledTimes(1);
        expect(wrappedFetch).not.toHaveBeenCalled();
        expect(global.WCRecorder._queueSize()).toBe(0);
    });

    it("respects enabled=false configuration flag", async () => {
        const wrappedFetch = jest.fn(() => Promise.resolve({}));
        global.fetch = wrappedFetch;

        const originalRequest = jest.fn(() => Promise.resolve({}));
        setupInterceptor({ enabled: false, batchSize: 1 }, originalRequest);

        await global.WCHttp.request("tasks/disabled", { method: "post", json: { a: 1 } });

        expect(wrappedFetch).not.toHaveBeenCalled();
        expect(global.WCRecorder._queueSize()).toBe(0);
    });

    it("summarises form-data payloads and marks file uploads", async () => {
        const wrappedFetch = jest.fn(() => Promise.resolve({}));
        global.fetch = wrappedFetch;

        const originalRequest = jest.fn(() => Promise.resolve({ status: 200, ok: true }));
        setupInterceptor({ batchSize: 1 }, originalRequest);

        const form = new global.FormData();
        form.append("file", new global.File("demo.bin"));
        form.append("meta", "value");
        form.append("repeat", "first");
        form.append("repeat", "second");

        await global.WCHttp.request("tasks/upload", {
            method: "post",
            body: form
        });

        const requestEvent = parseEvents(0)[0];
        expect(requestEvent.category).toBe("file_upload");
        expect(requestEvent.requestMeta).toEqual(expect.objectContaining({
            hasBody: true,
            bodyType: "form-data",
            formKeys: ["file", "meta", "repeat"]
        }));
        expect(requestEvent.requestMeta.formValues).toEqual({
            meta: "value",
            repeat: ["first", "second"]
        });
        expect(requestEvent.requestMeta.formValues).not.toHaveProperty("file");
    });

    it("summarises text payloads with preview and length", async () => {
        const wrappedFetch = jest.fn(() => Promise.resolve({}));
        global.fetch = wrappedFetch;

        const originalRequest = jest.fn(() => Promise.resolve({ status: 204, ok: false }));
        setupInterceptor({ batchSize: 1 }, originalRequest);

        const body = "plain text payload";
        await global.WCHttp.request("tasks/text", {
            method: "put",
            body: body
        });

        const requestEvent = parseEvents(0)[0];
        expect(requestEvent.requestMeta).toEqual(expect.objectContaining({
            hasBody: true,
            bodyType: "text",
            bodyPreview: body,
            bodyLength: body.length
        }));
    });

    it("flushes queue immediately when batch size threshold is reached", () => {
        const wrappedFetch = jest.fn(() => Promise.resolve({}));
        global.fetch = wrappedFetch;

        setupInterceptor({ batchSize: 2, flushIntervalMs: 500 });

        global.WCRecorder.emit("stage-one", { label: "first" });
        expect(global.WCRecorder._queueSize()).toBe(1);
        expect(wrappedFetch).not.toHaveBeenCalled();

        global.WCRecorder.emit("stage-two", { label: "second" });
        expect(wrappedFetch).toHaveBeenCalledTimes(1);
        const events = parseEvents(0);
        expect(events).toHaveLength(2);
        expect(global.WCRecorder._queueSize()).toBe(0);
    });

    it("flushes queued events after the configured interval", () => {
        jest.useFakeTimers();

        const wrappedFetch = jest.fn(() => Promise.resolve({}));
        global.fetch = wrappedFetch;

        setupInterceptor({ batchSize: 5, flushIntervalMs: 300 });

        global.WCRecorder.emit("stage-delay", { step: 1 });
        expect(global.WCRecorder._queueSize()).toBe(1);
        expect(wrappedFetch).not.toHaveBeenCalled();

        jest.advanceTimersByTime(300);

        expect(wrappedFetch).toHaveBeenCalledTimes(1);
        const events = parseEvents(0);
        expect(events).toHaveLength(1);
        expect(events[0].stage).toBe("stage-delay");
        expect(global.WCRecorder._queueSize()).toBe(0);

        jest.useRealTimers();
    });

    it("emits error events with normalised payloads when requests fail", async () => {
        const wrappedFetch = jest.fn(() => Promise.resolve({}));
        global.fetch = wrappedFetch;

        const error = new Error("boom");
        error.status = 503;
        error.detail = "Service unavailable";
        const originalRequest = jest.fn(() => Promise.reject(error));

        setupInterceptor({ batchSize: 1 }, originalRequest);

        await expect(global.WCHttp.request("tasks/error", { method: "delete" })).rejects.toThrow("boom");

        // request and error events
        expect(wrappedFetch).toHaveBeenCalledTimes(2);

        const errorEvent = parseEvents(1)[0];
        expect(errorEvent).toEqual(expect.objectContaining({
            stage: "error",
            method: "DELETE",
            endpoint: "tasks/error",
            category: "http_request"
        }));
        expect(errorEvent.error).toEqual(expect.objectContaining({
            name: "Error",
            message: "boom",
            status: 503,
            detail: "Service unavailable"
        }));
        expect(errorEvent.durationMs).toBeGreaterThanOrEqual(0);
    });

    it("exposes WCRecorder globally and allows config updates", () => {
        setupInterceptor({ batchSize: 4, flushIntervalMs: 120 });

        expect(global.WCRecorder).toBeDefined();
        expect(global.WCRecorder.getConfig()).toEqual(expect.objectContaining({
            batchSize: 4,
            flushIntervalMs: 120
        }));
        expect(global.WCRecorder.isEnabled()).toBe(true);

        global.WCRecorder.setConfig({ enabled: false, batchSize: 7 });

        expect(global.WCRecorder.getConfig()).toEqual(expect.objectContaining({
            enabled: false,
            batchSize: 7,
            flushIntervalMs: 120
        }));
        expect(global.WCRecorder.isEnabled()).toBe(false);
    });
});
