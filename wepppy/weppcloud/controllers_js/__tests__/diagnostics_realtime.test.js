/**
 * @jest-environment jsdom
 */

function makeSocketCtor(attemptPlans) {
  var attemptIndex = 0;

  return function MockWebSocket() {
    var plan = attemptPlans[Math.min(attemptIndex, attemptPlans.length - 1)] || {};
    attemptIndex += 1;

    this.send = function () {
      return undefined;
    };
    this.close = function () {
      return undefined;
    };

    var socket = this;
    setTimeout(function () {
      if (plan.error) {
        if (typeof socket.onerror === "function") {
          socket.onerror({ type: "error" });
        }
        return;
      }

      if (typeof socket.onopen === "function") {
        socket.onopen({ type: "open" });
      }

      if (plan.ping) {
        setTimeout(function () {
          if (typeof socket.onmessage === "function") {
            socket.onmessage({ data: '{"type":"ping"}' });
          }
        }, 1);
      }

      if (plan.preflight) {
        setTimeout(function () {
          if (typeof socket.onmessage === "function") {
            socket.onmessage({ data: '{"type":"preflight"}' });
          }
        }, 2);
      }
    }, 0);
  };
}

var originalFetch = global.fetch;

describe("diagnostics realtime module", () => {
  beforeEach(() => {
    jest.resetModules();
    delete window.WCDiagnosticsRealtime;
    delete window.WCDiagnostics;
    delete window.__wcDiagnosticsPendingChecks;
  });

  afterEach(() => {
    jest.useRealTimers();
    if (typeof originalFetch === "function") {
      global.fetch = originalFetch;
    } else {
      delete global.fetch;
    }
  });

  async function loadModule() {
    await import("../../static/js/diagnostics/diagnostics-realtime.js");
    return window.WCDiagnosticsRealtime;
  }

  test("createDiagRunId returns a run id that matches the service contract", async () => {
    var api = await loadModule();

    var runId = api.createDiagRunId();

    expect(runId.startsWith("diag-")).toBe(true);
    expect(runId.indexOf(":")).toBe(-1);
    expect(api.isValidDiagRunId(runId)).toBe(true);
    expect(/^[A-Za-z0-9_.;-]+$/.test(runId)).toBe(true);
  });

  test("status and preflight probe URLs reuse one encoded diagRunId", async () => {
    var api = await loadModule();
    var diagRunId = "diag-1776723456-k8r3m1;unit";

    var statusUrl = api.createStatusProbeUrl(diagRunId, {
      location: {
        protocol: "https:",
        host: "example.test"
      }
    });
    var preflightUrl = api.createPreflightProbeUrl(diagRunId, {
      location: {
        protocol: "https:",
        host: "example.test"
      }
    });

    expect(statusUrl).toBe(
      "wss://example.test/weppcloud-microservices/status/diag-1776723456-k8r3m1%3Bunit:diagnostics"
    );
    expect(preflightUrl).toBe(
      "wss://example.test/weppcloud-microservices/preflight/diag-1776723456-k8r3m1%3Bunit"
    );

    var bundle = api.buildRealtimeChecks({
      diagRunId: diagRunId,
      location: {
        protocol: "https:",
        host: "example.test"
      }
    });

    expect(bundle.diagRunId).toBe(diagRunId);
    expect(bundle.checks.map((check) => check.id)).toEqual([
      "realtime-status-websocket",
      "realtime-preflight-websocket",
      "status-health-reachability",
      "preflight-health-reachability"
    ]);
    expect(api.createStatusHealthUrl()).toBe("/weppcloud-microservices/status/health");
    expect(api.createPreflightHealthUrl()).toBe("/weppcloud-microservices/preflight/health");
  });

  test("runProbeWithRetry retries once after first failure", async () => {
    jest.useFakeTimers();
    var api = await loadModule();

    var resultPromise = api._internals.runProbeWithRetry({
      SocketCtor: makeSocketCtor([
        { error: true },
        { ping: true }
      ]),
      url: "ws://example.test/weppcloud-microservices/status/demo:diagnostics",
      probeWindowMs: 120,
      reconnectRetries: 1,
      requirePreflightFrame: false
    });
    await jest.advanceTimersByTimeAsync(300);
    var result = await resultPromise;

    expect(result.ok).toBe(true);
    expect(result.attempts).toHaveLength(2);
    expect(result.attempts[0].ok).toBe(false);
    expect(result.attempts[1].ok).toBe(true);

    var evidence = api._internals.buildRetryEvidence(result, { probeWindowMs: 120 });
    expect(evidence).toContain("retried once");
  });

  test("preflight probe requires a preflight frame within the probe window", async () => {
    jest.useFakeTimers();
    var api = await loadModule();

    var resultPromise = api._internals.runProbeWithRetry({
      SocketCtor: makeSocketCtor([{ ping: true }]),
      url: "ws://example.test/weppcloud-microservices/preflight/demo",
      probeWindowMs: 20,
      reconnectRetries: 0,
      requirePreflightFrame: true
    });
    await jest.advanceTimersByTimeAsync(50);
    var result = await resultPromise;

    expect(result.ok).toBe(false);
    expect(result.attempts).toHaveLength(1);
    expect(result.attempts[0].reason).toContain("without preflight frame");
  });

  test("module queues realtime checks when diagnostics engine is not loaded yet", async () => {
    await loadModule();

    expect(Array.isArray(window.__wcDiagnosticsPendingChecks)).toBe(true);
    expect(window.__wcDiagnosticsPendingChecks.map((item) => item.id)).toEqual(
      expect.arrayContaining([
        "realtime-status-websocket",
        "realtime-preflight-websocket",
        "status-health-reachability",
        "preflight-health-reachability"
      ])
    );
  });

  test("service health checks run as degraded checks and expose actionable failure hints", async () => {
    var api = await loadModule();
    var fetchMock = jest
      .fn()
      .mockResolvedValueOnce({ ok: true, status: 200 })
      .mockResolvedValueOnce({ ok: false, status: 503 });
    var bundle = api.buildRealtimeChecks({ fetch: fetchMock });

    var statusResult = await bundle.checks[2].run();
    var preflightResult = await bundle.checks[3].run();

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/weppcloud-microservices/status/health",
      expect.objectContaining({
        method: "GET",
        credentials: "omit",
        cache: "no-store"
      })
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/weppcloud-microservices/preflight/health",
      expect.objectContaining({
        method: "GET",
        credentials: "omit",
        cache: "no-store"
      })
    );

    expect(statusResult.severity).toBe("degraded");
    expect(statusResult.status).toBe("pass");
    expect(statusResult.evidence).toContain("HTTP 200");

    expect(preflightResult.severity).toBe("degraded");
    expect(preflightResult.status).toBe("fail");
    expect(preflightResult.evidence).toContain("HTTP 503");
    expect(preflightResult.fix_hint).toContain("preflight2");
  });

  test("service health checks time out and fail as degraded", async () => {
    jest.useFakeTimers();
    var api = await loadModule();
    var pendingFetch = jest.fn(() => new Promise(() => {}));
    var bundle = api.buildRealtimeChecks({
      fetch: pendingFetch,
      healthProbeTimeoutMs: 30
    });

    var statusResultPromise = bundle.checks[2].run();
    await jest.advanceTimersByTimeAsync(600);
    var statusResult = await statusResultPromise;

    expect(statusResult.severity).toBe("degraded");
    expect(statusResult.status).toBe("fail");
    expect(statusResult.evidence).toContain("timeout after 500ms");
  });
});
