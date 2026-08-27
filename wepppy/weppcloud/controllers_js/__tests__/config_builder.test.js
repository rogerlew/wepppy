/** @jest-environment jsdom */
/* eslint-env node */

const fs = require("node:fs");
const path = require("node:path");

const source = fs.readFileSync(path.resolve(__dirname, "../config_builder.js"), "utf8");

function description(canOverride = false) {
    const empty = {
        requires: [], conflicts: [], allowed_dem: [], allowed_delineation: [],
        allowed_representation: [], allowed_soil: [], allowed_landuse: [],
        allowed_wepp_binary: [], allowed_climate: [], allowed_mods: [],
        allowed_capability_profiles: [], allowed_climate_station_database: []
    };
    const localeConstraints = Object.assign({}, empty, {
        allowed_dem: ["dem-a", "dem-b"], allowed_delineation: ["wbt"],
        allowed_representation: ["single", "multiple-ofe"], allowed_wepp_binary: ["wepp_dcc52a6", "wepp_260803"], allowed_soil: ["soil"],
        allowed_landuse: ["land"], allowed_climate: ["climate"],
        allowed_climate_station_database: ["stations-2015"],
        allowed_capability_profiles: ["continental-us-capabilities"]
    });
    const item = (component_id, kind, label, extra = {}) => Object.assign({
        component_id, kind, label, description: label + " help", default_cellsize: null,
        constraints: empty
    }, extra);
    const graph = {
        capabilities: {
            schema_version: 3,
            locale_profiles: ["continental-us"], dem_sources: ["dem-a", "dem-b"],
            delineation_backends: ["wbt"], watershed_representations: ["single", "multiple-ofe"],
            wepp_binaries: ["wepp_dcc52a6", "wepp_260803"], soil_datasets: ["soil"],
            landuse_datasets: ["land"], climate_datasets: ["climate"],
            climate_station_databases: ["stations-2015"], mods: [],
            allowed_model_tuples: [
                "wbt|single|wepp_dcc52a6", "wbt|single|wepp_260803",
                "wbt|multiple-ofe|wepp_260803"
            ]
        },
        capability_defaults: {
            locale_profile: "continental-us", dem_source: "dem-a", soil_dataset: "soil",
            landuse_dataset: "land", climate_dataset: "climate",
            climate_station_database: "stations-2015", delineation_backend: "wbt",
            watershed_representation: "single", wepp_binary: "wepp_260803"
        }
    };
    const components = [
        item("continental-us", "locale", "Continental US", {constraints: localeConstraints}),
        item("dem-a", "dem", "DEM A", {default_cellsize: 10}),
        item("dem-b", "dem", "DEM B", {default_cellsize: 30}),
        item("wbt", "delineation", "WBT"), item("single", "representation", "Single OFE"),
        item("multiple-ofe", "representation", "Multiple OFE", {constraints: Object.assign({}, empty, {requires: ["continental-us", "wbt", "wepp_260803"]})}),
        item("wepp_dcc52a6", "wepp_binary", "WEPP legacy"), item("wepp_260803", "wepp_binary", "WEPP 260803"),
        item("soil", "soil", "Soil"), item("land", "landuse", "Land cover"),
        item("climate", "climate", "Climate"),
        item("stations-2015", "climate_station_database", "2015"),
        item("continental-us-capabilities", "capability", "Capabilities")
    ];
    return {
        schema_version: 2, builder_description_schema_version: 2,
        registry_revision: "registry-1", can_override_cellsize: canOverride,
        allowed_cell_sizes: [1, 2, 5, 10, 25, 30, 90, 100], config_token: "config",
        config_filename: "config.cfg", default_selections: {delineation_backend: "wbt", watershed_representation: "single", wepp_binary: "wepp_260803"},
        capability_graph: graph,
        components,
        capability_graphs_by_locale: {"continental-us": graph},
        components_by_locale: {"continental-us": components}
    };
}

function review() {
    return {
        locale: "continental-us", dem: "dem-a", dem_default_cellsize: 10, cellsize: 10,
        cellsize_source: "dem_default", delineation_backend: "wbt",
        watershed_representation: "single", wepp_binary: "wepp_260803", soil: "soil", landuse: "land",
        climate: "climate", climate_station_database: "stations-2015",
        mods: [], capabilities: {climate: ["station"]},
        config_filename: "config.cfg"
    };
}

