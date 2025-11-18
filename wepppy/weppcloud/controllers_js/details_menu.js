(function (global) {
    "use strict";

    var doc = global.document;
    var SELECTORS = [".wc-run-header__menu", ".wc-nav__menu"];
    var bound = false;

    function closeMenus(target) {
        if (!doc || !doc.querySelectorAll) {
            return;
        }
        SELECTORS.forEach(function (selector) {
            var openMenus = doc.querySelectorAll(selector + "[open]");
            Array.prototype.forEach.call(openMenus, function (menu) {
                if (!menu || (target && menu.contains(target))) {
                    return;
                }
                menu.removeAttribute("open");
            });
        });
    }

    function bind() {
        if (bound || !doc || !doc.addEventListener) {
            return;
        }
        bound = true;

        doc.addEventListener("click", function handleClick(event) {
            closeMenus(event && event.target);
        });

        doc.addEventListener("keyup", function handleKeyup(event) {
            var key = event && (event.key || event.keyCode);
            if (key === "Escape" || key === "Esc" || key === 27) {
                closeMenus();
            }
        });
    }

    bind();

    var api = global.WCDetailsMenu || {};
    api.closeAll = function () {
        closeMenus();
    };
    global.WCDetailsMenu = api;
}(typeof window !== "undefined" ? window : this));
