/** @jest-environment jsdom */
/* eslint-env node */

const fs = require("node:fs");
const path = require("node:path");

function clientScript() {
    const template = fs.readFileSync(
        path.resolve(__dirname, "../../templates/cap_gate.htm"),
        "utf8"
    );
    const scripts = [...template.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];
    return scripts.at(-1)[1]
        .replace("{{ cap_next | tojson }}", JSON.stringify("/interfaces/"))
        .replace("{{ cap_verify_url | tojson }}", JSON.stringify("/cap/verify"))
        .replace("{{ cap_api_endpoint | tojson }}", JSON.stringify("/cap/"))
        .replace("window.location.replace(nextUrl);", "window.__capRedirect(nextUrl);")
        .replace('window.addEventListener("load", solve);', "window.__capSolve = solve;");
}

function installDom() {
    document.head.innerHTML = '<meta name="csrf-token" content="csrf-1">';
    document.body.innerHTML = `
      <p id="cap-status">Completing verification...</p>
      <button type="button" id="cap-retry">Verify now</button>
      <button type="button" id="cap-reload">Reload</button>
    `;
    window.__capRedirect = jest.fn();
    window.fetch = jest.fn();
}

async function settle() {
    for (let index = 0; index < 16; index += 1) {
        await Promise.resolve();
    }
}

describe("CAP gate inline contract", () => {
    beforeEach(() => {
        installDom();
        delete window.Cap;
    });

    afterEach(() => {
        jest.restoreAllMocks();
        delete window.Cap;
        delete window.__capRedirect;
        delete window.__capSolve;
    });

    test("solves, verifies with CSRF, and redirects to the confined continuation", async () => {
        window.Cap = jest.fn(() => ({
            solve: jest.fn().mockResolvedValue({ token: "<cap-token>" }),
        }));
        window.fetch.mockResolvedValue({ ok: true });

        window.eval(clientScript());
        window.__capSolve();
        await settle();

        expect(window.Cap).toHaveBeenCalledWith({ apiEndpoint: "/cap/" });
        expect(window.fetch).toHaveBeenCalledWith("/cap/verify", {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded",
                "X-CSRFToken": "csrf-1",
            },
            body: "cap_token=%3Ccap-token%3E",
        });
        expect(window.__capRedirect).toHaveBeenCalledWith("/interfaces/");
    });

    test("fails visibly and remains retryable when the CAPTCHA runtime is absent", () => {
        window.eval(clientScript());
        window.__capSolve();

        expect(document.querySelector("#cap-status").textContent).toContain(
            "CAPTCHA library failed to load"
        );
        expect(document.querySelector("#cap-status").classList.contains("is-error")).toBe(true);
        expect(document.querySelector("#cap-retry").disabled).toBe(false);
        expect(window.fetch).not.toHaveBeenCalled();
    });

    test("does not start a second solve while one is in flight", () => {
        window.Cap = jest.fn(() => ({
            solve: jest.fn(() => new Promise(() => {})),
        }));

        window.eval(clientScript());
        window.__capSolve();
        window.__capSolve();

        expect(window.Cap).toHaveBeenCalledTimes(1);
        expect(document.querySelector("#cap-retry").disabled).toBe(true);
    });
});
