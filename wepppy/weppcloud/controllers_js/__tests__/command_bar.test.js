/** @jest-environment jsdom */
/* eslint-env node */

const fs = require("node:fs");
const path = require("node:path");

const source = fs.readFileSync(
    path.resolve(__dirname, "../../routes/command_bar/static/command-bar.js"),
    "utf8"
);

function response(payload, status = 200) {
    return {
        ok: status >= 200 && status < 300,
        status,
        statusText: status === 200 ? "OK" : "Error",
        headers: { get: () => "application/json" },
        json: jest.fn().mockResolvedValue(payload),
        text: jest.fn().mockResolvedValue(JSON.stringify(payload))
    };
}

describe("Command Bar production client", () => {
    test("owns one lifecycle and confines every mutation and remote message", async () => {
        window.history.replaceState({}, "", "/weppcloud/runs/run-1/cfg/");
        document.head.innerHTML = '<meta name="csrf-token" content="csrf-123">';
        document.body.innerHTML = `
          <div data-command-bar>
            <div data-command-tip></div>
            <div data-command-input-wrapper hidden><input data-command-input></div>
            <div data-command-result hidden></div>
            <div data-agent-chat hidden>
              <span data-agent-status></span>
              <button data-agent-start>Start</button>
              <button data-agent-stop hidden>Stop</button>
              <div data-agent-messages></div>
              <div data-agent-typing hidden></div>
              <div data-agent-composer hidden>
                <textarea data-agent-input></textarea>
                <button data-agent-send>Send</button>
              </div>
              <div data-agent-log hidden></div>
            </div>
          </div>
        `;
        const stream = {};
        window.StatusStream = {
            attach: jest.fn(() => stream),
            disconnect: jest.fn()
        };
        const marked = function marked() {};
        marked.setOptions = jest.fn();
        marked.parse = jest.fn(() => (
            '<a href="javascript:alert(1)" onclick="alert(2)">unsafe</a>'
            + '<a href="https://example.test/ok">safe</a>'
            + '<img src="data:text/html,unsafe" onerror="alert(3)" style="background:url(https://evil.test)">'
        ));
        window.marked = marked;
        const sockets = [];
        class FakeWebSocket {
            constructor(url) {
                this.url = url;
                this.readyState = FakeWebSocket.CONNECTING;
                this.listeners = {};
                this.close = jest.fn();
                this.send = jest.fn();
                sockets.push(this);
            }

            addEventListener(name, handler) {
                this.listeners[name] = handler;
            }

            removeEventListener(name) {
                delete this.listeners[name];
            }
        }
        FakeWebSocket.CONNECTING = 0;
        FakeWebSocket.OPEN = 1;
        window.WebSocket = FakeWebSocket;
        window.fetch = jest.fn((url, options = {}) => {
            if (url.endsWith("/agent/chat") && options.method === "POST") {
                return Promise.resolve(response({
                    session_id: "session/a",
                    redis_channel: "agent_response-session/a"
                }, 202));
            }
            if (url.includes("/agent/chat/session%2Fa") && options.method === "POST") {
                return Promise.resolve(response({ status: "sent" }));
            }
            if (url.includes("/agent/chat/session%2Fa") && options.method === "DELETE") {
                return Promise.resolve(response({ status: "terminated" }));
            }
            if (url.endsWith("/query_engine_mcp_token")) {
                return Promise.resolve(response({
                    Content: {
                        token: "secret",
                        scopes: ["runs:read"],
                        instructions: [],
                        spec_url: "https://example.test/spec",
                        instructions_path: "_query_engine/instructions.md"
                    }
                }));
            }
            if (url.endsWith("/clear_directory_locks")) {
                return Promise.resolve(response({ Content: { cleared_directory_locks: [] } }));
            }
            if (url.endsWith("/clear_nodb_cache")) {
                return Promise.resolve(response({ Content: { cleared_entries: [] } }));
            }
            return Promise.resolve(response({ Content: { log_level: "info" } }));
        });

        window.eval(source);
        const commandBar = window.initializeCommandBar();
        expect(window.initializeCommandBar()).toBe(commandBar);
        expect(sockets).toHaveLength(1);
        expect(sockets[0].url).toContain("run-1");

        document.dispatchEvent(new KeyboardEvent("keydown", { key: ":" }));
        expect(commandBar.active).toBe(true);
        commandBar.inputEl.value = "help";
        commandBar.inputEl.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
        expect(commandBar.commandHistory).toEqual(["help"]);

        const hostile = commandBar.agentChat.renderMarkdown("hostile");
        const parsed = new DOMParser().parseFromString(hostile, "text/html");
        const links = parsed.querySelectorAll("a");
        expect(links[0].hasAttribute("href")).toBe(false);
        expect(links[0].hasAttribute("onclick")).toBe(false);
        expect(links[1].getAttribute("href")).toBe("https://example.test/ok");
        expect(parsed.querySelector("img").hasAttribute("src")).toBe(false);
        expect(parsed.querySelector("img").hasAttribute("onerror")).toBe(false);
        expect(parsed.querySelector("img").hasAttribute("style")).toBe(false);

        await commandBar.clearDirectoryLocks();
        await commandBar.clearNodbCache();
        await commandBar.clearLocks();
        await commandBar.routeGetQueryEngineMcpToken();
        const tokenField = commandBar.resultEl.querySelector(".command-bar-token-card__secret-input");
        expect(tokenField.value).toBe("secret");
        expect(tokenField.readOnly).toBe(true);
        expect(window.localStorage).toHaveLength(0);
        await commandBar.routeRunInterchangeMigration(["wepp/output"]);
        await commandBar.routeSetLogLevel(["info"]);
        await commandBar.agentChat.startSession();
        commandBar.agentChat.inputEl.value = "hello";
        await commandBar.agentChat.handleSend();
        await commandBar.agentChat.terminateSession();

        const mutations = window.fetch.mock.calls.filter(([, options]) => (
            ["POST", "DELETE"].includes(options.method)
        ));
        expect(mutations).toHaveLength(9);
        mutations.forEach(([, options]) => {
            expect(options.credentials).toBe("same-origin");
            expect(options.headers["X-CSRFToken"]).toBe("csrf-123");
        });
        expect(window.StatusStream.attach).toHaveBeenCalledWith(
            expect.objectContaining({
                channel: "agent_response-session/a",
                runId: "run-1"
            })
        );
        expect(window.StatusStream.disconnect).toHaveBeenCalledWith(stream);

        window.fetch.mockRejectedValueOnce(new Error("offline"));
        await commandBar.clearDirectoryLocks();
        expect(commandBar.resultEl.textContent).toContain("Error: offline");

        commandBar.destroy();
        expect(sockets[0].close).toHaveBeenCalledTimes(1);
    });
});
