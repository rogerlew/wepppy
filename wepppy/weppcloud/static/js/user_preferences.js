(function userPreferencesModule(window, document) {
    "use strict";

    function init(root) {
        var scope = root || document;
        var form = scope.querySelector("[data-user-preferences-form]");
        if (!form || form.dataset.userPreferencesReady === "true") {
            return;
        }

        var fields = Array.prototype.slice.call(
            form.querySelectorAll(
                "select[name='unit_system'], " +
                "select[name='wbt_boundary_touch_behavior']"
            )
        );
        var status = form.querySelector("[data-user-preferences-status]");
        var statusMessage = form.querySelector(
            "[data-user-preferences-status-message]"
        );
        var error = form.querySelector("[data-user-preferences-error]");
        var errorMessage = form.querySelector(
            "[data-user-preferences-error-message]"
        );
        var retry = form.querySelector("[data-user-preferences-retry]");
        var saving = false;
        var pending = false;

        if (
            fields.length !== 2 ||
            !status ||
            !statusMessage ||
            !error ||
            !errorMessage ||
            !retry
        ) {
            return;
        }

        form.dataset.userPreferencesReady = "true";

        function showStatus(message, kind) {
            status.className = (
                "wc-alert wc-alert--" + kind +
                " wc-user-preferences__status"
            );
            statusMessage.textContent = message;
            status.hidden = false;
        }

        function showError(message) {
            status.hidden = true;
            errorMessage.textContent = message;
            error.hidden = false;
        }

        function clearError() {
            error.hidden = true;
            errorMessage.textContent = "";
        }

        async function save() {
            if (saving) {
                pending = true;
                return;
            }

            saving = true;
            pending = false;
            clearError();
            form.setAttribute("aria-busy", "true");
            showStatus("Saving preferences…", "info");

            try {
                var response = await window.fetch(form.action, {
                    method: "POST",
                    body: new window.FormData(form),
                    credentials: "same-origin",
                    headers: {
                        "Accept": "application/json",
                        "X-Requested-With": "XMLHttpRequest"
                    }
                });
                var payload = await response.json().catch(function emptyPayload() {
                    return {};
                });
                if (!response.ok || payload.ok !== true) {
                    throw new Error(
                        payload.message ||
                        "Preferences could not be saved. Try again."
                    );
                }
                showStatus(
                    payload.message || "Preferences saved.",
                    "success"
                );
            } catch (requestError) {
                showError(
                    requestError && requestError.message
                        ? requestError.message
                        : "Preferences could not be saved. Try again."
                );
            } finally {
                saving = false;
                form.removeAttribute("aria-busy");
                if (pending) {
                    save();
                }
            }
        }

        fields.forEach(function bindField(field) {
            field.addEventListener("change", save);
        });
        form.addEventListener("submit", function onSubmit(event) {
            event.preventDefault();
            save();
        });
        retry.addEventListener("click", save);
    }

    window.WCUserPreferences = { init: init };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function onReady() {
            init(document);
        }, { once: true });
    } else {
        init(document);
    }
}(window, document));
