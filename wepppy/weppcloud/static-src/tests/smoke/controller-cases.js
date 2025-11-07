const controllerCases = [
  {
    name: "landuse",
    formSelector: "form#landuse_form",
    actionSelector: "#btn_build_landuse",
    requestUrlPattern: "**/rq/api/build_landuse",
    stacktraceLocator: "#landuse_stacktrace_panel [data-stacktrace-body]",
    hintLocator: "#hint_build_landuse",
    workflow: "rq_job"
  },
  {
    name: "soils",
    formSelector: "form#soil_form",
    actionSelector: "#btn_build_soil",
    requestUrlPattern: "**/rq/api/build_soils",
    stacktraceLocator: "#soil_stacktrace_panel [data-stacktrace-body]",
    hintLocator: "#hint_build_soil",
    workflow: "rq_job"
  },
  {
    name: "climate",
    formSelector: "form#climate_form",
    actionSelector: "#btn_build_climate",
    requestUrlPattern: "**/rq/api/build_climate",
    stacktraceLocator: "#climate_stacktrace_panel [data-stacktrace-body]",
    hintLocator: "#hint_build_climate",
    workflow: "rq_job"
  },
  {
    name: "subcatchments",
    formSelector: "form#subcatchments_form",
    actionSelector: "#btn_build_subcatchments",
    requestUrlPattern: "**/rq/api/build_subcatchments",
    stacktraceLocator: "#subcatchments_stacktrace_panel [data-stacktrace-body]",
    hintLocator: "#hint_build_subcatchments",
    workflow: "rq_job"
  },
  {
    name: "set_outlet",
    formSelector: "form#set_outlet_form",
    actionSelector: "#btn_set_outlet_entry",
    requestUrlPattern: "**/rq/api/set_outlet",
    stacktraceLocator: "#set_outlet_stacktrace_panel [data-stacktrace-body]",
    hintLocator: "#hint_set_outlet_cursor",
    workflow: "rq_job",
    prepareAction: async ({ page }) => {
      const entryModeRadio = page.locator("#set_outlet_mode_entry");
      if (await entryModeRadio.count()) {
        await entryModeRadio.check({ force: true });
      }
      const entryField = page.locator("#input_set_outlet_entry");
      await entryField.fill("-116.95, 46.73");
    },
    failureStatus: 200
  },
  {
    name: "rap_ts",
    formSelector: "form#rap_ts_form",
    actionSelector: "#btn_build_rap_ts",
    requestUrlPattern: "**/rq/api/acquire_rap_ts",
    stacktraceLocator: "#rap_ts_stacktrace_panel [data-stacktrace-body]",
    hintLocator: "#hint_build_rap_ts",
    workflow: "rq_job"
  },
  {
    name: "wepp",
    formSelector: "form#wepp_form",
    actionSelector: "#btn_run_wepp",
    requestUrlPattern: "**/rq/api/run_wepp",
    stacktraceLocator: "#wepp_stacktrace_panel [data-stacktrace-body]",
    hintLocator: "#hint_run_wepp",
    workflow: "rq_job"
  },
  {
    name: "observed",
    formSelector: "form#observed_form",
    actionSelector: "#btn_run_observed",
    requestUrlPattern: /\/tasks\/run_model_fit\/?(?:\?.*)?$/,
    stacktraceLocator: "#observed_stacktrace_panel [data-stacktrace-body]",
    hintLocator: "#hint_run_observed",
    expectJobHint: false
  },
  {
    name: "debris_flow",
    formSelector: "form#debris_flow_form",
    actionSelector: "#btn_run_debris_flow",
    requestUrlPattern: "**/rq/api/run_debris_flow",
    stacktraceLocator: "#debris_flow_stacktrace_panel [data-stacktrace-body]",
    hintLocator: "#hint_run_debris_flow",
    workflow: "rq_job"
  }
];

export default controllerCases;
