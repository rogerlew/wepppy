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
            capability_refresh_acknowledgment_required: "Review and accept the capability-authority warning before applying this refresh.",
            config_update_in_progress: "A configuration update is already active. Wait for it to finish, then refresh the preview.",
            config_update_unavailable: "This configuration update is no longer available. Refresh the preview.",
            builder_registry_error: "The Builder registry is temporarily unavailable. Retry shortly; if the problem continues, report the diagnostic below.",
            locale_authority_invalid: "This run's locale authority is invalid. Review the diagnostic below before retrying.",
            forbidden: "Only the project owner or an Admin/Root user can preview or apply this update.",
            job_failed: "The configuration update job failed. Review the run logs, then refresh the preview before retrying."
        };
        return messages[code] || "The configuration update request could not be completed. Try again or review the run logs.";
    }

    function errorDiagnostic(error) {
        var body = error && error.body ? error.body : {};
        var payload = body && body.error ? body.error : {};
        var parts = [errorMessage(error)];
        if (payload.details) { parts.push("Details: " + String(payload.details)); }
        if (body.error_id) { parts.push("Error ID: " + String(body.error_id)); }
        return parts.join(" ");
    }

    function appliedResultMatchesPreview(result, reviewed) {
        return Boolean(result && result.applied === true && reviewed &&
            typeof result.recovered === "boolean" &&
            Number.isInteger(result.sequence) && result.sequence > 0 &&
            /^[0-9a-f]{64}$/.test(String(result.prior_digest || "")) &&
            /^[0-9a-f]{64}$/.test(String(result.resulting_digest || "")) &&
            result.prior_digest === reviewed.current_digest &&
            result.resulting_digest === reviewed.resulting_digest);
    }

    function ProjectConfigUpdate(root, dependencies) {
        this.root = root;
        this.http = dependencies && dependencies.http ? dependencies.http : global.WCHttp;
        this.modal = global.document.getElementById("projectConfigUpdateModal");
        this.openButton = root.querySelector("[data-project-config-update-open]");
        this.warning = root.querySelector("[data-project-config-digest-warning]");
        this.availabilityError = root.querySelector("[data-project-config-update-availability-error]");
        this.status = this.modal.querySelector("[data-project-config-update-status]");
        this.error = this.modal.querySelector("[data-project-config-update-error]");
        this.review = this.modal.querySelector("[data-project-config-update-review]");
        this.rows = this.modal.querySelector("[data-project-config-update-rows]");
        this.additionsPanel = this.modal.querySelector("[data-project-config-update-additions]");
        this.capabilityPanel = this.modal.querySelector("[data-project-config-update-capability-changes]");
        this.capabilityRows = this.modal.querySelector("[data-project-config-update-capability-rows]");
        this.capabilityDetailsPanel = this.modal.querySelector("[data-project-config-update-capability-details]");
        this.capabilityDetailsRows = this.modal.querySelector("[data-project-config-update-capability-detail-rows]");
        this.acknowledgment = this.modal.querySelector("[data-project-config-update-acknowledgment]");
        this.acknowledgmentCheckbox = this.modal.querySelector("[data-project-config-update-acknowledgment-checkbox]");
        this.refreshButton = this.modal.querySelector("[data-project-config-update-refresh]");
        this.reloadButton = this.modal.querySelector("[data-project-config-update-reload]");
        this.applyButton = this.modal.querySelector("[data-project-config-update-apply]");
        this.preview = null;
        this.busy = false;
        this.pollTimer = null;
    }

    ProjectConfigUpdate.prototype._resetAcknowledgment = function () {
        this.acknowledgmentCheckbox.checked = false;
        this.applyButton.disabled = true;
    };

    ProjectConfigUpdate.prototype._canApply = function () {
        if (!this.preview || !this.preview.preview_id) { return false; }
        var hasRefresh = Boolean(this.preview.capability_refresh);
        var hasAdditions = Boolean((this.preview.additions || []).length);
        return (hasRefresh || hasAdditions) && (!hasRefresh || this.acknowledgmentCheckbox.checked);
    };

    ProjectConfigUpdate.prototype._hideReloadAction = function () {
        this.reloadButton.hidden = true;
        this.applyButton.hidden = false;
    };

    ProjectConfigUpdate.prototype._showReloadAction = function () {
        this.applyButton.hidden = true;
        this.reloadButton.hidden = false;
        this.reloadButton.focus();
    };

    ProjectConfigUpdate.prototype._request = function (url, options) {
        return this.http.requestWithSessionToken(url, options || {});
    };

    ProjectConfigUpdate.prototype._requestAsUser = function (url, options) {
        return this.http.requestWithUserToken(url, options || {});
    };

    ProjectConfigUpdate.prototype._setStatus = function (message, focus) {
        this.status.textContent = message;
        if (focus) { this.status.focus(); }
    };

    ProjectConfigUpdate.prototype._showError = function (error) {
        this._resetAcknowledgment();
        this.error.textContent = errorDiagnostic(error);
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
            self.availabilityError.hidden = true;
            self.availabilityError.textContent = "";
            if (state.reason === "config_update_unavailable" && state.details) {
                self._resetAcknowledgment();
                self.root.hidden = false;
                self.openButton.hidden = true;
                self.warning.hidden = !state.digest_warning;
                self.availabilityError.textContent = errorDiagnostic({
                    body: {
                        error: {
                            code: "config_update_unavailable",
                            details: state.details
                        }
                    }
                });
                self.availabilityError.hidden = false;
                return state;
            }
            self.root.hidden = !(state.available || state.digest_warning);
            self.openButton.hidden = !state.available;
            self.warning.hidden = !state.digest_warning;
            self.root.dataset.previewId = state.preview_id || "";
            return state;
        }).catch(function (error) {
            self._resetAcknowledgment();
            self.root.hidden = false;
            self.openButton.hidden = true;
            self.warning.hidden = true;
            self.availabilityError.textContent = errorDiagnostic(error);
            self.availabilityError.hidden = false;
            return null;
        });
    };

    ProjectConfigUpdate.prototype._renderPreview = function (preview) {
        var self = this;
        this._resetAcknowledgment();
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
        this.additionsPanel.hidden = !(preview.additions || []).length;
        this.capabilityRows.replaceChildren();
        var refresh = preview.capability_refresh;
        ((refresh && refresh.changes) || []).forEach(function (change) {
            var row = global.document.createElement("tr");
            [
                change.section,
                change.option,
                change.kind,
                change.before,
                change.after,
                change.added_ids || [],
                change.removed_ids || [],
                change.added_support || []
            ].forEach(function (value) {
                var cell = global.document.createElement("td");
                cell.textContent = value === null ? "—" : (typeof value === "string" ? value : JSON.stringify(value));
                row.appendChild(cell);
            });
            self.capabilityRows.appendChild(row);
        });
        this.capabilityPanel.hidden = !refresh;
        this.capabilityDetailsRows.replaceChildren();
        var detailCount = 0;
        function appendDetail(scope, field, value) {
            var row = global.document.createElement("tr");
            [scope, field, value].forEach(function (item) {
                var cell = global.document.createElement("td");
                cell.textContent = typeof item === "string" ? item : JSON.stringify(item);
                row.appendChild(cell);
            });
            self.capabilityDetailsRows.appendChild(row);
            detailCount += 1;
        }
        if (refresh) {
            appendDetail("project", "locale_profile", refresh.locale_profile);
            appendDetail("project", "locales", refresh.locales);
            Object.keys((refresh.preserved_project_selections || {}).capability_defaults || {}).sort().forEach(function (key) {
                appendDetail("preserved capability default", key, refresh.preserved_project_selections.capability_defaults[key]);
            });
            appendDetail("preserved project selection", "nodb.mods", ((refresh.preserved_project_selections || {}).nodb || {}).mods || []);
            appendDetail("preserved project selection", "climate.cligen_db", ((refresh.preserved_project_selections || {}).climate || {}).cligen_db);
            ["prior", "resulting"].forEach(function (scope) {
                var identity = refresh[scope] || {};
                ["graph_sha256", "structure_sha256", "provider_revision", "wepp_binary_revisions"].forEach(function (field) {
                    appendDetail(scope, field, identity[field]);
                });
                (identity.selected_parent_chain || []).forEach(function (entry, index) {
                    appendDetail(scope, "selected_parent_chain[" + index + "]", entry);
                });
            });
        }
        this.capabilityDetailsPanel.hidden = !refresh;
        this.acknowledgment.hidden = !refresh;
        this.preview = preview;
        this.review.hidden = false;
        this.applyButton.disabled = !this._canApply();
        this._setStatus(
            (preview.additions || []).length + " additions and " +
            ((refresh && refresh.changes) || []).length + " capability changes across " +
            detailCount + " provenance details are ready for review."
        );
    };

    ProjectConfigUpdate.prototype.loadPreview = function () {
        var self = this;
        this._hideReloadAction();
        this._clearError();
        this._resetAcknowledgment();
        this.review.hidden = true;
        this._setStatus("Loading the complete configuration update preview…");
        return this._requestAsUser(this.root.dataset.previewUrl).then(function (result) {
            self._renderPreview(result.body || {});
        }).catch(function (error) {
            self.preview = null;
            self._showError(error);
            self._setStatus("Preview unavailable.");
        });
    };

    ProjectConfigUpdate.prototype._reconcileFailure = function (reviewed) {
        var self = this;
        return this._request(this.root.dataset.availabilityUrl).then(function (result) {
            var state = result.body || {};
            var latest = state.last_update || {};
            if (reviewed && latest.preview_id === reviewed.preview_id &&
                    state.current_digest === reviewed.resulting_digest) {
                self._clearError();
                self._setStatus("Configuration update committed and was recovered.", true);
                self.openButton.hidden = true;
                self._showReloadAction();
            } else if (reviewed && state.current_digest === reviewed.current_digest) {
                self._clearError();
                self._setStatus("Configuration update was not applied.", true);
            } else {
                self._setStatus("Configuration update outcome is indeterminate. Review availability and run logs before retrying.", true);
            }
            return state;
        }).catch(function () {
            self._setStatus("Configuration update outcome is indeterminate. Review run logs before retrying.", true);
            return null;
        });
    };

    ProjectConfigUpdate.prototype._finishSuccessfulJob = function (jobId, reviewed) {
        var self = this;
        var jobInfoUrl = "/rq-engine/api/jobinfo/" + encodeURIComponent(jobId);
        return this.http.request(jobInfoUrl).then(function (response) {
            var result = (response.body || {}).result;
            self.busy = false;
            if (!appliedResultMatchesPreview(result, reviewed)) {
                self._setStatus(
                    "Configuration update job finished, but its result diagnostics are missing, invalid, " +
                    "or do not match the reviewed preview. " +
                    "The outcome is indeterminate; review availability and run logs before retrying.",
                    true
                );
                return;
            }
            self._clearError();
            self.openButton.hidden = true;
            self._resetAcknowledgment();
            self._showReloadAction();
            self._setStatus(
                (result.recovered
                    ? "Configuration update committed and was recovered. "
                    : "Configuration update complete. ") +
                "Sequence " + result.sequence + ". Prior digest " + result.prior_digest +
                ". Resulting digest " + result.resulting_digest + ".",
                true
            );
        }).catch(function (error) {
            self.busy = false;
            self._showError(error);
            self._setStatus(
                "Configuration update job finished, but its result diagnostics are unavailable. " +
                "The outcome is indeterminate; review availability and run logs before retrying.",
                true
            );
        });
    };

    ProjectConfigUpdate.prototype._poll = function (jobId, reviewed) {
        var self = this;
        return this.http.request("/rq-engine/api/jobstatus/" + encodeURIComponent(jobId)).then(function (result) {
            var status = String((result.body || {}).status || "").toLowerCase();
            if (TERMINAL_SUCCESS[status]) {
                return self._finishSuccessfulJob(jobId, reviewed);
            }
            if (TERMINAL_FAILURE[status]) {
                self.busy = false;
                self._showError({ body: { error: { code: "job_failed" } } });
                self._setStatus("Configuration update job failed.");
                return self._reconcileFailure(reviewed);
            }
            self._setStatus("Configuration update job is " + (status || "pending") + "…");
            self.pollTimer = global.setTimeout(function () { self._poll(jobId, reviewed); }, 1000);
        }).catch(function (error) {
            self.busy = false;
            self._showError(error);
            return self._reconcileFailure(reviewed);
        });
    };

    ProjectConfigUpdate.prototype.apply = function () {
        var self = this;
        if (this.busy || !this._canApply()) { return Promise.resolve(); }
        var trigger = (this.preview.additions || [])[0];
        var payload = { preview_id: this.preview.preview_id };
        var reviewed = Object.freeze({
            preview_id: this.preview.preview_id,
            current_digest: this.preview.current_digest,
            resulting_digest: this.preview.resulting_digest
        });
        if (trigger) {
            payload.trigger = { section: trigger.section, option: trigger.option };
        }
        if (this.preview.capability_refresh) {
            payload.capability_acknowledgment = {
                accepted: true,
                revision: this.preview.capability_refresh.acknowledgment.revision
            };
        }
        this.busy = true;
        this.applyButton.disabled = true;
        this._clearError();
        this._setStatus("Requesting the reviewed configuration update…");
        return this._requestAsUser(this.root.dataset.applyUrl, {
            method: "POST",
            json: payload
        }).then(function (result) {
            var resultBody = result.body || {};
            var jobId = resultBody.job_id;
            if (!jobId && resultBody.recovered) {
                self.busy = false;
                if (!appliedResultMatchesPreview(resultBody, reviewed)) {
                    self._setStatus(
                        "Configuration update recovery diagnostics do not match the reviewed preview. " +
                        "The outcome is indeterminate; review availability and run logs before retrying.",
                        true
                    );
                    return;
                }
                self._resetAcknowledgment();
                self.openButton.hidden = true;
                self._showReloadAction();
                self._setStatus(
                    "Configuration update was already committed and recovered. Sequence " +
                    resultBody.sequence + ". Prior digest " + resultBody.prior_digest +
                    ". Resulting digest " + resultBody.resulting_digest + ".",
                    true
                );
                return;
            }
            if (!jobId) { throw new Error("Update response did not include a job ID"); }
            self._setStatus("Configuration update queued…");
            return self._poll(jobId, reviewed);
        }).catch(function (error) {
            self.busy = false;
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
        this.reloadButton.addEventListener("click", function () { global.location.reload(); });
        this.applyButton.addEventListener("click", function () { self.apply(); });
        this.acknowledgmentCheckbox.addEventListener("change", function () {
            self.applyButton.disabled = !self._canApply();
        });
        this.modal.querySelectorAll("[data-modal-dismiss]").forEach(function (element) {
            element.addEventListener("click", function () { self._resetAcknowledgment(); });
        });
        global.document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") { self._resetAcknowledgment(); }
        });
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
