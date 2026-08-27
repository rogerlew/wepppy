(function (global) {
    "use strict";

    var TERMINAL_SUCCESS = { finished: true, complete: true, completed: true };
    var TERMINAL_FAILURE = { failed: true, canceled: true, stopped: true };

    function errorCode(error) {
        var body = error && error.body ? error.body : {};
        return body && body.error ? body.error.code : "";
    }

    function errorMessage(error) {
        var code = errorCode(error);
        var messages = {
            stale_config_preview: "The preview is stale. Refresh it and review the current additions before applying.",
            config_update_in_progress: "A configuration update is already active. Wait for it to finish, then refresh the preview.",
            config_update_unavailable: "This configuration update is no longer available. Refresh the preview.",
            forbidden: "Only the project owner or an Admin/Root user can preview or apply this update.",
            job_failed: "The configuration update job failed. Review the run logs, then refresh the preview before retrying."
        };
        return messages[code] || "The configuration update request could not be completed. Try again or review the run logs.";
    }

    function ProjectConfigUpdate(root, dependencies) {
        this.root = root;
        this.http = dependencies && dependencies.http ? dependencies.http : global.WCHttp;
        this.modal = global.document.getElementById("projectConfigUpdateModal");
        this.openButton = root.querySelector("[data-project-config-update-open]");
        this.warning = root.querySelector("[data-project-config-digest-warning]");
        this.status = this.modal.querySelector("[data-project-config-update-status]");
        this.error = this.modal.querySelector("[data-project-config-update-error]");
        this.review = this.modal.querySelector("[data-project-config-update-review]");
        this.rows = this.modal.querySelector("[data-project-config-update-rows]");
        this.refreshButton = this.modal.querySelector("[data-project-config-update-refresh]");
        this.applyButton = this.modal.querySelector("[data-project-config-update-apply]");
        this.preview = null;
        this.busy = false;
        this.pollTimer = null;
    }

    ProjectConfigUpdate.prototype._request = function (url, options) {
        return this.http.requestWithSessionToken(url, options || {});
    };

    ProjectConfigUpdate.prototype._setStatus = function (message, focus) {
        this.status.textContent = message;
        if (focus) { this.status.focus(); }
    };

    ProjectConfigUpdate.prototype._showError = function (error) {
        this.error.textContent = errorMessage(error);
        this.error.hidden = false;
        this.error.focus();
    };

    ProjectConfigUpdate.prototype._clearError = function () {
        this.error.hidden = true;
        this.error.textContent = "";
    };

    ProjectConfigUpdate.prototype.checkAvailability = function () {
        var self = this;
        return this._request(this.root.dataset.availabilityUrl).then(function (result) {
            var state = result.body || {};
            self.root.hidden = !(state.available || state.digest_warning);
            self.openButton.hidden = !state.available;
            self.warning.hidden = !state.digest_warning;
            self.root.dataset.previewId = state.preview_id || "";
            return state;
        }).catch(function () {
            self.root.hidden = true;
            return null;
        });
    };

    ProjectConfigUpdate.prototype._renderPreview = function (preview) {
        var self = this;
        this.rows.replaceChildren();
        (preview.additions || []).forEach(function (addition) {
            var row = global.document.createElement("tr");
            [addition.section, addition.option, addition.value, addition.source_id, addition.source_revision].forEach(function (value) {
                var cell = global.document.createElement("td");
                cell.textContent = String(value);
                row.appendChild(cell);
            });
            self.rows.appendChild(row);
        });
        this.preview = preview;
        this.review.hidden = false;
        this.applyButton.disabled = !preview.preview_id || !(preview.additions || []).length;
        this._setStatus((preview.additions || []).length + " additions are ready for review.");
    };

    ProjectConfigUpdate.prototype.loadPreview = function () {
        var self = this;
        this._clearError();
        this.applyButton.disabled = true;
        this.review.hidden = true;
        this._setStatus("Loading the complete configuration update preview…");
        return this._request(this.root.dataset.previewUrl).then(function (result) {
            self._renderPreview(result.body || {});
        }).catch(function (error) {
            self.preview = null;
            self._showError(error);
            self._setStatus("Preview unavailable.");
        });
    };

    ProjectConfigUpdate.prototype._poll = function (jobId) {
        var self = this;
        return this.http.request("/rq-engine/api/jobstatus/" + encodeURIComponent(jobId)).then(function (result) {
            var status = String((result.body || {}).status || "").toLowerCase();
            if (TERMINAL_SUCCESS[status]) {
                self.busy = false;
                self._setStatus("Configuration update complete. Reload the page to use the added attributes.", true);
                self.openButton.hidden = true;
                self.applyButton.disabled = true;
                return;
            }
            if (TERMINAL_FAILURE[status]) {
                self.busy = false;
                self.applyButton.disabled = false;
                self._showError({ body: { error: { code: "job_failed" } } });
                self._setStatus("Configuration update job failed.");
                return;
            }
            self._setStatus("Configuration update job is " + (status || "pending") + "…");
            self.pollTimer = global.setTimeout(function () { self._poll(jobId); }, 1000);
        }).catch(function (error) {
            self.busy = false;
            self.applyButton.disabled = false;
            self._showError(error);
        });
    };

    ProjectConfigUpdate.prototype.apply = function () {
        var self = this;
        if (this.busy || !this.preview || !this.preview.additions.length) { return Promise.resolve(); }
        var trigger = this.preview.additions[0];
        this.busy = true;
        this.applyButton.disabled = true;
        this._clearError();
        this._setStatus("Requesting the reviewed configuration update…");
        return this._request(this.root.dataset.applyUrl, {
            method: "POST",
            json: {
                preview_id: this.preview.preview_id,
                trigger: { section: trigger.section, option: trigger.option }
            }
        }).then(function (result) {
            var jobId = (result.body || {}).job_id;
            if (!jobId) { throw new Error("Update response did not include a job ID"); }
            self._setStatus("Configuration update queued…");
            return self._poll(jobId);
        }).catch(function (error) {
            self.busy = false;
            self.applyButton.disabled = false;
            self._showError(error);
            if (errorCode(error) === "stale_config_preview") {
                self.preview = null;
                self.applyButton.disabled = true;
            }
        });
    };

    ProjectConfigUpdate.prototype.bind = function () {
        var self = this;
        this.openButton.addEventListener("click", function () { self.loadPreview(); });
        this.refreshButton.addEventListener("click", function () { self.loadPreview(); });
        this.applyButton.addEventListener("click", function () { self.apply(); });
        return this.checkAvailability();
    };

    function initialize() {
        var root = global.document.querySelector("[data-project-config-update]");
        if (!root || root.dataset.initialized === "true" || !global.WCHttp || !global.WCHttp.requestWithSessionToken) { return null; }
        root.dataset.initialized = "true";
        var controller = new ProjectConfigUpdate(root);
        controller.bind();
        global.ProjectConfigUpdate = controller;
        return controller;
    }

    global.ProjectConfigUpdateController = ProjectConfigUpdate;
    if (global.document.readyState === "loading") {
        global.document.addEventListener("DOMContentLoaded", initialize, { once: true });
    } else {
        initialize();
    }
})(window);
