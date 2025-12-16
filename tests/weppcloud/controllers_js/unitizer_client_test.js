"use strict";

const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

class MockElement {
  constructor(id, attrs = {}) {
    this.id = id;
    this.attributes = { ...attrs };
    this.dataset = {};
    this.value = attrs.value ? String(attrs.value) : "";
    this.listeners = {};
    this.parent = null;
  }

  getAttribute(name) {
    const value = this.attributes[name];
    return value !== undefined ? String(value) : null;
  }

  setAttribute(name, value) {
    this.attributes[name] = value;
  }

  addEventListener(type, handler) {
    if (!this.listeners[type]) {
      this.listeners[type] = [];
    }
    this.listeners[type].push(handler);
  }

  dispatchEvent(event) {
    (this.listeners[event.type] || []).forEach((handler) => handler(event));
    return true;
  }
}

class MockDocument {
  constructor() {
    this.elements = [];
    this.listeners = {};
  }

  registerElement(element) {
    this.elements.push(element);
    element.parent = this;
  }

  querySelectorAll(selector) {
    if (selector === "[data-unitizer-category][data-unitizer-unit]") {
      return this.elements.filter(
        (el) =>
          el.getAttribute("data-unitizer-category") &&
          el.getAttribute("data-unitizer-unit")
      );
    }
    return [];
  }

  querySelector() {
    return null;
  }

  addEventListener(type, handler) {
    if (!this.listeners[type]) {
      this.listeners[type] = [];
    }
    this.listeners[type].push(handler);
  }

  dispatchEvent(event) {
    (this.listeners[event.type] || []).forEach((handler) => handler(event));
    return true;
  }

  contains(element) {
    return this.elements.includes(element);
  }
}

function buildUnitizerMap() {
  return {
    categories: [
      {
        key: "chem",
        label: "Chemistry",
        defaultIndex: 0,
        units: [
          { key: "ppm", token: "ppm", label: "ppm", htmlLabel: "ppm", precision: 3 },
          {
            key: "kg_ha",
            token: "kg/ha",
            label: "kg/ha",
            htmlLabel: "kg/ha",
            precision: 3,
          },
        ],
        conversions: [
          { from: "ppm", to: "kg_ha", scale: 2, offset: 0 },
          { from: "kg_ha", to: "ppm", scale: 0.5, offset: 0 },
        ],
      },
    ],
  };
}

async function runTests() {
  global.window = global;
  global.Element = MockElement;
  global.document = new MockDocument();
  global.CustomEvent = function CustomEvent(type, options) {
    this.type = type;
    this.detail = options && options.detail;
  };
  global.__unitizerMap = buildUnitizerMap();
  delete global.__unitizerMapModule;
  const document = global.document;

  const modulePath = path.resolve(
    __dirname,
    "..",
    "..",
    "..",
    "wepppy",
    "weppcloud",
    "controllers_js",
    "unitizer_client.js"
  );
  const code = fs.readFileSync(modulePath, "utf8");
  vm.runInThisContext(code, { filename: modulePath });

  const UnitizerClient = global.UnitizerClient;
  assert(UnitizerClient, "UnitizerClient should be defined");

  const client = await UnitizerClient.ready();

  const blankInput = new MockElement("blank", {
    "data-unitizer-category": "chem",
    "data-unitizer-unit": "ppm",
  });
  const populatedInput = new MockElement("populated", {
    "data-unitizer-category": "chem",
    "data-unitizer-unit": "ppm",
    value: "10",
  });

  document.registerElement(blankInput);
  document.registerElement(populatedInput);

  client.registerNumericInputs(document);

  assert.strictEqual(blankInput.dataset.unitizerCanonicalValue, "");
  assert.strictEqual(populatedInput.dataset.unitizerCanonicalValue, "10");
  assert.strictEqual(populatedInput.dataset.unitizerActiveUnit, "ppm");

  client.setPreference("chem", "kg_ha");
  client.updateNumericFields();

  assert.strictEqual(
    blankInput.value,
    "",
    "Blank inputs should remain untouched when preferences change"
  );
  assert.strictEqual(
    blankInput.dataset.unitizerCanonicalValue,
    "",
    "Blank canonical values should stay empty"
  );
  assert.strictEqual(
    blankInput.dataset.unitizerActiveUnit,
    "ppm",
    "Empty fields should keep the canonical unit"
  );

  assert.strictEqual(populatedInput.dataset.unitizerActiveUnit, "kg_ha");
  assert.strictEqual(populatedInput.value, "20");
  assert.strictEqual(populatedInput.dataset.unitizerCanonicalValue, "10");

  console.log("unitizer_client tests passed");
}

runTests().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
