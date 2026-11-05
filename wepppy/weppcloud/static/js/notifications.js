(function () {
    "use strict";

    function initialize() {
        document.querySelectorAll("[data-notification-bell]").forEach(function (bell) {
            if (bell.dataset.notificationReady) return;
            bell.dataset.notificationReady = "true";
            var badge = bell.querySelector("[data-notification-count]");
            fetch(bell.dataset.countUrl, {credentials: "same-origin", cache: "no-store"})
                .then(function (response) {
                    if (!response.ok) throw new Error("count unavailable");
                    return response.json();
                }).then(function (payload) {
                    var count = payload.Content && payload.Content.unread_count;
                    if (!Number.isInteger(count) || count < 0) throw new Error("invalid count");
                    badge.textContent = String(count);
                    badge.hidden = count === 0;
                    bell.setAttribute("aria-label", "Notifications, " + count + " unread");
                }).catch(function () {
                    badge.textContent = "?";
                    badge.hidden = false;
                    bell.setAttribute("aria-label", "Notifications, unread count unavailable");
                    bell.title = "Unread count unavailable. Open notifications to try again.";
                });
        });

        var list = document.querySelector("[data-notification-list]");
        if (!list || list.dataset.notificationReady) return;
        list.dataset.notificationReady = "true";
        var boxes = Array.from(list.querySelectorAll("[data-notification-id]"));
        var all = list.querySelector("[data-select-all]");
        var buttons = Array.from(list.querySelectorAll("[data-mark-read]"));
        var error = list.querySelector("[data-notification-error]");
        var busy = false;
        function selected() { return boxes.filter(function (box) { return box.checked; }); }
        function refresh() {
            var count = selected().length;
            all.checked = boxes.length > 0 && count === boxes.length;
            all.indeterminate = count > 0 && count < boxes.length;
            buttons.forEach(function (button) { button.disabled = busy || count === 0; });
        }
        all.addEventListener("change", function () {
            boxes.forEach(function (box) { box.checked = all.checked; });
            refresh();
        });
        boxes.forEach(function (box) { box.addEventListener("change", refresh); });
        window.addEventListener("pageshow", function () {
            boxes.forEach(function (box) { box.checked = false; });
            refresh();
        });
        buttons.forEach(function (button) {
            button.addEventListener("click", function () {
                if (busy || selected().length === 0) return;
                busy = true;
                error.hidden = true;
                refresh();
                var token = document.querySelector('meta[name="csrf-token"]');
                fetch(list.dataset.updateUrl, {
                    method: "POST", credentials: "same-origin", cache: "no-store",
                    headers: {"Content-Type": "application/json", "X-CSRFToken": token ? token.content : ""},
                    body: JSON.stringify({notification_ids: selected().map(function (box) {
                        return Number(box.dataset.notificationId);
                    }), read: button.dataset.markRead === "true"})
                }).then(function (response) {
                    if (!response.ok) throw new Error("update unavailable");
                    return response.json();
                }).then(function () {
                    boxes.forEach(function (box) { box.checked = false; });
                    window.location.reload();
                }).catch(function () {
                    error.textContent = "The change could not be confirmed. Refresh to check the saved state, or try again.";
                    error.hidden = false;
                    busy = false;
                    refresh();
                });
            });
        });
        refresh();
    }
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize);
    else initialize();
}());
