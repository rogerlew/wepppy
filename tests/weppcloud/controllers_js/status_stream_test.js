"use strict";

const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

class MockElement {
  constructor(id, attrs = {}) {
    this.id = id;
    this.attrs = attrs;
    this.children = [];
    this.listeners = {};
    this.hidden = false;
    this.open = false;
    this._text = "";
    this.scrollTop = 0;
    this.scrollHeight = 0;
    this.clientHeight = 100;
  }

  appendChild(child) {
    this.children.push(child);
    child.parent = this;
  }

  querySelector(selector) {
    if (selector === "[data-status-log]") {
      return this.children.find((child) => child.attrs["data-status-log"]);
    }
    if (selector === "[data-stacktrace-body]") {
      return this.children.find((child) => child.attrs["data-stacktrace-body"]);
    }
    return null;
  }

  addEventListener(type, handler) {
    if (!this.listeners[type]) {
      this.listeners[type] = [];
    }
    this.listeners[type].push(handler);
  }

  dispatchEvent(event) {
    const handlers = this.listeners[event.type] || [];
    handlers.forEach((handler) => handler(event));
    return true;
  }

  get textContent() {
    return this._text;
  }

  set textContent(value) {
    this._text = String(value);
    this.scrollHeight = this._text.length;
  }
}

class MockWebSocket {
  constructor(url) {
    this.url = url;
    this.readyState = MockWebSocket.CONNECTING;
    this.sent = [];
    this.onopen = null;
    this.onmessage = null;
    this.onerror = null;
    this.onclose = null;
    MockWebSocket.instances.push(this);
  }

  send(payload) {
    this.sent.push(payload);
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose();
    }
  }

  open() {
    this.readyState = MockWebSocket.OPEN;
    if (this.onopen) {
      this.onopen();
    }
  }

  emitMessage(data) {
    if (this.onmessage) {
      this.onmessage({ data });
    }
  }
}

MockWebSocket.CONNECTING = 0;
MockWebSocket.OPEN = 1;
MockWebSocket.CLOSED = 3;
MockWebSocket.instances = [];

async function runTests() {
  const originalSetTimeout = global.setTimeout;
  const deferred = [];
  global.setTimeout = (fn) => {
    deferred.push(fn);
    return 0;
  };

  global.window = global;
  global.Element = MockElement;
  global.CustomEvent = function CustomEvent(type, options) {
    this.type = type;
    this.detail = options && options.detail;
  };
  global.document = {
    querySelector() {
      return null;
    },
    createEvent() {
      return {
        initCustomEvent(type, _bubbles, _cancelable, detail) {
          this.type = type;
          this.detail = detail;
        },
      };
    },
  };
  global.location = {
    protocol: "https:",
    host: "example.com",
    origin: "https://example.com",
  };
  global.WebSocket = MockWebSocket;

  const statusPanel = new MockElement("status_panel", { "data-status-panel": true });
  const logElement = new MockElement("status_log", { "data-status-log": true });
  statusPanel.appendChild(logElement);

  const stacktracePanel = new MockElement("stacktrace_panel");
  const stacktraceBody = new MockElement("stacktrace_body", { "data-stacktrace-body": true });
  stacktracePanel.appendChild(stacktraceBody);
  stacktracePanel.hidden = true;

  const events = { append: 0, trigger: 0 };
  statusPanel.addEventListener("status:append", () => events.append++);
  statusPanel.addEventListener("status:trigger", () => events.trigger++);

  const triggerCalls = [];
  const stacktraceFetches = [];

  const modulePath = path.resolve(
    __dirname,
    "..",
    "..",
    "..",
    "wepppy",
    "weppcloud",
    "controllers_js",
    "status_stream.js"
  );
  const code = fs.readFileSync(modulePath, "utf8");
  vm.runInThisContext(code, { filename: modulePath });

  const StatusStream = global.StatusStream;
  assert(StatusStream, "StatusStream should be defined");

  const instance = StatusStream.attach({
    element: statusPanel,
    channel: "fork",
    runId: "demo-run",
    logLimit: 4,
    stacktrace: {
      element: stacktracePanel,
      fetchJobInfo: (jobId) => {
        stacktraceFetches.push(jobId);
        return Promise.resolve(`STACK:${jobId}`);
      },
    },
    onTrigger: (detail) => triggerCalls.push(detail),
  });

  assert.strictEqual(typeof instance.append, "function");

  // WebSocket lifecycle
  assert.strictEqual(MockWebSocket.instances.length, 1, "WebSocket should connect immediately");
  const socket = MockWebSocket.instances[0];
  socket.open();
  assert.strictEqual(instance.isConnected(), true);

  // Manual append before WS message
  StatusStream.append(statusPanel, "manual");
  assert.strictEqual(logElement.textContent.trim(), "manual");

  // Status payload logging
  socket.emitMessage(JSON.stringify({ type: "status", data: "line one" }));
  assert.ok(logElement.textContent.includes("line one"), "Log should contain message");
  assert.strictEqual(events.append, 2, "status:append should fire twice");

  // Ping handling
  socket.emitMessage(JSON.stringify({ type: "ping" }));
  assert.strictEqual(socket.sent.includes(JSON.stringify({ type: "pong" })), true);

  // Trigger handling
  socket.emitMessage(
    JSON.stringify({ type: "status", data: "token data TRIGGER fork FORK_COMPLETE" })
  );
  assert.strictEqual(events.trigger, 1, "Trigger event should fire");
  assert.strictEqual(triggerCalls.length, 1);
  assert.strictEqual(triggerCalls[0].event, "FORK_COMPLETE");

  // Stacktrace handling
  socket.emitMessage(JSON.stringify({ type: "status", data: "JID123 EXCEPTION Failure" }));
  await new Promise((resolve) => setImmediate(resolve));
  assert.strictEqual(stacktraceFetches[0], "123");
  assert.strictEqual(stacktracePanel.hidden, false);
  assert.strictEqual(stacktracePanel.open, true);
  assert.strictEqual(stacktraceBody.textContent, "STACK:123");

  // Reconnect on close
  socket.close();
  assert.ok(deferred.length > 0, "Reconnect should schedule retry");
  deferred.pop()();
  assert.strictEqual(MockWebSocket.instances.length, 2, "New WebSocket should spawn");

  const nextSocket = MockWebSocket.instances[1];
  nextSocket.open();
  nextSocket.emitMessage(JSON.stringify({ type: "status", data: "second socket" }));
  assert.ok(logElement.textContent.includes("second socket"));

  global.setTimeout = originalSetTimeout;
  console.log("status_stream tests passed");
}

runTests().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
