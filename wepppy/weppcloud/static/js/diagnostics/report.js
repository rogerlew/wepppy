(function (root) {
  "use strict";

  if (!root || root.WEPPDiagnosticsReport) {
    return;
  }

  var ALLOWED_STATUSES = {
    pass: true,
    fail: true,
    warn: true,
    skipped: true
  };

  var ALLOWED_SEVERITIES = {
    blocker: true,
    degraded: true,
    info: true
  };

  var REPORT_CHECK_CATALOG = Object.freeze([
    Object.freeze({ id: "javascript-execution", title: "JavaScript support", severity: "blocker" }),
    Object.freeze({ id: "browser-api-baseline", title: "Browser API baseline", severity: "blocker" }),
    Object.freeze({ id: "cookie-storage", title: "Cookie storage", severity: "blocker" }),
    Object.freeze({ id: "local-storage", title: "Local browser storage", severity: "info" }),
    Object.freeze({ id: "abort-controller", title: "Request cancellation", severity: "info" }),
    Object.freeze({ id: "session-heartbeat", title: "Signed-in session", severity: "blocker" }),
    Object.freeze({ id: "rq-engine-token", title: "Job service access", severity: "blocker" }),
    Object.freeze({ id: "bandwidth-rtt", title: "Connection response time", severity: "info" }),
    Object.freeze({ id: "bandwidth-download", title: "Download speed", severity: "info" }),
    Object.freeze({ id: "bandwidth-upload", title: "Upload speed", severity: "info" }),
    Object.freeze({ id: "realtime-status-websocket", title: "Live status updates", severity: "degraded" }),
    Object.freeze({ id: "realtime-preflight-websocket", title: "Live setup checks", severity: "degraded" }),
    Object.freeze({ id: "status-health-reachability", title: "Status service", severity: "degraded" }),
    Object.freeze({ id: "preflight-health-reachability", title: "Setup-check service", severity: "degraded" })
  ]);

  var FIXED_STATUS_TEXT = Object.freeze({
    pass: Object.freeze({
      evidence: "Check completed successfully.",
      fix_hint: ""
    }),
    fail: Object.freeze({
      evidence: "Check did not complete successfully.",
      fix_hint: "Review this check on the diagnostics page and retry."
    }),
    warn: Object.freeze({
      evidence: "Check completed with an advisory result.",
      fix_hint: "Review this check on the diagnostics page and retry."
    }),
    skipped: Object.freeze({
      evidence: "Check was not run.",
      fix_hint: "Review this check's prerequisites on the diagnostics page and retry."
    })
  });

  function normalizePrefix(value) {
    if (!value) {
      return "";
    }
    var text = String(value).trim();
    if (!text || text === "/") {
      return "";
    }
    if (text.charAt(0) !== "/") {
      text = "/" + text;
    }
    return text.replace(/\/+$/, "");
  }

  function normalizeCheck(rawCheck) {
    var check = rawCheck || {};
    var severity = ALLOWED_SEVERITIES[check.severity] ? check.severity : "info";
    var status = ALLOWED_STATUSES[check.status] ? check.status : "fail";

    return {
      id: String(check.id || "unknown-check"),
      title: String(check.title || "Unnamed check"),
      severity: severity,
      status: status,
      evidence: String(check.evidence || "No evidence provided."),
      fix_hint: String(check.fix_hint || "Review browser settings and retry diagnostics.")
    };
  }

  function buildOrderIndex(explicitOrder) {
    var orderIndex = {};
    var order = explicitOrder || [];
    var idx;

    for (idx = 0; idx < order.length; idx += 1) {
      orderIndex[String(order[idx])] = idx;
    }

    return orderIndex;
  }

  function sortChecksDeterministically(rawChecks, explicitOrder) {
    var checks = [];
    var idx;

    for (idx = 0; idx < rawChecks.length; idx += 1) {
      checks.push(normalizeCheck(rawChecks[idx]));
    }

    var orderIndex = buildOrderIndex(explicitOrder);

    checks.sort(function (left, right) {
      var leftRank = Object.prototype.hasOwnProperty.call(orderIndex, left.id)
        ? orderIndex[left.id]
        : 9007199254740991;
      var rightRank = Object.prototype.hasOwnProperty.call(orderIndex, right.id)
        ? orderIndex[right.id]
        : 9007199254740991;

      if (leftRank !== rightRank) {
        return leftRank - rightRank;
      }

      if (left.id < right.id) {
        return -1;
      }
      if (left.id > right.id) {
        return 1;
      }
      return 0;
    });

    return checks;
  }

  function isProblemStatus(status) {
    return status === "fail" || status === "warn";
  }

  function computeOverallStatus(checks) {
    var hasDegradedIssue = false;
    var idx;

    for (idx = 0; idx < checks.length; idx += 1) {
      var check = checks[idx];

      if (check.severity === "blocker" && isProblemStatus(check.status)) {
        return "not_ready";
      }

      if (check.severity === "degraded" && isProblemStatus(check.status)) {
        hasDegradedIssue = true;
      }
    }

    if (hasDegradedIssue) {
      return "ready_with_degraded_realtime";
    }

    return "ready";
  }

  function redactText(value) {
    var text = String(value || "");

    text = text.replace(/(authorization\s*[:=]\s*)([^\s,;]+)/gi, "$1[redacted]");
    text = text.replace(/(token\s*[:=]\s*)([^\s,;]+)/gi, "$1[redacted]");
    text = text.replace(/(cookie\s*[:=]\s*)([^\s,;]+)/gi, "$1[redacted]");
    text = text.replace(/\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b/g, "[redacted-jwt]");

    return text;
  }

  function normalizeCopiedPrefix(value) {
    var prefix = normalizePrefix(value);
    if (!prefix || !/^\/[A-Za-z0-9/_-]*$/.test(prefix)) {
      return "";
    }
    return prefix;
  }

  function redactCheck(check, catalogEntry) {
    var status = ALLOWED_STATUSES[check.status] ? check.status : "fail";
    var fixedText = FIXED_STATUS_TEXT[status];
    return {
      id: catalogEntry.id,
      title: catalogEntry.title,
      severity: catalogEntry.severity,
      status: status,
      evidence: redactText(fixedText.evidence),
      fix_hint: redactText(fixedText.fix_hint)
    };
  }

  function buildReport(rawChecks, options) {
    var sourceChecks = rawChecks || [];
    var context = options || {};
    var explicitOrder = context.checkOrder || [];
    var checks = sortChecksDeterministically(sourceChecks, explicitOrder);

    return {
      overall: computeOverallStatus(checks),
      checks: checks,
      generated_at: new Date().toISOString(),
      site_prefix: normalizePrefix(context.sitePrefix || "")
    };
  }

  function redactReport(report) {
    var source = report || {};
    var checks = Array.isArray(source.checks) ? source.checks : [];
    var firstCheckById = {};
    var redactedChecks = [];
    var idx;

    for (idx = 0; idx < checks.length; idx += 1) {
      var check = checks[idx] || {};
      var id = String(check.id || "");
      if (id && !Object.prototype.hasOwnProperty.call(firstCheckById, id)) {
        firstCheckById[id] = check;
      }
    }

    for (idx = 0; idx < REPORT_CHECK_CATALOG.length; idx += 1) {
      var catalogEntry = REPORT_CHECK_CATALOG[idx];
      if (Object.prototype.hasOwnProperty.call(firstCheckById, catalogEntry.id)) {
        redactedChecks.push(redactCheck(firstCheckById[catalogEntry.id], catalogEntry));
      }
    }

    return {
      overall: computeOverallStatus(redactedChecks),
      checks: redactedChecks,
      generated_at: new Date().toISOString(),
      site_prefix: normalizeCopiedPrefix(source.site_prefix || "")
    };
  }

  function toRedactedJson(report) {
    return JSON.stringify(redactReport(report), null, 2);
  }

  root.WEPPDiagnosticsReport = {
    buildReport: buildReport,
    computeOverallStatus: computeOverallStatus,
    sortChecksDeterministically: sortChecksDeterministically,
    reportCheckCatalog: REPORT_CHECK_CATALOG,
    redactReport: redactReport,
    toRedactedJson: toRedactedJson
  };
})(window);
