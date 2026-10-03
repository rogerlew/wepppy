/**
 * @jest-environment jsdom
 */

/* eslint-env node */

const fs = require("node:fs");
const path = require("node:path");

const script = fs.readFileSync(
    path.resolve(__dirname, "../../static/js/feature_access.js"),
    "utf8"
);

function installForm() {
    document.head.innerHTML = '<meta name="csrf-token" content="csrf-123">';
    document.body.innerHTML = `
        <form action="/access/poweruser" data-feature-access-form="poweruser"
              data-statement-version="v1">
          <input type="checkbox" name="needs_poweruser" checked>
          <input type="checkbox" name="accepts_training" checked>
          <p data-access-status hidden tabindex="-1"></p>
          <button type="submit">Save</button>
          <a data-access-refresh hidden>Refresh</a>
        </form>
    `;
    HTMLFormElement.prototype.reportValidity = jest.fn(() => true);
    window.eval(script);
    return document.querySelector("form");
}

async function submitAndFlush(form) {
    form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    await new Promise((resolve) => setTimeout(resolve, 0));
}

describe("feature access forms", () => {
    afterEach(() => {
        jest.restoreAllMocks();
    });

    test.each([200, 500])("treats a non-JSON %i response as a failure", async (statusCode) => {
        window.fetch = jest.fn().mockResolvedValue({
            ok: statusCode < 400,
            status: statusCode,
            json: () => Promise.reject(new SyntaxError("not JSON"))
        });
        const form = installForm();

        await submitAndFlush(form);

        const status = form.querySelector("[data-access-status]");
        expect(status.className).toBe("wc-alert wc-alert--danger");
        expect(status.textContent).toBe("Unable to save. Reload and retry.");
        expect(form.querySelector("[data-access-refresh]").hidden).toBe(true);
        expect(form.querySelector("button[type=submit]").disabled).toBe(false);
    });

    test("shows the server message after a valid JSON success", async () => {
        window.fetch = jest.fn().mockResolvedValue({
            ok: true,
            status: 200,
            json: () => Promise.resolve({ message: "Access request saved." })
        });
        const form = installForm();

        await submitAndFlush(form);

        const status = form.querySelector("[data-access-status]");
        expect(status.className).toBe("wc-alert wc-alert--success");
        expect(status.textContent).toBe("Access request saved.");
        expect(form.querySelector("[data-access-refresh]").hidden).toBe(false);
    });
});
