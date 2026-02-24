/**
 * @jest-environment jsdom
 */

const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");

describe("csrf bootstrap script", () => {
    const originalFetch = global.fetch;
    const scriptPath = resolve(globalThis.process.cwd(), "../static/js/csrf_bootstrap.js");
    const scriptSource = readFileSync(scriptPath, "utf-8");

    function runBootstrapScript() {
        window.eval(scriptSource);
    }

    function okResponse() {
        return Promise.resolve({
            ok: true,
            status: 200,
            statusText: "OK",
            headers: {
                get: () => "application/json"
            },
            text: () => Promise.resolve("{}")
        });
    }

    beforeEach(() => {
        document.head.innerHTML = "";
        document.body.innerHTML = "";
        delete window.__csrfToken;
        jest.restoreAllMocks();
    });

    afterEach(() => {
        global.fetch = originalFetch;
        delete window.__csrfToken;
    });

    afterAll(() => {
        global.fetch = originalFetch;
        delete window.__csrfToken;
    });

    test("captures meta token and injects hidden csrf_token on unsafe same-origin forms", async () => {
        document.head.innerHTML = `<meta name="csrf-token" content="token-form">`;
        document.body.innerHTML = `
            <form id="unsafe" method="POST" action="/api/update"></form>
            <form id="safe" method="GET" action="/api/list"></form>
            <form id="rq" method="POST" action="/rq-engine/api/runs/run-1/config/session-token"></form>
            <form id="external" method="POST" action="https://example.com/post"></form>
        `;
        global.fetch = jest.fn().mockImplementation(okResponse);

        runBootstrapScript();

        expect(window.__csrfToken).toBe("token-form");
        expect(document.querySelector("#unsafe input[name='csrf_token']")).not.toBeNull();
        expect(document.querySelector("#unsafe input[name='csrf_token']").value).toBe("token-form");
        expect(document.querySelector("#safe input[name='csrf_token']")).toBeNull();
        expect(document.querySelector("#rq input[name='csrf_token']")).toBeNull();
        expect(document.querySelector("#external input[name='csrf_token']")).toBeNull();
    });

    test("adds X-CSRFToken for unsafe same-origin fetch requests", async () => {
        document.head.innerHTML = `<meta name="csrf-token" content="token-fetch">`;
        const nativeFetch = jest.fn().mockImplementation(okResponse);
        global.fetch = nativeFetch;

        runBootstrapScript();
        await global.fetch("/api/mutate", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            }
        });

        expect(nativeFetch).toHaveBeenCalledTimes(1);
        const [url, options] = nativeFetch.mock.calls[0];
        expect(url).toBe("/api/mutate");
        expect(new Headers(options.headers).get("Content-Type")).toBe("application/json");
        expect(new Headers(options.headers).get("X-CSRFToken")).toBe("token-fetch");
    });

    test("keeps existing CSRF header and does not add CSRF to cross-origin requests", async () => {
        document.head.innerHTML = `<meta name="csrf-token" content="token-preserve">`;
        const nativeFetch = jest.fn().mockImplementation(okResponse);
        global.fetch = nativeFetch;

        runBootstrapScript();
        await global.fetch("/api/mutate", {
            method: "POST",
            headers: {
                "X-CSRF-Token": "already-set"
            }
        });
        await global.fetch("https://external.example/api/mutate", {
            method: "POST",
            headers: {
                Accept: "application/json"
            }
        });

        const [, firstOptions] = nativeFetch.mock.calls[0];
        const [, secondOptions] = nativeFetch.mock.calls[1];
        expect(new Headers(firstOptions.headers).get("X-CSRF-Token")).toBe("already-set");
        expect(new Headers(firstOptions.headers).get("X-CSRFToken")).toBeNull();
        expect(new Headers(secondOptions.headers).get("X-CSRFToken")).toBeNull();
    });

    test("leaves fetch untouched when csrf token is absent", async () => {
        const nativeFetch = jest.fn().mockImplementation(okResponse);
        global.fetch = nativeFetch;

        runBootstrapScript();
        expect(global.fetch).toBe(nativeFetch);

        await global.fetch("/api/mutate", { method: "POST" });
        expect(nativeFetch).toHaveBeenCalledTimes(1);
        const [, options] = nativeFetch.mock.calls[0];
        expect(new Headers(options && options.headers ? options.headers : {}).get("X-CSRFToken")).toBeNull();
    });
});
