/**
 * @jest-environment jsdom
 */

var originalFetch = global.fetch;
var originalConnectionDescriptor = Object.getOwnPropertyDescriptor(window.navigator, "connection");

function restoreNavigatorConnection() {
  if (originalConnectionDescriptor) {
    Object.defineProperty(window.navigator, "connection", originalConnectionDescriptor);
    return;
  }
  Object.defineProperty(window.navigator, "connection", {
    configurable: true,
    value: undefined
  });
}

function setNavigatorConnection(connection) {
  Object.defineProperty(window.navigator, "connection", {
    configurable: true,
    value: connection
  });
}

describe("diagnostics bandwidth checks module", () => {
  beforeEach(() => {
    jest.resetModules();
    delete window.WEPPDiagnosticsBandwidthChecks;
    delete window.WEPPDiagnosticsCore;
    delete window.__weppDiagnosticsPendingChecks;
    restoreNavigatorConnection();
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.restoreAllMocks();
    restoreNavigatorConnection();
    if (typeof originalFetch === "function") {
      global.fetch = originalFetch;
    } else {
      delete global.fetch;
    }
  });

  async function loadModule() {
    await import("../../static/js/diagnostics/bandwidth_checks.js");
    return window.WEPPDiagnosticsBandwidthChecks;
  }

  test("registers checks with diagnostics core in deterministic order", async () => {
    var registerChecks = jest.fn();
    window.WEPPDiagnosticsCore = {
      registerChecks: registerChecks
    };

    await loadModule();

    expect(registerChecks).toHaveBeenCalledTimes(1);
    var checks = registerChecks.mock.calls[0][0];
    expect(checks.map((check) => check.id)).toEqual([
      "bandwidth-rtt",
      "bandwidth-download",
      "bandwidth-upload"
    ]);
    expect(checks.map((check) => check.severity)).toEqual(["info", "info", "info"]);
  });

  test("queues checks when diagnostics core is unavailable", async () => {
    await loadModule();

    expect(Array.isArray(window.__weppDiagnosticsPendingChecks)).toBe(true);
    expect(window.__weppDiagnosticsPendingChecks.map((check) => check.id)).toEqual([
      "bandwidth-rtt",
      "bandwidth-download",
      "bandwidth-upload"
    ]);
  });

  test("Save-Data skips all bandwidth checks with explicit evidence", async () => {
    setNavigatorConnection({ saveData: true });
    var api = await loadModule();

    var idx;
    for (idx = 0; idx < api.checks.length; idx += 1) {
      var result = await api.checks[idx].run({});
      expect(result.status).toBe("skipped");
      expect(result.evidence).toContain("navigator.connection.saveData === true");
      expect(result.evidence).toContain("bytes=");
      expect(result.evidence).toContain("elapsed_ms=");
      expect(result.evidence).toContain("approx_mbps=");
    }
  });

  test("download probe reports bytes, elapsed time, and approximate Mbps", async () => {
    setNavigatorConnection({ saveData: false });
    var nowValues = [1000, 1200];
    jest.spyOn(Date, "now").mockImplementation(() => {
      if (nowValues.length) {
        return nowValues.shift();
      }
      return 1200;
    });

    var fetchMock = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      arrayBuffer: () => Promise.resolve(new ArrayBuffer(256 * 1024))
    });
    global.fetch = fetchMock;

    var api = await loadModule();
    var result = await api.checks[1].run({});

    expect(fetchMock).toHaveBeenCalledWith(
      "/query-engine/diagnostics/bandwidth/download?bytes=262144",
      expect.objectContaining({
        method: "GET",
        credentials: "same-origin",
        cache: "no-store"
      })
    );
    expect(result.status).toBe("pass");
    expect(result.evidence).toContain("bytes=262144");
    expect(result.evidence).toContain("elapsed_ms=200");
    expect(result.evidence).toContain("approx_mbps=10.49");
  });

  test("upload probe degrades to warn on non-2xx responses", async () => {
    setNavigatorConnection({ saveData: false });
    var nowValues = [2000, 2300];
    jest.spyOn(Date, "now").mockImplementation(() => {
      if (nowValues.length) {
        return nowValues.shift();
      }
      return 2300;
    });

    var fetchMock = jest.fn().mockResolvedValue({
      ok: false,
      status: 429,
      json: () => Promise.resolve({ error: { code: "rate_limited" } })
    });
    global.fetch = fetchMock;

    var api = await loadModule();
    var result = await api.checks[2].run({});

    expect(fetchMock).toHaveBeenCalledWith(
      "/query-engine/diagnostics/bandwidth/upload",
      expect.objectContaining({
        method: "POST",
        credentials: "same-origin",
        cache: "no-store",
        headers: expect.objectContaining({
          "Content-Type": "application/octet-stream",
          Accept: "application/json"
        })
      })
    );

    var requestOptions = fetchMock.mock.calls[0][1];
    expect(requestOptions.body).toBeInstanceOf(Uint8Array);
    expect(requestOptions.body.byteLength).toBe(262144);

    expect(result.status).toBe("warn");
    expect(result.evidence).toContain("http_status=429");
    expect(result.evidence).toContain("error_code=rate_limited");
    expect(result.evidence).toContain("target_bytes=262144");
    expect(result.evidence).toContain("bytes=0");
    expect(result.evidence).toContain("elapsed_ms=300");
    expect(result.evidence).toContain("approx_mbps=");
  });

  test("download probe degrades to warn on non-2xx responses", async () => {
    setNavigatorConnection({ saveData: false });
    var nowValues = [3000, 3150];
    jest.spyOn(Date, "now").mockImplementation(() => {
      if (nowValues.length) {
        return nowValues.shift();
      }
      return 3150;
    });

    var fetchMock = jest.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: () => Promise.resolve({ error: { code: "busy" } })
    });
    global.fetch = fetchMock;

    var api = await loadModule();
    var result = await api.checks[1].run({});

    expect(result.status).toBe("warn");
    expect(result.evidence).toContain("target_bytes=262144");
    expect(result.evidence).toContain("http_status=503");
    expect(result.evidence).toContain("error_code=busy");
    expect(result.evidence).toContain("bytes=0");
    expect(result.evidence).toContain("elapsed_ms=150");
    expect(result.evidence).toContain("approx_mbps=");
  });

  test("RTT probe times out within bounded client timeout", async () => {
    jest.useFakeTimers();
    setNavigatorConnection({ saveData: false });

    global.fetch = jest.fn(() => new Promise(() => {}));

    var api = await loadModule();
    var probePromise = api.checks[0].run({});
    await jest.advanceTimersByTimeAsync(5000);
    var result = await probePromise;

    expect(result.status).toBe("warn");
    expect(result.evidence).toContain("timeout after 4000ms");
    expect(result.evidence).toContain("timeout_ms=4000");
  });

  test("timeout normalization clamps to supported lower and upper bounds", async () => {
    var api = await loadModule();
    var internals = api._internals;

    expect(internals.executeFetchProbe).toBeInstanceOf(Function);

    global.fetch = jest.fn(() => Promise.resolve({ ok: true, status: 200 }));
    var fastOutcome = await internals.executeFetchProbe({
      url: "/query-engine/diagnostics/bandwidth/download?bytes=1",
      timeoutMs: 1
    });
    expect(fastOutcome.timeoutMs).toBe(500);

    var slowOutcome = await internals.executeFetchProbe({
      url: "/query-engine/diagnostics/bandwidth/download?bytes=1",
      timeoutMs: 999999
    });
    expect(slowOutcome.timeoutMs).toBe(30000);
  });
});
