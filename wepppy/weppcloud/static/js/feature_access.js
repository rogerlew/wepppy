/* Session/CSRF forms for feature membership and current-user acknowledgment. */
(function () {
    "use strict";
    var heading = document.getElementById("poweruser-access-heading");
    if (heading && window.location.hash === "#poweruser-access-heading") { heading.focus(); }
    document.querySelectorAll("[data-feature-access-form]").forEach(function (form) {
        var formKind = form.dataset.featureAccessForm;
        var membership = formKind === "membership";
        var operation = form.elements.namedItem("operation");
        var dates = form.querySelector("[data-access-dates]");
        var status = form.querySelector("[data-access-status]");
        var button = form.querySelector("button[type=submit]");
        function refreshProfile() {
            var destination = new URL(refreshLink.href, window.location.href);
            if (destination.origin !== window.location.origin) {
                throw new Error("Reload Profile to check your access status.");
            }
            var current = new URL(window.location.href);
            if (current.pathname === destination.pathname && current.search === destination.search) {
                window.location.hash = destination.hash;
                window.location.reload();
            } else {
                window.location.assign(destination.href);
            }
        }
        var refreshLink = form.querySelector("[data-access-refresh]");
        if (formKind === "poweruser" && refreshLink) {
            refreshLink.addEventListener("click", function (event) {
                event.preventDefault();
                refreshProfile();
            });
        }
        function updateDates() {
            if (dates) {
                dates.disabled = operation.value === "remove";
                dates.hidden = dates.disabled;
            }
        }
        if (operation) {
            operation.addEventListener("change", updateDates);
            updateDates();
        }
        form.addEventListener("submit", async function (event) {
            event.preventDefault();
            if (!form.reportValidity() || button.disabled) { return; }
            var data = new FormData(form);
            var payload;
            if (membership) {
                payload = {
                    operation: data.get("operation"),
                    user_id: Number(data.get("user_id")),
                    group_key: data.get("group_key"),
                    reason: data.get("reason")
                };
                if (payload.operation === "add") {
                    payload.review_at = data.get("review_at").trim() || null;
                    payload.expires_at = data.get("expires_at").trim() || null;
                }
            } else if (formKind === "poweruser") {
                payload = {
                    needs_poweruser: form.elements.namedItem("needs_poweruser").checked,
                    accepts_training: form.elements.namedItem("accepts_training").checked,
                    statement_version: form.dataset.statementVersion
                };
            } else {
                payload = { accepts_training: form.elements.namedItem("accepts_training").checked,
                    statement_version: form.dataset.statementVersion };
            }
            button.disabled = true;
            status.hidden = false;
            status.textContent = "Saving…";
            try {
                var csrf = document.querySelector('meta[name="csrf-token"]');
                var response = await fetch(form.action, {
                    method: "POST", credentials: "same-origin",
                    headers: { "Content-Type": "application/json", "Accept": "application/json",
                        "X-CSRFToken": csrf ? csrf.content : "" },
                    body: JSON.stringify(payload)
                });
                var body = null;
                try {
                    body = await response.json();
                } catch {
                    body = null;
                }
                if (!response.ok) {
                    throw new Error((body && body.error && body.error.message ? body.error.message : "Unable to save. Reload and retry.") +
                        (body && body.error_id ? " Reference: " + body.error_id : ""));
                }
                if (!body || typeof body.message !== "string" || !body.message.trim()) {
                    throw new Error("Unable to save. Reload and retry.");
                }
                if (formKind === "acknowledgment" && (!body.result ||
                    body.result.statement_kind !== "internal" ||
                    body.result.statement_version !== form.dataset.statementVersion ||
                    typeof body.result.changed !== "boolean")) {
                    throw new Error("Unable to save. Reload and retry.");
                }
                if (formKind === "poweruser" && (!body.result ||
                    body.result.status !== "granted" ||
                    typeof body.result.role_changed !== "boolean" ||
                    body.result.statement_version !== form.dataset.statementVersion)) {
                    throw new Error("Unable to save. Reload and retry.");
                }
                status.className = "wc-alert wc-alert--success";
                if (formKind === "acknowledgment") {
                    status.textContent = "You have accepted this version.";
                    form.closest("[data-internal-access]").querySelectorAll("[data-internal-membership-status]")
                        .forEach(function (label) {
                            label.textContent = "membership current; acknowledgment complete";
                        });
                    form.replaceWith(status);
                } else if (formKind === "poweruser") {
                    var refresh = form.querySelector("[data-access-refresh]");
                    var destination = new URL(refresh.href, window.location.href);
                    if (destination.origin !== window.location.origin) {
                        throw new Error("Reload Profile to check your access status.");
                    }
                    status.textContent = body.message;
                    refresh.hidden = false;
                    var completed = document.createElement("div");
                    completed.append(status, refresh);
                    form.replaceWith(completed);
                    // A hash-only assignment does not refresh server-rendered roles.
                    refreshProfile();
                } else {
                    status.textContent = body.message;
                    form.querySelector("[data-access-refresh]").hidden = false;
                }
            } catch (error) {
                status.className = "wc-alert wc-alert--danger";
                status.textContent = error.message || "Unable to save. Check your connection and retry.";
                if (formKind === "poweruser") {
                    status.textContent += " Reload Profile and retry; sign in again if your session has expired.";
                }
            } finally {
                if (button.isConnected) { button.disabled = false; }
                status.focus();
            }
        });
    });
}());
