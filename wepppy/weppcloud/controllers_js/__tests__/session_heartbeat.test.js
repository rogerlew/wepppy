/**
 * @jest-environment jsdom
 */

const flushMicrotasks = async () => {
    await Promise.resolve();
    await Promise.resolve();
};

describe("session heartbeat", () => {
    let originalReadyStateDescriptor;

    beforeEach(() => {
        jest.resetModules();
        jest.useFakeTimers();

        originalReadyStateDescriptor = Object.getOwnPropertyDescriptor(document, "readyState");
        Object.defineProperty(document, "readyState", {
            configurable: true,
            value: "complete",
        });

        document.body.innerHTML = "";
        window.history.replaceState({}, "", "/");
        document.body.dataset.userAuthenticated = "true";
        document.body.dataset.sitePrefix = "/weppcloud";
        global.fetch = jest.fn(() =>
            Promise.resolve({
                ok: true,
                status: 200,
            })
        );
    });

    afterEach(() => {
        if (originalReadyStateDescriptor) {
            Object.defineProperty(document, "readyState", originalReadyStateDescriptor);
        } else {
            delete document.readyState;
        }
        window.dispatchEvent(new Event("pagehide"));
        jest.runOnlyPendingTimers();
        jest.useRealTimers();
        delete window.__weppSessionHeartbeatLoaded;
        delete global.fetch;
    });

    test("does not start heartbeat when user is not authenticated", async () => {
        window.history.replaceState({}, "", "/weppcloud/interfaces");
        document.body.dataset.userAuthenticated = "false";

        await import("../../static/js/session_heartbeat.js");
        await flushMicrotasks();

        expect(global.fetch).not.toHaveBeenCalled();
    });

    test("starts heartbeat on authenticated pages", async () => {
        window.history.replaceState({}, "", "/weppcloud/interfaces");

        await import("../../static/js/session_heartbeat.js");
        await flushMicrotasks();

        expect(global.fetch).toHaveBeenCalledWith(
            "/weppcloud/api/auth/session-heartbeat",
            expect.objectContaining({
                method: "POST",
                credentials: "same-origin",
            })
        );

        jest.advanceTimersByTime(5 * 60 * 1000);
        await flushMicrotasks();
        expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    test("stops heartbeat and emits event after unauthorized response", async () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({
                ok: false,
                status: 401,
            })
        );
        const expiredListener = jest.fn();
        document.addEventListener("wepp:session-heartbeat-expired", expiredListener);

        window.history.replaceState({}, "", "/weppcloud/runs/demo-run/cfg/README");
        await import("../../static/js/session_heartbeat.js");
        await flushMicrotasks();

        expect(global.fetch).toHaveBeenCalledTimes(1);
        expect(expiredListener).toHaveBeenCalledTimes(1);
        expect(document.getElementById("wc-session-expired-banner")).not.toBeNull();

        jest.advanceTimersByTime(15 * 60 * 1000);
        await flushMicrotasks();
        expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    test("fires heartbeat immediately when tab becomes visible", async () => {
        window.history.replaceState({}, "", "/weppcloud/runs/demo-run/cfg/rq-fork-console");

        await import("../../static/js/session_heartbeat.js");
        await flushMicrotasks();
        expect(global.fetch).toHaveBeenCalledTimes(1);

        Object.defineProperty(document, "visibilityState", {
            configurable: true,
            value: "visible",
        });
        document.dispatchEvent(new Event("visibilitychange"));
        await flushMicrotasks();

        expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    test("keeps retrying after transient network failures", async () => {
        let attempts = 0;
        global.fetch = jest.fn(() => {
            attempts += 1;
            if (attempts <= 3) {
                return Promise.reject(new Error("network down"));
            }
            return Promise.resolve({
                ok: true,
                status: 200,
            });
        });

        window.history.replaceState({}, "", "/weppcloud/runs/demo-run/cfg/reports");
        await import("../../static/js/session_heartbeat.js");
        await flushMicrotasks();
        expect(global.fetch).toHaveBeenCalledTimes(1);

        jest.advanceTimersByTime(5 * 60 * 1000);
        await flushMicrotasks();
        jest.advanceTimersByTime(5 * 60 * 1000);
        await flushMicrotasks();
        jest.advanceTimersByTime(5 * 60 * 1000);
        await flushMicrotasks();
        expect(global.fetch).toHaveBeenCalledTimes(4);
        expect(document.getElementById("wc-session-expired-banner")).toBeNull();
    });
});
