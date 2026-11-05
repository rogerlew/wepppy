/* eslint-env node, jest */
const fs = require("node:fs");
const path = require("node:path");

const source = () => fs.readFileSync(path.join(__dirname, "../notifications.js"), "utf8");
const flush = async () => { for (let i = 0; i < 10; i += 1) await Promise.resolve(); };

function start() {
    window.eval(source());
    document.dispatchEvent(new Event("DOMContentLoaded"));
}

beforeEach(() => {
    document.body.innerHTML = '<a data-notification-bell data-count-url="/count"><span data-notification-count hidden></span></a>';
    window.fetch = jest.fn().mockResolvedValue({ok: true, json: async () => ({Content: {unread_count: 3}})});
});

test("badge shows confirmed count and zero hides it", async () => {
    start(); await flush();
    expect(document.querySelector("[data-notification-count]").textContent).toBe("3");
    expect(document.querySelector("a").getAttribute("aria-label")).toBe("Notifications, 3 unread");
});

test("failure is unavailable, never false zero", async () => {
    window.fetch.mockRejectedValue(new Error("offline"));
    start(); await flush();
    expect(document.querySelector("a").getAttribute("aria-label")).toContain("unavailable");
    expect(document.querySelector("[data-notification-count]").textContent).toBe("?");
});

test("zero has no badge", async () => {
    window.fetch.mockResolvedValue({ok: true, json: async () => ({Content: {unread_count: 0}})});
    start(); await flush();
    expect(document.querySelector("[data-notification-count]").hidden).toBe(true);
});

test("select-all is page-bound and failed mutation retains selection", async () => {
    document.body.innerHTML += '<div data-notification-list data-update-url="/update"><input type="checkbox" data-select-all><input type="checkbox" data-notification-id="1"><input type="checkbox" data-notification-id="2"><button data-mark-read="true" disabled>Read</button><button data-mark-read="false" disabled>Unread</button><p data-notification-error hidden></p></div>';
    start(); await flush();
    document.querySelector("[data-select-all]").click();
    expect(document.querySelector("[data-mark-read]").disabled).toBe(false);
    window.fetch.mockResolvedValueOnce({ok: false});
    document.querySelector("[data-mark-read]").click(); await flush();
    const [url, options] = window.fetch.mock.calls.at(-1);
    expect(url).toBe("/update");
    expect(JSON.parse(options.body)).toEqual({notification_ids: [1, 2], read: true});
    expect(document.querySelectorAll("[data-notification-id]:checked")).toHaveLength(2);
    expect(document.querySelector("[data-notification-error]").hidden).toBe(false);
});
