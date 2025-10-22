module.exports = {
  root: true,
  env: {
    browser: true,
    es2021: true,
    jest: true,
    jquery: true
  },
  extends: ["eslint:recommended", "plugin:jest/recommended", "plugin:jest/style", "prettier"],
  parserOptions: {
    sourceType: "module",
    ecmaVersion: 2021
  },
  plugins: ["jest"],
  globals: {
    WCDom: "readonly",
    WCForms: "readonly",
    WCHttp: "readonly",
    WCEvents: "readonly",
    controlBase: "readonly",
    WSClient: "readonly",
    StatusStream: "readonly",
    Project: "readonly",
    MapController: "readonly",
    UnitizerClient: "readonly",
    SubcatchmentDelineation: "readonly",
    Observed: "readonly",
    Baer: "readonly",
    Disturbed: "readonly",
    Treatments: "readonly",
    Team: "readonly",
    url_for_run: "readonly",
    pup_relpath: "readonly",
    createColormap: "readonly",
    runid: "readonly",
    global: "readonly",
    L: "readonly",
    jqXHR: "readonly",
    textStatus: "readonly",
    errorThrown: "readonly",
    Outlet: "readonly",
    parseBboxText: "readonly",
    ispoweruser: "readonly",
    Landuse: "readonly",
    ChannelDelineation: "readonly",
    coordRound: "readonly",
    site_prefix: "readonly",
    addScenario: "readonly",
    updateControls: "readonly",
    refreshScenarioOptions: "readonly",
    cellsize: "readonly",
    plotty: "readonly",
    Wepp: "readonly",
    render_legend: "readonly",
    linearToLog: "readonly",
    updateRangeMaxLabel_mm: "readonly",
    updateRangeMaxLabel_kgha: "readonly",
    updateRangeMaxLabel_tonneha: "readonly",
    polylabel: "readonly",
    getAshTransportMeasure: "readonly"
    ,
    fromHex: "readonly",
    config: "readonly",
    RangelandCover: "readonly"
  },
  rules: {
    "no-unused-vars": "off",
    "no-useless-escape": "off"
  },
  overrides: [
    {
      files: ["controllers_js/__tests__/**/*.js"],
      env: {
        jest: true
      }
    }
  ]
};