function addLocale(schema, spec) {
    const baseLocale = schema.components_by_locale["continental-us"].find((item) => item.kind === "locale");
    const constraints = Object.assign({}, baseLocale.constraints, {
        allowed_dem: spec.dem,
        allowed_soil: spec.soil,
        allowed_landuse: spec.landuse,
        allowed_climate: spec.climate,
        allowed_climate_station_database: spec.stations,
        allowed_capability_profiles: [spec.id + "-capabilities"]
    });
    const locale = Object.assign({}, baseLocale, {
        component_id: spec.id,
        label: spec.id,
        constraints
    });
    const shared = schema.components_by_locale["continental-us"].filter((item) => [
        "delineation", "representation", "wepp_binary"
    ].includes(item.kind));
    const component = (component_id, kind) => ({
        component_id, kind, label: component_id, description: component_id,
        default_cellsize: kind === "dem" ? 30 : null, constraints: {}
    });
    const population = [locale, ...shared];
    [
        [spec.dem, "dem"], [spec.soil, "soil"], [spec.landuse, "landuse"],
        [spec.climate, "climate"], [spec.stations, "climate_station_database"]
    ].forEach(([ids, kind]) => ids.forEach((id) => population.push(component(id, kind))));
    population.push(component(spec.id + "-capabilities", "capability"));
    schema.components_by_locale[spec.id] = population;
    schema.capability_graphs_by_locale[spec.id] = {
        capabilities: Object.assign({}, schema.capability_graphs_by_locale["continental-us"].capabilities, {
            locale_profiles: [spec.id],
            dem_sources: spec.dem,
            soil_datasets: spec.soil,
            landuse_datasets: spec.landuse,
            climate_datasets: spec.climate,
            climate_station_databases: spec.stations
        }),
        capability_defaults: {
            locale_profile: spec.id,
            dem_source: spec.dem[0],
            soil_dataset: spec.soil[0],
            landuse_dataset: spec.defaultLanduse,
            climate_dataset: "vanilla_cligen",
            climate_station_database: spec.stations[0],
            delineation_backend: "wbt",
            watershed_representation: "single",
            wepp_binary: "wepp_260803"
        }
    };
}

