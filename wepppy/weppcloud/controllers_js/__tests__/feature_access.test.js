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

function installForm(kind = "poweruser") {
    document.head.innerHTML = '<meta name="csrf-token" content="csrf-123">';
    document.body.innerHTML = `
        <section data-internal-access>
        <span data-internal-membership-status>membership current; actions await acknowledgment</span>
        <span data-expired-membership>membership expired</span>
        <form action="/access/poweruser" data-feature-access-form="${kind}"
              data-statement-version="v1">
          <input type="checkbox" name="needs_poweruser" checked>
          <input type="checkbox" name="accepts_training" checked>
          <p data-access-status hidden tabindex="-1"></p>
          <button type="submit">Save</button>
          ${kind === "acknowledgment" ? "" : '<a data-access-refresh hidden>Refresh</a>'}
        </form>
        </section>
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

    test.each([true, false])("acknowledgment completes in place when changed=%s", async (changed) => {
        window.fetch = jest.fn().mockResolvedValue({
            ok: true,
            json: async () => ({ message: "Internal access statement accepted.", result: {
                statement_kind: "internal", statement_version: "v1", changed
            } })
        });
        const form = installForm("acknowledgment");
        const status = form.querySelector("[data-access-status]");
        await submitAndFlush(form);
        expect(document.querySelector("form")).toBeNull();
        expect(document.querySelector("[data-access-refresh]")).toBeNull();
        expect(status.textContent).toBe("You have accepted this version.");
        expect(document.activeElement).toBe(status);
        expect(document.querySelector("[data-internal-membership-status]").textContent)
            .toBe("membership current; acknowledgment complete");
        expect(document.querySelector("[data-expired-membership]").textContent).toBe("membership expired");
        await submitAndFlush(form);
        expect(window.fetch).toHaveBeenCalledTimes(1);
    });

    test.each([
        { ok: false, body: { error: { message: "Please retry." } } },
        { ok: true, body: { message: "Saved", result: { statement_kind: "internal", statement_version: "old", changed: true } } },
        { ok: true, body: { message: "Saved" } }
    ])("failed acknowledgment retains retryable controls: %j", async ({ ok, body }) => {
        window.fetch = jest.fn().mockResolvedValue({ ok, json: async () => body });
        const form = installForm("acknowledgment");
        await submitAndFlush(form);
        expect(form.isConnected).toBe(true);
        expect(form.querySelector("button").disabled).toBe(false);
        expect(form.querySelector("[data-access-status]").className).toBe("wc-alert wc-alert--danger");
        expect(document.querySelector("[data-internal-membership-status]").textContent)
            .toContain("await acknowledgment");
    });
});
