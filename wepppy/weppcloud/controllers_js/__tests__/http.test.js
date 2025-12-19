/**
 * @jest-environment jsdom
 */

beforeAll(async () => {
    await import("../forms.js");
    await import("../http.js");
});

describe("WCHttp helpers", () => {
    const originalFetch = global.fetch;
    const originalHeaders = global.Headers;

    beforeAll(() => {
        if (typeof global.Headers === "undefined") {
            class SimpleHeaders {
                constructor() {
                    this._store = new Map();
                }
                set(key, value) {
                    this._store.set(key.toLowerCase(), value);
                }
                get(key) {
                    return this._store.get(key.toLowerCase()) || null;
                }
                has(key) {
                    return this._store.has(key.toLowerCase());
                }
                forEach(callback) {
                    this._store.forEach((value, key) => callback(value, key));
                }
            }
            global.Headers = SimpleHeaders;
        }
    });

    afterEach(() => {
        jest.restoreAllMocks();
        document.head.innerHTML = "";
        document.body.innerHTML = "";
        delete window.site_prefix;
    });

    afterAll(() => {
        global.fetch = originalFetch;
        if (originalHeaders) {
            global.Headers = originalHeaders;
        } else {
            delete global.Headers;
        }
    });

    test("request prefixes URLs and returns parsed payloads", async () => {
        window.site_prefix = "/wepp";
        global.fetch = jest.fn().mockResolvedValue({
            ok: true,
            status: 200,
            statusText: "OK",
            headers: {
                get: () => ""
            },
            text: () => Promise.resolve("")
        });

        const result = await window.WCHttp.request("/api/ping", { method: "GET" });

        expect(global.fetch).toHaveBeenCalledTimes(1);
        const [url, options] = global.fetch.mock.calls[0];
        expect(url).toBe("/wepp/api/ping");
        expect(options.method).toBe("GET");
        expect(options.headers.get("Accept")).toContain("application/json");
        expect(result.ok).toBe(true);
        expect(result.status).toBe(200);
    });

    test("postForm serializes payloads, propagates CSRF, and throws HttpError", async () => {
        document.head.innerHTML = `<meta name="csrf-token" content="token-head">`;
        global.fetch = jest.fn().mockResolvedValue({
            ok: false,
            status: 500,
            statusText: "Server Error",
            headers: {
                get: () => "application/json"
            },
            text: () => Promise.resolve(JSON.stringify({ detail: "boom" }))
        });

        await expect(window.WCHttp.postForm("/api/fail", { foo: "bar" })).rejects.toMatchObject({
            status: 500,
            detail: "boom"
        });

        const [, options] = global.fetch.mock.calls[0];
        expect(options.method).toBe("POST");
        expect(options.headers.get("X-CSRFToken")).toBe("token-head");
        expect(typeof options.body).toBe("string");
        const bodyParams = new URLSearchParams(options.body);
        expect(bodyParams.get("foo")).toBe("bar");
    });

    test("request parses +json content types", async () => {
        global.fetch = jest.fn().mockResolvedValue({
            ok: true,
            status: 200,
            statusText: "OK",
            headers: {
                get: () => "application/geo+json;charset=UTF-8"
            },
            text: () => Promise.resolve(JSON.stringify({ type: "FeatureCollection", features: [] }))
        });

        const result = await window.WCHttp.request("/resources/nhd", { method: "GET" });

        expect(result.body).toEqual({ type: "FeatureCollection", features: [] });
    });
});
