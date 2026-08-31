/**
 * @jest-environment jsdom
 */

function setWidths(wrapper, clientWidth, scrollWidth) {
  Object.defineProperty(wrapper, "clientWidth", {
    configurable: true,
    get: () => clientWidth.value,
  });
  Object.defineProperty(wrapper, "scrollWidth", {
    configurable: true,
    get: () => scrollWidth.value,
  });
}

describe("table overflow accessibility", () => {
  let resizeCallback;
  let mutationCallback;
  let originalRequestAnimationFrame;

  beforeEach(() => {
    jest.resetModules();
    document.body.innerHTML = "";
    delete window.__weppTableOverflowAccessibilityLoaded;
    delete window.WCTableOverflowAccessibility;

    resizeCallback = null;
    mutationCallback = null;
    originalRequestAnimationFrame = window.requestAnimationFrame;
    window.requestAnimationFrame = (callback) => callback();
    window.ResizeObserver = class ResizeObserver {
      constructor(callback) {
        resizeCallback = callback;
      }

      observe() {}
    };
    window.MutationObserver = class MutationObserver {
      constructor(callback) {
        mutationCallback = callback;
      }

      observe() {}
    };
  });

  afterEach(() => {
    delete window.ResizeObserver;
    delete window.MutationObserver;
    delete window.__weppTableOverflowAccessibilityLoaded;
    delete window.WCTableOverflowAccessibility;
    if (originalRequestAnimationFrame) {
      window.requestAnimationFrame = originalRequestAnimationFrame;
    } else {
      delete window.requestAnimationFrame;
    }
  });

  async function loadModule() {
    await import("../../static/js/table_overflow_accessibility.js");
    return window.WCTableOverflowAccessibility;
  }

  function appendWrapper(markup = "<table><caption>Loss summary</caption></table>") {
    const wrapper = document.createElement("div");
    wrapper.className = "wc-table-wrapper";
    wrapper.innerHTML = markup;
    document.body.appendChild(wrapper);
    return wrapper;
  }

  test("leaves fitting, hidden, and malformed wrappers without generated UI", async () => {
    const fitting = appendWrapper();
    setWidths(fitting, { value: 400 }, { value: 401 });
    const hidden = appendWrapper();
    setWidths(hidden, { value: 0 }, { value: 900 });
    const malformed = appendWrapper("<div>wide content</div>");
    setWidths(malformed, { value: 200 }, { value: 900 });

    await loadModule();

    [fitting, hidden, malformed].forEach((wrapper) => {
      expect(wrapper.hasAttribute("tabindex")).toBe(false);
      expect(wrapper.hasAttribute("role")).toBe(false);
      expect(wrapper.previousElementSibling?.classList.contains("wc-table-overflow-hint")).not.toBe(true);
    });
  });

  test("enhances an overflowing table once with caption-derived semantics", async () => {
    const wrapper = appendWrapper();
    setWidths(wrapper, { value: 300 }, { value: 600 });

    const api = await loadModule();
    api.sync(wrapper);

    const hint = wrapper.previousElementSibling;
    expect(hint.className).toBe("wc-table-overflow-hint");
    expect(hint.textContent).toContain("Shift + mouse wheel");
    expect(hint.textContent).toContain("Left and Right Arrow keys");
    expect(wrapper.getAttribute("tabindex")).toBe("0");
    expect(wrapper.getAttribute("role")).toBe("region");
    expect(wrapper.getAttribute("aria-label")).toBe("Loss summary");
    expect(wrapper.getAttribute("aria-describedby")).toBe(hint.id);
    expect(wrapper.getAttribute("data-wc-horizontal-overflow")).toBe("true");
    expect(document.querySelectorAll(".wc-table-overflow-hint")).toHaveLength(1);
  });

  test("uses the first non-empty heading in the nearest section", async () => {
    document.body.innerHTML = `
      <section>
        <h2>   </h2>
        <h3>Channel summary</h3>
        <div class="wc-table-wrapper"><table></table></div>
      </section>
    `;
    const wrapper = document.querySelector(".wc-table-wrapper");
    setWidths(wrapper, { value: 300 }, { value: 600 });

    await loadModule();

    expect(wrapper.getAttribute("role")).toBe("region");
    expect(wrapper.getAttribute("aria-label")).toBe("Channel summary");
  });

  test("removes only generated state when overflow ends", async () => {
    const wrapper = appendWrapper();
    wrapper.setAttribute("aria-describedby", "authored-description");
    const clientWidth = { value: 300 };
    const scrollWidth = { value: 600 };
    setWidths(wrapper, clientWidth, scrollWidth);

    await loadModule();
    const generatedHintId = wrapper.getAttribute("aria-describedby").split(" ")[1];
    wrapper.setAttribute("role", "group");
    wrapper.setAttribute("tabindex", "-1");
    scrollWidth.value = 300;
    resizeCallback([{ target: wrapper }]);

    expect(document.getElementById(generatedHintId)).toBeNull();
    expect(wrapper.getAttribute("aria-describedby")).toBe("authored-description");
    expect(wrapper.getAttribute("role")).toBe("group");
    expect(wrapper.getAttribute("tabindex")).toBe("-1");
    expect(wrapper.hasAttribute("aria-label")).toBe(false);
    expect(wrapper.hasAttribute("data-wc-horizontal-overflow")).toBe(false);
  });

  test("adds generated state when resize introduces overflow after a hidden state", async () => {
    const wrapper = appendWrapper();
    const clientWidth = { value: 0 };
    const scrollWidth = { value: 600 };
    setWidths(wrapper, clientWidth, scrollWidth);

    await loadModule();
    expect(wrapper.hasAttribute("data-wc-horizontal-overflow")).toBe(false);

    clientWidth.value = 300;
    resizeCallback([{ target: wrapper }]);

    expect(wrapper.getAttribute("data-wc-horizontal-overflow")).toBe("true");
    expect(wrapper.getAttribute("tabindex")).toBe("0");
    expect(wrapper.previousElementSibling.className).toBe("wc-table-overflow-hint");
  });

  test.each([
    {
      label: "usable labelledby takes precedence over a usable label",
      ariaLabel: "Label fallback",
      labelledby: "usable-heading",
      heading: "Usable heading",
      expectedRole: "region",
    },
    {
      label: "usable labelledby applies when the authored label is empty",
      ariaLabel: "  ",
      labelledby: "usable-heading",
      heading: "Usable heading",
      expectedRole: "region",
    },
    {
      label: "usable label applies when labelledby is broken",
      ariaLabel: "Label fallback",
      labelledby: "missing-heading",
      heading: null,
      expectedRole: "region",
    },
    {
      label: "no region is generated when both authored names are unusable",
      ariaLabel: "  ",
      labelledby: "missing-heading",
      heading: null,
      expectedRole: null,
    },
  ])("preserves authored accessible names: $label", async (fixture) => {
    if (fixture.heading) {
      const heading = document.createElement("h2");
      heading.id = "usable-heading";
      heading.textContent = fixture.heading;
      document.body.appendChild(heading);
    }
    const wrapper = appendWrapper();
    wrapper.setAttribute("aria-label", fixture.ariaLabel);
    wrapper.setAttribute("aria-labelledby", fixture.labelledby);
    setWidths(wrapper, { value: 300 }, { value: 600 });

    await loadModule();

    expect(wrapper.getAttribute("aria-label")).toBe(fixture.ariaLabel);
    expect(wrapper.getAttribute("aria-labelledby")).toBe(fixture.labelledby);
    expect(wrapper.getAttribute("role")).toBe(fixture.expectedRole);
    expect(wrapper.getAttribute("tabindex")).toBe("0");
  });

  test("registers dynamically inserted wrappers through the mutation observer", async () => {
    await loadModule();
    const wrapper = appendWrapper();
    setWidths(wrapper, { value: 300 }, { value: 600 });

    mutationCallback([{ addedNodes: [wrapper] }]);
    await new Promise((resolve) => window.setTimeout(resolve, 0));

    expect(wrapper.getAttribute("data-wc-horizontal-overflow")).toBe("true");
    expect(wrapper.previousElementSibling.className).toBe("wc-table-overflow-hint");
  });

  test("initial sync and explicit refresh work without observer APIs", async () => {
    delete window.ResizeObserver;
    delete window.MutationObserver;
    const wrapper = appendWrapper();
    const clientWidth = { value: 300 };
    const scrollWidth = { value: 600 };
    setWidths(wrapper, clientWidth, scrollWidth);

    const api = await loadModule();
    expect(wrapper.getAttribute("data-wc-horizontal-overflow")).toBe("true");

    scrollWidth.value = 300;
    api.refresh(document);
    expect(wrapper.hasAttribute("data-wc-horizontal-overflow")).toBe(false);
  });
});
