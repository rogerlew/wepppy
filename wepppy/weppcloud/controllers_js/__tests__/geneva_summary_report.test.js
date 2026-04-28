/**
 * @jest-environment jsdom
 */

describe("Geneva summary report interactions", () => {
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
            <table><tbody data-geneva-summary-event-body></tbody></table>
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
});
