/**
 * @jest-environment jsdom
 */

const flushMicrotasks = async () => {
    await Promise.resolve();
    await Promise.resolve();
};

describe("controllers_gl_stale_check", () => {
    let originalReadyStateDescriptor;

    beforeEach(() => {
        jest.resetModules();

        originalReadyStateDescriptor = Object.getOwnPropertyDescriptor(document, "readyState");
        Object.defineProperty(document, "readyState", {
            configurable: true,
            value: "complete"
        });

        document.body.innerHTML = "";
        document.body.dataset.controllersGlExpectedBuildId = "";
        delete window.__weppControllersGlBuildId;
        delete window.__weppControllersGlStaleCheckLoaded;
    });

    afterEach(() => {
        jest.restoreAllMocks();
        if (originalReadyStateDescriptor) {
            Object.defineProperty(document, "readyState", originalReadyStateDescriptor);
        } else {
            delete document.readyState;
        }
        delete window.__weppControllersGlBuildId;
        delete window.__weppControllersGlStaleCheckLoaded;
    });

    test("does not render banner when build ids match", async () => {
        document.body.dataset.controllersGlExpectedBuildId = "2026-02-14T04:40:41Z";
        window.__weppControllersGlBuildId = "2026-02-14T04:40:41Z";

        await import("../../static/js/controllers_gl_stale_check.js");
        await flushMicrotasks();

        expect(document.getElementById("wc-stale-client-banner")).toBeNull();
    });

    test("renders banner when build id is missing", async () => {
        document.body.dataset.controllersGlExpectedBuildId = "2026-02-14T04:40:41Z";

        await import("../../static/js/controllers_gl_stale_check.js");
        await flushMicrotasks();

        expect(document.getElementById("wc-stale-client-banner")).not.toBeNull();
    });

    test("renders banner when build ids mismatch", async () => {
        document.body.dataset.controllersGlExpectedBuildId = "2026-02-14T04:40:41Z";
        window.__weppControllersGlBuildId = "2026-02-13T17:17:50Z";

        await import("../../static/js/controllers_gl_stale_check.js");
        await flushMicrotasks();

        expect(document.getElementById("wc-stale-client-banner")).not.toBeNull();
    });

    test("does not render banner when expected build id is missing/empty", async () => {
        document.body.dataset.controllersGlExpectedBuildId = "";
        window.__weppControllersGlBuildId = "anything";

        await import("../../static/js/controllers_gl_stale_check.js");
        await flushMicrotasks();

        expect(document.getElementById("wc-stale-client-banner")).toBeNull();
    });

    test("does not render banner when expected build id is literal None", async () => {
        document.body.dataset.controllersGlExpectedBuildId = "None";
        window.__weppControllersGlBuildId = "";

        await import("../../static/js/controllers_gl_stale_check.js");
        await flushMicrotasks();

        expect(document.getElementById("wc-stale-client-banner")).toBeNull();
    });

    test("reload button emits a reload-requested event", async () => {
        document.body.dataset.controllersGlExpectedBuildId = "expected";
        window.__weppControllersGlBuildId = "stale";

        const listener = jest.fn();
        document.addEventListener("wepp:controllers-gl-stale-reload", listener);
        jest.spyOn(console, "error").mockImplementation(() => {});

        await import("../../static/js/controllers_gl_stale_check.js");
        await flushMicrotasks();

        const button = document.querySelector('[data-wc-stale-action="reload"]');
        expect(button).not.toBeNull();
        button.click();
        expect(listener).toHaveBeenCalledTimes(1);
    });

    test("dismiss button removes the banner", async () => {
        document.body.dataset.controllersGlExpectedBuildId = "expected";
        window.__weppControllersGlBuildId = "stale";

        await import("../../static/js/controllers_gl_stale_check.js");
        await flushMicrotasks();

        const banner = document.getElementById("wc-stale-client-banner");
        expect(banner).not.toBeNull();

        const button = document.querySelector('[data-wc-stale-action="dismiss"]');
        expect(button).not.toBeNull();
        button.click();

        expect(document.getElementById("wc-stale-client-banner")).toBeNull();
    });

    test("does not create duplicate banners when loaded twice", async () => {
        document.body.dataset.controllersGlExpectedBuildId = "expected";
        window.__weppControllersGlBuildId = "stale";

        await import("../../static/js/controllers_gl_stale_check.js");
        await flushMicrotasks();

        expect(document.querySelectorAll("#wc-stale-client-banner")).toHaveLength(1);

        delete window.__weppControllersGlStaleCheckLoaded;
        jest.resetModules();

        await import("../../static/js/controllers_gl_stale_check.js");
        await flushMicrotasks();

        expect(document.querySelectorAll("#wc-stale-client-banner")).toHaveLength(1);
    });

    test("stacks above session-expired banner after heartbeat event", async () => {
        document.body.dataset.controllersGlExpectedBuildId = "expected";
        window.__weppControllersGlBuildId = "stale";

        await import("../../static/js/controllers_gl_stale_check.js");
        await flushMicrotasks();

        const staleBanner = document.getElementById("wc-stale-client-banner");
        expect(staleBanner).not.toBeNull();
        expect(staleBanner.style.bottom).toBe("0px");

        const sessionBanner = document.createElement("div");
        sessionBanner.id = "wc-session-expired-banner";
        Object.defineProperty(sessionBanner, "offsetHeight", { configurable: true, value: 48 });
        document.body.appendChild(sessionBanner);

        document.dispatchEvent(new CustomEvent("wepp:session-heartbeat-expired"));
        await flushMicrotasks();

        expect(staleBanner.style.bottom).toBe("48px");
    });
});
