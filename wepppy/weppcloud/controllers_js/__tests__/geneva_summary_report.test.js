/**
 * @jest-environment jsdom
 */

describe("Geneva summary report interactions", () => {
    afterEach(() => {
        delete global.UnitizerClient;
        delete global.fetch;
        delete global.deck;
        delete window.fetch;
        delete window.deck;
    });

    beforeEach(() => {
        jest.resetModules();
        document.body.innerHTML = `
            <section data-geneva-summary-root data-query-url="/runs/demo/cfg/query/geneva/summary">
              <script id="geneva-summary-payload" type="application/json">
                {
                  "schema_version": 1,
                  "filters": { "datasource_id": "all", "ari_years": [10], "measure": "peak_discharge" },
                  "filter_options": {
                    "datasource_ids": ["all", "cligen_freq", "noaa14_pds"],
                    "datasource_availability": { "cligen_freq": true, "noaa14_pds": true },
                    "ari_years": [10],
                    "measures": ["peak_discharge", "runoff_depth", "runoff_volume"],
                    "duration_minutes": [30, 60]
                  },
                  "assumptions": {
                    "arc_condition": "arc_ii",
                    "storm_distribution_assumption": "neh4_type_b",
                    "uniform_rainfall_assumed": true
                  },
                  "storm_parameters": {
                    "hyetograph_time_step_minutes": 1.0,
                    "storm_shape": "neh4_type_b",
                    "lambda_mode_override": "0.20",
                    "unit_hydrograph_override": "scs_triangular",
                    "timing_method": "kirpich",
                    "tc_override_hours": null
                  },
                  "chart": {
                    "x_axis": "intensity_mm_per_hr",
                    "y_axis": "selected_measure",
                    "series_grouping": "ari_years",
                    "marker_grouping": "duration_minutes",
                    "series": [
                      {
                        "series_id": "ari_10",
                        "series_label": "ARI 10-year",
                        "ari_years": 10,
                        "points": [
                          {
                            "storm_id": "cligen_30m_10y",
                            "datasource_id": "cligen_freq",
                            "duration_minutes": 30,
                            "intensity_mm_per_hr": 40.0,
                            "measure_value": 1.2,
                            "marker_label": "30m"
                          },
                          {
                            "storm_id": "noaa14_60m_10y",
                            "datasource_id": "noaa14_pds",
                            "duration_minutes": 60,
                            "intensity_mm_per_hr": 50.0,
                            "measure_value": 1.5,
                            "marker_label": "1h"
                          }
                        ]
                      }
                    ]
                  },
                  "selected_storm_id": "cligen_30m_10y",
                  "event_table": [
                    {
                      "storm_id": "cligen_30m_10y",
                      "status": "completed",
                      "datasource_id": "cligen_freq",
                      "duration_minutes": 30,
                      "ari_years": 10,
                      "depth_mm": 20.0,
                      "intensity_mm_per_hr": 40.0,
                      "distribution_type": "neh4_type_b",
                      "peak_discharge": { "value": 1.2, "unit": "m3_s" },
                      "time_to_peak_minutes": 5.0,
                      "runoff_volume": { "value": 100.0, "unit": "m3" },
                      "runoff_depth": { "value": 4.0, "unit": "mm" },
                      "warning_count": 0,
                      "error_count": 0
                    },
                    {
                      "storm_id": "noaa14_60m_10y",
                      "status": "completed",
                      "datasource_id": "noaa14_pds",
                      "duration_minutes": 60,
                      "ari_years": 10,
                      "depth_mm": 30.0,
                      "intensity_mm_per_hr": 50.0,
                      "distribution_type": "neh4_type_b",
                      "peak_discharge": { "value": 1.5, "unit": "m3_s" },
                      "time_to_peak_minutes": 6.0,
                      "runoff_volume": { "value": 120.0, "unit": "m3" },
                      "runoff_depth": { "value": 5.0, "unit": "mm" },
                      "warning_count": 0,
                      "error_count": 0
                    },
                    {
                      "storm_id": "cligen_90m_10y",
                      "status": "failed",
                      "datasource_id": "cligen_freq",
                      "duration_minutes": 90,
                      "ari_years": 10,
                      "depth_mm": null,
                      "intensity_mm_per_hr": null,
                      "distribution_type": "",
                      "peak_discharge": null,
                      "time_to_peak_minutes": null,
                      "runoff_volume": null,
                      "runoff_depth": null,
                      "warning_count": 1,
                      "error_count": 1
                    },
                    {
                      "storm_id": "cligen_120m_10y",
                      "status": "unavailable",
                      "datasource_id": "cligen_freq",
                      "duration_minutes": 120,
                      "ari_years": 10,
                      "depth_mm": null,
                      "intensity_mm_per_hr": null,
                      "distribution_type": "",
                      "peak_discharge": null,
                      "time_to_peak_minutes": null,
                      "runoff_volume": null,
                      "runoff_depth": null,
                      "warning_count": 0,
                      "error_count": 0
                    }
                  ],
                  "warnings": [],
                  "errors": []
                }
              </script>
            </section>
            <select id="geneva-summary-datasource"></select>
            <select id="geneva-summary-ari"></select>
            <select id="geneva-summary-measure"></select>
            <p data-geneva-summary-noaa-note hidden></p>
            <div data-geneva-summary-chart></div>
            <p data-geneva-summary-chart-empty hidden></p>
            <table><tbody data-geneva-summary-params-body></tbody></table>
            <table id="geneva-summary-event-table">
              <thead>
                <tr>
                  <th scope="col" class="sorttable_nosort">Select</th>
                  <th scope="col">Storm ID</th>
                  <th scope="col">Datasource</th>
                  <th scope="col" class="wc-text-right" data-sort-type="numeric">Duration</th>
                  <th scope="col" class="wc-text-right" data-sort-type="numeric">ARI</th>
                  <th scope="col" class="wc-text-right" data-sort-type="numeric">Depth</th>
                  <th scope="col" class="wc-text-right" data-sort-type="numeric">Intensity</th>
                  <th scope="col">Distribution</th>
                  <th scope="col" class="wc-text-right" data-sort-type="numeric">Peak Discharge</th>
                  <th scope="col" class="wc-text-right" data-sort-type="numeric">Time to Peak</th>
                  <th scope="col" class="wc-text-right" data-sort-type="numeric">Runoff Volume</th>
                  <th scope="col" class="wc-text-right" data-sort-type="numeric">Runoff Depth</th>
                  <th scope="col" class="wc-text-right" data-sort-type="numeric">Warnings</th>
                  <th scope="col" class="wc-text-right" data-sort-type="numeric">Errors</th>
                </tr>
              </thead>
              <tbody data-geneva-summary-event-body></tbody>
            </table>
            <p data-geneva-summary-events-empty hidden></p>
            <section data-geneva-summary-messages hidden>
              <div data-geneva-summary-warnings hidden><p data-geneva-summary-warnings-body></p></div>
              <div data-geneva-summary-errors hidden><p data-geneva-summary-errors-body></p></div>
            </section>
        `;
    });

    test("marker click selects and focuses matching event table row", async () => {
        const scrollIntoView = jest.fn();
        Element.prototype.scrollIntoView = scrollIntoView;

        await import("../geneva_summary_report.js");
        window.GenevaSummaryReport.getInstance().init();

        const marker = document.querySelector('[data-geneva-summary-chart] [data-storm-id="noaa14_60m_10y"]');
        expect(marker).toBeTruthy();
        marker.dispatchEvent(new MouseEvent("click", { bubbles: true }));

        const rows = document.querySelectorAll('[data-geneva-summary-event-body] tr[data-storm-id]');
        expect(rows).toHaveLength(2);
        expect(document.querySelector('[data-geneva-summary-event-body] tr[data-storm-id="cligen_90m_10y"]')).toBeNull();
        expect(document.querySelector('[data-geneva-summary-event-body] tr[data-storm-id="cligen_120m_10y"]')).toBeNull();

        const selectedRow = document.querySelector('[data-geneva-summary-event-body] tr[data-storm-id="noaa14_60m_10y"]');
        const unselectedRow = document.querySelector('[data-geneva-summary-event-body] tr[data-storm-id="cligen_30m_10y"]');
        const selectedMarker = document.querySelector('[data-geneva-summary-chart] [data-storm-id="noaa14_60m_10y"]');

        expect(selectedRow.classList.contains("is-selected")).toBe(true);
        expect(unselectedRow.classList.contains("is-selected")).toBe(false);
        expect(selectedMarker.getAttribute("aria-pressed")).toBe("true");
        expect(document.activeElement).toBe(selectedRow);
        expect(scrollIntoView).toHaveBeenCalledWith({ block: "center", inline: "nearest" });
        expect(selectedRow.cells[6].getAttribute("sorttable_customkey")).toBe("50");
        expect(selectedRow.cells[8].getAttribute("sorttable_customkey")).toBe("1.5");

        const payload = JSON.parse(document.getElementById("geneva-summary-payload").textContent);
        expect(payload.selected_storm_id).toBe("noaa14_60m_10y");
    });

    test("unavailable selected storm falls back to the first visible completed event", async () => {
        await import("../geneva_summary_report.js");
        window.GenevaSummaryReport.getInstance().init();

        window.GenevaSummaryReport.getInstance().syncSelection("cligen_120m_10y", { focusSelection: false });

        const payload = JSON.parse(document.getElementById("geneva-summary-payload").textContent);
        expect(payload.selected_storm_id).toBe("cligen_30m_10y");
        expect(document.querySelector('[data-geneva-summary-event-body] tr[data-storm-id="cligen_30m_10y"]').classList.contains("is-selected")).toBe(true);
    });

    test("renders storm parameter table from summary payload", async () => {
        await import("../geneva_summary_report.js");
        window.GenevaSummaryReport.getInstance().init();

        const rows = document.querySelectorAll("[data-geneva-summary-params-body] tr");
        expect(rows).toHaveLength(6);

        expect(rows[0].cells[0].textContent).toBe("Hyetograph time step");
        expect(rows[0].cells[1].textContent).toBe("1.00 min");
        expect(rows[1].cells[0].textContent).toBe("Storm Shape");
        expect(rows[1].cells[1].textContent).toBe("NEH-4 B");
        expect(rows[2].cells[1].textContent).toBe("0.20");
        expect(rows[3].cells[1].textContent).toBe("SCS Triangular");
        expect(rows[4].cells[1].textContent).toBe("Kirpich");
        expect(rows[5].cells[1].textContent).toBe("—");
    });

    test("renders pinned unit labels row and unit-free data cells when unitizer client is available", async () => {
        const renderValue = jest.fn((value, unit, options) => {
            const suffix = options && options.includeUnits ? ` ${unit}` : "";
            return `<div class="unitizer-wrapper"><div class="unitizer">${value}${suffix}</div></div>`;
        });
        const renderUnits = jest.fn((unit) =>
            `<div class="unitizer-wrapper"><div class="unitizer">${unit}</div></div>`
        );
        global.UnitizerClient = {
            getClientSync: jest.fn(() => ({
                renderValue,
                renderUnits
            })),
            ready: jest.fn(() => Promise.resolve())
        };

        await import("../geneva_summary_report.js");
        window.GenevaSummaryReport.getInstance().init();
        await Promise.resolve();

        const row = document.querySelector('[data-geneva-summary-event-body] tr[data-storm-id="cligen_30m_10y"]');
        expect(row).toBeTruthy();
        const unitsRow = document.querySelector("[data-geneva-summary-event-body] tr[data-sort-position='top']");
        expect(unitsRow).toBeTruthy();
        expect(unitsRow.cells[5].querySelector(".unitizer-wrapper")).toBeTruthy(); // depth unit
        expect(unitsRow.cells[6].querySelector(".unitizer-wrapper")).toBeTruthy(); // intensity unit
        expect(unitsRow.cells[8].querySelector(".unitizer-wrapper")).toBeTruthy(); // peak discharge unit
        expect(unitsRow.cells[10].querySelector(".unitizer-wrapper")).toBeTruthy(); // runoff volume unit
        expect(unitsRow.cells[11].querySelector(".unitizer-wrapper")).toBeTruthy(); // runoff depth unit

        expect(row.cells[5].querySelector(".unitizer-wrapper")).toBeTruthy(); // depth
        expect(row.cells[6].querySelector(".unitizer-wrapper")).toBeTruthy(); // intensity
        expect(row.cells[8].querySelector(".unitizer-wrapper")).toBeTruthy(); // peak discharge
        expect(row.cells[10].querySelector(".unitizer-wrapper")).toBeTruthy(); // runoff volume
        expect(row.cells[11].querySelector(".unitizer-wrapper")).toBeTruthy(); // runoff depth
        expect(row.cells[5].textContent).toBe("20");
        expect(row.cells[6].textContent).toBe("40");
        expect(row.cells[8].textContent).toBe("1.2");
        expect(renderValue.mock.calls.length).toBeGreaterThan(0);
        renderValue.mock.calls.forEach((call) => {
            expect(call[2]).toMatchObject({ includeUnits: false });
        });
        const axisLabels = Array.from(
            document.querySelectorAll("[data-geneva-summary-chart] .geneva-summary__axis-label")
        ).map((node) => node.textContent);
        expect(axisLabels).toContain("Intensity (mm/hr)");
        expect(axisLabels).toContain("Peak Discharge (m^3/s)");
        expect(renderUnits).toHaveBeenCalledWith("mm", { parentheses: false });
        expect(renderUnits).toHaveBeenCalledWith("mm/hour", { parentheses: false });
        expect(renderUnits).toHaveBeenCalledWith("m^3/s", { parentheses: false });
        expect(renderUnits).toHaveBeenCalledWith("m^3", { parentheses: false });
    });

    test("redraws chart with converted axis units when unitizer preferences change", async () => {
        const preferences = {
            flow: "m^3/s",
            "xs-distance-rate": "mm/hour",
            "xs-distance": "mm",
            volume: "m^3"
        };
        const categories = {
            flow: {
                units: [
                    { key: "m^3/s", label: "m^3/s" },
                    { key: "ft^3/s", label: "ft^3/s" }
                ]
            },
            "xs-distance-rate": {
                units: [
                    { key: "mm/hour", label: "mm/hour" },
                    { key: "in/hour", label: "in/hour" }
                ]
            },
            "xs-distance": {
                units: [
                    { key: "mm", label: "mm" },
                    { key: "in", label: "in" }
                ]
            },
            volume: {
                units: [
                    { key: "m^3", label: "m^3" },
                    { key: "ft^3", label: "ft^3" }
                ]
            }
        };
        const convert = jest.fn((value, fromUnit, toUnit) => {
            if (fromUnit === "mm/hour" && toUnit === "in/hour") {
                return Number(value) / 25.4;
            }
            if (fromUnit === "m^3/s" && toUnit === "ft^3/s") {
                return Number(value) * 35.3147;
            }
            return Number(value);
        });
        global.UnitizerClient = {
            getClientSync: jest.fn(() => ({
                convert,
                getPreferencePayload: jest.fn(() => ({ ...preferences })),
                getCategory: jest.fn((categoryKey) => categories[categoryKey] || null),
                renderValue: jest.fn((value) => `<div class="unitizer-wrapper"><div class="unitizer">${value}</div></div>`),
                renderUnits: jest.fn((unit) => `<div class="unitizer-wrapper"><div class="unitizer">${unit}</div></div>`)
            })),
            ready: jest.fn(() => Promise.resolve())
        };

        await import("../geneva_summary_report.js");
        window.GenevaSummaryReport.getInstance().init();
        await Promise.resolve();

        let axisLabels = Array.from(
            document.querySelectorAll("[data-geneva-summary-chart] .geneva-summary__axis-label")
        ).map((node) => node.textContent);
        expect(axisLabels).toContain("Intensity (mm/hr)");
        expect(axisLabels).toContain("Peak Discharge (m^3/s)");

        preferences.flow = "ft^3/s";
        preferences["xs-distance-rate"] = "in/hour";
        document.dispatchEvent(new CustomEvent("unitizer:preferences-changed", { detail: { preferences } }));

        axisLabels = Array.from(
            document.querySelectorAll("[data-geneva-summary-chart] .geneva-summary__axis-label")
        ).map((node) => node.textContent);
        expect(axisLabels).toContain("Intensity (in/hr)");
        expect(axisLabels).toContain("Peak Discharge (ft^3/s)");
        expect(convert).toHaveBeenCalledWith(40, "mm/hour", "in/hour");
        expect(convert).toHaveBeenCalledWith(1.2, "m^3/s", "ft^3/s");
    });

    test("loads HRU map geometry + rows and renders deck layer with winter legend", async () => {
        const root = document.querySelector("[data-geneva-summary-root]");
        root.setAttribute("data-map-features-url", "/runs/demo/cfg/query/geneva/hru_map_features");
        root.setAttribute("data-map-rows-url", "/runs/demo/cfg/query/geneva/hru_map_rows");

        document.body.insertAdjacentHTML(
            "beforeend",
            `
            <select id="geneva-summary-map-measure" data-geneva-summary-map-field="measure">
              <option value="runoff_depth" selected>Runoff Depth</option>
              <option value="runoff_volume">Runoff Volume</option>
              <option value="hru_peak_runoff">HRU peak runoff</option>
            </select>
            <button type="button" data-geneva-summary-map-refresh>Refresh</button>
            <div id="geneva-summary-map-canvas"></div>
            <p data-geneva-summary-map-status></p>
            <div data-geneva-summary-map-legend hidden>
              <p data-geneva-summary-map-legend-title></p>
              <span data-geneva-summary-map-legend-min></span>
              <span data-geneva-summary-map-legend-max></span>
            </div>
            <div data-geneva-summary-map-empty hidden><p data-geneva-summary-map-empty-body></p></div>
            <div data-geneva-summary-map-error hidden><p data-geneva-summary-map-error-body></p></div>
            `
        );

        const mapSetProps = jest.fn();
        class Deck {
            constructor() {
                this.setProps = mapSetProps;
            }
        }
        function TileLayer(props) {
            this.props = props;
        }
        function BitmapLayer(props, overrides) {
            this.props = Object.assign({}, props, overrides || {});
        }
        function GeoJsonLayer(props) {
            this.props = props;
        }
        class WebMercatorViewport {
            fitBounds() {
                return Object.freeze({
                    longitude: -116.45,
                    latitude: 45.25,
                    zoom: 11,
                    pitch: 0,
                    bearing: 0
                });
            }
        }
        function MapView(props) {
            this.props = props;
        }
        global.deck = {
            Deck,
            TileLayer,
            BitmapLayer,
            GeoJsonLayer,
            WebMercatorViewport,
            MapView
        };
        window.deck = global.deck;

        global.fetch = jest.fn((url, options) => {
            if (url.indexOf("hru_map_features") >= 0) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        schema_version: 1,
                        availability: { status: "available", reason_code: null },
                        feature_collection: {
                            type: "FeatureCollection",
                            bbox: [-116.5, 45.2, -116.4, 45.3],
                            features: [
                                {
                                    type: "Feature",
                                    properties: { hru_value: 7, hru_id: "hru_7" },
                                    geometry: {
                                        type: "Polygon",
                                        coordinates: [[[-116.5, 45.2], [-116.4, 45.2], [-116.4, 45.3], [-116.5, 45.3], [-116.5, 45.2]]]
                                    }
                                }
                            ]
                        }
                    })
                });
            }
            if (url.indexOf("hru_map_rows") >= 0) {
                const requestBody = JSON.parse((options && options.body) || "{}");
                const stormId = requestBody.storm_id || "cligen_30m_10y";
                const measureId = requestBody.measure_id || "runoff_depth";
                const rowValue = stormId === "noaa14_60m_10y" ? 5.0 : 4.0;
                const unit = measureId === "hru_peak_runoff" ? "m3_s" : "mm";
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve({
                        schema_version: 1,
                        availability: { status: "available", reason_code: null },
                        records: [
                            {
                                storm_id: stormId,
                                hru_id: "hru_7",
                                hru_value: 7,
                                measure_id: measureId,
                                value: rowValue,
                                unit
                            }
                        ]
                    })
                });
            }
            return Promise.reject(new Error("unexpected fetch URL: " + url));
        });

        await import("../geneva_summary_report.js");
        window.GenevaSummaryReport.getInstance().init();
        await new Promise((resolve) => setTimeout(resolve, 0));
        await new Promise((resolve) => setTimeout(resolve, 0));

        const mapCanvas = document.getElementById("geneva-summary-map-canvas");
        expect(mapCanvas).toBeTruthy();
        const wheelBubbleHandler = jest.fn();
        document.body.addEventListener("wheel", wheelBubbleHandler);

        const wheelWithoutCtrl = new Event("wheel", { bubbles: true, cancelable: true });
        Object.defineProperty(wheelWithoutCtrl, "ctrlKey", { value: false });
        mapCanvas.dispatchEvent(wheelWithoutCtrl);
        expect(wheelBubbleHandler).not.toHaveBeenCalled();

        const wheelWithCtrl = new Event("wheel", { bubbles: true, cancelable: true });
        Object.defineProperty(wheelWithCtrl, "ctrlKey", { value: true });
        mapCanvas.dispatchEvent(wheelWithCtrl);
        expect(wheelBubbleHandler).toHaveBeenCalledTimes(1);
        document.body.removeEventListener("wheel", wheelBubbleHandler);

        expect(global.fetch).toHaveBeenCalled();
        expect(mapSetProps.mock.calls.length).toBeGreaterThan(0);

        const layerCall = mapSetProps.mock.calls.find((call) => {
            if (!call[0] || !Array.isArray(call[0].layers)) {
                return false;
            }
            return call[0].layers.some((layerInstance) =>
                layerInstance
                && layerInstance.props
                && layerInstance.props.id === "geneva-summary-hru-choropleth"
            );
        });
        expect(layerCall).toBeTruthy();
        expect(layerCall[0].layers).toHaveLength(2);
        expect(layerCall[0].layers[0].props.id).toBe("geneva-summary-base-google-terrain");
        expect(layerCall[0].layers[1].props.id).toBe("geneva-summary-hru-choropleth");

        const initialRowsRequest = global.fetch.mock.calls.find((call) => call[0].indexOf("hru_map_rows") >= 0);
        expect(initialRowsRequest).toBeTruthy();
        expect(JSON.parse(initialRowsRequest[1].body).storm_id).toBe("cligen_30m_10y");
        expect(JSON.parse(initialRowsRequest[1].body).measure_id).toBe("runoff_depth");

        const marker = document.querySelector('[data-geneva-summary-chart] [data-storm-id="noaa14_60m_10y"]');
        expect(marker).toBeTruthy();
        marker.dispatchEvent(new MouseEvent("click", { bubbles: true }));
        await new Promise((resolve) => setTimeout(resolve, 0));
        await new Promise((resolve) => setTimeout(resolve, 0));

        const rowsRequests = global.fetch.mock.calls
            .filter((call) => call[0].indexOf("hru_map_rows") >= 0);
        const latestRowsRequest = rowsRequests[rowsRequests.length - 1];
        expect(JSON.parse(latestRowsRequest[1].body).storm_id).toBe("noaa14_60m_10y");

        const mapMeasureSelect = document.getElementById("geneva-summary-map-measure");
        mapMeasureSelect.value = "hru_peak_runoff";
        mapMeasureSelect.dispatchEvent(new Event("change", { bubbles: true }));
        await new Promise((resolve) => setTimeout(resolve, 0));
        await new Promise((resolve) => setTimeout(resolve, 0));

        const rowsRequestsAfterMeasureChange = global.fetch.mock.calls
            .filter((call) => call[0].indexOf("hru_map_rows") >= 0);
        const latestAfterMeasureChange = rowsRequestsAfterMeasureChange[rowsRequestsAfterMeasureChange.length - 1];
        expect(JSON.parse(latestAfterMeasureChange[1].body).measure_id).toBe("hru_peak_runoff");

        const boundsFitCall = mapSetProps.mock.calls.find((call) => call[0] && call[0].initialViewState);
        expect(boundsFitCall).toBeTruthy();
        expect(boundsFitCall[0]).not.toHaveProperty("viewState");

        const legend = document.querySelector("[data-geneva-summary-map-legend]");
        expect(legend.hidden).toBe(false);
        expect(document.querySelector("[data-geneva-summary-map-legend-title]").textContent).toContain("HRU peak runoff");
        expect(document.querySelector("[data-geneva-summary-map-status]").textContent).toContain("noaa14_60m_10y");
        expect(document.querySelector("[data-geneva-summary-map-error]").hidden).toBe(true);
    });
});
