// NOTE: If more controllers need bespoke helpers, move these helpers into a small
// config module so the main spec stays lean.
const prepareSetOutletLonLat = async ({ page }) => {
  const entryModeRadio = page.locator("#set_outlet_mode_entry");
  if (await entryModeRadio.count()) {
    await entryModeRadio.check({ force: true });
  }
  const entryField = page.locator("#input_set_outlet_entry");
  await entryField.fill("-116.95, 46.73");
};

const prepareOmniScenario = async ({ page }) => {
  const addButton = page.locator("#add-omni-scenario");
  await addButton.click();
  const scenarioSelect = page.locator("[data-omni-role='scenario-select']").last();
  await scenarioSelect.waitFor({ state: "visible" });
  await scenarioSelect.selectOption({ value: "uniform_low" });
};

/**
 * @typedef {Object} ControllerCase
 * @property {string} name
 * @property {string} formSelector
 * @property {string} actionSelector
 * @property {string|RegExp} requestUrlPattern
 * @property {string} stacktraceLocator
 * @property {string} [stacktracePanelLocator]
 * @property {string} [hintLocator]
 * @property {"rq_job"} [workflow]
 * @property {(args: { page: import("@playwright/test").Page, phase?: "success"|"failure" }) => Promise<void>|void} [prepareAction]
 * @property {number} [failureStatus]
 * @property {boolean} [requireHintVisible]
 * @property {boolean} [expectJobHint]
 * @property {string} [skipMessage]
 */

