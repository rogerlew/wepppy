import { describe, expect, it, jest } from "@jest/globals";
import {
  rankDailyFlows,
  createFlowDurationLoader,
} from "../graphs/flow-duration-data.js";
import {
  closestFlowPoint,
  probabilityAtFraction,
} from "../graphs/flow-duration-renderer.js";

const row = (day, flow, year = 2000) => ({
  year,
  month: 1,
  day,
  julian: day,
  flow: flow === null ? null : String(flow * 86400),
});

describe("daily flow duration", () => {
  it("preserves daily ties and zero in the Weibull population", () => {
    const result = rankDailyFlows(
      [row(1, 4), row(2, 2), row(3, 2), row(4, 0)],
      "outlet",
      0,
    );
    expect(result.points.map((p) => [p.flow, p.probability])).toEqual([
      [4, 20],
      [2, 40],
      [2, 60],
      [0, 80],
    ]);
    expect(result.zeroDays).toBe(1);
    expect(result.missing).toBe(0);
  });
  it("uses year groups, keeps synthetic years, and preserves explicit all years", () => {
    const rows = [row(1, 3, 1), row(1, 2, 2), row(1, 1, 3)];
    expect(rankDailyFlows(rows, "outlet").points).toEqual([
      { flow: 1, probability: 50, date: "0003-01-01" },
    ]);
    expect(rankDailyFlows(rows, "outlet", 0).count).toBe(3);
    expect(rankDailyFlows(rows, "outlet", 5).count).toBe(0);
  });
  it("counts absent and null/NaN days without adding zero flow", () => {
    const rows = [
      row(1, 1),
      row(3, null),
      { ...row(4, 1), flow: "nan" },
      row(5, 0),
    ];
    const result = rankDailyFlows(rows, "outlet", 0);
    expect(result.count).toBe(2);
    expect(result.missing).toBe(3);
    expect(result.expected).toBe(5);
  });
  it.each(["-1", "Infinity", "-Infinity", "bad", ""])(
    "rejects invalid flow %s",
    (flow) => {
      expect(() =>
        rankDailyFlows([{ ...row(1, 1), flow }], "outlet", 0),
      ).toThrow("Invalid");
    },
  );
  it("rejects duplicate and impossible dates, but excludes invalid warm-up flow", () => {
    expect(() => rankDailyFlows([row(1, 1), row(1, 2)], "outlet", 0)).toThrow(
      "Duplicate",
    );
    expect(() =>
      rankDailyFlows([{ ...row(1, 1), month: 2, day: 30 }], "outlet", 0),
    ).toThrow("Invalid");
    expect(
      rankDailyFlows(
        [{ ...row(1, 1, 2000), flow: "-1" }, row(1, 2, 2001)],
        "outlet",
        1,
      ).count,
    ).toBe(1);
  });
  it("converts watershed depth and includes leap days", () => {
    const result = rankDailyFlows(
      [
        {
          year: 2000,
          month: 2,
          day: 28,
          julian: 59,
          flow: "1",
          area: "86400000",
        },
        {
          year: 2000,
          month: 3,
          day: 1,
          julian: 61,
          flow: "0",
          area: "86400000",
        },
      ],
      "hillslope",
      0,
    );
    expect(result.points[0].flow).toBe(1);
    expect(result.missing).toBe(1);
  });
  it("inverse log hover snaps to an actual independent ranked point", () => {
    expect(probabilityAtFraction(0.5, 1, true)).toBeCloseTo(10);
    const points = rankDailyFlows([row(1, 4), row(2, 2)], "outlet", 0).points;
    expect(closestFlowPoint(points, 65)).toBe(points[1]);
  });
  it("loads independent records, uses both outlet IDs and caches across scale/year changes", async () => {
    const query = jest.fn(async (_payload, path) => ({
      records: path ? [row(1, 0, 2005)] : [row(1, 4), row(2, 2)],
      row_count: path ? 1 : 2,
    }));
    const load = createFlowDurationLoader({
      scenarios: [
        { path: "", name: "Burned" },
        { path: "child", name: "undisturbed" },
      ],
      metadata: {
        scenarios: {
          "": { outlet: { available: true, channelId: 128, elementId: 412 } },
          child: {
            outlet: { available: true, channelId: 128, elementId: 412 },
          },
        },
      },
      query,
      displayName: (s) => s.name,
      color: () => [0, 0, 0],
    });
    const data = await load({ source: "outlet", excludedYears: 0 });
    expect(data.series.map((s) => s.count)).toEqual([2, 1]);
    expect(query.mock.calls[0][0].filters.map((f) => f.value)).toEqual([
      128, 412,
    ]);
    expect(query.mock.calls[0][0].limit).toBeUndefined();
    await load({ source: "outlet", excludedYears: 1, scale: "log" });
    expect(query).toHaveBeenCalledTimes(2);
  });
  it("does not query an unavailable child and does not cache failed requests", async () => {
    const query = jest
      .fn()
      .mockResolvedValueOnce(null)
      .mockResolvedValue({ records: [row(1, 1)], row_count: 1 });
    const load = createFlowDurationLoader({
      scenarios: [{ path: "" }, { path: "child" }],
      metadata: { scenarios: { "": { outlet: { available: true } } } },
      query,
      displayName: (s) => s.path || "base",
      color: () => [0, 0, 0],
    });
    expect(
      (await load({ source: "outlet", excludedYears: 0 })).series[0].error,
    ).toContain("query failed");
    const result = await load({ source: "outlet", excludedYears: 0 });
    expect(result.series[0].count).toBe(1);
    expect(result.series[1].error).toContain("unavailable");
    expect(query).toHaveBeenCalledTimes(2);
  });
});

it("shows the coverage horizon including absent leading days after warm-up", () => {
  const result = rankDailyFlows(
    [row(1, 1, 2000), row(4, 1, 2001)],
    "outlet",
    1,
  );
  expect(result.start).toBe("2001-01-01");
  expect(result.end).toBe("2001-01-04");
  expect(result.missing).toBe(3);
});

it("queries the active pup when the page URL still names the parent", async () => {
  const query = jest.fn(async () => ({ records: [row(1, 1)], row_count: 1 }));
  const load = createFlowDurationLoader({
    scenarios: [{ path: "" }],
    metadata: {
      queryScenarioPath: "_pups/omni/scenarios/undisturbed",
      scenarios: {
        "": { outlet: { available: true, channelId: 1, elementId: 2 } },
      },
    },
    query,
    displayName: () => "undisturbed",
    color: () => [0, 1, 0],
  });
  await load({ source: "outlet", excludedYears: 0 });
  expect(query.mock.calls[0][1]).toBe("_pups/omni/scenarios/undisturbed");
});
