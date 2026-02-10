/**
 * @jest-environment jsdom
 */

describe("url_for_run helper", () => {
  beforeEach(async () => {
    jest.resetModules();
    window.site_prefix = "";
    window.history.pushState({}, "", "/runs/decimal-pleasing/cfg/");

    await import("../utils.js");
  });

  afterEach(() => {
    delete window.pup_relpath;
    delete window.site_prefix;
    delete window.url_for_run;
    if (typeof globalThis !== "undefined") {
      delete globalThis.url_for_run;
    }
  });

  test("rewrites omni scenario pup_relpath into composite runid", () => {
    window.pup_relpath = "omni/scenarios/treated";

    const url = window.url_for_run("elevationquery/");

    expect(url).toContain("/runs/decimal-pleasing%3B%3Bomni%3B%3Btreated/cfg/elevationquery/");
    expect(url).not.toContain("pup=");
  });

  test("rewrites omni contrast pup_relpath into composite runid", () => {
    window.pup_relpath = "omni/contrasts/3";

    const url = window.url_for_run("elevationquery/");

    expect(url).toContain("/runs/decimal-pleasing%3B%3Bomni-contrast%3B%3B3/cfg/elevationquery/");
    expect(url).not.toContain("pup=");
  });

  test("does not rewrite non-omni pup_relpath", () => {
    window.pup_relpath = "some/pup";

    const url = window.url_for_run("elevationquery/");

    expect(url).toContain("/runs/decimal-pleasing/cfg/elevationquery/");
    expect(url.toLowerCase()).not.toContain("%3b%3b");
  });
});

