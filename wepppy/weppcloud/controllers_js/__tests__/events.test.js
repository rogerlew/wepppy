/**
 * @jest-environment jsdom
 */

beforeAll(async () => {
    await import("../dom.js");
    await import("../events.js");
});

describe("WCEvents helpers", () => {
    let WCEvents;

    beforeAll(() => {
        WCEvents = window.WCEvents;
    });

    afterEach(() => {
        delete global.__WEPPCLOUD_DEV__;
        document.body.innerHTML = "";
    });

    test("createEmitter supports on/off/once semantics", () => {
        const emitter = WCEvents.createEmitter();
        const onHandler = jest.fn();
        const onceHandler = jest.fn();

        const unsubscribe = emitter.on("update", onHandler);
        emitter.once("update", onceHandler);

        emitter.emit("update", { step: 1 });
        emitter.emit("update", { step: 2 });
        unsubscribe();
        emitter.emit("update", { step: 3 });

        expect(onHandler).toHaveBeenCalledTimes(2);
        expect(onceHandler).toHaveBeenCalledTimes(1);
        expect(emitter.listenerCount("update")).toBe(0);
    });

    test("emitDom dispatches CustomEvents with detail payloads", () => {
        const node = document.createElement("div");
        node.id = "dom-target";
        document.body.appendChild(node);

        const handler = jest.fn();
        node.addEventListener("wc:ping", handler);

        const event = WCEvents.emitDom("#dom-target", "wc:ping", { ok: true });
        expect(event.detail).toEqual({ ok: true });
        expect(handler).toHaveBeenCalledTimes(1);
    });

    test("useEventMap warns on unknown events in development mode", () => {
        global.__WEPPCLOUD_DEV__ = true;
        const emitter = WCEvents.useEventMap(["ready"]);
        const warnSpy = jest.spyOn(console, "warn").mockImplementation(() => {});

        emitter.emit("ready");
        emitter.emit("missing");

        expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining("unknown event 'missing'"));
        warnSpy.mockRestore();
    });
});
