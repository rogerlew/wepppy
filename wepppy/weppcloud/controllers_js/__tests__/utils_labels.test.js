/**
 * @jest-environment jsdom
 */

describe("applyLabelHtml", () => {
    beforeEach(() => {
        jest.resetModules();
    });

    test("prefers html() when provided", async () => {
        await import("../utils.js");
        const applyLabelHtml = global.applyLabelHtml;
        const label = { html: jest.fn() };
        applyLabelHtml(label, "<b>value</b>");
        expect(label.html).toHaveBeenCalledWith("<b>value</b>");
    });

    test("falls back to innerHTML when html is not a function", async () => {
        await import("../utils.js");
        const applyLabelHtml = global.applyLabelHtml;
        const label = { html: "nope", innerHTML: "" };
        applyLabelHtml(label, "<b>value</b>");
        expect(label.innerHTML).toEqual("<b>value</b>");
    });

    test("handles exceptions and writes textContent", async () => {
        await import("../utils.js");
        const applyLabelHtml = global.applyLabelHtml;
        const label = {
            html: jest.fn(() => { throw new Error("fail"); }),
            textContent: ""
        };
        applyLabelHtml(label, "<b>value</b>");
        expect(label.textContent).toEqual("<b>value</b>");
    });
});
