const controllerTestCases = [
  {
    name: "landuse",
    formSelector: "form#landuse_form",
    actionSelector: "#btn_build_landuse",
    requestUrlPattern: "**/rq-engine/api/**/build-landuse",
    stacktraceLocator: "#landuse_stacktrace_panel [data-stacktrace-body]",
    stacktracePanelLocator: "#landuse_stacktrace_panel",
    hintLocator: "#hint_build_landuse"
  },
  {
    name: "soils",
    formSelector: "form#soil_form",
    actionSelector: "#btn_build_soil",
    requestUrlPattern: "**/rq-engine/api/**/build-soils",
    stacktraceLocator: "#soil_stacktrace_panel [data-stacktrace-body]",
    stacktracePanelLocator: "#soil_stacktrace_panel",
    hintLocator: "#hint_build_soil"
  },
  {
    name: "climate",
    formSelector: "form#climate_form",
    actionSelector: "#btn_build_climate",
    requestUrlPattern: "**/rq-engine/api/**/build-climate",
    stacktraceLocator: "#climate_stacktrace_panel [data-stacktrace-body]",
    stacktracePanelLocator: "#climate_stacktrace_panel",
    hintLocator: "#hint_build_climate"
  },
  {
    name: "rap_ts",
    formSelector: "form#rap_ts_form",
    actionSelector: "#btn_build_rap_ts",
    requestUrlPattern: "**/rq-engine/api/**/acquire-rap-ts",
    stacktraceLocator: "#rap_ts_stacktrace_panel [data-stacktrace-body]",
    stacktracePanelLocator: "#rap_ts_stacktrace_panel",
    hintLocator: "#hint_build_rap_ts",
    skipMessage: "RAP time series control not enabled for this run"
  },
  {
    name: "openet_ts",
    formSelector: "form#openet_ts_form",
    actionSelector: "#btn_build_openet_ts",
    requestUrlPattern: "**/rq-engine/api/**/acquire-openet-ts",
    stacktraceLocator: "#openet_ts_stacktrace_panel [data-stacktrace-body]",
    stacktracePanelLocator: "#openet_ts_stacktrace_panel",
    hintLocator: "#hint_build_openet_ts",
    skipMessage: "OpenET time series control not enabled for this run"
  },
  {
    name: "ash",
    formSelector: "form#ash_form",
    actionSelector: "#btn_run_ash",
    requestUrlPattern: "**/rq-engine/api/**/run-ash",
    stacktraceLocator: "#ash_form [data-stacktrace-body], #ash_form #stacktrace",
    stacktracePanelLocator: "#ash_form [data-stacktrace-panel]",
    hintLocator: "#hint_run_ash",
    skipMessage: "Ash control not enabled for this run"
  }
];

export default controllerTestCases;
