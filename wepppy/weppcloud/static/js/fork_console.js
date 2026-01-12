(function () {
  "use strict";

  var MAX_STATUS_MESSAGES = 3000;

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  function createHintAdapter(element) {
    if (!element) {
      return null;
    }

    return {
      element: element,
      length: 1,
      show: function () {
        element.hidden = false;
        if (element.style && element.style.display === "none") {
          element.style.removeProperty("display");
        }
      },
      hide: function () {
        element.hidden = true;
        if (element.style) {
          element.style.display = "none";
        }
      },
      html: function (value) {
        if (value === undefined) {
          return element.innerHTML;
        }
        element.innerHTML = value === null ? "" : String(value);
      }
    };
  }

  function normalizeErrorValue(value) {
    if (value === undefined || value === null) {
      return null;
    }
    if (typeof value === "string") {
      return value;
    }
    if (Array.isArray(value)) {
      return value.map(function (item) {
        return item === undefined || item === null ? "" : String(item);
      }).join("\n");
    }
    if (typeof value === "object") {
      if (typeof value.message === "string") {
        return value.message;
      }
      if (typeof value.detail === "string") {
        return value.detail;
      }
      if (typeof value.details === "string") {
        return value.details;
      }
      if (value.details !== undefined) {
        return normalizeErrorValue(value.details);
      }
      try {
        return JSON.stringify(value);
      } catch (err) {
        return String(value);
      }
    }
    return String(value);
  }

  function formatErrorList(errors) {
    if (!Array.isArray(errors)) {
      return null;
    }
    var parts = [];
    errors.forEach(function (entry) {
      if (entry === undefined || entry === null) {
        return;
      }
      if (typeof entry === "string") {
        parts.push(entry);
        return;
      }
      if (typeof entry.message === "string") {
        parts.push(entry.message);
        return;
      }
      if (typeof entry.detail === "string") {
        parts.push(entry.detail);
        return;
      }
      if (typeof entry.code === "string") {
        parts.push(entry.code);
        return;
      }
      try {
        parts.push(JSON.stringify(entry));
      } catch (err) {
        parts.push(String(entry));
      }
    });
    return parts.length ? parts.join("\n") : null;
  }

  function resolveErrorMessage(body, fallback) {
    if (body && typeof body === "object") {
      if (body.error !== undefined) {
        var message = normalizeErrorValue(body.error);
        if (message) {
          return message;
        }
      }
      if (body.errors) {
        var errorList = formatErrorList(body.errors);
        if (errorList) {
          return errorList;
        }
      }
      if (body.message !== undefined) {
        return normalizeErrorValue(body.message);
      }
      if (body.detail !== undefined) {
        return normalizeErrorValue(body.detail);
      }
    }
    return fallback || null;
  }

  function hasErrorPayload(body) {
    return Boolean(body && typeof body === "object" && (body.error || body.errors));
  }

  function initForkConsole(container) {
    if (!container || container.__forkConsoleInit === true) {
      return;
    }

    container.__forkConsoleInit = true;

    var configReader = window.WCConsoleConfig && typeof window.WCConsoleConfig.readConfig === "function"
      ? window.WCConsoleConfig.readConfig
      : null;
    var dataset = configReader ? configReader(container, "[data-fork-console-config]") : (container.dataset || {});

    var origin = window.location.origin;
    var runId = dataset.runid || dataset.runId || "";
    var capRequired = dataset.capRequired === true || dataset.capRequired === "true";
    var capSection = dataset.capSection || "";
    var undisturbifyRaw = dataset.undisturbify;
    var initialUndisturbify = false;
    if (typeof undisturbifyRaw === "string") {
      initialUndisturbify = undisturbifyRaw.toLowerCase() === "true";
    } else if (typeof undisturbifyRaw !== "undefined") {
      initialUndisturbify = Boolean(undisturbifyRaw);
    }

    var form = container.querySelector("#fork_form");
    var runIdInput = container.querySelector("#runid_input");
    var undisturbifyCheckbox = container.querySelector("#undisturbify_checkbox");
    var submitButton = container.querySelector("#submit_button");
    var cancelButton = container.querySelector("#cancel_button");
    var consoleBlock = container.querySelector("#the_console");
    var statusPanel = container.querySelector("#fork_status_panel");
    var statusLog = container.querySelector("#fork_status_log");
    var stacktracePanel = container.querySelector("#fork_stacktrace_panel");
    var stacktraceBody = stacktracePanel ? stacktracePanel.querySelector("[data-stacktrace-body]") : null;
    var rqJob = container.querySelector("#rq_job");
    var hintElement = container.querySelector("#hint_run_fork");
    var hintAdapter = createHintAdapter(hintElement);
    var capTokenInput = null;
    var capPrompt = null;
    var capTrigger = null;
    var capStatus = null;

    var statusStream = null;
    var pendingStatusMessages = [];
    var jobId = "";
    var newRunId = "";
    var poller = null;
    var completionState = { completed: false, failed: false };

    function initCapElements() {
      if (!capRequired || !capSection) {
        return;
      }
      capTokenInput = form ? form.querySelector("[data-cap-token]") : null;
      capPrompt = container.querySelector('.wc-cap-prompt[data-cap-section="' + capSection + '"]');
      if (capPrompt) {
        capTrigger = capPrompt.querySelector("[data-cap-trigger]");
        capStatus = capPrompt.querySelector("[data-cap-status]");
      }
    }

    function getCapToken() {
      if (!capTokenInput) {
        return "";
      }
      return (capTokenInput.value || "").trim();
    }

    function setCapVerified(token) {
      if (!token) {
        return;
      }
      if (capTokenInput) {
        capTokenInput.value = token;
      }
      if (capPrompt) {
        capPrompt.setAttribute("data-cap-verified", "true");
      }
      if (capTrigger) {
        capTrigger.classList.add("is-verified");
        capTrigger.setAttribute("aria-disabled", "true");
        capTrigger.setAttribute("disabled", "true");
      }
      if (capStatus) {
        capStatus.textContent = "Verification complete.";
      }
      if (submitButton) {
        submitButton.classList.remove("is-disabled");
        submitButton.removeAttribute("disabled");
        submitButton.disabled = false;
        submitButton.setAttribute("aria-disabled", "false");
      }
    }

    function triggerCapPrompt() {
      if (!capTrigger || capTrigger.disabled) {
        return false;
      }
      capTrigger.click();
      return true;
    }

    function attachCapHandlers() {
      if (!capRequired || !capSection) {
        return;
      }
      var widgets = container.querySelectorAll('cap-widget[data-cap-section="' + capSection + '"]');
      widgets.forEach(function (widget) {
        widget.addEventListener("solve", function (event) {
          var detail = event && event.detail ? event.detail : null;
          var token = detail && detail.token ? String(detail.token) : "";
          if (!token) {
            return;
          }
          setCapVerified(token);
        });
      });
    }

    function appendStatus(message) {
      if (message === undefined || message === null) {
        return;
      }
      var text = typeof message === "string" ? message : String(message);
      if (statusStream) {
        statusStream.append(text);
        return;
      }
      pendingStatusMessages.push(text);
      if (pendingStatusMessages.length > MAX_STATUS_MESSAGES) {
        pendingStatusMessages.splice(0, pendingStatusMessages.length - MAX_STATUS_MESSAGES);
      }
      if (statusLog) {
        statusLog.textContent = pendingStatusMessages.join("\n") + "\n";
        statusLog.scrollTop = statusLog.scrollHeight;
      }
    }

    function resetCompletionState() {
      completionState.completed = false;
      completionState.failed = false;
    }

    function resetJobStatus() {
      if (poller) {
        poller.set_rq_job_id(poller, null);
        return;
      }
      if (rqJob) {
        rqJob.textContent = "";
      }
    }

    function flushPendingStatus() {
      if (!statusStream || pendingStatusMessages.length === 0) {
        return;
      }
      if (statusStream.logElement && statusStream.logElement.textContent) {
        var expected = pendingStatusMessages.join("\n") + "\n";
        if (statusStream.logElement.textContent === expected) {
          pendingStatusMessages.length = 0;
          return;
        }
      }
      pendingStatusMessages.splice(0).forEach(function (msg) {
        statusStream.append(msg);
      });
    }

    function resetStatusLog() {
      pendingStatusMessages.length = 0;
      resetCompletionState();
      if (statusStream) {
        statusStream.disconnect();
        statusStream = null;
      }
      if (poller) {
        poller.statusStream = null;
      }
      resetJobStatus();
      if (statusLog) {
        statusLog.textContent = "";
      }
      if (stacktracePanel && stacktraceBody) {
        stacktraceBody.textContent = "";
        stacktracePanel.hidden = true;
        if (typeof stacktracePanel.open !== "undefined") {
          stacktracePanel.open = false;
        }
      }
    }

    function handleForkComplete() {
      jobId = "";
      if (cancelButton) {
        cancelButton.hidden = true;
        cancelButton.disabled = false;
      }
      if (submitButton) {
        submitButton.hidden = false;
        submitButton.disabled = false;
      }
      if (consoleBlock) {
        consoleBlock.dataset.state = "positive";
        if (newRunId) {
          var link = document.createElement("a");
          link.href = origin + "/weppcloud/runs/" + newRunId + "/cfg";
          link.target = "_blank";
          link.rel = "noopener";
          link.textContent = "Load " + newRunId + " project";
          link.className = "pure-button pure-button-secondary";
          consoleBlock.innerHTML = "";
          consoleBlock.appendChild(link);
        } else {
          consoleBlock.textContent = "Fork job completed.";
        }
      }
      appendStatus("Fork job completed.");
    }

    function handleForkFailed() {
      jobId = "";
      if (cancelButton) {
        cancelButton.hidden = true;
        cancelButton.disabled = false;
      }
      if (submitButton) {
        submitButton.hidden = false;
        submitButton.disabled = false;
      }
      if (consoleBlock) {
        consoleBlock.dataset.state = "critical";
        consoleBlock.textContent = "Fork job failed. Review the status log for details.";
      }
      appendStatus("Fork job failed.");
    }

    function markCompleted(detail) {
      if (completionState.completed) {
        return;
      }
      completionState.completed = true;
      completionState.failed = false;
      handleForkComplete(detail);
    }

    function markFailed(detail) {
      if (completionState.failed) {
        return;
      }
      completionState.failed = true;
      completionState.completed = false;
      handleForkFailed(detail);
    }

    function handleTrigger(eventOrDetail, payload) {
      var eventName = null;
      var detail = null;
      if (typeof eventOrDetail === "string") {
        eventName = eventOrDetail;
        detail = payload || {};
      } else if (eventOrDetail && eventOrDetail.event) {
        eventName = eventOrDetail.event;
        detail = eventOrDetail;
      }
      if (!eventName) {
        return;
      }
      var normalized = String(eventName).toUpperCase();
      if (normalized === "FORK_COMPLETE" || normalized === "JOB:COMPLETED") {
        markCompleted(detail);
      } else if (normalized === "FORK_FAILED" || normalized === "JOB:ERROR") {
        markFailed(detail);
      }
    }

    function initPoller() {
      if (typeof controlBase !== "function") {
        console.warn("controlBase is unavailable; fork polling disabled.");
        return;
      }
      poller = controlBase();
      poller.form = form;
      poller.rq_job = rqJob;
      poller.stacktrace = stacktraceBody;
      poller.hint = hintAdapter;
      poller.poll_completion_event = "FORK_COMPLETE";
      poller.triggerEvent = function (eventName, detail) {
        handleTrigger(eventName, detail);
      };
    }

    function connectStatusStreamForRun(currentRunId) {
      if (typeof StatusStream === "undefined") {
        console.error("StatusStream module is unavailable.");
        return;
      }
      if (!statusPanel) {
        return;
      }
      if (statusStream) {
        statusStream.disconnect();
      }
      var stacktrace = stacktracePanel ? { element: stacktracePanel } : null;
      statusStream = StatusStream.attach({
        element: statusPanel,
        channel: "fork",
        runId: currentRunId,
        logLimit: MAX_STATUS_MESSAGES,
        stacktrace: stacktrace,
        onTrigger: handleTrigger
      });
      if (poller) {
        poller.statusStream = statusStream;
      }
      flushPendingStatus();
    }

    function showStacktrace(lines) {
      if (!stacktracePanel || !stacktraceBody) {
        return;
      }
      stacktracePanel.hidden = false;
      if (typeof stacktracePanel.open !== "undefined") {
        stacktracePanel.open = true;
      }
      var text = "";
      if (Array.isArray(lines)) {
        text = lines.map(function (item) {
          return item === undefined || item === null ? "" : String(item);
        }).join("\n");
      } else if (lines && typeof lines === "object") {
        try {
          text = JSON.stringify(lines, null, 2);
        } catch (err) {
          text = String(lines);
        }
      } else {
        text = String(lines || "");
      }
      stacktraceBody.textContent = text;
    }

    function renderErrorDetails(body) {
      if (!stacktracePanel || !stacktraceBody) {
        return;
      }
      var details = null;
      if (body && typeof body === "object") {
        if (body.error && Object.prototype.hasOwnProperty.call(body.error, "details")) {
          details = body.error.details;
        } else if (body.errors) {
          details = body.errors;
        }
      }
      if (details === null || details === undefined) {
        stacktraceBody.textContent = "";
        stacktracePanel.hidden = true;
        if (typeof stacktracePanel.open !== "undefined") {
          stacktracePanel.open = false;
        }
        return;
      }
      showStacktrace(details);
    }

    function forkProject(event) {
      event.preventDefault();
      if (!form) {
        return;
      }
      var submittedRunId = runIdInput ? (runIdInput.value || "").trim() : "";
      if (!submittedRunId) {
        if (runIdInput) {
          runIdInput.focus();
        }
        return;
      }

      runId = submittedRunId;
      var undisturbify = undisturbifyCheckbox ? !!undisturbifyCheckbox.checked : false;

      if (capRequired) {
        var capToken = getCapToken();
        if (!capToken) {
          triggerCapPrompt();
          return;
        }
      }

      if (submitButton) {
        submitButton.disabled = true;
      }
      if (consoleBlock) {
        consoleBlock.dataset.state = "attention";
        consoleBlock.textContent = "Submitting fork job...";
      }

      resetStatusLog();
      appendStatus("Submitting fork job...");

      var forkUrl = origin + "/weppcloud/runs/" + runId + "/cfg/rq/api/fork";
      var payload = new URLSearchParams({ undisturbify: undisturbify ? "true" : "false" });
      if (capRequired) {
        var verifiedToken = getCapToken();
        if (verifiedToken) {
          payload.set("cap_token", verifiedToken);
        }
      }

      fetch(forkUrl, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: payload.toString()
      })
        .then(function (resp) {
          return resp.text().then(function (text) {
            var body = null;
            if (text) {
              try {
                body = JSON.parse(text);
              } catch (err) {
                body = text;
              }
            }
            return { ok: resp.ok, body: body };
          });
        })
        .then(function (result) {
          var body = result.body || {};
          if (!result.ok || hasErrorPayload(body)) {
            var errMsg = resolveErrorMessage(body, "Fork submission failed");
            if (consoleBlock) {
              consoleBlock.dataset.state = "critical";
              consoleBlock.textContent = "Error: " + errMsg;
            }
            appendStatus("Error submitting fork job: " + errMsg);
            renderErrorDetails(body);
            if (submitButton) {
              submitButton.disabled = false;
              submitButton.hidden = false;
            }
            return;
          }
          if (!body || typeof body !== "object") {
            var unknownErr = "Fork submission failed";
            if (consoleBlock) {
              consoleBlock.dataset.state = "critical";
              consoleBlock.textContent = "Error: " + unknownErr;
            }
            appendStatus("Error submitting fork job: " + unknownErr);
            renderErrorDetails(null);
            if (submitButton) {
              submitButton.disabled = false;
              submitButton.hidden = false;
            }
            return;
          }
          newRunId = body.new_runid || "";
          jobId = body.job_id || "";
          var undisturbifyFlag = body.undisturbify;

          if (consoleBlock) {
            var jobDashboard = origin + "/weppcloud/rq/job-dashboard/" + jobId;
            var newRunLink = origin + "/weppcloud/runs/" + newRunId + "/cfg";
            consoleBlock.dataset.state = "attention";
            consoleBlock.innerHTML = [
              'New runid: <a href="' + newRunLink + '" target="_blank" rel="noopener">' + newRunId + "</a>",
              "Undisturbify: " + undisturbifyFlag
            ].join("<br>");
          }

          if (submitButton) {
            submitButton.hidden = true;
          }
          if (cancelButton) {
            cancelButton.hidden = false;
            cancelButton.disabled = false;
          }

          connectStatusStreamForRun(runId);
          if (poller) {
            poller.set_rq_job_id(poller, jobId);
          }
        })
        .catch(function (err) {
          if (consoleBlock) {
            consoleBlock.dataset.state = "critical";
            consoleBlock.textContent = "Error: " + (err.message || err);
          }
          appendStatus("Error submitting fork job: " + (err.message || err));
          renderErrorDetails(err && err.details ? { error: { details: err.details } } : null);
          if (err && err.stack) {
            showStacktrace(err.stack.split("\n"));
          }
          if (submitButton) {
            submitButton.disabled = false;
            submitButton.hidden = false;
          }
        });
    }

    function cancelJob() {
      if (!jobId) {
        return;
      }
      if (cancelButton) {
        cancelButton.disabled = true;
      }
      appendStatus("Cancelling job " + jobId + "...");
      var cancelUrl = origin + "/weppcloud/rq/canceljob/" + jobId;
      fetch(cancelUrl, { method: "GET" })
        .then(function (resp) {
          if (!resp.ok) {
            throw new Error("Cancel job failed");
          }
          appendStatus("Cancel request acknowledged for " + jobId + ".");
          window.alert("Job cancelled");
        })
        .catch(function (err) {
          console.error(err);
          appendStatus("Cancel request failed: " + (err.message || err));
          window.alert("Unable to cancel job.");
        })
        .finally(function () {
          if (cancelButton) {
            cancelButton.disabled = false;
          }
        });
    }

    if (stacktracePanel) {
      stacktracePanel.hidden = true;
    }
    if (undisturbifyCheckbox) {
      undisturbifyCheckbox.checked = initialUndisturbify;
    }
    if (form) {
      form.addEventListener("submit", forkProject);
    }
    if (cancelButton) {
      cancelButton.addEventListener("click", cancelJob);
    }
    if (statusPanel) {
      statusPanel.addEventListener("status:error", function (event) {
        if (event && event.detail && event.detail.error) {
          console.error("Fork status stream error:", event.detail.error);
        }
      });
    }

    initCapElements();
    attachCapHandlers();
    initPoller();
    connectStatusStreamForRun(runId);
    flushPendingStatus();
  }

  ready(function () {
    var containers = document.querySelectorAll('[data-controller="fork-console"]');
    containers.forEach(initForkConsole);
  });
})();
