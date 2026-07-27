(function (root) {
  "use strict";

  if (!root || root.WEPPDiagnosticsPageLoaded === true) {
    return;
  }
  root.WEPPDiagnosticsPageLoaded = true;

  var activeRun = false;
  var currentReport = null;

  function clearNode(node) {
    while (node && node.firstChild) {
      node.removeChild(node.firstChild);
    }
  }

  function createStatusChip(label, state) {
    var chip = document.createElement("span");
    chip.className = "wc-status-chip";
    chip.setAttribute("data-state", state);
    chip.textContent = label;
    return chip;
  }

  function statusChipState(status) {
    if (status === "pass") {
      return "success";
    }
    if (status === "fail") {
      return "critical";
    }
    if (status === "warn") {
      return "warning";
    }
    if (status === "queued") {
      return "attention";
    }
    return "info";
  }

  function overallChipState(overall) {
    if (overall === "ready") {
      return "success";
    }
    if (overall === "ready_with_degraded_realtime") {
      return "warning";
    }
    return "critical";
  }

  function impactText(severity, title) {
    if (severity === "blocker") {
      return "Impact: WEPPcloud cannot run in this browser until this is fixed.";
    }
    if (severity === "degraded") {
      return "Impact: WEPPcloud will work, but " + String(title || "this capability").toLowerCase()
        + " may be limited.";
    }
    return "Impact: This is advisory; WEPPcloud will still run.";
  }

  function appendTextLine(row, text, className, role) {
    var line = document.createElement("p");
    if (className) {
      line.className = className;
    }
    if (role) {
      line.setAttribute("data-check-role", role);
    }
    line.textContent = text;
    row.appendChild(line);
    return line;
  }

  function createQueuedCard(definition) {
    var row = document.createElement("li");
    row.className = "wc-panel wc-stack";
    row.setAttribute("data-check-id", definition.id);
    row.setAttribute("data-check-state", "queued");
    row.setAttribute("aria-live", "polite");
    row.setAttribute("aria-atomic", "true");

    var titleLine = appendTextLine(row, "", "", "title");
    var strong = document.createElement("strong");
    strong.textContent = definition.title;
    titleLine.appendChild(strong);

    if (definition.description) {
      appendTextLine(row, definition.description, "wc-text-muted", "description");
    }

    var statusLine = appendTextLine(row, "", "", "status");
    statusLine.appendChild(createStatusChip("queued", statusChipState("queued")));
    return row;
  }

  function renderRoster(definitions, rootNode) {
    var checkList = rootNode.querySelector("[data-diagnostics-check-list]");
    if (!checkList) {
      return;
    }
    clearNode(checkList);
    for (var idx = 0; idx < definitions.length; idx += 1) {
      checkList.appendChild(createQueuedCard(definitions[idx]));
    }
  }

  function updateCard(checkId, state, result, rootNode) {
    var row = rootNode.querySelector('[data-check-id="' + checkId + '"]');
    if (!row) {
      return;
    }
    row.setAttribute("data-check-state", state);
    var statusLine = row.querySelector('[data-check-role="status"]');
    clearNode(statusLine);
    statusLine.appendChild(createStatusChip(state, statusChipState(state)));

    var oldDetails = row.querySelectorAll("[data-check-detail]");
    for (var detailIdx = 0; detailIdx < oldDetails.length; detailIdx += 1) {
      oldDetails[detailIdx].remove();
    }

    if (state === "running") {
      statusLine.appendChild(document.createTextNode(" Check in progress."));
      return;
    }
    if (!result) {
      return;
    }
    if (state === "pass") {
      var passLine = appendTextLine(row, result.evidence, "", "result");
      passLine.setAttribute("data-check-detail", "");
      return;
    }
    if (state === "skipped") {
      var skippedLine = appendTextLine(row, result.evidence, "", "result");
      skippedLine.setAttribute("data-check-detail", "");
      return;
    }

    var impactLine = appendTextLine(row, impactText(result.severity, result.title), "", "impact");
    impactLine.setAttribute("data-check-detail", "");
    var hintLine = appendTextLine(row, "What to do: " + result.fix_hint, "", "fix-hint");
    hintLine.setAttribute("data-check-detail", "");
    var evidenceLine = appendTextLine(row, "Technical detail: " + result.evidence, "wc-text-muted", "evidence");
    evidenceLine.setAttribute("data-check-detail", "");
  }

  function setProgress(rootNode, completed, total) {
    var progress = rootNode.querySelector("[data-diagnostics-progress]");
    if (progress) {
      progress.textContent = String(completed) + " of " + String(total) + " checks complete.";
    }
  }

  function resetRunUi(rootNode) {
    currentReport = null;
    var chipHost = rootNode.querySelector("[data-diagnostics-overall-chip]");
    clearNode(chipHost);
    chipHost.appendChild(createStatusChip("running", "info"));
    rootNode.querySelector("[data-diagnostics-overall-value]").textContent = "checks in progress";
    rootNode.querySelector("[data-diagnostics-report-generated]").textContent = "Report not generated yet.";
    rootNode.querySelector("[data-diagnostics-json-preview]").textContent = "Report not generated yet.";
    rootNode.querySelector("[data-diagnostics-copy-json]").disabled = true;
    rootNode.querySelector("[data-diagnostics-rerun]").disabled = true;
    setCopyFeedback(rootNode, "Copy JSON is available after checks finish.");
  }

  function renderReport(report, rootNode) {
    var chipHost = rootNode.querySelector("[data-diagnostics-overall-chip]");
    clearNode(chipHost);
    chipHost.appendChild(createStatusChip(report.overall, overallChipState(report.overall)));
    rootNode.querySelector("[data-diagnostics-overall-value]").textContent = report.overall;
    rootNode.querySelector("[data-diagnostics-report-generated]").textContent =
      "Generated at " + report.generated_at + ".";
    rootNode.querySelector("[data-diagnostics-json-preview]").textContent =
      root.WEPPDiagnosticsReport.toRedactedJson(report);
  }

  function setCopyFeedback(rootNode, text) {
    var feedback = rootNode.querySelector("[data-diagnostics-copy-feedback]");
    if (feedback) {
      feedback.textContent = text;
    }
  }

  function copyViaExecCommand(text, rootNode) {
    var helper = document.getElementById("wepp-diagnostics-copy-helper");
    if (!helper) {
      helper = document.createElement("textarea");
      helper.id = "wepp-diagnostics-copy-helper";
      helper.setAttribute("readonly", "readonly");
      helper.style.position = "fixed";
      helper.style.left = "-9999px";
      document.body.appendChild(helper);
    }
    helper.value = text;
    helper.focus();
    helper.select();
    try {
      if (document.execCommand("copy")) {
        setCopyFeedback(rootNode, "Copy status: success. Redacted diagnostics JSON copied.");
        return;
      }
    } catch (_error) {
      // The manual-copy message below is the explicit fallback.
    }
    setCopyFeedback(rootNode, "Copy failed. Select text from Report Preview and copy manually.");
  }

  function copyCurrentReport(rootNode) {
    if (!currentReport) {
      return;
    }
    var payload = root.WEPPDiagnosticsReport.toRedactedJson(currentReport);
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      navigator.clipboard.writeText(payload).then(function () {
        setCopyFeedback(rootNode, "Copy status: success. Redacted diagnostics JSON copied.");
      }, function () {
        copyViaExecCommand(payload, rootNode);
      });
      return;
    }
    copyViaExecCommand(payload, rootNode);
  }

  function runDiagnostics(rootNode) {
    if (activeRun) {
      return Promise.resolve(false);
    }
    if (!root.WEPPDiagnosticsCore
        || typeof root.WEPPDiagnosticsCore.runAllChecks !== "function"
        || !root.WEPPDiagnosticsReport) {
      setCopyFeedback(rootNode, "Diagnostics scripts failed to load.");
      return Promise.resolve(false);
    }

    activeRun = true;
    resetRunUi(rootNode);
    var completed = 0;
    var total = 0;

    return Promise.resolve().then(function () {
      return root.WEPPDiagnosticsCore.runAllChecks({
        onLifecycle: function (event) {
          if (event.type === "registered") {
            total = event.checks.length;
            renderRoster(event.checks, rootNode);
            setProgress(rootNode, 0, total);
          } else if (event.type === "started") {
            updateCard(event.check.id, "running", null, rootNode);
          } else if (event.type === "settled") {
            completed += 1;
            updateCard(event.check.id, event.result.status, event.result, rootNode);
            setProgress(rootNode, completed, total);
          }
        }
      });
    }).then(function (checks) {
      currentReport = root.WEPPDiagnosticsReport.buildReport(checks, {
        checkOrder: root.WEPPDiagnosticsCore.getCheckOrder(),
        sitePrefix: root.WEPPDiagnosticsCore.readSitePrefix()
      });
      renderReport(currentReport, rootNode);
      rootNode.querySelector("[data-diagnostics-copy-json]").disabled = false;
      setCopyFeedback(rootNode, "Copy JSON is ready.");
      return true;
    }).catch(function (error) {
      var message = error && error.message ? String(error.message) : "Unexpected error.";
      setCopyFeedback(rootNode, "Diagnostics run failed: " + message);
      return false;
    }).then(function (succeeded) {
      activeRun = false;
      rootNode.querySelector("[data-diagnostics-rerun]").disabled = false;
      return succeeded;
    });
  }

  function initialize() {
    var rootNode = document.querySelector("[data-diagnostics-root]");
    if (!rootNode) {
      return;
    }
    rootNode.querySelector("[data-diagnostics-copy-json]").addEventListener("click", function () {
      copyCurrentReport(rootNode);
    });
    rootNode.querySelector("[data-diagnostics-rerun]").addEventListener("click", function () {
      runDiagnostics(rootNode);
    });
    runDiagnostics(rootNode);
  }

  root.WEPPDiagnosticsPage = {
    impactText: impactText,
    renderRoster: renderRoster,
    updateCard: updateCard,
    runDiagnostics: runDiagnostics
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize);
  } else {
    initialize();
  }
})(window);
