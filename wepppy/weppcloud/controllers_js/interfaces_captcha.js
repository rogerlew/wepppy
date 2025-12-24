/* ----------------------------------------------------------------------------
 * Interfaces CAPTCHA gating
 * ----------------------------------------------------------------------------
 */
(function () {
    var SECTION_SELECTOR = "cap-widget[data-cap-section]";
    var BUTTON_SELECTOR = "[data-run-action]";
    var PROMPT_SELECTOR = ".wc-cap-prompt[data-cap-section]";

    function updateSection(sectionKey, token) {
        var prompt = document.querySelector(PROMPT_SELECTOR + '[data-cap-section="' + sectionKey + '"]');
        if (prompt) {
            prompt.setAttribute("data-cap-verified", "true");
            var trigger = prompt.querySelector("[data-cap-trigger]");
            if (trigger) {
                trigger.classList.add("is-verified");
                trigger.setAttribute("aria-disabled", "true");
                trigger.setAttribute("disabled", "true");
            }
            var status = prompt.querySelector("[data-cap-status]");
            if (status) {
                status.textContent = "Verification complete.";
            }
        }

        var forms = document.querySelectorAll('form[data-cap-section="' + sectionKey + '"]');
        forms.forEach(function (form) {
            var tokenInput = form.querySelector("[data-cap-token]");
            if (tokenInput) {
                tokenInput.value = token;
            }
            form.querySelectorAll(BUTTON_SELECTOR).forEach(function (button) {
                button.classList.remove("is-disabled");
                button.removeAttribute("disabled");
                button.disabled = false;
                button.setAttribute("aria-disabled", "false");
            });
        });
    }

    function triggerPromptForForm(form) {
        if (!form || !form.dataset || !form.dataset.capSection) {
            return false;
        }
        var prompt = document.querySelector(PROMPT_SELECTOR + '[data-cap-section="' + form.dataset.capSection + '"]');
        if (!prompt) {
            return false;
        }
        var trigger = prompt.querySelector("[data-cap-trigger]");
        if (!trigger || trigger.disabled) {
            return false;
        }
        trigger.click();
        return true;
    }

    function attachWidgetListeners() {
        var widgets = document.querySelectorAll(SECTION_SELECTOR);
        widgets.forEach(function (widget) {
            widget.addEventListener("solve", function (event) {
                var detail = event && event.detail ? event.detail : null;
                var token = detail && detail.token ? String(detail.token) : "";
                if (!token) {
                    return;
                }
                var sectionKey = widget.getAttribute("data-cap-section");
                if (!sectionKey) {
                    return;
                }
                updateSection(sectionKey, token);
            });
        });
    }

    function attachButtonHandlers() {
        var buttons = document.querySelectorAll(BUTTON_SELECTOR);
        buttons.forEach(function (button) {
            if (!button.dataset || !button.dataset.runAction) {
                return;
            }
            button.onclick = function (event) {
                var form = button.closest("form");
                if (!form) {
                    if (event) {
                        event.preventDefault();
                    }
                    return;
                }
                if (form.dataset && form.dataset.capRequired === "true") {
                    var tokenInput = form.querySelector("[data-cap-token]");
                    var hasToken = tokenInput && tokenInput.value;

                    if (!hasToken) {
                        if (event && typeof event.preventDefault === "function") {
                            event.preventDefault();
                            event.stopPropagation();
                        }
                        triggerPromptForForm(form);
                        return;
                    }
                }
                // Have token or not required - submit the form
                if (event && typeof event.preventDefault === "function") {
                    event.preventDefault();
                    event.stopPropagation();
                }
                // Ensure form is submitting via POST
                if (form.method && form.method.toLowerCase() !== 'post') {
                    form.method = 'post';
                }
                if (typeof form.requestSubmit === "function") {
                    form.requestSubmit();
                } else {
                    form.submit();
                }
            };
        });
    }

    function init() {
        if (!document.querySelector(SECTION_SELECTOR)) {
            return;
        }
        attachButtonHandlers();
        attachWidgetListeners();
    }

    init();
})();
