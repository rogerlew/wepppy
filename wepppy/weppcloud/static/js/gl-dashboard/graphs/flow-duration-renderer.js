import { getState, setValue } from "../state.js";

export function probabilityAtFraction(fraction, minimum, logarithmic) {
  return logarithmic
    ? Math.exp(
        Math.log(minimum) + fraction * (Math.log(100) - Math.log(minimum)),
      )
    : fraction * 100;
}

export function closestFlowPoint(points, probability) {
  if (!points.length) return null;
  const index = Math.max(
    0,
    Math.min(
      points.length - 1,
      Math.round((probability * (points.length + 1)) / 100) - 1,
    ),
  );
  return points[index];
}

function flowText(series, point) {
  return `${series.label}: ${point.flow.toPrecision(5)} m³/s at ${point.probability.toPrecision(5)}% exceedance (${point.date})`;
}

export function clearFlowDuration(graph) {
  graph._flowUi?.remove();
  graph._flowUi = null;
  graph._flowBounds = null;
}

function buildInfo(graph) {
  const box = document.createElement("div");
  box.className = "gl-flow-duration-info";
  const source = document.createElement("p");
  source.textContent = `${graph._data.settings.source === "outlet" ? "Channel outlet discharge" : "Hillslope streamflow"} · daily mean m³/s · Weibull plotting positions · each scenario uses its own record`;
  box.appendChild(source);
  for (const series of graph._data.series) {
    const row = document.createElement("div");
    if (series.error) {
      row.textContent = `${series.label}: ${series.error}. Reload the page to retry source discovery.`;
      row.setAttribute("role", "status");
    } else {
      const label = document.createElement("label");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = !(getState().flowDurationHidden || []).includes(
        series.id,
      );
      input.addEventListener("change", () => {
        const hidden = new Set(getState().flowDurationHidden || []);
        if (input.checked) hidden.delete(series.id);
        else hidden.add(series.id);
        setValue("flowDurationHidden", [...hidden]);
        graph.render();
      });
      const swatch = document.createElement("span");
      swatch.textContent = " — ";
      swatch.style.color = `rgb(${series.color.slice(0, 3).join(",")})`;
      label.append(
        input,
        swatch,
        document.createTextNode(
          `${series.label}: ${series.start}–${series.end}; N=${series.count.toLocaleString()}; missing=${series.missing.toLocaleString()}; zero-flow=${series.zeroDays} (${((100 * series.zeroDays) / series.count).toFixed(2)}%)`,
        ),
      );
      row.appendChild(label);
    }
    box.appendChild(row);
  }
  const label = document.createElement("label");
  label.textContent = "Inspect exceedance probability (%) ";
  const input = document.createElement("input");
  input.type = "range";
  input.min = "0";
  input.max = "1000";
  input.value = "500";
  input.setAttribute("aria-label", "Inspect exceedance probability");
  const output = document.createElement("div");
  output.setAttribute("aria-live", "polite");
  const inspect = () => {
    const bounds = graph._flowBounds;
    if (!bounds || !bounds.series.length) {
      output.textContent = "No visible daily values";
      return;
    }
    const p = probabilityAtFraction(
      Number(input.value) / 1000,
      bounds.minimum,
      bounds.log,
    );
    input.setAttribute(
      "aria-valuetext",
      `${p.toPrecision(4)} percent exceedance`,
    );
    output.textContent = bounds.series
      .map((series) => flowText(series, closestFlowPoint(series.points, p)))
      .join(" · ");
  };
  input.addEventListener("input", inspect);
  label.appendChild(input);
  box.append(label, output);
  graph.container.appendChild(box);
  graph._flowUi = box;
  graph._flowInspect = inspect;
}

