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

    describe("unitizer canonical value handling", () => {
        test("serializeForm uses unitizerCanonicalValue when present (URL format)", () => {
            const form = document.createElement("form");
            form.innerHTML = `
                <input type="number" name="snow_density" value="6242.8">
            `;
            const input = form.querySelector("input");
            // Simulate unitizer setting the canonical value (in g/cm³)
            // while displaying in lb/ft³
            input.dataset.unitizerCanonicalValue = "100";

            const params = WCForms.serializeForm(form);
            expect(params.get("snow_density")).toBe("100");
        });

        test("serializeForm uses unitizerCanonicalValue when present (JSON format)", () => {
            const form = document.createElement("form");
            form.innerHTML = `
                <input type="number" name="snow_density" value="6242.8">
                <input type="number" name="settling_density" value="15607">
            `;
            const inputs = form.querySelectorAll("input");
            inputs[0].dataset.unitizerCanonicalValue = "100";
            inputs[1].dataset.unitizerCanonicalValue = "250";

            const payload = WCForms.serializeForm(form, { format: "json" });
            expect(payload.snow_density).toBe("100");
            expect(payload.settling_density).toBe("250");
        });

        test("serializeForm falls back to field.value when unitizerCanonicalValue is empty", () => {
            const form = document.createElement("form");
            form.innerHTML = `
                <input type="number" name="temperature" value="32">
            `;
            const input = form.querySelector("input");
            input.dataset.unitizerCanonicalValue = "";

            const params = WCForms.serializeForm(form);
            expect(params.get("temperature")).toBe("32");
        });

        test("serializeForm falls back to field.value when unitizerCanonicalValue is absent", () => {
            const form = document.createElement("form");
            form.innerHTML = `
                <input type="number" name="plain_field" value="42">
            `;

            const params = WCForms.serializeForm(form);
            expect(params.get("plain_field")).toBe("42");
        });

        test("serializeForm handles mixed fields with and without canonical values", () => {
            const form = document.createElement("form");
            form.innerHTML = `
                <input type="text" name="name" value="test-project">
                <input type="number" name="snow_density" value="6242.8">
                <input type="checkbox" name="enabled" checked>
                <input type="number" name="threshold" value="5">
            `;
            const snowInput = form.querySelector('input[name="snow_density"]');
            snowInput.dataset.unitizerCanonicalValue = "100";
            // threshold has no canonical value set

            const payload = WCForms.serializeForm(form, { format: "json" });
            expect(payload.name).toBe("test-project");
            expect(payload.snow_density).toBe("100");  // Uses canonical
            expect(payload.enabled).toBe(true);
            expect(payload.threshold).toBe("5");  // Uses displayed value
        });

        test("serializeForm preserves canonical value precision", () => {
            const form = document.createElement("form");
            form.innerHTML = `
                <input type="number" name="precise_value" value="0.123">
            `;
            const input = form.querySelector("input");
            // High precision canonical value
            input.dataset.unitizerCanonicalValue = "0.00123456789";

            const payload = WCForms.serializeForm(form, { format: "json" });
            expect(payload.precise_value).toBe("0.00123456789");
        });

        test("applyValues clears stale canonical value to prevent incorrect serialization", () => {
            const form = document.createElement("form");
            form.innerHTML = `
                <input type="number" name="snow_density" value="6242.8">
            `;
            const input = form.querySelector("input");
            // Simulate unitizer having set a canonical value
            input.dataset.unitizerCanonicalValue = "100";

            // Programmatically update the field via applyValues
            WCForms.applyValues(form, { snow_density: "200" });

            // The canonical value should be cleared so serialization uses the new displayed value
            expect(input.dataset.unitizerCanonicalValue).toBe("");
            const payload = WCForms.serializeForm(form, { format: "json" });
            expect(payload.snow_density).toBe("200");
        });

        test("applyValues on field without canonical value works normally", () => {
            const form = document.createElement("form");
            form.innerHTML = `
                <input type="number" name="threshold" value="5">
            `;

            WCForms.applyValues(form, { threshold: "10" });

            const payload = WCForms.serializeForm(form, { format: "json" });
            expect(payload.threshold).toBe("10");
        });

        test("applyValues resets activeUnit to canonical to prevent misinterpretation", () => {
            const form = document.createElement("form");
            form.innerHTML = `
                <input type="number" name="snow_density" value="6242.8"
                       data-unitizer-category="snow-density"
                       data-unitizer-unit="g/cm^3">
            `;
            const input = form.querySelector("input");
            // Simulate unitizer state after user switched to imperial
            input.dataset.unitizerCanonicalValue = "100";
            input.dataset.unitizerActiveUnit = "lb/ft^3";

            // Programmatically set a new canonical value (e.g., from server response)
            WCForms.applyValues(form, { snow_density: "150" });

            // Active unit should be reset to canonical so unitizer won't misinterpret
            expect(input.dataset.unitizerActiveUnit).toBe("g/cm^3");
            expect(input.dataset.unitizerCanonicalValue).toBe("");
            expect(input.value).toBe("150");

            // Serialization should use the new displayed value
            const payload = WCForms.serializeForm(form, { format: "json" });
            expect(payload.snow_density).toBe("150");
        });
    });
});
