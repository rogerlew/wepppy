(function () {
  "use strict";

  var MAX_STATUS_MESSAGES = 400;
  var STATUS_RENDER_BATCH_MS = 100;
  var FORK_HEARTBEAT_PREFIX = "FORK_HEARTBEAT ";
  var FORK_STORAGE_PREFIX = "weppcloud:fork-console:";

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

  function _normalizeErrorCode(code) {
    if (typeof code !== "string") {
      return "";
    }
    return code.trim().toLowerCase();
  }

  function _extractErrorCode(body) {
    if (!body || typeof body !== "object") {
      return "";
    }
    if (body.error && typeof body.error === "object") {
      return _normalizeErrorCode(body.error.code);
    }
    return _normalizeErrorCode(body.code);
  }

  function isAuthFailureStatus(status, body) {
    if (status === 401 || status === 403) {
      return true;
    }
    var code = _extractErrorCode(body);
    return code === "unauthorized" || code === "forbidden";
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
    var config = dataset.config || dataset.configSlug || "cfg";
    var capRequired = dataset.capRequired === true || dataset.capRequired === "true";
    var capSection = dataset.capSection || "";
    var rqEngineToken = (dataset.rqEngineToken || "").trim();
    var undisturbifyRaw = dataset.undisturbify;
    var skipWeppRunsOutputRaw = dataset.skipWeppRunsOutput;
    var initialUndisturbify = false;
    var initialSkipWeppRunsOutput = false;
    if (typeof undisturbifyRaw === "string") {
      initialUndisturbify = undisturbifyRaw.toLowerCase() === "true";
    } else if (typeof undisturbifyRaw !== "undefined") {
      initialUndisturbify = Boolean(undisturbifyRaw);
    }
    if (typeof skipWeppRunsOutputRaw === "string") {
      initialSkipWeppRunsOutput = skipWeppRunsOutputRaw.toLowerCase() === "true";
    } else if (typeof skipWeppRunsOutputRaw !== "undefined") {
      initialSkipWeppRunsOutput = Boolean(skipWeppRunsOutputRaw);
    }

    var form = container.querySelector("#fork_form");
    var runIdInput = container.querySelector("#runid_input");
    var undisturbifyCheckbox = container.querySelector("#undisturbify_checkbox");
    var skipWeppRunsOutputCheckbox = container.querySelector("#skip_wepp_runs_output_checkbox");
    var submitButton = container.querySelector("#submit_button");
    var cancelButton = container.querySelector("#cancel_button");
    var consoleBlock = container.querySelector("#the_console");
    var statusPanel = container.querySelector("#fork_status_panel");
    var statusLog = container.querySelector("#fork_status_log");
    var stacktracePanel = container.querySelector("#fork_stacktrace_panel");
    var stacktraceBody = stacktracePanel ? stacktracePanel.querySelector("[data-stacktrace-body]") : null;
    var rqJob = container.querySelector("#rq_job");
    var liveProgress = container.querySelector("[data-fork-progress]");
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
    var authRecoveryTriggered = false;

    function storageKey() {
      return FORK_STORAGE_PREFIX + encodeURIComponent(runId) + ":" + encodeURIComponent(config);
    }

    function clearTrackedForkRecord() {
      try {
        if (window.sessionStorage) {
          window.sessionStorage.removeItem(storageKey());
        }
      } catch (err) {
        console.warn("Unable to clear fork tracking state:", err);
      }
    }

    function saveTrackedForkRecord() {
      if (!jobId || !newRunId) {
        return;
      }
      var record = {
        version: 1,
        runId: runId,
        config: config,
        jobId: jobId,
        newRunId: newRunId
      };
      try {
        if (window.sessionStorage) {
          window.sessionStorage.setItem(storageKey(), JSON.stringify(record));
        }
      } catch (err) {
        console.warn("Unable to persist fork tracking state:", err);
      }
    }

    function loadTrackedForkRecord() {
      var raw = null;
      try {
        if (!window.sessionStorage) {
          return null;
        }
        raw = window.sessionStorage.getItem(storageKey());
      } catch (err) {
        console.warn("Unable to read fork tracking state:", err);
        return null;
      }
      if (!raw) {
        return null;
      }
      try {
        var record = JSON.parse(raw);
        if (!record || record.version !== 1 || record.runId !== runId || record.config !== config) {
          clearTrackedForkRecord();
          return null;
        }
        if (typeof record.jobId !== "string" || !record.jobId.trim()
            || typeof record.newRunId !== "string" || !record.newRunId.trim()) {
          clearTrackedForkRecord();
          return null;
        }
        return {
          jobId: record.jobId.trim(),
          newRunId: record.newRunId.trim()
        };
      } catch (err) {
        clearTrackedForkRecord();
        return null;
      }
    }

    function setLiveProgress(message) {
      if (!liveProgress) {
        return;
      }
      liveProgress.textContent = message || "";
      liveProgress.hidden = !message;
    }

    function appendNewRunLink(target, prefix) {
      if (!target) {
        return;
      }
      target.appendChild(document.createTextNode(prefix));
      var link = document.createElement("a");
      link.href = origin + "/weppcloud/runs/" + encodeURIComponent(newRunId) + "/cfg";
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = newRunId;
      target.appendChild(link);
    }

    function formatForkStatus(message) {
      var text = message === undefined || message === null ? "" : String(message);
      if (text.indexOf(FORK_HEARTBEAT_PREFIX) === 0) {
        setLiveProgress(text.slice(FORK_HEARTBEAT_PREFIX.length));
        return "";
      }
      if (/^Copying project files\.\.\. done\.$/.test(text)) {
        setLiveProgress("");
      }
      return text;
    }

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

    function fetchSessionToken() {
      var sessionHelper = window.WCHttp && typeof window.WCHttp.getSessionToken === "function"
        ? window.WCHttp
        : null;
      if (sessionHelper) {
        return sessionHelper.getSessionToken(runId, config);
      }
      var tokenUrl = origin + "/rq-engine/api/runs/" + runId + "/" + config + "/session-token";
      return fetch(tokenUrl, { method: "POST", headers: { Accept: "application/json" } })
        .then(function (resp) {
          return resp.json().then(function (payload) {
            if (!resp.ok) {
              var message = resolveErrorMessage(payload, "Session token request failed");
              var error = new Error(message);
              error.status = resp.status;
              error.body = payload;
              throw error;
            }
            return payload;
          });
        })
        .then(function (payload) {
          if (!payload || !payload.token) {
            throw new Error("Session token response missing token");
          }
          return payload.token;
        });
    }

    function handleStaleAuth(message) {
      if (authRecoveryTriggered) {
        return;
      }
      authRecoveryTriggered = true;
      var prompt = "Your session expired. Reload this page and sign in again.";
      if (message) {
        prompt = message + " " + prompt;
      }
      if (consoleBlock) {
        consoleBlock.dataset.state = "critical";
        consoleBlock.textContent = prompt;
      }
      appendStatus(prompt);
      if (submitButton) {
        submitButton.disabled = true;
      }
      window.alert(prompt);
      var userAgent = window.navigator && window.navigator.userAgent
        ? String(window.navigator.userAgent).toLowerCase()
        : "";
      if (userAgent.indexOf("jsdom") !== -1) {
        return;
      }
      if (window.location && typeof window.location.reload === "function") {
        try {
          window.location.reload();
        } catch (err) {
          console.warn("Reload failed after auth expiration prompt:", err);
        }
      }
    }

    function requestWithBearerToken(url, options, token) {
      var requestOptions = options ? Object.assign({}, options) : {};
      var headers = requestOptions.headers ? Object.assign({}, requestOptions.headers) : {};
      headers.Authorization = "Bearer " + token;
      requestOptions.headers = headers;

      if (window.WCHttp && typeof window.WCHttp.request === "function") {
        return window.WCHttp.request(url, requestOptions);
      }

      return fetch(url, requestOptions).then(function (resp) {
        return resp.text().then(function (text) {
          var body = null;
          if (text) {
            try {
              body = JSON.parse(text);
            } catch (err) {
              body = text;
            }
          }
          if (!resp.ok) {
            var errMsg = resolveErrorMessage(body, "Request failed");
            var error = new Error(errMsg);
            error.status = resp.status;
            error.detail = errMsg;
            error.body = body;
            if (body && typeof body === "object" && body.error && body.error.details !== undefined) {
              error.details = body.error.details;
            }
            throw error;
          }
          return { ok: true, body: body };
        });
      });
    }

    function requestWithRenewal(url, options) {
      var sessionHelper = window.WCHttp && typeof window.WCHttp.requestWithSessionToken === "function"
        ? window.WCHttp
        : null;

      if (rqEngineToken) {
        return requestWithBearerToken(url, options, rqEngineToken).catch(function (error) {
          if (error && (error.status === 401 || error.status === 403)) {
            rqEngineToken = "";
            if (sessionHelper) {
              var fallbackOptions = options ? Object.assign({}, options) : {};
              fallbackOptions.runId = runId;
              fallbackOptions.config = config;
              return sessionHelper.requestWithSessionToken(url, fallbackOptions);
            }
            return fetchSessionToken().then(function (token) {
              return requestWithBearerToken(url, options, token);
            });
          }
          throw error;
        });
      }

      if (!sessionHelper) {
        return fetchSessionToken().then(function (token) {
          return requestWithBearerToken(url, options, token);
        });
      }
      var requestOptions = options ? Object.assign({}, options) : {};
      requestOptions.runId = runId;
      requestOptions.config = config;
      return sessionHelper.requestWithSessionToken(url, requestOptions);
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
      setLiveProgress("");
      if (stacktracePanel && stacktraceBody) {
        stacktraceBody.textContent = "";
        stacktracePanel.hidden = true;
        if (typeof stacktracePanel.open !== "undefined") {
          stacktracePanel.open = false;
        }
      }
    }

    function handleForkComplete() {
      clearTrackedForkRecord();
      jobId = "";
      setLiveProgress("");
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
          link.href = origin + "/weppcloud/runs/" + encodeURIComponent(newRunId) + "/cfg";
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
      clearTrackedForkRecord();
      jobId = "";
      setLiveProgress("");
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
      var fromPoll = detail && detail.source === "poll";
      if (normalized === "FORK_COMPLETE" || normalized === "JOB:COMPLETED") {
        if (fromPoll) {
          markCompleted(detail);
        } else {
          requestAuthoritativeJobStatus("Completion signal received; confirming job status...");
        }
      } else if (normalized === "FORK_FAILED" || normalized === "JOB:ERROR") {
        if (fromPoll) {
          markFailed(detail);
        } else {
          requestAuthoritativeJobStatus("Failure signal received; confirming job status...");
        }
      }
    }

    function requestAuthoritativeJobStatus(message) {
      if (!poller || !poller.rq_job_id || completionState.completed || completionState.failed) {
        return;
      }
      if (message) {
        setLiveProgress(message);
      }
      if (typeof poller.fetch_job_status === "function") {
        poller.fetch_job_status(poller);
      }
    }

    function reconcileTrackedJob() {
      requestAuthoritativeJobStatus("Checking current fork job status...");
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
        renderBatchMs: STATUS_RENDER_BATCH_MS,
        formatter: formatForkStatus,
        stacktrace: stacktrace,
        onTrigger: handleTrigger,
        autoConnect: false
      });
      if (poller) {
        poller.statusStream = statusStream;
      }
      flushPendingStatus();
      if (statusStream && typeof statusStream.connect === "function") {
        statusStream.connect();
      }
    }

    function showTrackedJob(restored) {
      if (consoleBlock) {
        consoleBlock.dataset.state = "attention";
        if (restored) {
          consoleBlock.innerHTML = "";
          appendNewRunLink(consoleBlock, "Restored fork job for ");
          consoleBlock.appendChild(document.createTextNode("."));
        }
      }
      if (submitButton) {
        submitButton.hidden = true;
        submitButton.disabled = true;
      }
      if (cancelButton) {
        cancelButton.hidden = false;
        cancelButton.disabled = false;
      }
      connectStatusStreamForRun(runId);
      if (poller) {
        poller.set_rq_job_id(poller, jobId);
      }
    }

    function restoreTrackedJob() {
      var record = loadTrackedForkRecord();
      if (!record) {
        return;
      }
      jobId = record.jobId;
      newRunId = record.newRunId;
      resetCompletionState();
      setLiveProgress("Restored fork job; checking current status...");
      showTrackedJob(true);
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
      var skipWeppRunsOutput = skipWeppRunsOutputCheckbox ? !!skipWeppRunsOutputCheckbox.checked : false;

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

      var forkUrl = origin + "/rq-engine/api/runs/" + runId + "/" + config + "/fork";
      var payload = new URLSearchParams({
        undisturbify: undisturbify ? "true" : "false",
        skip_wepp_runs_output: skipWeppRunsOutput ? "true" : "false"
      });
      if (capRequired) {
        var verifiedToken = getCapToken();
        if (verifiedToken) {
          payload.set("cap_token", verifiedToken);
        }
      }

      var submitPromise;
      if (capRequired) {
        submitPromise = fetch(forkUrl, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: payload.toString()
        }).then(function (resp) {
          return resp.text().then(function (text) {
            var body = null;
            if (text) {
              try {
                body = JSON.parse(text);
              } catch (err) {
                body = text;
              }
            }
            return { ok: resp.ok, status: resp.status, body: body };
          });
        });
      } else {
        submitPromise = requestWithRenewal(forkUrl, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: payload.toString()
        }).then(function (result) {
          return { ok: true, status: 200, body: result && result.body ? result.body : {} };
        });
      }

      submitPromise
        .then(function (result) {
          var body = result && result.body ? result.body : {};
          if (!result || !result.ok || hasErrorPayload(body)) {
            var errMsg = resolveErrorMessage(body, "Fork submission failed");
            if (!capRequired && isAuthFailureStatus(result && result.status, body)) {
              handleStaleAuth(errMsg);
              return;
            }
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
          var skipWeppRunsOutputFlag = body.skip_wepp_runs_output;

          if (consoleBlock) {
            consoleBlock.dataset.state = "attention";
            consoleBlock.innerHTML = "";
            appendNewRunLink(consoleBlock, "New runid: ");
            consoleBlock.appendChild(document.createElement("br"));
            consoleBlock.appendChild(document.createTextNode("Undisturbify: " + undisturbifyFlag));
            consoleBlock.appendChild(document.createElement("br"));
            consoleBlock.appendChild(document.createTextNode("Skip wepp/runs + wepp/output: " + skipWeppRunsOutputFlag));
          }

          if (submitButton) {
            submitButton.hidden = true;
          }
          if (cancelButton) {
            cancelButton.hidden = false;
            cancelButton.disabled = false;
          }

          saveTrackedForkRecord();
          showTrackedJob(false);
        })
        .catch(function (err) {
          if (!capRequired && isAuthFailureStatus(err && err.status, err && err.body)) {
            var authMessage = err && err.message ? String(err.message) : "Fork submission failed";
            handleStaleAuth(authMessage);
            return;
          }
          var detail = err && err.detail ? String(err.detail) : null;
          var message = detail || (err && err.message ? err.message : String(err));
          var detailsBody = null;
          if (err && err.details !== undefined) {
            detailsBody = { error: { details: err.details } };
          } else if (err && err.body && typeof err.body === "object") {
            detailsBody = err.body;
          }
          if (consoleBlock) {
            consoleBlock.dataset.state = "critical";
            consoleBlock.textContent = "Error: " + message;
          }
          appendStatus("Error submitting fork job: " + message);
          renderErrorDetails(detailsBody);
          if (!detailsBody && err && err.stack) {
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
      appendStatus("Canceling job " + jobId + "...");
      var sessionHelper = window.WCHttp && typeof window.WCHttp.getSessionToken === "function"
        ? window.WCHttp
        : null;

      if (!capRequired && window.WCHttp && typeof window.WCHttp.requestWithSessionToken === "function") {
        requestWithRenewal("/rq-engine/api/canceljob/" + encodeURIComponent(jobId), {
          method: "POST"
        })
          .then(function () {
            appendStatus("Cancel request acknowledged for " + jobId + ".");
            window.alert("Job canceled");
          })
          .catch(function (err) {
            if (!capRequired && isAuthFailureStatus(err && err.status, err && err.body)) {
              var authMessage = err && err.message ? String(err.message) : "Unable to cancel job.";
              handleStaleAuth(authMessage);
              return;
            }
            var detail = err && err.detail ? String(err.detail) : null;
            var message = detail || (err && err.message ? err.message : String(err));
            console.error(err);
            appendStatus("Cancel request failed: " + message);
            window.alert("Unable to cancel job.");
          })
          .finally(function () {
            if (cancelButton) {
              cancelButton.disabled = false;
            }
          });
        return;
      }

      var tokenPromise = sessionHelper ? sessionHelper.getSessionToken(runId, config) : fetchSessionToken();

      tokenPromise
        .then(function (token) {
          var requestFn = sessionHelper && typeof sessionHelper.request === "function"
            ? sessionHelper.request.bind(sessionHelper)
            : null;
          if (requestFn) {
            return requestFn("/rq-engine/api/canceljob/" + encodeURIComponent(jobId), {
              method: "POST",
              headers: {
                Authorization: "Bearer " + token
              }
            });
          }
          return requestWithBearerToken(
            "/rq-engine/api/canceljob/" + encodeURIComponent(jobId),
            { method: "POST" },
            token
          );
        })
        .then(function () {
          appendStatus("Cancel request acknowledged for " + jobId + ".");
          window.alert("Job canceled");
        })
        .catch(function (err) {
          if (!capRequired && isAuthFailureStatus(err && err.status, err && err.body)) {
            var authMessage = err && err.message ? String(err.message) : "Unable to cancel job.";
            handleStaleAuth(authMessage);
            return;
          }
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
    if (skipWeppRunsOutputCheckbox) {
      skipWeppRunsOutputCheckbox.checked = initialSkipWeppRunsOutput;
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
    container.__forkConsoleReconcileJob = reconcileTrackedJob;
    restoreTrackedJob();
  }

  function reconcileVisibleForkConsoles() {
    var containers = document.querySelectorAll('[data-controller="fork-console"]');
    containers.forEach(function (container) {
      if (typeof container.__forkConsoleReconcileJob === "function") {
        container.__forkConsoleReconcileJob();
      }
    });
  }

  function attachRecoveryListeners() {
    if (window.__forkConsoleRecoveryListenersAttached === true) {
      return;
    }
    window.__forkConsoleRecoveryListenersAttached = true;
    document.addEventListener("visibilitychange", function () {
      if (document.hidden !== true) {
        reconcileVisibleForkConsoles();
      }
    });
    window.addEventListener("focus", reconcileVisibleForkConsoles);
    window.addEventListener("pageshow", reconcileVisibleForkConsoles);
  }

  ready(function () {
    attachRecoveryListeners();
    var containers = document.querySelectorAll('[data-controller="fork-console"]');
    containers.forEach(initForkConsole);
  });
})();
