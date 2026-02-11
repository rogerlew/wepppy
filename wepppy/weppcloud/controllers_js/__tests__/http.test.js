/**
 * @jest-environment jsdom
 */

beforeAll(async () => {
    await import("../utils.js");
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
        delete window.runId;
        delete window.runid;
        delete window.config;
        if (window.WCHttp && typeof window.WCHttp.clearSessionToken === "function") {
            window.WCHttp.clearSessionToken();
        }
        if (window.WCHttp && typeof window.WCHttp.clearRqEngineToken === "function") {
            window.WCHttp.clearRqEngineToken();
        }
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

    test("request bypasses site_prefix for rq-engine endpoints", async () => {
        window.site_prefix = "/weppcloud";
        global.fetch = jest.fn().mockResolvedValue({
            ok: true,
            status: 200,
            statusText: "OK",
            headers: {
                get: () => ""
            },
            text: () => Promise.resolve("")
        });

        await window.WCHttp.request("/rq-engine/api/jobstatus/job-1", { method: "GET" });

        const [url] = global.fetch.mock.calls[0];
        expect(url).toBe("/rq-engine/api/jobstatus/job-1");
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

    test("request uses error.details when message is missing", async () => {
        global.fetch = jest.fn().mockResolvedValue({
            ok: false,
            status: 400,
            statusText: "Bad Request",
            headers: {
                get: () => "application/json"
            },
            text: () => Promise.resolve(JSON.stringify({ error: { details: "Detailed info" } }))
        });

        await expect(window.WCHttp.request("/api/fail", { method: "POST" })).rejects.toMatchObject({
            status: 400,
            detail: "Detailed info"
        });
    });

    test("getSessionToken caches tokens per run/config", async () => {
        window.site_prefix = "/weppcloud";
        const nowSpy = jest.spyOn(Date, "now").mockReturnValue(0);
        global.fetch = jest.fn().mockResolvedValue({
            ok: true,
            status: 200,
            statusText: "OK",
            headers: {
                get: () => "application/json"
            },
            text: () => Promise.resolve(JSON.stringify({ token: "tok-1", expires_at: 9999999999 }))
        });

        const token1 = await window.WCHttp.getSessionToken("run-1", "cfg");
        const token2 = await window.WCHttp.getSessionToken("run-1", "cfg");

        expect(token1).toBe("tok-1");
        expect(token2).toBe("tok-1");
        expect(global.fetch).toHaveBeenCalledTimes(1);

        const [url, options] = global.fetch.mock.calls[0];
        expect(url).toBe("/rq-engine/api/runs/run-1/cfg/session-token");
        expect(options.method).toBe("POST");

        nowSpy.mockRestore();
    });

    test("getSessionToken falls back to rq-engine token on 401", async () => {
        window.site_prefix = "/weppcloud";
        global.fetch = jest.fn()
            .mockResolvedValueOnce({
                ok: false,
                status: 401,
                statusText: "Unauthorized",
                headers: {
                    get: () => "application/json"
                },
                text: () => Promise.resolve(JSON.stringify({ error: { message: "Session expired" } }))
            })
            .mockResolvedValueOnce({
                ok: true,
                status: 200,
                statusText: "OK",
                headers: {
                    get: () => "application/json"
                },
                text: () => Promise.resolve(JSON.stringify({ token: "user-fallback-tok" }))
            });

        const token = await window.WCHttp.getSessionToken("run-1", "cfg");
        expect(token).toBe("user-fallback-tok");
        expect(global.fetch).toHaveBeenCalledTimes(2);
        expect(global.fetch.mock.calls[0][0]).toBe("/rq-engine/api/runs/run-1/cfg/session-token");
        expect(global.fetch.mock.calls[1][0]).toBe("/weppcloud/api/auth/rq-engine-token");
    });

    test("getSessionToken caches rq-engine fallback token per run/config", async () => {
        window.site_prefix = "/weppcloud";
        global.fetch = jest.fn()
            .mockResolvedValueOnce({
                ok: false,
                status: 401,
                statusText: "Unauthorized",
                headers: {
                    get: () => "application/json"
                },
                text: () => Promise.resolve(JSON.stringify({ error: { message: "Session expired" } }))
            })
            .mockResolvedValueOnce({
                ok: true,
                status: 200,
                statusText: "OK",
                headers: {
                    get: () => "application/json"
                },
                text: () => Promise.resolve(JSON.stringify({ token: "user-fallback-cached" }))
            });

        const token1 = await window.WCHttp.getSessionToken("run-cache", "cfg");
        const token2 = await window.WCHttp.getSessionToken("run-cache", "cfg");

        expect(token1).toBe("user-fallback-cached");
        expect(token2).toBe("user-fallback-cached");
        expect(global.fetch).toHaveBeenCalledTimes(2);
        expect(global.fetch.mock.calls[0][0]).toBe("/rq-engine/api/runs/run-cache/cfg/session-token");
        expect(global.fetch.mock.calls[1][0]).toBe("/weppcloud/api/auth/rq-engine-token");
    });

    test("requestWithSessionToken attaches Authorization header", async () => {
        window.runId = "run-1";
        window.config = "cfg";
        global.fetch = jest.fn()
            .mockResolvedValueOnce({
                ok: true,
                status: 200,
                statusText: "OK",
                headers: {
                    get: () => "application/json"
                },
                text: () => Promise.resolve(JSON.stringify({ token: "tok-1", expires_at: 9999999999 }))
            })
            .mockResolvedValueOnce({
                ok: true,
                status: 200,
                statusText: "OK",
                headers: {
                    get: () => "application/json"
                },
                text: () => Promise.resolve(JSON.stringify({ ok: true }))
            });

        const result = await window.WCHttp.requestWithSessionToken(
            "/rq-engine/api/runs/run-1/cfg/fetch-dem-and-build-channels",
            { method: "POST", json: { demo: true } },
        );

        expect(result.body).toEqual({ ok: true });
        expect(global.fetch).toHaveBeenCalledTimes(2);
        const [, options] = global.fetch.mock.calls[1];
        expect(options.headers.get("Authorization")).toBe("Bearer tok-1");
    });

    test("requestWithSessionToken transparently falls back to rq-engine token on 401 session-token", async () => {
        window.site_prefix = "/weppcloud";
        window.runId = "run-1";
        window.config = "cfg";

        global.fetch = jest.fn()
            .mockResolvedValueOnce({
                ok: false,
                status: 401,
                statusText: "Unauthorized",
                headers: {
                    get: () => "application/json"
                },
                text: () => Promise.resolve(JSON.stringify({ error: { message: "Session expired" } }))
            })
            .mockResolvedValueOnce({
                ok: true,
                status: 200,
                statusText: "OK",
                headers: {
                    get: () => "application/json"
                },
                text: () => Promise.resolve(JSON.stringify({ token: "user-tok-1" }))
            })
            .mockResolvedValueOnce({
                ok: true,
                status: 200,
                statusText: "OK",
                headers: {
                    get: () => "application/json"
                },
                text: () => Promise.resolve(JSON.stringify({ ok: true }))
            });

        const result = await window.WCHttp.requestWithSessionToken(
            "/rq-engine/api/runs/run-1/cfg/fetch-dem-and-build-channels",
            { method: "POST", json: { demo: true } },
        );

        expect(result.body).toEqual({ ok: true });
        expect(global.fetch).toHaveBeenCalledTimes(3);

        const [tokenUrl] = global.fetch.mock.calls[0];
        expect(tokenUrl).toBe("/rq-engine/api/runs/run-1/cfg/session-token");

        const [fallbackUrl] = global.fetch.mock.calls[1];
        expect(fallbackUrl).toBe("/weppcloud/api/auth/rq-engine-token");

        const [, requestOptions] = global.fetch.mock.calls[2];
        expect(requestOptions.headers.get("Authorization")).toBe("Bearer user-tok-1");
    });

    test("requestWithSessionToken surfaces fallback auth errors", async () => {
        window.site_prefix = "/weppcloud";
        window.runId = "run-1";
        window.config = "cfg";

        global.fetch = jest.fn()
            .mockResolvedValueOnce({
                ok: false,
                status: 401,
                statusText: "Unauthorized",
                headers: {
                    get: () => "application/json"
                },
                text: () => Promise.resolve(JSON.stringify({ error: { message: "Session expired" } }))
            })
            .mockResolvedValueOnce({
                ok: false,
                status: 401,
                statusText: "Unauthorized",
                headers: {
                    get: () => "application/json"
                },
                text: () => Promise.resolve(JSON.stringify({ error: { message: "Authentication required." } }))
            });

        await expect(
            window.WCHttp.requestWithSessionToken(
                "/rq-engine/api/runs/run-1/cfg/fetch-dem-and-build-channels",
                { method: "POST", json: { demo: true } },
            )
        ).rejects.toMatchObject({
            status: 401,
            detail: "Authentication required.",
        });

        expect(global.fetch).toHaveBeenCalledTimes(2);
        expect(global.fetch.mock.calls[0][0]).toBe("/rq-engine/api/runs/run-1/cfg/session-token");
        expect(global.fetch.mock.calls[1][0]).toBe("/weppcloud/api/auth/rq-engine-token");
    });

    test("requestWithSessionToken refreshes cached rq-engine fallback token on auth failure", async () => {
        window.site_prefix = "/weppcloud";
        window.runId = "run-1";
        window.config = "cfg";

        global.fetch = jest.fn()
            // Prime rq-engine fallback cache with a stale token.
            .mockResolvedValueOnce({
                ok: true,
                status: 200,
                statusText: "OK",
                headers: {
                    get: () => "application/json"
                },
                text: () => Promise.resolve(JSON.stringify({ token: "stale-user-token" }))
            })
            // requestWithSessionToken -> session-token fails
            .mockResolvedValueOnce({
                ok: false,
                status: 401,
                statusText: "Unauthorized",
                headers: {
                    get: () => "application/json"
                },
                text: () => Promise.resolve(JSON.stringify({ error: { message: "Session expired" } }))
            })
            // requestWithSessionToken must force-refresh fallback token
            .mockResolvedValueOnce({
                ok: false,
                status: 401,
                statusText: "Unauthorized",
                headers: {
                    get: () => "application/json"
                },
                text: () => Promise.resolve(JSON.stringify({ error: { message: "Token revoked" } }))
            })
            // requestWithSessionToken must force-refresh fallback token
            .mockResolvedValueOnce({
                ok: true,
                status: 200,
                statusText: "OK",
                headers: {
                    get: () => "application/json"
                },
                text: () => Promise.resolve(JSON.stringify({ token: "fresh-user-token" }))
            })
            // final rq-engine request succeeds with fresh token
            .mockResolvedValueOnce({
                ok: true,
                status: 200,
                statusText: "OK",
                headers: {
                    get: () => "application/json"
                },
                text: () => Promise.resolve(JSON.stringify({ ok: true }))
            });

        const primed = await window.WCHttp.getRqEngineToken();
        expect(primed).toBe("stale-user-token");

        const result = await window.WCHttp.requestWithSessionToken(
            "/rq-engine/api/runs/run-1/cfg/fetch-dem-and-build-channels",
            { method: "POST", json: { demo: true } },
        );

        expect(result.body).toEqual({ ok: true });
        expect(global.fetch).toHaveBeenCalledTimes(5);
        expect(global.fetch.mock.calls[0][0]).toBe("/weppcloud/api/auth/rq-engine-token");
        expect(global.fetch.mock.calls[1][0]).toBe("/rq-engine/api/runs/run-1/cfg/session-token");
        expect(global.fetch.mock.calls[2][0]).toBe("/rq-engine/api/runs/run-1/cfg/fetch-dem-and-build-channels");
        expect(global.fetch.mock.calls[3][0]).toBe("/weppcloud/api/auth/rq-engine-token");
        expect(global.fetch.mock.calls[4][0]).toBe("/rq-engine/api/runs/run-1/cfg/fetch-dem-and-build-channels");
        const [, requestOptions] = global.fetch.mock.calls[4];
        expect(requestOptions.headers.get("Authorization")).toBe("Bearer fresh-user-token");
    });
});