function installDom() {
    document.body.innerHTML = `
      <div data-config-builder data-description-url="/describe" data-validation-url="/validate" data-creation-url="/create">
        <div data-builder-error-summary tabindex="-1" hidden><ul data-builder-error-list></ul></div>
        <form data-builder-form>${["locale", "dem", "delineation_backend", "watershed_representation", "wepp_binary", "soil", "landuse", "climate", "climate_station_database"].map((field) => `
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
            locale: "continental-us", dem: "dem-a", delineation_backend: "wbt",
            watershed_representation: "single", wepp_binary: "wepp_260803", soil: "soil", landuse: "land",
            climate: "climate", mods: [], capability_profile: "continental-us-capabilities",
            climate_station_database: "stations-2015"
        });
        expect(http.request.mock.calls.at(-1)[1].json.builder_description_schema_version).toBe(2);
    });

    test("clears an invalidated graph value visibly and never submits it", async () => {
        const schema = description(false);
        const http = {getRqEngineToken: jest.fn().mockResolvedValue("token"), request: jest.fn().mockResolvedValue({body: schema})};
        const root = document.querySelector("[data-config-builder]");
        const controller = new window.ConfigBuilder(root, dependencies(http));
        await controller.init();
        controller.description.capability_graphs_by_locale["continental-us"].capabilities.dem_sources = ["dem-b"];
        controller._renderDependencies(true);

        expect(root.querySelector("[name=dem]").value).toBe("dem-b");
        expect(root.querySelector("[data-builder-change-reason]").textContent).toContain("incompatible with the current combination");
        expect(controller._selections().dem).toBe("dem-b");
    });

    test("switches locale authority and applies that profile's exact defaults", async () => {
        const schema = description(false);
        const baseLocale = schema.components_by_locale["continental-us"].find((item) => item.kind === "locale");
        const europeLocale = Object.assign({}, baseLocale, {
            component_id: "europe",
            label: "Europe",
            constraints: Object.assign({}, baseLocale.constraints, {
                allowed_dem: ["eu-dem"], allowed_soil: ["eu-soil"],
                allowed_landuse: ["eu-land-1990", "eu-land-2018"],
                allowed_climate: ["eu-vanilla", "eobs"],
                allowed_climate_station_database: ["stations-ghcn"],
                allowed_capability_profiles: ["europe-capabilities"]
            })
        });
        const unique = [
            {component_id: "eu-dem", kind: "dem", label: "EUDEM", description: "EUDEM", default_cellsize: 25, constraints: {}},
            {component_id: "eu-soil", kind: "soil", label: "ESDAC", description: "ESDAC", default_cellsize: null, constraints: {}},
            {component_id: "eu-land-1990", kind: "landuse", label: "CORINE 1990", description: "CORINE 1990", default_cellsize: null, constraints: {}},
            {component_id: "eu-land-2018", kind: "landuse", label: "CORINE 2018", description: "CORINE 2018", default_cellsize: null, constraints: {}},
            {component_id: "eu-vanilla", kind: "climate", label: "Vanilla CLIGEN", description: "Vanilla", default_cellsize: null, constraints: {}},
            {component_id: "eobs", kind: "climate", label: "E-OBS", description: "E-OBS", default_cellsize: null, constraints: {}},
            {component_id: "stations-ghcn", kind: "climate_station_database", label: "GHCN", description: "GHCN", default_cellsize: null, constraints: {}},
            {component_id: "europe-capabilities", kind: "capability", label: "Europe capabilities", description: "Europe", default_cellsize: null, constraints: {}}
        ];
        const shared = schema.components_by_locale["continental-us"].filter((item) => [
            "delineation", "representation", "wepp_binary"
        ].includes(item.kind));
        schema.components_by_locale.europe = [europeLocale, ...shared, ...unique];
        schema.capability_graphs_by_locale.europe = {
            capabilities: Object.assign({}, schema.capability_graphs_by_locale["continental-us"].capabilities, {
                locale_profiles: ["europe"], dem_sources: ["eu-dem"],
                soil_datasets: ["eu-soil"],
                landuse_datasets: ["eu-land-1990", "eu-land-2018"],
                climate_datasets: ["eu-vanilla", "eobs"],
                climate_station_databases: ["stations-ghcn"]
            }),
            capability_defaults: {
                locale_profile: "europe", dem_source: "eu-dem", soil_dataset: "eu-soil",
                landuse_dataset: "eu-land-2018", climate_dataset: "eu-vanilla",
                climate_station_database: "stations-ghcn", delineation_backend: "wbt",
                watershed_representation: "single", wepp_binary: "wepp_260803"
            }
        };
        const http = {
            getRqEngineToken: jest.fn().mockResolvedValue("token"),
            request: jest.fn((url) => Promise.resolve({body: url === "/describe" ? schema : {review: review()}}))
        };
        const root = document.querySelector("[data-config-builder]");
        const controller = new window.ConfigBuilder(root, dependencies(http));
        await controller.init();

        root.querySelector("[name=locale]").value = "europe";
        root.querySelector("[name=locale]").dispatchEvent(new Event("change", {bubbles: true}));
        await settle();

        expect([...root.querySelector("[name=landuse]").options].map((option) => option.value)).toEqual(["eu-land-1990", "eu-land-2018"]);
        expect(root.querySelector("[name=landuse]").value).toBe("eu-land-2018");
        expect(root.querySelector("[name=climate]").value).toBe("eu-vanilla");
        expect([...root.querySelector("[name=climate_station_database]").options].map((option) => option.value)).toEqual(["stations-ghcn"]);
        expect(controller._selections().capability_profile).toBe("europe-capabilities");
    });

    test("renders the authoritative dependent controls for every exposed locale", async () => {
        const schema = description(false);
        const profiles = [
            {
                id: "europe", dem: ["europe-eudem-v1-1"], soil: ["esdac-europe"],
                landuse: ["corine-1990", "corine-2018"], defaultLanduse: "corine-2018",
                climate: ["vanilla_cligen", "eobs_modified"], stations: ["cligen-stations-ghcn"]
            },
            {
                id: "canada", dem: ["copernicus-dem-30"], soil: ["isric-global"],
                landuse: ["c3s-landcover-2020", "c3s-landcover-2019"], defaultLanduse: "c3s-landcover-2020",
                climate: ["vanilla_cligen", "observed_daymet"], stations: ["cligen-stations-ghcn"]
            },
            {
                id: "australia", dem: ["australia-srtm-1s"], soil: ["asris-australia"],
                landuse: ["australia-landuse-2010-2011"], defaultLanduse: "australia-landuse-2010-2011",
                climate: ["vanilla_cligen", "agdc"], stations: ["cligen-stations-ghcn"]
            },
            {
                id: "global-earth", dem: ["copernicus-dem-30"], soil: ["isric-global"],
                landuse: ["c3s-landcover-2020", "c3s-landcover-2019"], defaultLanduse: "c3s-landcover-2020",
                climate: ["vanilla_cligen"], stations: ["cligen-stations-ghcn"]
            }
        ];
        profiles.forEach((profile) => addLocale(schema, profile));
        const http = {
            getRqEngineToken: jest.fn().mockResolvedValue("token"),
            request: jest.fn().mockResolvedValue({body: schema})
        };
        const root = document.querySelector("[data-config-builder]");
        const controller = new window.ConfigBuilder(root, dependencies(http));
        await controller.init();

        expect([...root.querySelector("[name=locale]").options].map((option) => option.value)).toEqual([
            "continental-us", "europe", "canada", "australia", "global-earth"
        ]);
        for (const profile of profiles) {
            root.querySelector("[name=locale]").value = profile.id;
            root.querySelector("[name=locale]").dispatchEvent(new Event("change", {bubbles: true}));
            await settle();
            expect([...root.querySelector("[name=dem]").options].map((option) => option.value)).toEqual(profile.dem);
            expect([...root.querySelector("[name=soil]").options].map((option) => option.value)).toEqual(profile.soil);
            expect([...root.querySelector("[name=landuse]").options].map((option) => option.value)).toEqual(profile.landuse);
            expect(root.querySelector("[name=landuse]").value).toBe(profile.defaultLanduse);
            expect([...root.querySelector("[name=climate]").options].map((option) => option.value)).toEqual(profile.climate);
            expect(root.querySelector("[name=climate]").value).toBe("vanilla_cligen");
            expect([...root.querySelector("[name=climate_station_database]").options].map((option) => option.value)).toEqual(profile.stations);
            expect(controller._selections().capability_profile).toBe(profile.id + "-capabilities");
        }
    });

    test("defaults to WBT and WEPP 260803 and filters invalid model tuples", async () => {
        const schema = description(false);
        const topaz = Object.assign({}, schema.components.find((item) => item.component_id === "wbt"), {component_id: "topaz", label: "TOPAZ"});
        schema.components.push(topaz);
        schema.components_by_locale["continental-us"].push(topaz);
        schema.capability_graphs_by_locale["continental-us"].capabilities.delineation_backends = ["topaz", "wbt"];
        schema.capability_graphs_by_locale["continental-us"].capabilities.allowed_model_tuples.push(
            "topaz|single|wepp_dcc52a6", "topaz|single|wepp_260803"
        );
        const http = {getRqEngineToken: jest.fn().mockResolvedValue("token"), request: jest.fn().mockResolvedValue({body: schema})};
        const root = document.querySelector("[data-config-builder]");
        const controller = new window.ConfigBuilder(root, dependencies(http));
        await controller.init();

        expect(root.querySelector("[name=delineation_backend]").value).toBe("wbt");
        expect(root.querySelector("[name=wepp_binary]").value).toBe("wepp_260803");
        expect([...root.querySelector("[name=watershed_representation]").options].map((option) => option.value)).toContain("multiple-ofe");

        root.querySelector("[name=watershed_representation]").value = "multiple-ofe";
        root.querySelector("[name=watershed_representation]").dispatchEvent(new Event("change", {bubbles: true}));
        await settle();
        expect(root.querySelector("[name=wepp_binary]").value).toBe("wepp_260803");
        expect(controller._selections().wepp_binary).toBe("wepp_260803");
        expect([...root.querySelector("[name=wepp_binary]").options].map((option) => option.value)).toEqual(["wepp_260803"]);
        expect([...root.querySelector("[name=delineation_backend]").options].map((option) => option.value)).toEqual(["wbt"]);

        root.querySelector("[name=watershed_representation]").value = "single";
        controller._renderDependencies(true, "watershed_representation");
        expect([...root.querySelector("[name=wepp_binary]").options].map((option) => option.value)).toEqual(["wepp_dcc52a6", "wepp_260803"]);
        expect([...root.querySelector("[name=delineation_backend]").options].map((option) => option.value)).toEqual(["topaz", "wbt"]);
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
