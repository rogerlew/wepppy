/**
 * @jest-environment jsdom
 */

describe("diagnostics copied report allowlist", () => {
  beforeEach(() => {
    jest.resetModules();
    delete window.WEPPDiagnosticsReport;
  });

  async function loadModule() {
    await import("../../static/js/diagnostics/report.js");
    return window.WEPPDiagnosticsReport;
  }

  test("copies fixed catalog values and fixed status messages only", async () => {
    var api = await loadModule();
    var hostile = "backend.internal:6379 token=secret@example.test";
    var report = {
      overall: hostile,
      generated_at: hostile,
      site_prefix: "/safe?leak=" + hostile,
      checks: [
        {
          id: "rq-engine-token",
          title: hostile,
          severity: "info",
          status: "fail",
          evidence: hostile,
          fix_hint: hostile,
          probe_url: "wss://private.example.test/socket"
        },
        {
          id: "rq-engine-token",
          title: "duplicate hostile title",
          severity: "degraded",
          status: "pass"
        },
        {
          id: "unknown-extension",
          title: hostile,
          severity: "blocker",
          status: "fail",
          evidence: hostile
        }
      ]
    };

    var copied = JSON.parse(api.toRedactedJson(report));

    expect(copied.overall).toBe("not_ready");
    expect(copied.site_prefix).toBe("");
    expect(copied.generated_at).not.toBe(hostile);
    expect(Number.isNaN(Date.parse(copied.generated_at))).toBe(false);
    expect(copied.checks).toEqual([
      {
        id: "rq-engine-token",
        title: "Job service access",
        severity: "blocker",
        status: "fail",
        evidence: "Check did not complete successfully.",
        fix_hint: "Review this check on the diagnostics page and retry."
      }
    ]);

    var json = JSON.stringify(copied);
    expect(json).not.toContain(hostile);
    expect(json).not.toContain("private.example.test");
    expect(json).not.toContain("unknown-extension");
    expect(json).not.toContain("duplicate hostile title");
  });

  test("uses catalog order and fixed text for every allowed status", async () => {
    var api = await loadModule();
    var copied = api.redactReport({
      site_prefix: "weppcloud/diagnostics",
      checks: [
        { id: "bandwidth-upload", status: "skipped" },
        { id: "javascript-execution", status: "pass" },
        { id: "realtime-status-websocket", status: "warn" }
      ]
    });

    expect(copied.site_prefix).toBe("/weppcloud/diagnostics");
    expect(copied.checks.map((check) => check.id)).toEqual([
      "javascript-execution",
      "bandwidth-upload",
      "realtime-status-websocket"
    ]);
    expect(copied.checks.map((check) => check.evidence)).toEqual([
      "Check completed successfully.",
      "Check was not run.",
      "Check completed with an advisory result."
    ]);
    expect(copied.overall).toBe("ready_with_degraded_realtime");
  });
});
