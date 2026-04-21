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

  function redactCheck(check) {
    return {
      id: String(check.id || "unknown-check"),
      title: String(check.title || "Unnamed check"),
      severity: ALLOWED_SEVERITIES[check.severity] ? check.severity : "info",
      status: ALLOWED_STATUSES[check.status] ? check.status : "fail",
      evidence: redactText(check.evidence),
      fix_hint: redactText(check.fix_hint)
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
    var checks = source.checks || [];
    var redactedChecks = [];
    var idx;

    for (idx = 0; idx < checks.length; idx += 1) {
      redactedChecks.push(redactCheck(checks[idx]));
    }

    return {
      overall: String(source.overall || "not_ready"),
      checks: redactedChecks,
      generated_at: String(source.generated_at || ""),
      site_prefix: normalizePrefix(source.site_prefix || "")
    };
  }

  function toRedactedJson(report) {
    return JSON.stringify(redactReport(report), null, 2);
  }

  root.WEPPDiagnosticsReport = {
    buildReport: buildReport,
    computeOverallStatus: computeOverallStatus,
    sortChecksDeterministically: sortChecksDeterministically,
    redactReport: redactReport,
    toRedactedJson: toRedactedJson
  };
})(window);
