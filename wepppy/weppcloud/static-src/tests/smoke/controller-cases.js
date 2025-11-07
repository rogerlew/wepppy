const controllerCases = [
  {
    name: "landuse",
    formSelector: "form#landuse_form",
    actionSelector: "#btn_build_landuse",
    requestUrlPattern: "**/rq/api/build_landuse",
    stacktraceLocator: "#landuse_stacktrace_panel [data-stacktrace-body]",
    hintLocator: "#hint_build_landuse",
    workflow: "landuse"
  }
];

export default controllerCases;
