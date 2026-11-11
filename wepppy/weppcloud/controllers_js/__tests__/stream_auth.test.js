/** @jest-environment jsdom */

describe("authenticated stream transport", () => {
    let sockets;
    let http;
    let sequence = 0;
    const flush = async () => { for (let i = 0; i < 10; i += 1) { await Promise.resolve(); } };
    beforeEach(async () => {
        jest.resetModules();
        jest.useFakeTimers();
        delete window.WCHttp;
        await import("../http.js");
        http = window.WCHttp;
        sockets = [];
        window.WebSocket = class {
            constructor(url, protocols) { this.url = url; this.protocols = protocols; this.readyState = 0; sockets.push(this); }
            send() {}
            close(code) { this.readyState = 3; if (this.onclose) { this.onclose({ code }); } }
        };
        http.postJson = jest.fn(async (url, body) => ({ body: {
            token: "synthetic-stream-credential-" + (++sequence), config: "resolved", service: body.service,
            expires_at: Math.floor(Date.now() / 1000) + 300
        } }));
    });
    afterEach(() => { jest.useRealTimers(); jest.restoreAllMocks(); });

    test("coalesces same authority but isolates operation and service credentials", async () => {
        const values = await Promise.all([
            http.getStreamToken("example", "cfg", "status"), http.getStreamToken("example", "cfg", "status"),
            http.getStreamToken("example", "cfg", "preflight"),
            http.getStreamToken("example", "cfg", "status", { jobId: "job" })
        ]);
        expect(http.postJson).toHaveBeenCalledTimes(3);
        expect(values[0] === values[1]).toBe(true);
        expect(values[0] === values[2]).toBe(false);
        expect(values[0] === values[3]).toBe(false);
    });

    test("both services use protocol authorization and token-free URLs", async () => {
        const connections = ["status", "preflight"].map(service => http.createStreamConnection({ runId: "example", config: "cfg", service, channel: "wepp" }));
        await flush();
        expect(sockets).toHaveLength(2);
        sockets.forEach(socket => {
            expect(socket.url).not.toContain("credential");
            expect(socket.url.endsWith("?config=resolved")).toBe(true);
            expect(socket.protocols[0]).toBe("wepp-stream.v1");
            expect(socket.protocols[1].startsWith("bearer.")).toBe(true);
        });
        connections.forEach(connection => connection.close());
    });

    test("disconnect while minting cannot create a socket", async () => {
        let resolve;
        http.postJson.mockImplementation(() => new Promise(done => { resolve = done; }));
        const connection = http.createStreamConnection({ runId: "example", config: "cfg", service: "status", channel: "wepp" });
        await flush();
        connection.close();
        resolve({ body: { token: "synthetic", config: "cfg", service: "status", expires_at: Date.now() / 1000 + 300 } });
        await flush();
        expect(sockets).toHaveLength(0);
    });

    test("denial stops without anonymous socket or retry", async () => {
        http.postJson.mockRejectedValue({ status: 403, body: { token: "must-not-escape" } });
        const connection = http.createStreamConnection({ runId: "example", config: "cfg", service: "status", channel: "wepp" });
        const closed = jest.fn(); connection.onclose = closed;
        await flush();
        jest.advanceTimersByTime(600000); await flush();
        expect(sockets).toHaveLength(0);
        expect(http.postJson).toHaveBeenCalledTimes(1);
        expect(closed).toHaveBeenCalledTimes(1);
    });

    test("failed upgrade retries once with fresh token and then stops", async () => {
        const connection = http.createStreamConnection({ runId: "example", config: "cfg", service: "status", channel: "wepp" });
        const closed = jest.fn(); connection.onclose = closed;
        await flush(); sockets[0].close(1006);
        jest.advanceTimersByTime(1000); await flush(); sockets[1].close(1006);
        jest.advanceTimersByTime(10000); await flush();
        expect(sockets).toHaveLength(2);
        expect(http.postJson).toHaveBeenCalledTimes(2);
        expect(closed).toHaveBeenCalledTimes(1);
    });

    test("expiry refreshes a successful connection without terminal hangup", async () => {
        const connection = http.createStreamConnection({ runId: "example", config: "cfg", service: "status", channel: "wepp" });
        const closed = jest.fn(); connection.onclose = closed;
        await flush(); sockets[0].readyState = 1; sockets[0].onopen();
        jest.advanceTimersByTime(271000); await flush();
        expect(sockets).toHaveLength(2);
        expect(http.postJson).toHaveBeenCalledTimes(2);
        expect(closed).not.toHaveBeenCalled();
        connection.close();
        connection.close();
        expect(closed).toHaveBeenCalledTimes(1);
    });
});
