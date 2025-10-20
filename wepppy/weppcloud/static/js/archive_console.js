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

  function initArchiveConsole(container) {
    if (!container || container.__archiveConsoleInit === true) {
      return;
    }
    container.__archiveConsoleInit = true;

    var dataset = container.dataset || {};
    var runId = dataset.runid || dataset.runId || "";
    var archivesUrl = dataset.archivesUrl || dataset.archivesurl || "";
    var archiveApiUrl = dataset.archiveApiUrl || dataset.archiveapiurl || "";
    var restoreApiUrl = dataset.restoreApiUrl || dataset.restoreapiurl || "";
    var deleteApiUrl = dataset.deleteApiUrl || dataset.deleteapiurl || "";
    var projectPath = dataset.projectPath || dataset.projectpath || "";
    var isUserAnonymous = String(dataset.userAnonymous || dataset.useranonymous || "").toLowerCase() === "true";

    var statusPanel = container.querySelector("#archive_status_panel");
    var statusLog = container.querySelector("#archive_status_log");
    var stacktracePanel = container.querySelector("#archive_stacktrace_panel");
    var archiveButton = container.querySelector("#archive_button");
    var refreshButton = container.querySelector("#refresh_button");
    var commentInput = container.querySelector("#archive_comment");
    var archiveEmpty = container.querySelector("#archive_empty");
    var restoreLink = container.querySelector("#restore_link");
    var tableBody = container.querySelector("#archives_table tbody");

    var statusStream = null;
    var pendingStatusMessages = [];
    var currentJobId = null;

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

    function flushPendingStatus() {
      if (!statusStream || pendingStatusMessages.length === 0) {
        return;
      }
      pendingStatusMessages.splice(0).forEach(function (msg) {
        statusStream.append(msg);
      });
    }

    function setRestoreButtonsDisabled(disabled) {
      container.querySelectorAll('button[data-role="restore"]').forEach(function (btn) {
        if (isUserAnonymous) {
          btn.disabled = true;
        } else {
          btn.disabled = !!disabled;
        }
      });
    }

    function setDeleteButtonsDisabled(disabled) {
      container.querySelectorAll('button[data-role="delete"]').forEach(function (btn) {
        if (isUserAnonymous) {
          btn.disabled = true;
        } else {
          btn.disabled = !!disabled;
        }
      });
    }

    function formatBytes(bytes) {
      if (!bytes) {
        return "0 B";
      }
      var units = ["B", "KB", "MB", "GB", "TB"];
      var index = Math.floor(Math.log(bytes) / Math.log(1024));
      var value = bytes / Math.pow(1024, index);
      return value.toFixed(value >= 10 || index === 0 ? 0 : 1) + " " + units[index];
    }

    function renderArchiveRow(item) {
      var tr = document.createElement("tr");

      var nameTd = tr.insertCell();
      nameTd.textContent = item.name;

      var commentTd = tr.insertCell();
      commentTd.textContent = item.comment || "";

      var sizeTd = tr.insertCell();
      sizeTd.textContent = formatBytes(item.size || 0);

      var modTd = tr.insertCell();
      modTd.textContent = item.modified || "";

      var linkTd = tr.insertCell();
      var link = document.createElement("a");
      link.href = item.download_url;
      link.textContent = "Download";
      link.rel = "nofollow";
      link.target = "_blank";
      link.className = "pure-button pure-button-secondary";
      linkTd.appendChild(link);

      var restoreTd = tr.insertCell();
      var restoreBtn = document.createElement("button");
      restoreBtn.type = "button";
      restoreBtn.className = "pure-button pure-button-secondary";
      restoreBtn.textContent = "Restore";
      restoreBtn.dataset.role = "restore";
      restoreBtn.addEventListener("click", function () {
        requestRestore(item.name);
      });
      if (isUserAnonymous) {
        restoreBtn.disabled = true;
        restoreBtn.title = "Restore is only available for authorized users.";
      }
      restoreTd.appendChild(restoreBtn);

      var deleteTd = tr.insertCell();
      var deleteBtn = document.createElement("button");
      deleteBtn.type = "button";
      deleteBtn.className = "pure-button pure-button-secondary";
      deleteBtn.textContent = "Delete";
      deleteBtn.dataset.role = "delete";
      deleteBtn.addEventListener("click", function () {
        requestDelete(item.name);
      });
      if (isUserAnonymous) {
        deleteBtn.disabled = true;
        deleteBtn.title = "Delete is only available for authorized users.";
      }
      deleteTd.appendChild(deleteBtn);

      return tr;
    }

    function populateArchiveTable(data) {
      if (!tableBody) {
        return;
      }
      tableBody.innerHTML = "";
      var archives = (data && data.archives) || [];
      if (!archives.length) {
        if (archiveEmpty) {
          archiveEmpty.hidden = false;
        }
      } else {
        if (archiveEmpty) {
          archiveEmpty.hidden = true;
        }
        archives.forEach(function (item) {
          tableBody.appendChild(renderArchiveRow(item));
        });
      }

      if (data && data.in_progress) {
        if (archiveButton) {
          archiveButton.disabled = true;
        }
        currentJobId = data.job_id || null;
        setRestoreButtonsDisabled(true);
        setDeleteButtonsDisabled(true);
      } else if (!currentJobId) {
        if (archiveButton) {
          archiveButton.disabled = false;
        }
        setRestoreButtonsDisabled(false);
        setDeleteButtonsDisabled(false);
      }
    }

    function fetchArchives() {
      if (!archivesUrl) {
        return Promise.resolve();
      }
      return fetch(archivesUrl, { cache: "no-store" })
        .then(function (response) {
          if (!response.ok) {
            throw new Error("Failed to fetch archives");
          }
          return response.json();
        })
        .then(populateArchiveTable)
        .catch(function (err) {
          console.error(err);
        });
    }

    function archiveFinished() {
      currentJobId = null;
      if (archiveButton) {
        archiveButton.disabled = false;
      }
      setRestoreButtonsDisabled(false);
      setDeleteButtonsDisabled(false);
      if (commentInput) {
        commentInput.value = "";
      }
      appendStatus("Archive job completed.");
      fetchArchives();
    }

    function restoreFinished() {
      currentJobId = null;
      setRestoreButtonsDisabled(false);
      setDeleteButtonsDisabled(false);
      fetchArchives();
      appendStatus("Restore job completed.");
      if (restoreLink && projectPath) {
        restoreLink.innerHTML = "";
        var link = document.createElement("a");
        link.href = projectPath;
        link.textContent = "Load " + runId + " Project";
        link.className = "pure-button pure-button-secondary";
        restoreLink.appendChild(link);
      }
    }

    function handleTrigger(detail) {
      if (!detail || !detail.event) {
        return;
      }
      var eventName = String(detail.event).toUpperCase();
      if (eventName === "ARCHIVE_COMPLETE") {
        archiveFinished();
      } else if (eventName === "RESTORE_COMPLETE") {
        restoreFinished();
      }
    }

    function startArchive() {
      if (!archiveApiUrl) {
        return;
      }
      if (archiveButton) {
        archiveButton.disabled = true;
      }
      setRestoreButtonsDisabled(true);
      setDeleteButtonsDisabled(true);
      var comment = "";
      if (commentInput) {
        comment = (commentInput.value || "").trim();
        if (comment.length > 40) {
          comment = comment.slice(0, 40);
          commentInput.value = comment;
        }
      }
      appendStatus("Submitting archive job...");
      fetch(archiveApiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ comment: comment })
      })
        .then(function (response) {
          return response.json();
        })
        .then(function (body) {
          if (!body.Success) {
            throw new Error(body.Error || "Archive submission failed");
          }
          currentJobId = body.job_id || null;
          appendStatus("Archive job submitted: " + currentJobId);
        })
        .catch(function (err) {
          appendStatus("ERROR: " + (err.message || err));
          if (archiveButton) {
            archiveButton.disabled = false;
          }
          setRestoreButtonsDisabled(false);
          setDeleteButtonsDisabled(false);
        });
    }

    function requestRestore(name) {
      if (!name) {
        return;
      }
      var confirmed = window.confirm('Restore archive "' + name + '"?\nThis replaces current project files.');
      if (!confirmed) {
        return;
      }
      startRestore(name);
    }

    function startRestore(name) {
      if (!restoreApiUrl) {
        return;
      }
      setRestoreButtonsDisabled(true);
      setDeleteButtonsDisabled(true);
      appendStatus("Restoring archive " + name + "...");
      fetch(restoreApiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ archive_name: name })
      })
        .then(function (response) {
          return response.json();
        })
        .then(function (body) {
          if (!body.Success) {
            throw new Error(body.Error || "Restore failed");
          }
          currentJobId = body.job_id || null;
          appendStatus("Restore job submitted: " + currentJobId);
        })
        .catch(function (err) {
          appendStatus("ERROR: " + (err.message || err));
          setRestoreButtonsDisabled(false);
          setDeleteButtonsDisabled(false);
        });
    }

    function requestDelete(name) {
      if (!name) {
        return;
      }
      var confirmed = window.confirm('Delete archive "' + name + '"? This cannot be undone.');
      if (!confirmed) {
        return;
      }
      startDelete(name);
    }

    function startDelete(name) {
      if (!deleteApiUrl) {
        return;
      }
      setDeleteButtonsDisabled(true);
      appendStatus("Deleting archive " + name + "...");
      fetch(deleteApiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ archive_name: name })
      })
        .then(function (response) {
          return response.json();
        })
        .then(function (body) {
          if (!body.Success) {
            throw new Error(body.Error || "Delete failed");
          }
          fetchArchives();
        })
        .catch(function (err) {
          appendStatus("ERROR: " + (err.message || err));
        })
        .finally(function () {
          if (!currentJobId) {
            setRestoreButtonsDisabled(false);
            setDeleteButtonsDisabled(false);
          }
        });
    }

    function initStatusStream() {
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
        channel: "archive",
        runId: runId,
        logLimit: MAX_STATUS_MESSAGES,
        stacktrace: stacktrace,
        onTrigger: handleTrigger
      });
      statusPanel.addEventListener("status:error", function (event) {
        if (event && event.detail && event.detail.error) {
          console.error("Archive status stream error:", event.detail.error);
        }
      });
      flushPendingStatus();
    }

    if (stacktracePanel) {
      stacktracePanel.hidden = true;
    }

    if (archiveButton) {
      archiveButton.addEventListener("click", startArchive);
    }
    if (refreshButton) {
      refreshButton.addEventListener("click", fetchArchives);
    }

    var projectLabel = document.getElementById("project_label");
    if (projectLabel) {
      projectLabel.textContent = "Create and manage project archives.";
    }

    initStatusStream();
    fetchArchives();
  }

  ready(function () {
    var containers = document.querySelectorAll('[data-controller="archive-dashboard"]');
    containers.forEach(initArchiveConsole);
  });
})();
