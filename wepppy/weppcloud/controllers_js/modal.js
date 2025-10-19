/* ----------------------------------------------------------------------------
 * Modal Manager
 * ----------------------------------------------------------------------------
 * Lightweight controller for Pure-styled modals triggered via data attributes.
 * Markup requirements:
 *   <div class="wc-modal" id="exampleModal" data-modal hidden>
 *     <div class="wc-modal__overlay" data-modal-dismiss></div>
 *     <div class="wc-modal__dialog" role="dialog" aria-modal="true">
 *       ...
 *       <button type="button" data-modal-dismiss>Close</button>
 *     </div>
 *   </div>
 *   <button type="button" data-modal-open="exampleModal">Open</button>
 */
(function (global) {
    "use strict";

    var ACTIVE_CLASS = "is-visible";
    var BODY_ACTIVE_CLASS = "wc-modal-open";

    var focusableSelectors = [
        "a[href]",
        "button:not([disabled])",
        "input:not([disabled])",
        "select:not([disabled])",
        "textarea:not([disabled])",
        "[tabindex]:not([tabindex='-1'])",
    ].join(",");

    var activeModal = null;
    var previouslyFocused = null;

    function toElement(target) {
        if (!target) {
            return null;
        }
        if (typeof target === "string") {
            return document.getElementById(target);
        }
        return target;
    }

    function getFocusableElements(modal) {
        var dialog = modal.querySelector(".wc-modal__dialog") || modal;
        return Array.prototype.slice.call(dialog.querySelectorAll(focusableSelectors));
    }

    function trapFocus(event) {
        if (!activeModal) {
            return;
        }
        if (event.key !== "Tab") {
            return;
        }

        var focusable = getFocusableElements(activeModal);
        if (focusable.length === 0) {
            event.preventDefault();
            return;
        }

        var first = focusable[0];
        var last = focusable[focusable.length - 1];
        var current = document.activeElement;

        if (event.shiftKey) {
            if (current === first || !activeModal.contains(current)) {
                event.preventDefault();
                last.focus();
            }
        } else if (current === last) {
            event.preventDefault();
            first.focus();
        }
    }

    function onKeyDown(event) {
        if (!activeModal) {
            return;
        }
        if (event.key === "Escape") {
            closeModal(activeModal);
            return;
        }
        trapFocus(event);
    }

    function activateModal(modal) {
        if (activeModal === modal) {
            return;
        }
        if (activeModal) {
            closeModal(activeModal);
        }
        previouslyFocused = document.activeElement;
        activeModal = modal;

        modal.removeAttribute("hidden");
        modal.setAttribute("data-modal-open", "true");
        modal.classList.add(ACTIVE_CLASS);
        document.body.classList.add(BODY_ACTIVE_CLASS);

        var focusable = getFocusableElements(modal);
        if (focusable.length > 0) {
            focusable[0].focus();
        } else {
            modal.focus({ preventScroll: true });
        }

        document.addEventListener("keydown", onKeyDown, true);
    }

    function deactivateModal(modal) {
        modal.classList.remove(ACTIVE_CLASS);
        modal.removeAttribute("data-modal-open");
        modal.setAttribute("hidden", "hidden");
    }

    function closeModal(modal) {
        var element = toElement(modal);
        if (!element) {
            return;
        }
        deactivateModal(element);

        if (activeModal === element) {
            activeModal = null;
            document.body.classList.remove(BODY_ACTIVE_CLASS);
            document.removeEventListener("keydown", onKeyDown, true);

            if (previouslyFocused && typeof previouslyFocused.focus === "function") {
                previouslyFocused.focus({ preventScroll: true });
            }
            previouslyFocused = null;
        }
    }

    function openModal(modal) {
        var element = toElement(modal);
        if (!element) {
            return;
        }
        activateModal(element);
    }

    function toggleModal(modal) {
        var element = toElement(modal);
        if (!element) {
            return;
        }
        if (element.hasAttribute("data-modal-open")) {
            closeModal(element);
        } else {
            openModal(element);
        }
    }

    function handleOpenClick(event) {
        var trigger = event.target.closest("[data-modal-open]");
        if (!trigger) {
            return;
        }
        event.preventDefault();
        var targetId = trigger.getAttribute("data-modal-open");
        if (targetId) {
            openModal(targetId);
        }
    }

    function handleDismissClick(event) {
        var dismiss = event.target.closest("[data-modal-dismiss]");
        if (!dismiss) {
            return;
        }
        event.preventDefault();
        var modal = dismiss.closest("[data-modal]");
        if (modal) {
            closeModal(modal);
        }
    }

    function handleOverlayClick(event) {
        if (!activeModal) {
            return;
        }
        if (event.target === activeModal) {
            closeModal(activeModal);
        }
    }

    document.addEventListener("click", handleOpenClick);
    document.addEventListener("click", handleDismissClick);
    document.addEventListener("mousedown", handleOverlayClick);

    global.ModalManager = {
        open: openModal,
        close: closeModal,
        toggle: toggleModal,
        get activeModal() {
            return activeModal;
        },
    };
})(window);
