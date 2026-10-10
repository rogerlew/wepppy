import { describe, expect, it, jest } from "@jest/globals";
import { createGraphController } from "../graphs/controller.js";

function deferred() {
  let resolve;
  const promise = new Promise((done) => {
    resolve = done;
  });
  return { promise, resolve };
}
function harness(loads) {
  const state = {};
  const graph = { hide: jest.fn(), setData: jest.fn() };
  const controller = createGraphController({
    graphDefs: [],
    graphScenarios: [],
    graphLoadersFactory: () => ({
      loadGraphDataset: jest.fn(() => loads.shift().promise),
    }),
    getState: () => state,
    setValue: (key, value) => {
      state[key] = value;
    },
    timeseriesGraph: graph,
    graphModeController: {
      clearGraphModeOverride: jest.fn(),
      setGraphFocus: jest.fn(),
      setGraphMode: jest.fn(),
      syncGraphLayout: jest.fn(),
      ensureGraphExpanded: jest.fn(),
    },
  });
  return { graph, controller };
}

describe("flow-duration graph activation races", () => {
  it("does not let an older null response hide the new curve", async () => {
    const old = deferred(),
      next = deferred();
    const { controller, graph } = harness([old, next]);
    const first = controller.activateGraphItem("old");
    const second = controller.activateGraphItem("flow-duration");
    const data = { source: "flow-duration" };
    next.resolve(data);
    await second;
    const hides = graph.hide.mock.calls.length;
    old.resolve(null);
    await first;
    expect(graph.setData).toHaveBeenLastCalledWith(data);
    expect(graph.hide).toHaveBeenCalledTimes(hides);
  });
  it("keeps the latest forced same-key source selection", async () => {
    const old = deferred(),
      next = deferred();
    const { controller, graph } = harness([old, next]);
    const first = controller.activateGraphItem("flow-duration");
    const second = controller.activateGraphItem("flow-duration", {
      force: true,
    });
    const current = { source: "flow-duration", title: "Outlet" };
    next.resolve(current);
    await second;
    old.resolve({ source: "flow-duration", title: "Hillslope" });
    await first;
    expect(graph.setData).toHaveBeenCalledTimes(1);
    expect(graph.setData).toHaveBeenCalledWith(current);
  });
});
