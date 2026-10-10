import { FLOW_DURATION_DEFAULTS } from "./flow-duration-data.js";

export function renderFlowDurationControls(
  parent,
  { getState, setValue, activate },
) {
  const controls = document.createElement("div");
  controls.className = "gl-layer-items";
  const settings = () => ({
    ...FLOW_DURATION_DEFAULTS,
    ...getState().flowDuration,
  });
  const update = (key, value) => {
    setValue("flowDuration", { ...settings(), [key]: value });
    if (getState().activeGraphKey === "flow-duration") activate();
  };
  for (const [key, title, choices] of [
    [
      "source",
      "Daily flow source",
      [
        ["hillslope", "Hillslope streamflow (totalwatsed)"],
        ["outlet", "Channel outlet discharge"],
      ],
    ],
    [
      "scale",
      "Exceedance probability x-axis",
      [
        ["linear", "Linear"],
        ["log", "Logarithmic"],
      ],
    ],
  ]) {
    const fieldset = document.createElement("fieldset");
    const legend = document.createElement("legend");
    legend.textContent = title;
    fieldset.appendChild(legend);
    for (const [value, text] of choices) {
      const label = document.createElement("label");
      label.style.display = "block";
      const input = document.createElement("input");
      input.type = "radio";
      input.name = `fdc-${key}`;
      input.value = value;
      input.checked = settings()[key] === value;
      input.addEventListener("change", () => {
        if (input.checked) update(key, value);
      });
      label.append(input, document.createTextNode(` ${text}`));
      fieldset.appendChild(label);
    }
    controls.appendChild(fieldset);
  }
  const label = document.createElement("label");
  label.textContent = "Year selection ";
  const select = document.createElement("select");
  select.id = "fdc-year-selection";
  for (const [value, text] of [
    [0, "All years included"],
    [1, "Exclude first year"],
    [2, "Exclude first two years"],
    [5, "Exclude first five years"],
  ]) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = text;
    option.selected = settings().excludedYears === value;
    select.appendChild(option);
  }
  select.addEventListener("change", () =>
    update("excludedYears", Number(select.value)),
  );
  label.appendChild(select);
  controls.appendChild(label);
  parent.appendChild(controls);
}
