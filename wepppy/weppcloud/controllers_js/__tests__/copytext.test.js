/**
 * @jest-environment jsdom
 */

const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");

function installMiniJquery() {
    global.$ = function $(selector, context) {
        if (typeof context === "string") {
            var root = document.querySelector(context);
            if (!root) {
                return [];
            }
            return Array.prototype.slice.call(root.querySelectorAll(selector));
        }

        var matches = Array.prototype.slice.call(document.querySelectorAll(selector));
        return {
            prev: function prev() {
                if (matches.length === 0) {
                    return [];
                }
                var previous = matches[0].previousElementSibling;
                return previous ? [previous] : [];
            }
        };
    };
}

describe("copytext copytable", () => {
    beforeEach(() => {
        jest.resetModules();
        document.body.innerHTML = "";
        installMiniJquery();
        global.alert = jest.fn();
        document.execCommand = jest.fn(() => true);
    });

    afterEach(() => {
        delete global.$;
        delete global.copytable;
        delete global.setClipboardText;
        delete global.alert;
    });

    function loadCopyTextScript() {
        var scriptPath = resolve(require.resolve("../../static/js/copytext.js"));
        var script = readFileSync(scriptPath, "utf-8");
        window.eval(script);
    }

    test("prepends heading text for button-based copy controls", () => {
        document.body.innerHTML = `
            <h5>Report
              <button type="button" onclick="copytable('rpt_tbl')">
                <img src="/static/icon.png" alt="" aria-hidden="true" />
              </button>
            </h5>
            <table id="rpt_tbl">
              <tr><th>A</th><th>B</th></tr>
              <tr><td>1</td><td>2</td></tr>
            </table>
        `;
        loadCopyTextScript();

        var clipboardSpy = jest.spyOn(window, "setClipboardText").mockReturnValue(1);
        window.copytable("rpt_tbl");

        expect(clipboardSpy).toHaveBeenCalledTimes(1);
        var copied = clipboardSpy.mock.calls[0][0];
        expect(copied).toContain("Report");
        expect(copied).toContain("A\tB");
        expect(copied).toContain("1\t2");
    });
});
