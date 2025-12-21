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

    var statusStream = null;
    var pendingStatusMessages = [];
    var jobId = "";
    var newRunId = "";
    var poller = null;
    var completionState = { completed: false, failed: false };

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
      var text = Array.isArray(lines) ? lines.join("\n") : String(lines || "");
      stacktraceBody.textContent = text;
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

      fetch(forkUrl, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: payload.toString()
      })
        .then(function (resp) {
          return resp.json();
        })
        .then(function (body) {
          if (!body.Success) {
            var errMsg = body.Error || "Fork submission failed";
            if (consoleBlock) {
              consoleBlock.dataset.state = "critical";
              consoleBlock.textContent = "Error: " + errMsg;
            }
            appendStatus("Error submitting fork job: " + errMsg);
            if (body.StackTrace) {
              showStacktrace(body.StackTrace);
            }
            if (submitButton) {
              submitButton.disabled = false;
              submitButton.hidden = false;
            }
            return;
          }
          newRunId = body.new_runid || "";
          jobId = body.job_id || "";
          var undisturbifyFlag = body.undisturbify;

          appendStatus("Fork job submitted: " + jobId);

          if (consoleBlock) {
            var jobDashboard = origin + "/weppcloud/rq/job-dashboard/" + jobId;
            var newRunLink = origin + "/weppcloud/runs/" + newRunId + "/cfg";
            consoleBlock.dataset.state = "attention";
            consoleBlock.innerHTML = [
              'Fork job submitted: <a href="' + jobDashboard + '" target="_blank" rel="noopener">' + jobId + "</a>",
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

    initPoller();
    connectStatusStreamForRun(runId);
    flushPendingStatus();
  }

  ready(function () {
    var containers = document.querySelectorAll('[data-controller="fork-console"]');
    containers.forEach(initForkConsole);
  });
})();
