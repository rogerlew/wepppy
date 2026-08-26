/** @jest-environment jsdom */
/* eslint-env node */

const fs = require("node:fs");
const path = require("node:path");

const source = fs.readFileSync(path.resolve(__dirname, "../config_builder.js"), "utf8");

function description(canOverride = false) {
    const empty = {
        requires: [], conflicts: [], allowed_dem: [], allowed_delineation: [],
        allowed_representation: [], allowed_soil: [], allowed_landuse: [],
        allowed_climate: [], allowed_mods: [], allowed_capability_profiles: []
    };
    const localeConstraints = Object.assign({}, empty, {
        allowed_dem: ["dem-a", "dem-b"], allowed_delineation: ["wbt"],
        allowed_representation: ["single"], allowed_soil: ["soil"],
        allowed_landuse: ["land"], allowed_climate: ["climate"],
        allowed_capability_profiles: ["capabilities"]
    });
    const item = (component_id, kind, label, extra = {}) => Object.assign({
        component_id, kind, label, description: label + " help", default_cellsize: null,
        constraints: empty
    }, extra);
    return {
        schema_version: 1, registry_revision: "registry-1", can_override_cellsize: canOverride,
        allowed_cell_sizes: [1, 2, 5, 10, 25, 30, 90, 100], config_token: "config",
        config_filename: "config.cfg",
        components: [
            item("conus", "locale", "Continental US", {constraints: localeConstraints}),
            item("dem-a", "dem", "DEM A", {default_cellsize: 10}),
            item("dem-b", "dem", "DEM B", {default_cellsize: 30}),
            item("wbt", "delineation", "WBT"), item("single", "representation", "Single OFE"),
            item("soil", "soil", "Soil"), item("land", "landuse", "Land cover"),
            item("climate", "climate", "Climate"), item("capabilities", "capability", "Capabilities")
        ]
    };
}

function review() {
    return {
        locale: "conus", dem: "dem-a", dem_default_cellsize: 10, cellsize: 10,
        cellsize_source: "dem_default", delineation_backend: "wbt",
        watershed_representation: "single", soil: "soil", landuse: "land",
        climate: "climate", mods: [], capabilities: {climate: ["station"]},
        config_filename: "config.cfg"
    };
}

function installDom() {
    document.body.innerHTML = `
      <div data-config-builder data-description-url="/describe" data-validation-url="/validate" data-creation-url="/create">
        <div data-builder-error-summary tabindex="-1" hidden><ul data-builder-error-list></ul></div>
        <form data-builder-form>${["locale", "dem", "delineation_backend", "watershed_representation", "soil", "landuse", "climate"].map((field) => `
          <label for="builder-${field}">${field}</label><select id="builder-${field}" name="${field}"></select>
          <p data-builder-field-error="${field}"></p>`).join("")}
          <p data-builder-cellsize></p>
          <div data-builder-override hidden><select name="cellsize_override" id="builder-cellsize-override"></select><p data-builder-field-error="cellsize_override"></p></div>
          <fieldset data-builder-mods hidden><div data-builder-mod-options></div><p data-builder-field-error="mods"></p></fieldset>
          <p data-builder-change-reason></p>
        </form>
        <section data-builder-review hidden><dl data-builder-review-list></dl></section>
        <button data-builder-validate disabled>Review</button><button data-builder-create disabled>Create</button>
        <p data-builder-status tabindex="-1"></p>
      </div>`;
}

function dependencies(http, navigate = jest.fn()) {
    return {
        http,
        navigate,
        dom: {
            setText: (node, value) => { node.textContent = String(value); },
            delegate: (root, eventName, selector, handler) => root.addEventListener(eventName, (event) => {
                if (event.target.matches(selector)) { handler(event, event.target); }
            })
        }
    };
}

async function settle() {
    for (let index = 0; index < 12; index += 1) { await Promise.resolve(); }
}

