/**
 * @jest-environment jsdom
 */

beforeAll(async () => {
    await import("../dom.js");
    await import("../forms.js");
});

describe("WCForms helpers", () => {
    let WCForms;

    beforeAll(() => {
        WCForms = window.WCForms;
    });

    afterEach(() => {
        document.head.innerHTML = "";
        document.body.innerHTML = "";
    });

    function buildSampleForm() {
        const form = document.createElement("form");
        form.innerHTML = `
            <input type="text" name="name" value="spruce">
            <input type="checkbox" name="agree" value="yes" checked>
            <input type="checkbox" name="agree" value="no">
            <input type="checkbox" name="single" checked>
            <input type="radio" name="mode" value="fast" checked>
            <input type="radio" name="mode" value="slow">
            <select name="multi" multiple>
                <option value="a" selected>A</option>
                <option value="b" selected>B</option>
                <option value="c">C</option>
            </select>
        `;
        return form;
    }

    test("serializeForm with URL format mirrors jQuery semantics", () => {
        const form = buildSampleForm();
        const params = WCForms.serializeForm(form);

        expect(params.get("name")).toBe("spruce");
        expect(params.getAll("agree")).toEqual(["yes"]);
        expect(params.get("single")).toBe("on");
        expect(params.getAll("multi")).toEqual(["a", "b"]);
        expect(params.get("mode")).toBe("fast");
    });

    test("serializeForm with json format normalizes booleans and arrays", () => {
        const form = buildSampleForm();
        const payload = WCForms.serializeForm(form, { format: "json" });

        expect(payload.name).toBe("spruce");
        expect(payload.agree).toEqual(["yes"]);
        expect(payload.single).toBe(true);
        expect(payload.multi).toEqual(["a", "b"]);
        expect(payload.mode).toBe("fast");
    });

    test("applyValues hydrates radios, checkboxes, and selects", () => {
        const form = document.createElement("form");
        form.innerHTML = `
            <input type="checkbox" name="flag" value="on">
            <input type="checkbox" name="group" value="x">
            <input type="checkbox" name="group" value="y">
            <input type="radio" name="mode" value="fast">
            <input type="radio" name="mode" value="slow">
            <select name="multi" multiple>
                <option value="a">A</option>
                <option value="b">B</option>
                <option value="c">C</option>
            </select>
            <input type="text" name="notes">
        `;

        WCForms.applyValues(form, {
            flag: true,
            group: ["y"],
            mode: "slow",
            multi: ["a", "c"],
            notes: "updated"
        });

        expect(form.elements.flag.checked).toBe(true);
        expect(form.elements.group[0].checked).toBe(false);
        expect(form.elements.group[1].checked).toBe(true);
        expect(form.elements.mode[1].checked).toBe(true);
        const selectedValues = Array.from(form.elements.multi.options)
            .filter((opt) => opt.selected)
            .map((opt) => opt.value);
        expect(selectedValues).toEqual(["a", "c"]);
        expect(form.elements.notes.value).toBe("updated");
    });

    test("findCsrfToken inspects meta tags and form fields", () => {
        document.head.innerHTML = `<meta name="csrf-token" content="token-head">`;
        expect(WCForms.findCsrfToken(null)).toBe("token-head");

        const form = document.createElement("form");
        form.innerHTML = `<input type="hidden" name="csrf_token" value="token-field">`;
        document.head.innerHTML = "";
        expect(WCForms.findCsrfToken(form)).toBe("token-field");
    });
});