/** @type {ControllerCase[]} */
const controllerCases = [
  {
    name: "landuse",
    formSelector: "form#landuse_form",
    actionSelector: "#btn_build_landuse",
    requestUrlPattern: "**/rq/api/build_landuse",
    stacktraceLocator: "#landuse_stacktrace_panel [data-stacktrace-body]",
    stacktracePanelLocator: "#landuse_stacktrace_panel",
    hintLocator: "#hint_build_landuse",
    workflow: "rq_job"
  },
  {
    name: "soils",
    formSelector: "form#soil_form",
    actionSelector: "#btn_build_soil",
    requestUrlPattern: "**/rq/api/build_soils",
    stacktraceLocator: "#soil_stacktrace_panel [data-stacktrace-body]",
    stacktracePanelLocator: "#soil_stacktrace_panel",
    hintLocator: "#hint_build_soil",
    workflow: "rq_job"
  },
  {
    name: "climate",
    formSelector: "form#climate_form",
    actionSelector: "#btn_build_climate",
    requestUrlPattern: "**/rq/api/build_climate",
    stacktraceLocator: "#climate_stacktrace_panel [data-stacktrace-body]",
    stacktracePanelLocator: "#climate_stacktrace_panel",
    hintLocator: "#hint_build_climate",
    workflow: "rq_job"
  },
  {
    name: "subcatchments",
    formSelector: "form#build_subcatchments_form",
    actionSelector: "#btn_build_subcatchments",
    requestUrlPattern: "**/rq/api/build_subcatchments_and_abstract_watershed",
    stacktraceLocator: "#subcatchments_stacktrace_panel [data-stacktrace-body]",
    stacktracePanelLocator: "#subcatchments_stacktrace_panel",
    hintLocator: "#hint_build_subcatchments",
    workflow: "rq_job"
  },
  {
    name: "set_outlet",
    formSelector: "form#set_outlet_form",
    actionSelector: "#btn_set_outlet_entry",
    requestUrlPattern: "**/rq/api/set_outlet",
    stacktraceLocator: "#set_outlet_stacktrace_panel [data-stacktrace-body]",
    stacktracePanelLocator: "#set_outlet_stacktrace_panel",
    hintLocator: "#hint_set_outlet_cursor",
    workflow: "rq_job",
    prepareAction: prepareSetOutletLonLat,
    failureStatus: 200
  },
  {
    name: "set_outlet_entry",
    formSelector: "form#set_outlet_form",
    actionSelector: "#btn_set_outlet_entry",
    requestUrlPattern: "**/rq/api/set_outlet",
    stacktraceLocator: "#set_outlet_stacktrace_panel [data-stacktrace-body]",
    stacktracePanelLocator: "#set_outlet_stacktrace_panel",
    hintLocator: "#hint_set_outlet_cursor",
    workflow: "rq_job",
    prepareAction: prepareSetOutletLonLat,
    failureStatus: 200,
    requireHintVisible: true
  },
  {
    name: "rap_ts",
    formSelector: "form#rap_ts_form",
    actionSelector: "#btn_build_rap_ts",
    requestUrlPattern: "**/rq/api/acquire_rap_ts",
    stacktraceLocator: "#rap_ts_stacktrace_panel [data-stacktrace-body]",
    stacktracePanelLocator: "#rap_ts_stacktrace_panel",
    hintLocator: "#hint_build_rap_ts",
    workflow: "rq_job"
  },
  {
    name: "wepp",
    formSelector: "form#wepp_form",
    actionSelector: "#btn_run_wepp",
    requestUrlPattern: "**/rq/api/run_wepp",
    stacktraceLocator: "#wepp_stacktrace_panel [data-stacktrace-body]",
    stacktracePanelLocator: "#wepp_stacktrace_panel",
    hintLocator: "#hint_run_wepp",
    workflow: "rq_job"
  },
  {
    name: "omni",
    formSelector: "form#omni_form",
    actionSelector: "#btn_run_omni",
    requestUrlPattern: "**/rq/api/run_omni",
    stacktraceLocator: "#omni_form [data-stacktrace-body]",
    stacktracePanelLocator: "#omni_form [data-stacktrace-panel]",
    hintLocator: "#hint_run_omni",
    workflow: "rq_job",
    prepareAction: prepareOmniScenario,
    requireHintVisible: true
  },
  {
    name: "observed",
    formSelector: "form#observed_form",
    actionSelector: "#btn_run_observed",
    requestUrlPattern: /\/tasks\/run_model_fit\/?(?:\?.*)?$/,
    stacktraceLocator: "#observed_stacktrace_panel [data-stacktrace-body]",
    stacktracePanelLocator: "#observed_stacktrace_panel",
    hintLocator: "#hint_run_observed",
    expectJobHint: false
  },
  {
    name: "debris_flow",
    formSelector: "form#debris_flow_form",
    actionSelector: "#btn_run_debris_flow",
    requestUrlPattern: "**/rq/api/run_debris_flow",
    stacktraceLocator: "#debris_flow_stacktrace_panel [data-stacktrace-body]",
    stacktracePanelLocator: "#debris_flow_stacktrace_panel",
    hintLocator: "#hint_run_debris_flow",
    workflow: "rq_job",
    expectJobHint: false
  },
  {
    name: "dss_export",
    formSelector: "form#dss_export_form",
    actionSelector: "#btn_export_dss",
    requestUrlPattern: "**/rq/api/post_dss_export_rq",
    stacktraceLocator: "#dss_export_stacktrace_panel [data-stacktrace-body], form#dss_export_form #stacktrace",
    stacktracePanelLocator: "#dss_export_stacktrace_panel",
    hintLocator: "#hint_export_dss",
    workflow: "rq_job",
    requireHintVisible: true
  },
  {
    name: "ash",
    formSelector: "form#ash_form",
    actionSelector: "#btn_run_ash",
    requestUrlPattern: "**/rq/api/run_ash",
    stacktraceLocator: "#ash_form [data-stacktrace-body], #ash_form #stacktrace",
    stacktracePanelLocator: "#ash_form [data-stacktrace-panel]",
    hintLocator: "#hint_run_ash",
    workflow: "rq_job",
    expectJobHint: false
  },
  {
    name: "treatments",
    formSelector: "form#treatments_form",
    actionSelector: "#btn_build_treatments",
    requestUrlPattern: "**/rq/api/build_treatments",
    stacktraceLocator: "#treatments_stacktrace_panel [data-stacktrace-body]",
    stacktracePanelLocator: "#treatments_stacktrace_panel",
    hintLocator: "#hint_build_treatments",
    workflow: "rq_job",
    skipMessage: "Treatments control not visible or not enabled for this configuration"
  },
  {
    name: "rhem",
    formSelector: "form#rhem_form",
    actionSelector: "#btn_run_rhem",
    requestUrlPattern: "**/rq/api/run_rhem_rq",
    stacktraceLocator: "#rhem_stacktrace_panel [data-stacktrace-body]",
    stacktracePanelLocator: "#rhem_stacktrace_panel",
    hintLocator: "#hint_run_rhem",
    workflow: "rq_job",
    expectJobHint: false
  }
];

export default controllerCases;
