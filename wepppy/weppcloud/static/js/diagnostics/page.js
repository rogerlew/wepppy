(function (root) {
  "use strict";

  if (!root || root.WEPPDiagnosticsPageLoaded === true) {
    return;
  }
  root.WEPPDiagnosticsPageLoaded = true;

  function createStatusChip(label, state) {
    var chip = document.createElement("span");
    chip.className = "wc-status-chip";
    chip.setAttribute("data-state", state);
    chip.textContent = label;
    return chip;
  }

  function severityText(severity) {
    if (severity === "blocker") {
      return "Blocker";
    }
    if (severity === "degraded") {
      return "Degraded";
    }
    return "Info";
  }

  function statusChipState(status) {
    if (status === "pass") {
      return "success";
    }
    if (status === "fail") {
      return "failed";
    }
    if (status === "warn") {
      return "warning";
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

  function clearNode(node) {
    while (node.firstChild) {
      node.removeChild(node.firstChild);
    }
  }

  function renderOverall(report, rootNode) {
    var chipHost = rootNode.querySelector("[data-diagnostics-overall-chip]");
    var overallValue = rootNode.querySelector("[data-diagnostics-overall-value]");
    var generatedAt = rootNode.querySelector("[data-diagnostics-report-generated]");

    if (chipHost) {
      clearNode(chipHost);
      chipHost.appendChild(createStatusChip(report.overall, overallChipState(report.overall)));
    }

    if (overallValue) {
      overallValue.textContent = report.overall;
    }

    if (generatedAt) {
      generatedAt.textContent = "Generated at " + report.generated_at + ".";
    }
  }

  function renderChecks(report, rootNode) {
    var checkList = rootNode.querySelector("[data-diagnostics-check-list]");
    if (!checkList) {
      return;
    }

    clearNode(checkList);

    var idx;
    for (idx = 0; idx < report.checks.length; idx += 1) {
      var check = report.checks[idx];

      var row = document.createElement("li");
      row.className = "wc-panel wc-stack";
      row.setAttribute("data-check-id", check.id);

      var titleLine = document.createElement("p");
      var titleStrong = document.createElement("strong");
      titleStrong.textContent = check.title;
      titleLine.appendChild(titleStrong);

      var statusLine = document.createElement("p");
      statusLine.className = "wc-text-muted";
      statusLine.appendChild(createStatusChip(check.status, statusChipState(check.status)));
      statusLine.appendChild(document.createTextNode(" Severity: " + severityText(check.severity)));

      var evidenceLine = document.createElement("p");
      evidenceLine.textContent = "Evidence: " + check.evidence;

      var hintLine = document.createElement("p");
      hintLine.className = "wc-text-muted";
      hintLine.textContent = "Fix hint: " + check.fix_hint;

      row.appendChild(titleLine);
      row.appendChild(statusLine);
      row.appendChild(evidenceLine);
      row.appendChild(hintLine);
      checkList.appendChild(row);
    }
  }

  function copyTextWithFallback(text, onSuccess, onError) {
    if (navigator && navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      try {
        var clipboardResult = navigator.clipboard.writeText(text);
        if (clipboardResult && typeof clipboardResult.then === "function") {
          clipboardResult.then(onSuccess, function () {
            copyViaExecCommand(text, onSuccess, onError);
          });
          return;
        }
        onSuccess();
        return;
      } catch (_error) {
        copyViaExecCommand(text, onSuccess, onError);
        return;
      }
    }

    copyViaExecCommand(text, onSuccess, onError);
  }

  function copyViaExecCommand(text, onSuccess, onError) {
    var helperId = "wepp-diagnostics-copy-helper";
    var helper = document.getElementById(helperId);
    if (!helper) {
      helper = document.createElement("textarea");
      helper.id = helperId;
      helper.setAttribute("readonly", "readonly");
      helper.style.position = "fixed";
      helper.style.left = "-9999px";
      helper.style.top = "0";
      document.body.appendChild(helper);
    }

    helper.value = text;
    helper.focus();
    helper.select();

    try {
      if (document.execCommand("copy")) {
        onSuccess();
        return;
      }
    } catch (_error) {
      // no-op: handled below
    }

    onError();
  }

  function setCopyFeedback(rootNode, kind, text) {
    var feedback = rootNode.querySelector("[data-diagnostics-copy-feedback]");
    if (!feedback) {
      return;
    }

    if (kind === "success") {
      feedback.textContent = "Copy status: success. " + text;
      feedback.className = "wc-text-muted";
      feedback.removeAttribute("data-state");
      return;
    }
    if (kind === "error") {
      feedback.textContent = "Copy status: failed. " + text;
      feedback.className = "wc-text-muted";
      feedback.removeAttribute("data-state");
      return;
    }

    feedback.textContent = text;
    feedback.className = "wc-text-muted";
    feedback.removeAttribute("data-state");
  }

  function renderJsonPreview(report, rootNode) {
    var preview = rootNode.querySelector("[data-diagnostics-json-preview]");
    if (!preview) {
      return;
    }

    preview.textContent = root.WEPPDiagnosticsReport.toRedactedJson(report);
  }

  function wireCopyAction(report, rootNode) {
    var copyButton = rootNode.querySelector("[data-diagnostics-copy-json]");
    if (!copyButton) {
      return;
    }

    copyButton.disabled = false;
    copyButton.addEventListener("click", function (event) {
      event.preventDefault();

      var payload = root.WEPPDiagnosticsReport.toRedactedJson(report);

      copyTextWithFallback(
        payload,
        function () {
          setCopyFeedback(rootNode, "success", "Redacted diagnostics JSON copied.");
        },
        function () {
          setCopyFeedback(rootNode, "error", "Copy failed. Select text from Report Preview and copy manually.");
        }
      );
    });
  }

  function appendUniqueCheckOrder(checkOrder, checkId) {
    if (!Array.isArray(checkOrder) || !checkId) {
      return;
    }
    if (checkOrder.indexOf(checkId) !== -1) {
      return;
    }
    checkOrder.push(checkId);
  }

  function normalizeRealtimeCheckResult(checkDef, rawResult, diagRunId) {
    var result = rawResult && typeof rawResult === "object" ? rawResult : {};
    var checkId = String(checkDef && checkDef.id ? checkDef.id : "realtime-check");
    var title = String(checkDef && checkDef.title ? checkDef.title : checkId);
    var severity = String(checkDef && checkDef.severity ? checkDef.severity : "degraded");
    var evidence = String(result.evidence || "");

    if (!evidence) {
      evidence = "Realtime diagnostics returned no evidence text.";
    }
    if (diagRunId && evidence.indexOf("diagRunId=") === -1) {
      evidence += " diagRunId=" + String(diagRunId) + ".";
    }

    return {
      id: String(result.id || checkId),
      title: String(result.title || title),
      severity: String(result.severity || severity),
      status: String(result.status || "fail"),
      evidence: evidence,
      fix_hint: String(result.fix_hint || "Verify status2/preflight2 websocket services and retry diagnostics.")
    };
  }

  function runRealtimeChecks(coreChecks, checkOrder) {
    var checks = Array.isArray(coreChecks) ? coreChecks.slice() : [];
    var order = Array.isArray(checkOrder) ? checkOrder.slice() : [];

    var realtimeApi = root.WCDiagnosticsRealtime;
    if (!realtimeApi || typeof realtimeApi.buildRealtimeChecks !== "function") {
      return Promise.resolve({
        checks: checks,
        checkOrder: order
      });
    }

    var realtimeBundle = realtimeApi.buildRealtimeChecks();
    var realtimeChecks = realtimeBundle && Array.isArray(realtimeBundle.checks) ? realtimeBundle.checks : [];
    var diagRunId = realtimeBundle && realtimeBundle.diagRunId ? String(realtimeBundle.diagRunId) : "";

    var sequence = Promise.resolve();

    for (var i = 0; i < realtimeChecks.length; i += 1) {
      (function (checkDef) {
        appendUniqueCheckOrder(order, checkDef && checkDef.id);

        sequence = sequence
          .then(function () {
            if (!checkDef || typeof checkDef.run !== "function") {
              throw new Error("Realtime check definition is missing a run function.");
            }
            return Promise.resolve(checkDef.run());
          })
          .then(function (result) {
            checks.push(normalizeRealtimeCheckResult(checkDef, result, diagRunId));
          })
          .catch(function (error) {
            var message = "Realtime websocket probe failed unexpectedly.";
            if (error && error.message) {
              message = String(error.message);
            }
            checks.push(normalizeRealtimeCheckResult(checkDef, {
              status: "fail",
              evidence: message,
              fix_hint: "Review browser console output and websocket service health."
            }, diagRunId));
          });
      })(realtimeChecks[i]);
    }

    return sequence.then(function () {
      return {
        checks: checks,
        checkOrder: order
      };
    });
  }

  function runDiagnostics() {
    var rootNode = document.querySelector("[data-diagnostics-root]");
    if (!rootNode) {
      return;
    }

    if (!root.WEPPDiagnosticsCore || !root.WEPPDiagnosticsReport) {
      setCopyFeedback(rootNode, "error", "Diagnostics scripts failed to load.");
      return;
    }

    var checkRunner = typeof root.WEPPDiagnosticsCore.runAllChecks === "function"
      ? root.WEPPDiagnosticsCore.runAllChecks
      : root.WEPPDiagnosticsCore.runCoreChecks;

    Promise.resolve()
      .then(function () {
        return checkRunner();
      })
      .then(function (checks) {
        var checkOrder = typeof root.WEPPDiagnosticsCore.getCheckOrder === "function"
          ? root.WEPPDiagnosticsCore.getCheckOrder()
          : root.WEPPDiagnosticsCore.CHECK_ORDER;

        return runRealtimeChecks(checks, checkOrder);
      })
      .then(function (payload) {
        var report = root.WEPPDiagnosticsReport.buildReport(payload.checks, {
          checkOrder: payload.checkOrder,
          sitePrefix: root.WEPPDiagnosticsCore.readSitePrefix()
        });

        renderOverall(report, rootNode);
        renderChecks(report, rootNode);
        renderJsonPreview(report, rootNode);
        wireCopyAction(report, rootNode);
      })
      .catch(function (error) {
        var message = "Diagnostics run failed.";
        if (error && error.message) {
          message = "Diagnostics run failed: " + String(error.message);
        }
        setCopyFeedback(rootNode, "error", message);
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", runDiagnostics);
    return;
  }

  runDiagnostics();
})(window);
