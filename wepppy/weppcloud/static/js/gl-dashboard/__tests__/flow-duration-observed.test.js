import { expect, it, jest } from "@jest/globals";
import { createFlowDurationLoader } from "../graphs/flow-duration-data.js";
import { renderFlowDurationControls } from "../graphs/flow-duration-controls.js";

const records = [4, 2, 2, 0].map((flow, i) => ({
  year: "2000", month: "1", day: String(i + 1), julian: i + 1,
  flow: String(flow), area: "86400000",
}));
const observed = { present: true, available: true, records };
function loader(observations = observed) {
  return createFlowDurationLoader({
    scenarios: [{ path: "" }, { path: "child" }],
    metadata: { observed: observations, scenarios: {} },
    query: jest.fn(), displayName: (s) => s.path || "Base", color: () => [1, 2, 3],
  });
}

it("adds exactly one full-record observed curve to either source, preserving ties and zeros", async () => {
  const load = loader();
  expect((await load()).series).toHaveLength(2);
  for (const source of ["hillslope", "outlet"]) {
    const data = await load({ source, includeObserved: true, excludedYears: 5 });
    expect(data.series).toHaveLength(3);
    const measured = data.series[2];
    expect(measured.id).toBe("observed");
    expect(measured.label).toBe("Observed");
    expect(measured.points.map((p) => [p.flow, p.probability])).toEqual([
      [4, 20], [2, 40], [2, 60], [0, 80],
    ]);
    expect(measured.count).toBe(4);
    expect(measured.start).toBe("2000-01-01");
    expect(measured.zeroDays).toBe(1);
  }
  expect((await load({ includeObserved: false })).series).toHaveLength(2);
});

it("isolates invalid observed data and explains empty valid populations", async () => {
  for (const flow of ["-1", "Infinity", "oops"]) {
    const load = loader({ ...observed, records: [{ ...records[0], flow }] });
    const data = await load({ includeObserved: true });
    expect(data.series[2].error).toContain("Invalid");
    expect(data.series[2].points).toEqual([]);
    expect(data.series).toHaveLength(3);
  }
  const load = loader({ ...observed, records: [{ ...records[0], flow: null }] });
  expect((await load({ includeObserved: true })).series[2].error).toContain("No valid observed");
});

it("shows unavailable observations without trusting stale checkbox state", async () => {
  const load = loader({ present: true, available: false, reason: "Missing area" });
  expect((await load({ includeObserved: true })).series[2].error).toBe("Missing area");
  expect((await loader({ present: false, available: false })({ includeObserved: true })).series).toHaveLength(2);
});

it("wires checkbox and source controls through preserved dashboard state", () => {
  const parent = document.createElement("div");
  const state = { activeGraphKey: "flow-duration", flowDuration: { excludedYears: 0 } };
  const activate = jest.fn();
  const deps = { observed, getState: () => state, setValue: (k, v) => { state[k] = v; }, activate };
  renderFlowDurationControls(parent, deps);
  const checkbox = parent.querySelector("#fdc-include-observed");
  expect(checkbox.checked).toBe(false);
  checkbox.checked = true;
  checkbox.dispatchEvent(new Event("change"));
  expect(state.flowDuration.includeObserved).toBe(true);
  const radio = parent.querySelector('input[value="outlet"]');
  radio.checked = true;
  radio.dispatchEvent(new Event("change"));
  expect(state.flowDuration).toMatchObject({ source: "outlet", includeObserved: true, excludedYears: 0 });
  expect(activate).toHaveBeenCalledTimes(2);
  parent.replaceChildren();
  renderFlowDurationControls(parent, deps);
  expect(parent.querySelector("#fdc-include-observed").checked).toBe(true);
  expect(parent.textContent).toContain("full observed record");
});

it("hides absent optional state and renders unavailable explanations as text", () => {
  const parent = document.createElement("div");
  const deps = { getState: () => ({}), setValue: jest.fn(), activate: jest.fn() };
  renderFlowDurationControls(parent, deps);
  expect(parent.querySelector("#fdc-include-observed")).toBeNull();
  parent.replaceChildren();
  renderFlowDurationControls(parent, { ...deps, observed: { present: true, available: false, reason: "<img src=x>" } });
  expect(parent.querySelector("img")).toBeNull();
  expect(parent.textContent).toContain("Observed streamflow unavailable: <img src=x>");
});

it("keeps a valid simulated curve when observed dates are invalid or duplicated", async () => {
  for (const invalid of [
    [{ ...records[0], month: 2, day: 30 }],
    [records[0], records[0]],
    [{ ...records[0], flow: "-1" }],
  ]) {
    const load = createFlowDurationLoader({
      scenarios: [{ path: "" }],
      metadata: { observed: { ...observed, records: invalid }, scenarios: { "": { outlet: { available: true, channelId: 1, elementId: 1 } } } },
      query: async () => ({ records: [{ ...records[0], flow: "86400" }], row_count: 1 }),
      displayName: () => "Base", color: () => [1, 2, 3],
    });
    const data = await load({ source: "outlet", excludedYears: 0, includeObserved: true });
    expect(data.series[0].points).toEqual([{ flow: 1, probability: 50, date: "2000-01-01" }]);
    expect(data.series[1].error).toBeTruthy();
    expect(data.series[1].points).toEqual([]);
  }
});