describe("Config Builder controller", () => {
    beforeEach(() => {
        document.body.innerHTML = "";
        delete window.WCHttp;
        delete window.WCDom;
        window.eval(source);
        installDom();
    });

    test("loads only server-described stable IDs and validates to the exact server review", async () => {
        const schema = description(false);
        const serverReview = review();
        const http = {
            getRqEngineToken: jest.fn().mockResolvedValue("token"),
            request: jest.fn((url) => Promise.resolve({body: url === "/describe" ? schema : {valid: true, registry_revision: "registry-1", review: serverReview}}))
        };
        const root = document.querySelector("[data-config-builder]");
        const controller = new window.ConfigBuilder(root, dependencies(http));
        await controller.init();
        await controller.validate(true);

        expect([...root.querySelector("[name=dem]").options].map((option) => option.value)).toEqual(["dem-a", "dem-b"]);
        expect(root.querySelector("[data-builder-override]").hidden).toBe(true);
        expect(controller.validatedReview).toEqual(serverReview);
        expect(root.querySelector("[data-builder-review-list]").textContent).toContain("config.cfg");
        expect(root.querySelector("[data-builder-create]").disabled).toBe(false);
        expect(http.request.mock.calls.at(-1)[1].json.selections).toEqual({
            locale: "conus", dem: "dem-a", delineation_backend: "wbt",
            watershed_representation: "single", soil: "soil", landuse: "land",
            climate: "climate", mods: [], capability_profile: "capabilities"
        });
    });

    test("clears an invalidated downstream value visibly and never submits it", async () => {
        const schema = description(false);
        const secondLocale = Object.assign({}, schema.components[0], {
            component_id: "limited", label: "Limited", constraints: Object.assign({}, schema.components[0].constraints, {allowed_dem: ["dem-b"]})
        });
        schema.components.push(secondLocale);
        const http = {getRqEngineToken: jest.fn().mockResolvedValue("token"), request: jest.fn().mockResolvedValue({body: schema})};
        const root = document.querySelector("[data-config-builder]");
        const controller = new window.ConfigBuilder(root, dependencies(http));
        await controller.init();
        root.querySelector("[name=locale]").value = "limited";
        controller._renderDependencies(true);

        expect(root.querySelector("[name=dem]").value).toBe("dem-b");
        expect(root.querySelector("[data-builder-change-reason]").textContent).toContain("unavailable");
        expect(controller._selections().dem).toBe("dem-b");
    });

    test("offers only fixed privileged overrides and clears intent at the DEM default", async () => {
        const schema = description(true);
        const http = {getRqEngineToken: jest.fn().mockResolvedValue("token"), request: jest.fn().mockResolvedValue({body: schema})};
        const root = document.querySelector("[data-config-builder]");
        const controller = new window.ConfigBuilder(root, dependencies(http));
        await controller.init();
        const override = root.querySelector("[name=cellsize_override]");

        expect(root.querySelector("[data-builder-override]").hidden).toBe(false);
        expect([...override.options].map((option) => Number(option.value))).toEqual(schema.allowed_cell_sizes);
        expect(controller._selections()).not.toHaveProperty("cellsize_override");
        override.value = "30";
        expect(controller._selections().cellsize_override).toBe(30);
        override.value = "10";
        expect(controller._selections()).not.toHaveProperty("cellsize_override");
    });

    test("focuses actionable validation errors and prevents duplicate active creation", async () => {
        let rejectCreation;
        const creation = new Promise((_resolve, reject) => { rejectCreation = reject; });
        const schema = description(false);
        const http = {
            getRqEngineToken: jest.fn().mockResolvedValue("token"),
            request: jest.fn((url) => {
                if (url === "/describe") { return Promise.resolve({body: schema}); }
                if (url === "/validate") {
                    const error = new Error("invalid");
                    error.body = {errors: [{field: "dem", message: "Choose another DEM."}], error: {details: "Choose another DEM."}};
                    return Promise.reject(error);
                }
                return creation;
            })
        };
        const root = document.querySelector("[data-config-builder]");
        const controller = new window.ConfigBuilder(root, dependencies(http));
        await controller.init();
        await controller.validate(true);
        expect(document.activeElement).toBe(root.querySelector("[data-builder-error-summary]"));
        expect(root.querySelector("[name=dem]").getAttribute("aria-invalid")).toBe("true");

        controller.validatedReview = review();
        controller.busy = false;
        const first = controller.create();
        const second = controller.create();
        await settle();
        expect(http.request.mock.calls.filter((call) => call[0] === "/create")).toHaveLength(1);
        rejectCreation(Object.assign(new Error("creation failed"), {body: {error: {details: "Try again."}}}));
        await first;
        await second;
    });

    test("reloads a stale schema and requires a fresh review without losing valid choices", async () => {
        const firstSchema = description(false);
        const refreshedSchema = Object.assign({}, description(false), {registry_revision: "registry-2"});
        let descriptions = 0;
        const http = {
            getRqEngineToken: jest.fn().mockResolvedValue("token"),
            request: jest.fn((url) => {
                if (url === "/describe") {
                    descriptions += 1;
                    return Promise.resolve({body: descriptions === 1 ? firstSchema : refreshedSchema});
                }
                if (url === "/validate") { return Promise.resolve({body: {review: review()}}); }
                return Promise.reject(Object.assign(new Error("stale"), {
                    status: 409, body: {error: {code: "stale_builder_schema", details: "Reload."}}
                }));
            })
        };
        const root = document.querySelector("[data-config-builder]");
        const controller = new window.ConfigBuilder(root, dependencies(http));
        await controller.init();
        await controller.validate(false);
        await controller.create();

        expect(controller.description.registry_revision).toBe("registry-2");
        expect(controller._selections().dem).toBe("dem-a");
        expect(controller.validatedReview).toBeNull();
        expect(root.querySelector("[data-builder-create]").disabled).toBe(true);
        expect(document.activeElement).toBe(root.querySelector("[data-builder-status]"));
        expect(root.querySelector("[data-builder-status]").textContent).toContain("Review and validate");
    });

    test("successful creation identifies the run and navigates to the server config location", async () => {
        const schema = description(false);
        const navigate = jest.fn();
        const http = {
            getRqEngineToken: jest.fn().mockResolvedValue("token"),
            request: jest.fn((url) => {
                if (url === "/describe") { return Promise.resolve({body: schema}); }
                if (url === "/validate") { return Promise.resolve({body: {review: review()}}); }
                return Promise.resolve({body: {run_id: "run-7", location: "/runs/run-7/config/"}});
            })
        };
        const root = document.querySelector("[data-config-builder]");
        const controller = new window.ConfigBuilder(root, dependencies(http, navigate));
        await controller.init();
        await controller.validate(false);
        await controller.create();

        expect(navigate).toHaveBeenCalledWith("/runs/run-7/config/");
        expect(root.querySelector("[data-builder-status]").textContent).toContain("run-7");
    });
});
