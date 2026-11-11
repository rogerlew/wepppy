/** @jest-environment jsdom */
/* global __dirname */
const fs = require("fs");
const path = require("path");

describe("preflight authorized transport consumer", () => {
    test("renders authenticated updates and stops visibly on terminal denial", () => {
        document.body.innerHTML = '<span id="preflight_status"></span><i id="pu_ron_lock"></i>';
        const socket = { send: jest.fn(), close: jest.fn() };
        window.WCHttp = { createStreamConnection: jest.fn(() => socket) };
        const source = fs.readFileSync(path.resolve(__dirname, "../../static/js/preflight.js"), "utf8");
        const init = new Function("window", "document", source + "\nreturn initPreflight;")(window, document);
        const updated = jest.fn();
        document.addEventListener("preflight:update", updated);
        init("example");
        expect(window.WCHttp.createStreamConnection).toHaveBeenCalledWith({ runId: "example", service: "preflight" });
        socket.onopen();
        expect(window.preflightConnected).toBe(true);
        expect(socket.send).toHaveBeenCalledWith(JSON.stringify({ type: "init" }));
        socket.onmessage({ data: JSON.stringify({ type: "preflight", checklist: {}, lock_statuses: { "ron.nodb": true }, last_modified: 1700000000 }) });
        expect(updated).toHaveBeenCalledTimes(1);
        expect(document.getElementById("pu_ron_lock").style.display).toBe("inline");
        socket.onclose({ code: 1008, reason: "Stream authorization unavailable" });
        expect(window.preflightConnected).toBe(false);
        expect(document.getElementById("preflight_status").textContent).toBe("Preflight Connection Closed");
        document.dispatchEvent(new Event("visibilitychange"));
        expect(window.WCHttp.createStreamConnection).toHaveBeenCalledTimes(1);
        document.removeEventListener("preflight:update", updated);
    });
});
