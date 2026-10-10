import { describe, expect, it, jest } from "@jest/globals";
import {
  renderFlowDuration,
  hoverFlowDuration,
  clearFlowDuration,
} from "../graphs/flow-duration-renderer.js";
import { setValue } from "../state.js";

describe("flow-duration renderer edge states", () => {
  it("renders one zero point, safe labels, hidden curves and accessible inspection", () => {
    setValue("flowDurationHidden", []);
    const ctx = Object.fromEntries(
      [
        "clearRect",
        "beginPath",
        "moveTo",
        "lineTo",
        "stroke",
        "fillText",
        "save",
        "translate",
        "rotate",
        "restore",
        "arc",
        "fill",
      ].map((name) => [name, jest.fn()]),
    );
    const label = "<img src=x onerror=alert(1)>";
    const graph = {
      ctx2d: ctx,
      canvas: {
        width: 600,
        height: 320,
        getBoundingClientRect: () => ({ left: 0, top: 0, width: 600 }),
      },
      container: document.createElement("div"),
      tooltipEl: document.createElement("div"),
      _getTheme: () => ({ text: "#000" }),
      _data: {
        settings: { source: "outlet", scale: "log" },
        series: [
          {
            id: "base",
            label,
            color: [1, 2, 3],
            points: [{ flow: 0, probability: 50, date: "2000-01-01" }],
            count: 1,
            missing: 0,
            zeroDays: 1,
            start: "2000-01-01",
            end: "2000-01-01",
          },
        ],
      },
    };
    graph.render = () => renderFlowDuration(graph);
    graph.render();
    expect(ctx.arc).toHaveBeenCalledTimes(1);
    expect(graph.container.querySelector("img")).toBeNull();
    expect(graph.container.textContent).toContain(label);
    expect(graph.container.querySelector("[aria-live]").textContent).toContain(
      "0.0000 m³/s",
    );
    hoverFlowDuration(graph, { clientX: 200, clientY: 100 });
    expect(graph.tooltipEl.textContent).toContain("50.000% exceedance");
    expect(graph.tooltipEl.querySelector("img")).toBeNull();
    const checkbox = graph.container.querySelector('input[type="checkbox"]');
    checkbox.checked = false;
    checkbox.dispatchEvent(new Event("change"));
    expect(graph.container.querySelector("[aria-live]").textContent).toBe(
      "No visible daily values",
    );
    clearFlowDuration(graph);
    expect(graph.container.children).toHaveLength(0);
    setValue("flowDurationHidden", []);
  });
});
