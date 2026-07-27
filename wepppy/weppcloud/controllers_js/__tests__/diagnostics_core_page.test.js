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

    var results = await window.WEPPDiagnosticsCore.runAllChecks({
      onLifecycle: (event) => events.push(event)
    });

    expect(events[0].type).toBe("registered");
    expect(events[0].checks.map((check) => check.id)).toEqual(
      window.WEPPDiagnosticsCore.getCheckOrder()
    );
    expect(events[0].checks.every((check) => check.description.length > 0)).toBe(true);
    expect(events.filter((event) => event.type === "started")).toHaveLength(results.length);
    expect(events.filter((event) => event.type === "settled")).toHaveLength(results.length);
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

    api.updateCard("sample", "pass", {
      title: "Sample check",
      severity: "blocker",
      evidence: "The check passed.",
      fix_hint: "Fix the setting."
    }, rootNode);
    expect(rootNode.querySelector('[data-check-id="sample"]')).toBe(originalCard);
    expect(originalCard.textContent).toContain("The check passed.");
    expect(originalCard.textContent).not.toContain("Blocker");
    expect(originalCard.textContent).not.toContain("Fix the setting.");

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
    expect(originalCard.textContent).not.toContain("Blocker");
  });

  test("re-run is concurrency guarded and resets copy/report gating", async () => {
    var resolveRun;
    var runPromise = new Promise((resolve) => {
      resolveRun = resolve;
    });
    window.WEPPDiagnosticsCore = {
      runAllChecks: jest.fn((options) => {
        options.onLifecycle({
          type: "registered",
          checks: [{ id: "sample", title: "Sample", description: "Checks something." }]
        });
        return runPromise;
      }),
      getCheckOrder: () => ["sample"],
      readSitePrefix: () => ""
    };
    window.WEPPDiagnosticsReport = {
      buildReport: jest.fn(() => ({
        overall: "ready",
        checks: [],
        generated_at: "2026-07-27T00:00:00.000Z",
        site_prefix: ""
      })),
      toRedactedJson: jest.fn(() => "{}")
    };
    await import("../../static/js/diagnostics/page.js");
    var rootNode = document.querySelector("[data-diagnostics-root]");

    var overlapping = window.WEPPDiagnosticsPage.runDiagnostics(rootNode);
    expect(await overlapping).toBe(false);
    expect(window.WEPPDiagnosticsCore.runAllChecks).toHaveBeenCalledTimes(1);
    expect(rootNode.querySelector("[data-diagnostics-copy-json]").disabled).toBe(true);
    expect(rootNode.querySelector("[data-diagnostics-rerun]").disabled).toBe(true);

    resolveRun([]);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(rootNode.querySelector("[data-diagnostics-copy-json]").disabled).toBe(false);
    expect(rootNode.querySelector("[data-diagnostics-rerun]").disabled).toBe(false);
  });
});
