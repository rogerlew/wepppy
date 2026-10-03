/* Session/CSRF forms for feature membership and current-user acknowledgment. */
(function () {
    "use strict";
    document.querySelectorAll("[data-feature-access-form]").forEach(function (form) {
        var formKind = form.dataset.featureAccessForm;
        var membership = formKind === "membership";
        var operation = form.elements.namedItem("operation");
        var dates = form.querySelector("[data-access-dates]");
        var status = form.querySelector("[data-access-status]");
        var button = form.querySelector("button[type=submit]");
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
                var body = await response.json();
                if (!response.ok) {
                    throw new Error((body.error && body.error.message ? body.error.message : "Unable to save. Reload and retry.") +
                        (body.error_id ? " Reference: " + body.error_id : ""));
                }
                status.className = "wc-alert wc-alert--success";
                status.textContent = body.message;
                form.querySelector("[data-access-refresh]").hidden = false;
            } catch (error) {
                status.className = "wc-alert wc-alert--danger";
                status.textContent = error.message || "Unable to save. Check your connection and retry.";
            } finally {
                button.disabled = false;
                status.focus();
            }
        });
    });
}());