export function renderFlowDuration(graph) {
  const data = graph._data;
  const hidden = getState().flowDurationHidden || [];
  const series = data.series.filter(
    (item) => item.points?.length && !hidden.includes(item.id),
  );
  const ctx = graph.ctx2d;
  const dpr = window.devicePixelRatio || 1;
  const width = graph.canvas.width / dpr,
    height = graph.canvas.height / dpr;
  const pad = { left: 80, right: 24, top: 24, bottom: 50 };
  const plotWidth = width - pad.left - pad.right,
    plotHeight = height - pad.top - pad.bottom;
  const theme = graph._getTheme();
  ctx.clearRect(0, 0, width, height);
  const textColor = theme.text || "#777";
  ctx.strokeStyle = textColor;
  ctx.fillStyle = textColor;
  ctx.font = "12px sans-serif";
  ctx.beginPath();
  ctx.moveTo(pad.left, pad.top);
  ctx.lineTo(pad.left, height - pad.bottom);
  ctx.lineTo(width - pad.right, height - pad.bottom);
  ctx.stroke();
  const minimum = series.length
    ? Math.min(...series.map((item) => item.points[0].probability))
    : 1;
  const log = data.settings.scale === "log";
  const x = (probability) =>
    pad.left +
    plotWidth *
      (log
        ? Math.log(probability / minimum) / Math.log(100 / minimum)
        : probability / 100);
  const maximum = series.length
    ? Math.max(...series.map((item) => item.points[0].flow)) || 1
    : 1;
  const y = (flow) => pad.top + plotHeight * (1 - flow / maximum);
  for (let index = 0; index <= 4; index += 1) {
    const flow = (maximum * index) / 4;
    ctx.textAlign = "right";
    ctx.fillText(flow.toPrecision(3), pad.left - 8, y(flow) + 4);
  }
  const ticks = log
    ? [0.001, 0.01, 0.1, 1, 10, 100].filter((p) => p >= minimum)
    : [0, 20, 40, 60, 80, 100];
  for (const tick of ticks) {
    ctx.textAlign = "center";
    ctx.fillText(String(tick), x(tick), height - pad.bottom + 20);
  }
  ctx.textAlign = "center";
  ctx.fillText(
    "Exceedance probability (%)",
    pad.left + plotWidth / 2,
    height - 6,
  );
  ctx.save();
  ctx.translate(16, pad.top + plotHeight / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText("Daily mean discharge (m³/s)", 0, 0);
  ctx.restore();
  for (const item of series) {
    ctx.strokeStyle = `rgb(${item.color.slice(0, 3).join(",")})`;
    ctx.lineWidth = 2;
    ctx.beginPath();
    item.points.forEach((point, index) => {
      if (index) ctx.lineTo(x(point.probability), y(point.flow));
      else ctx.moveTo(x(point.probability), y(point.flow));
    });
    ctx.stroke();
    if (item.points.length === 1) {
      const point = item.points[0];
      ctx.fillStyle = ctx.strokeStyle;
      ctx.beginPath();
      ctx.arc(x(point.probability), y(point.flow), 3, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  graph._flowBounds = {
    left: pad.left,
    top: pad.top,
    width: plotWidth,
    height: plotHeight,
    minimum,
    log,
    series,
  };
  if (!graph._flowUi) buildInfo(graph);
  graph._flowInspect?.();
}

export function hoverFlowDuration(graph, event) {
  const bounds = graph._flowBounds,
    tooltip = graph.tooltipEl;
  if (!bounds || !tooltip) return;
  const rect = graph.canvas.getBoundingClientRect();
  const x = event.clientX - rect.left,
    y = event.clientY - rect.top;
  if (
    x < bounds.left ||
    x > bounds.left + bounds.width ||
    y < bounds.top ||
    y > bounds.top + bounds.height
  ) {
    tooltip.style.display = "none";
    return;
  }
  const probability = probabilityAtFraction(
    (x - bounds.left) / bounds.width,
    bounds.minimum,
    bounds.log,
  );
  tooltip.textContent = bounds.series
    .map((series) =>
      flowText(series, closestFlowPoint(series.points, probability)),
    )
    .join("\n");
  tooltip.style.whiteSpace = "pre-line";
  tooltip.style.display = "block";
  tooltip.style.left = `${Math.min(x + 12, rect.width - 220)}px`;
  tooltip.style.top = `${y + 12}px`;
}
