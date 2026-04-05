/**
 * @jest-environment jsdom
 */

const { readFileSync } = require("node:fs");
const { resolve } = require("node:path");

const scriptPath = resolve(globalThis.process.cwd(), "../static/js/sorttable.js");
const scriptSource = readFileSync(scriptPath, "utf-8");

const flushMutations = () => new Promise((resolveMutation) => setTimeout(resolveMutation, 0));

function loadSorttable() {
    window.eval(scriptSource);
    document.dispatchEvent(new Event("DOMContentLoaded", { bubbles: true }));
}

function getRenderedColumnValues() {
    return Array.from(document.querySelectorAll("tbody tr"))
        .filter((row) => !row.dataset.sortPosition)
        .map((row) => {
            const visibleUnitizedValue = row.cells[0].querySelector(".unitizer:not(.invisible)");
            if (visibleUnitizedValue) {
                return visibleUnitizedValue.textContent.trim();
            }
            return row.cells[0].textContent.trim();
        });
}

describe("sorttable", () => {
    beforeAll(() => {
        loadSorttable();
    });

    beforeEach(() => {
        document.body.innerHTML = "";
    });

    afterEach(() => {
        document.body.innerHTML = "";
    });

    test("sorts mixed numeric unitizer values by the visible value", async () => {
        document.body.innerHTML = `
            <table class="sortable">
                <thead>
                    <tr><th>Avg Soil Loss</th></tr>
                </thead>
                <tbody>
                    <tr data-sort-position="top"><td>kg/yr</td></tr>
                    <tr><td><div class="unitizer-wrapper"><div class="unitizer">1.6</div><div class="unitizer invisible">0.06</div></div></td></tr>
                    <tr><td><div class="unitizer-wrapper"><div class="unitizer">2100000</div><div class="unitizer invisible">826771.6</div></div></td></tr>
                    <tr><td><div class="unitizer-wrapper"><div class="unitizer">2700</div><div class="unitizer invisible">1063</div></div></td></tr>
                    <tr><td><div class="unitizer-wrapper"><div class="unitizer">1400</div><div class="unitizer invisible">551.2</div></div></td></tr>
                    <tr data-sort-position="bottom"><td>Mean</td></tr>
                </tbody>
            </table>
        `;

        await flushMutations();

        const header = document.querySelector("th");
        header.click();
        expect(getRenderedColumnValues()).toEqual(["1.6", "1400", "2700", "2100000"]);
        expect(document.querySelector("tbody tr:first-child").dataset.sortPosition).toBe("top");
        expect(document.querySelector("tbody tr:last-child").dataset.sortPosition).toBe("bottom");

        header.click();
        expect(getRenderedColumnValues()).toEqual(["2100000", "2700", "1400", "1.6"]);
        expect(document.querySelector("tbody tr:first-child").dataset.sortPosition).toBe("top");
        expect(document.querySelector("tbody tr:last-child").dataset.sortPosition).toBe("bottom");
    });

    test("prefers sorttable_customkey over rendered cell text", async () => {
        document.body.innerHTML = `
            <table class="sortable">
                <thead>
                    <tr><th>Runoff</th></tr>
                </thead>
                <tbody>
                    <tr><td sorttable_customkey="2">two hundred</td></tr>
                    <tr><td sorttable_customkey="10">ten</td></tr>
                    <tr><td sorttable_customkey="-5">negative five</td></tr>
                </tbody>
            </table>
        `;

        await flushMutations();

        document.querySelector("th").click();
        expect(getRenderedColumnValues()).toEqual(["negative five", "two hundred", "ten"]);
    });
});
