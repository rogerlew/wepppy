/**
 * @jest-environment jsdom
 */

/* eslint-env node */

const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
let navigation;

const script = fs.readFileSync(
    path.resolve(__dirname, "../../static/js/feature_access.js"),
    "utf8"
);

function installForm(kind = "poweruser") {
    document.head.innerHTML = '<meta name="csrf-token" content="csrf-123">';
    document.body.innerHTML = `
        <h2 id="poweruser-access-heading" tabindex="-1">PowerUser access</h2>
        <section data-internal-access>
        <span data-internal-membership-status>membership current; actions await acknowledgment</span>
        <span data-expired-membership>membership expired</span>
        <form action="/access/poweruser" data-feature-access-form="${kind}"
              data-statement-version="v1">
          ${kind === "membership" ? '<select name="operation"><option value="remove">Remove</option></select><input name="user_id" value="42"><input name="group_key" value="ag_fields"><input name="reason" value="Reviewed removal">' : ''}
          <input type="checkbox" name="needs_poweruser" checked>
          <input type="checkbox" name="accepts_training" checked>
          <p data-access-status hidden tabindex="-1"></p>
          <button type="submit">Save</button>
          ${kind === "acknowledgment" ? "" : '<a href="/profile#poweruser-access-heading" data-access-refresh hidden>Refresh</a>'}
        </form>
        </section>
    `;
    HTMLFormElement.prototype.reportValidity = jest.fn(() => true);
    navigation = { href: "http://localhost/profile#poweruser-access-heading", origin: "http://localhost", hash: "#poweruser-access-heading", reload: jest.fn(), assign: jest.fn() };
    vm.runInNewContext(script, { document, window: { location: navigation }, URL,
        FormData: window.FormData, fetch: (...args) => window.fetch(...args) });
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
        expect(status.textContent).toContain("Unable to save. Reload and retry.");
        expect(form.querySelector("[data-access-refresh]").hidden).toBe(true);
        expect(form.querySelector("button[type=submit]").disabled).toBe(false);
    });

    test.each([true, false])("confirmed grant refreshes even at the same fragment: %s", async (role_changed) => {
        window.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({
            message: "PowerUser access granted.", result: {status: "granted", role_changed, statement_version: "v1"}
        }) });
        const form = installForm();
        await submitAndFlush(form);
        expect(form.isConnected).toBe(false);
        expect(document.querySelector("[data-access-status]").textContent).toBe("PowerUser access granted.");
        expect(document.querySelector("[data-access-refresh]").hidden).toBe(false);
        expect(navigation.reload).toHaveBeenCalledTimes(1);
        document.querySelector("[data-access-refresh]").click();
        expect(navigation.reload).toHaveBeenCalledTimes(2);
        await submitAndFlush(form);
        expect(window.fetch).toHaveBeenCalledTimes(1);
    });

    test.each([
        undefined,
        {status: "pending", role_changed: true, statement_version: "v1"},
        {status: "granted", role_changed: "yes", statement_version: "v1"},
        {status: "granted", role_changed: true, statement_version: "old"}
    ])("malformed grant cannot activate or navigate: %j", async (result) => {
        window.fetch = jest.fn().mockResolvedValue({ok: true, json: async () => ({message: "Saved", result})});
        const form = installForm();
        await submitAndFlush(form);
        expect(form.isConnected).toBe(true);
        expect(form.querySelector("button").disabled).toBe(false);
        expect(form.querySelector("[data-access-status]").className).toBe("wc-alert wc-alert--danger");
        expect(navigation.reload).not.toHaveBeenCalled();
        expect(navigation.assign).not.toHaveBeenCalled();
    });

    test("membership administration keeps its refresh and server feedback", async () => {
        window.fetch = jest.fn().mockResolvedValue({ok: true, json: async () => ({message: "Membership removed."})});
        const form = installForm("membership");
        await submitAndFlush(form);
        expect(form.isConnected).toBe(true);
        expect(form.querySelector("[data-access-status]").textContent).toBe("Membership removed.");
        expect(form.querySelector("[data-access-refresh]").hidden).toBe(false);
        expect(JSON.parse(window.fetch.mock.calls[0][1].body)).toEqual({operation:"remove", user_id:42, group_key:"ag_fields", reason:"Reviewed removal"});
        expect(navigation.reload).not.toHaveBeenCalled();
    });

    test("Profile fragment focuses the onboarding heading", () => {
        installForm();
        expect(document.activeElement).toBe(document.getElementById("poweruser-access-heading"));
    });

    test("network failure keeps retry and does not activate", async () => {
        window.fetch = jest.fn().mockRejectedValue(new Error("Network unavailable"));
        const form = installForm();
        await submitAndFlush(form);
        expect(form.querySelector("button").disabled).toBe(false);
        expect(document.activeElement).toBe(form.querySelector("[data-access-status]"));
        expect(navigation.reload).not.toHaveBeenCalled();
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
