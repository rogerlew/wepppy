/**
 * @jest-environment jsdom
 */

function installPageMarkup() {
  document.body.innerHTML = [
    '<main data-diagnostics-root>',
    '<span data-diagnostics-overall-chip></span>',
    '<span data-diagnostics-overall-value></span>',
    '<p data-diagnostics-report-generated></p>',
    '<p data-diagnostics-progress></p>',
    '<ol data-diagnostics-check-list></ol>',
    '<button data-diagnostics-rerun disabled></button>',
    '<button data-diagnostics-copy-json disabled></button>',
    '<p data-diagnostics-copy-feedback></p>',
    '<pre data-diagnostics-json-preview></pre>',
    "</main>"
  ].join("");
}

describe("diagnostics core lifecycle and page presentation", () => {
  beforeEach(() => {
    jest.resetModules();
    delete window.WEPPDiagnosticsCore;
    delete window.WEPPDiagnosticsPage;
    delete window.WEPPDiagnosticsPageLoaded;
    delete window.WEPPDiagnosticsReport;
    delete window.__weppDiagnosticsPendingChecks;
    installPageMarkup();
  });

  test("core publishes the ordered roster and each check lifecycle", async () => {
    await import("../../static/js/diagnostics/core.js");
    var events = [];
    var retryAttempts = 0;

    window.WEPPDiagnosticsCore.registerCheck({
      id: "throwing-extension",
      title: "Throwing extension",
      description: "Exercises extension failure settlement.",
      severity: "info",
      fix_hint: "Retry the extension.",
      run: () => {
        throw new Error("extension exploded");
      }
    });
    window.WEPPDiagnosticsCore.registerCheck({
      id: "realtime-retry-failure",
      title: "Realtime retry failure",
      description: "Exercises one retry followed by terminal failure.",
      severity: "degraded",
      fix_hint: "Check realtime connectivity.",
      run: async () => {
        while (retryAttempts < 2) {
          retryAttempts += 1;
          await Promise.resolve();
        }
        return {
          status: "fail",
          evidence: "Realtime failed after one retry."
        };
      }
    });

    var results = await window.WEPPDiagnosticsCore.runAllChecks({
      onLifecycle: (event) => events.push(event)
    });

    var checkOrder = window.WEPPDiagnosticsCore.getCheckOrder();
    expect(events[0]).toMatchObject({
      type: "registered",
      checks: checkOrder.map((id) => ({ id }))
    });
    expect(events[0].checks.every((check) => check.description.length > 0)).toBe(true);
    expect(events.slice(1).map((event) => event.type)).not.toContain("registered");
    expect(events.slice(1).map((event) => [event.type, event.check.id])).toEqual(
      checkOrder.flatMap((id) => [["started", id], ["settled", id]])
    );
    checkOrder.forEach((id) => {
      expect(events.filter((event) => event.type === "started" && event.check.id === id)).toHaveLength(1);
      expect(events.filter((event) => event.type === "settled" && event.check.id === id)).toHaveLength(1);
    });
    expect(results.map((result) => result.id)).toEqual(checkOrder);
    expect(results.find((result) => result.id === "throwing-extension")).toMatchObject({
      status: "fail",
      evidence: "extension exploded"
    });
    expect(retryAttempts).toBe(2);
    expect(results.find((result) => result.id === "realtime-retry-failure")).toMatchObject({
      status: "fail",
      evidence: "Realtime failed after one retry."
    });
  });

  test("cards render queued and update in place with state-dependent content", async () => {
    window.WEPPDiagnosticsCore = {};
    window.WEPPDiagnosticsReport = {};
    await import("../../static/js/diagnostics/page.js");
    var api = window.WEPPDiagnosticsPage;
    var rootNode = document.querySelector("[data-diagnostics-root]");
    var definitions = [{
      id: "sample",
      title: "Sample check",
      description: "Checks a user-facing capability.",
      severity: "blocker",
      fix_hint: "Fix the setting."
    }];

    api.renderRoster(definitions, rootNode);
    var originalCard = rootNode.querySelector('[data-check-id="sample"]');
    expect(originalCard.getAttribute("data-check-state")).toBe("queued");
    expect(originalCard.textContent).toContain(definitions[0].description);

    api.updateCard("sample", "running", null, rootNode);
    expect(originalCard.getAttribute("data-check-state")).toBe("running");
    expect(originalCard.textContent).toContain("Check in progress.");

    api.updateCard("sample", "pass", {
      title: "Sample check",
      severity: "blocker",
      evidence: "The check passed.",
      fix_hint: "Fix the setting."
    }, rootNode);
    expect(rootNode.querySelector('[data-check-id="sample"]')).toBe(originalCard);
    expect(originalCard.getAttribute("data-check-state")).toBe("pass");
    expect(originalCard.textContent).not.toContain("Check in progress.");
    expect(originalCard.textContent).toContain("The check passed.");
    expect(originalCard.textContent).not.toContain("Fix the setting.");

    api.updateCard("sample", "running", null, rootNode);
    expect(originalCard.textContent).not.toContain("The check passed.");
    expect(originalCard.textContent).toContain("Check in progress.");

    api.updateCard("sample", "skipped", {
      title: "Sample check",
      severity: "info",
      evidence: "Skipped because login is required.",
      fix_hint: "This hint must stay hidden."
    }, rootNode);
    expect(originalCard.getAttribute("data-check-state")).toBe("skipped");
    expect(originalCard.textContent).not.toContain("Check in progress.");
    expect(originalCard.textContent).toContain("Skipped because login is required.");
    expect(originalCard.textContent).not.toContain("This hint must stay hidden.");

    api.updateCard("sample", "warn", {
      title: "Realtime connection",
      severity: "degraded",
      evidence: "Realtime response was delayed.",
      fix_hint: "Check the network."
    }, rootNode);
    expect(originalCard.textContent).toContain(
      "Impact: WEPPcloud will work, but realtime connection may be limited."
    );
    expect(originalCard.textContent).toContain("What to do: Check the network.");
    expect(originalCard.textContent).toContain("Technical detail: Realtime response was delayed.");

    api.updateCard("sample", "fail", {
      title: "Sample check",
      severity: "blocker",
      evidence: "Technical failure.",
      fix_hint: "Fix the setting."
    }, rootNode);
    expect(originalCard.textContent).toContain(
      "WEPPcloud cannot run in this browser until this is fixed."
    );
    expect(originalCard.textContent).toContain("Fix the setting.");
    expect(originalCard.textContent).toContain("Technical detail: Technical failure.");

    api.updateCard("sample", "warn", {
      title: "Optional capability",
      severity: "info",
      evidence: "Advisory evidence.",
      fix_hint: "Review the advisory."
    }, rootNode);
    expect(originalCard.textContent).toContain(
      "Impact: This is advisory; WEPPcloud will still run."
    );
    expect(originalCard.textContent).toContain("What to do: Review the advisory.");
    expect(originalCard.textContent).toContain("Technical detail: Advisory evidence.");
    expect(originalCard.textContent).not.toMatch(/\b(?:blocker|degraded|info)\b/i);
  });

  test("auto run and re-run reset state and publish only the second report", async () => {
    var lifecycleSubscribers = [];
    var resolveRuns = [];
    var reports = [
      {
        overall: "ready",
        checks: [{ id: "sample", evidence: "first report" }],
        generated_at: "2026-07-27T00:00:00.000Z",
        site_prefix: ""
      },
      {
        overall: "ready_with_degraded_realtime",
        checks: [{ id: "sample", evidence: "second report" }],
        generated_at: "2026-07-27T00:01:00.000Z",
        site_prefix: ""
      }
    ];
    window.WEPPDiagnosticsCore = {
      runAllChecks: jest.fn((options) => {
        lifecycleSubscribers.push(options.onLifecycle);
        options.onLifecycle({
          type: "registered",
          checks: [{ id: "sample", title: "Sample", description: "Checks something." }]
        });
        return new Promise((resolve) => {
          resolveRuns.push(resolve);
        });
      }),
      getCheckOrder: () => ["sample"],
      readSitePrefix: () => ""
    };
    window.WEPPDiagnosticsReport = {
      buildReport: jest.fn(() => reports.shift()),
      toRedactedJson: jest.fn((report) => JSON.stringify(report))
    };
    await import("../../static/js/diagnostics/page.js");
    var rootNode = document.querySelector("[data-diagnostics-root]");
    document.dispatchEvent(new Event("DOMContentLoaded"));
    await Promise.resolve();

    expect(rootNode.querySelectorAll("[data-check-id]")).toHaveLength(1);
    expect(rootNode.querySelector('[data-check-id="sample"]').getAttribute("data-check-state")).toBe("queued");
    expect(rootNode.querySelector("[data-diagnostics-progress]").textContent).toContain("0 of 1");
    expect(await window.WEPPDiagnosticsPage.runDiagnostics(rootNode)).toBe(false);
    expect(window.WEPPDiagnosticsCore.runAllChecks).toHaveBeenCalledTimes(1);

    lifecycleSubscribers[0]({ type: "started", check: { id: "sample" } });
    expect(rootNode.querySelector("[data-diagnostics-progress]").textContent).toContain("0 of 1");
    lifecycleSubscribers[0]({
      type: "settled",
      check: { id: "sample" },
      result: { id: "sample", title: "Sample", severity: "info", status: "pass", evidence: "first" }
    });
    expect(rootNode.querySelector("[data-diagnostics-progress]").textContent).toContain("1 of 1");
    resolveRuns[0]([]);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(rootNode.querySelector("[data-diagnostics-report-generated]").textContent)
      .toContain("2026-07-27T00:00:00.000Z");

    var secondRun = window.WEPPDiagnosticsPage.runDiagnostics(rootNode);
    await Promise.resolve();
    expect(rootNode.querySelector('[data-check-id="sample"]').getAttribute("data-check-state")).toBe("queued");
    expect(rootNode.querySelector("[data-diagnostics-overall-value]").textContent).toBe("checks in progress");
    expect(rootNode.querySelector("[data-diagnostics-progress]").textContent).toContain("0 of 1");
    expect(rootNode.querySelector("[data-diagnostics-report-generated]").textContent).toBe("Report not generated yet.");
    expect(rootNode.querySelector("[data-diagnostics-json-preview]").textContent).toBe("Report not generated yet.");
    expect(rootNode.querySelector("[data-diagnostics-copy-json]").disabled).toBe(true);

    lifecycleSubscribers[1]({ type: "started", check: { id: "sample" } });
    expect(rootNode.querySelector("[data-diagnostics-progress]").textContent).toContain("0 of 1");
    lifecycleSubscribers[1]({
      type: "settled",
      check: { id: "sample" },
      result: { id: "sample", title: "Sample", severity: "degraded", status: "warn", evidence: "second", fix_hint: "Retry." }
    });
    expect(rootNode.querySelector("[data-diagnostics-progress]").textContent).toContain("1 of 1");
    resolveRuns[1]([]);
    await secondRun;

    expect(rootNode.querySelector("[data-diagnostics-report-generated]").textContent)
      .toContain("2026-07-27T00:01:00.000Z");
    expect(rootNode.querySelector("[data-diagnostics-json-preview]").textContent).toContain("second report");
    expect(rootNode.querySelector("[data-diagnostics-json-preview]").textContent).not.toContain("first report");
    expect(rootNode.querySelector("[data-diagnostics-copy-json]").disabled).toBe(false);
    expect(rootNode.querySelector("[data-diagnostics-rerun]").disabled).toBe(false);

    document.execCommand = jest.fn(() => true);
    rootNode.querySelector("[data-diagnostics-copy-json]").click();
    expect(document.getElementById("wepp-diagnostics-copy-helper").value).toContain("second report");
    expect(document.getElementById("wepp-diagnostics-copy-helper").value).not.toContain("first report");
  });

  test("a synchronous lifecycle subscriber failure releases the run latch", async () => {
    window.WEPPDiagnosticsCore = {
      runAllChecks: jest.fn((options) => {
        options.onLifecycle({
          type: "registered",
          checks: null
        });
        return Promise.resolve([]);
      }),
      getCheckOrder: () => [],
      readSitePrefix: () => ""
    };
    window.WEPPDiagnosticsReport = {
      buildReport: jest.fn(),
      toRedactedJson: jest.fn()
    };
    await import("../../static/js/diagnostics/page.js");
    var rootNode = document.querySelector("[data-diagnostics-root]");
    await new Promise((resolve) => setTimeout(resolve, 0));
    var automaticRunCalls = window.WEPPDiagnosticsCore.runAllChecks.mock.calls.length;

    await expect(window.WEPPDiagnosticsPage.runDiagnostics(rootNode)).resolves.toBe(false);
    expect(rootNode.querySelector("[data-diagnostics-rerun]").disabled).toBe(false);

    await expect(window.WEPPDiagnosticsPage.runDiagnostics(rootNode)).resolves.toBe(false);
    expect(window.WEPPDiagnosticsCore.runAllChecks).toHaveBeenCalledTimes(automaticRunCalls + 2);
    expect(rootNode.querySelector("[data-diagnostics-rerun]").disabled).toBe(false);
  });
});

describe("diagnostics browser reset", () => {
  beforeEach(() => {
    jest.resetModules();
    delete window.WEPPDiagnosticsBrowserReset;
    document.body.innerHTML = "";
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  test("clears only WEPPcloud-prefixed storage keys, case-insensitively", async () => {
    await import("../../static/js/diagnostics/browser_reset.js");
    window.localStorage.setItem("wc-theme", "dark");
    window.localStorage.setItem("WEPP-run", "state");
    window.localStorage.setItem("other-site", "keep");
    window.sessionStorage.setItem("WePpDiagnostics", "state");
    window.sessionStorage.setItem("unrelated", "keep");

    window.WEPPDiagnosticsBrowserReset.clearWeppStorage(window.localStorage);
    window.WEPPDiagnosticsBrowserReset.clearWeppStorage(window.sessionStorage);

    expect(window.localStorage.getItem("wc-theme")).toBeNull();
    expect(window.localStorage.getItem("WEPP-run")).toBeNull();
    expect(window.localStorage.getItem("other-site")).toBe("keep");
    expect(window.sessionStorage.getItem("WePpDiagnostics")).toBeNull();
    expect(window.sessionStorage.getItem("unrelated")).toBe("keep");
  });
});
