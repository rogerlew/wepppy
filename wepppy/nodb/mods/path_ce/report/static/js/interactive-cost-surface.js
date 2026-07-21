import {csvParse} from 'https://cdn.jsdelivr.net/npm/d3-dsv@3/+esm';

function formatNumber(value, digits = 0) {
  if (!Number.isFinite(value)) {
    return 'N/A';
  }
  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  });
}

function normalizeRows(rows) {
  const costByKey = new Map();
  const sdydValues = new Set();
  const sddcValues = new Set();

  for (const row of rows) {
    const sdyd = Number(row.sdyd_threshold);
    const sddc = Number(row.sddc_threshold);
    const cost = Number(row.total_cost);

    if (!Number.isFinite(sdyd) || !Number.isFinite(sddc) || !Number.isFinite(cost)) {
      continue;
    }

    const key = `${sdyd}_${sddc}`;
    costByKey.set(key, cost);
    sdydValues.add(sdyd);
    sddcValues.add(sddc);
  }

  const sdydArr = Array.from(sdydValues).sort((a, b) => a - b);
  const sddcArr = Array.from(sddcValues).sort((a, b) => a - b);

  // Build 2D z-grid: zGrid[sddcIdx][sdydIdx] = cost
  const zGrid = [];
  for (let j = 0; j < sddcArr.length; j++) {
    const row = [];
    for (let i = 0; i < sdydArr.length; i++) {
      const key = `${sdydArr[i]}_${sddcArr[j]}`;
      row.push(costByKey.get(key) ?? null);
    }
    zGrid.push(row);
  }

  // Calculate max cost for marker offset
  let maxCost = 0;
  for (const cost of costByKey.values()) {
    if (cost > maxCost) maxCost = cost;
  }

  return {
    costByKey,
    sdydValues: sdydArr,
    sddcValues: sddcArr,
    zGrid,
    maxCost
  };
}

export async function initInteractiveCostSurface(options) {
  const {
    containerId,
    container,
    csvUrl = 'gatecreek_threshold_analysis_results_50.csv',
    initialSdyd = 200,
    initialSddc = 200,
    height = 520
  } = options || {};

  const root =
    container ||
    (containerId ? document.getElementById(containerId) : null) ||
    document.body;

  root.classList.add('costsurface-root');
  root.innerHTML = '';

  const plotEl = document.createElement('div');
  plotEl.className = 'costsurface-plot';
  plotEl.style.height = `${height}px`;

  const status = document.createElement('div');
  status.className = 'costsurface-status';

  root.appendChild(plotEl);
  root.appendChild(status);

  // Load and parse CSV
  const csvText = await fetch(csvUrl).then(res => res.text());
  const rows = csvParse(csvText);
  const {costByKey, sdydValues, sddcValues, zGrid, maxCost} = normalizeRows(rows);

  // Current hover state
  let currentSdyd = sdydValues.includes(initialSdyd) ? initialSdyd : sdydValues[0];
  let currentSddc = sddcValues.includes(initialSddc) ? initialSddc : sddcValues[0];

  function getCost(sdyd, sddc) {
    const key = `${sdyd}_${sddc}`;
    return costByKey.get(key) ?? 0;
  }

  // Small offset to raise marker above surface
  const markerOffset = maxCost * 0.02;

  // Surface trace
  const surfaceTrace = {
    type: 'surface',
    x: sdydValues,
    y: sddcValues,
    z: zGrid,
    colorscale: 'Viridis',
    showscale: true,
    opacity: 0.95,
    colorbar: {
      title: {text: 'Total Cost ($)', side: 'right'},
      thickness: 15,
      len: 0.7
    },
    hovertemplate:
      'Sdyd: %{x}<br>' +
      'Sddc: %{y}<br>' +
      'Cost: $%{z:,.0f}<extra></extra>',
    contours: {
      x: {show: true, width: 3, color: 'rgba(0,0,0,0.3)'},
      y: {show: true, width: 3, color: 'rgba(0,0,0,0.3)'},
      z: {show: false}
    },
    hidesurface: false
  };

  // Selection marker trace (point + vertical line)
  function buildMarkerTrace(sdyd, sddc) {
    const cost = getCost(sdyd, sddc);

    return {
      type: 'scatter3d',
      mode: 'lines+markers',
      x: [sdyd, sdyd],
      y: [sddc, sddc],
      z: [0, cost + markerOffset],
      marker: {
        size: [0, 10],
        color: 'red',
        symbol: 'circle',
        line: {color: 'darkred', width: 2}
      },
      line: {
        color: 'red',
        width: 6
      },
      hoverinfo: 'skip',
      showlegend: false
    };
  }

  const layout = {
    scene: {
      xaxis: {title: 'Sdyd Threshold'},
      yaxis: {title: 'Sddc Threshold'},
      zaxis: {title: 'Total Cost ($)'},
      camera: {
        eye: {x: 1.5, y: 1.5, z: 1.2}
      }
    },
    margin: {l: 0, r: 0, t: 30, b: 0},
    height: height,
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    hovermode: 'closest'
  };

  const config = {
    responsive: true,
    displayModeBar: true,
    modeBarButtonsToRemove: ['toImage', 'sendDataToCloud'],
    displaylogo: false
  };

  // Initial render
  const Plotly = window.Plotly;
  await Plotly.newPlot(plotEl, [surfaceTrace, buildMarkerTrace(currentSdyd, currentSddc)], layout, config);

  function updateStatus(sdyd, sddc) {
    const cost = getCost(sdyd, sddc);
    status.innerHTML = `
      <div class="costsurface-status-item">
        <span class="costsurface-status-label">Hovering:</span>
        <span>Sdyd = ${sdyd}, Sddc = ${sddc}</span>
      </div>
      <div class="costsurface-status-item">
        <span class="costsurface-status-label">Total Cost:</span>
        <strong>$${formatNumber(cost, 0)}</strong>
      </div>
    `;
  }

  // Update marker on hover
  plotEl.on('plotly_hover', (data) => {
    if (data.points && data.points.length > 0) {
      const point = data.points[0];
      // Only respond to surface hover (trace 0)
      if (point.curveNumber === 0) {
        const sdyd = point.x;
        const sddc = point.y;

        if (sdyd !== currentSdyd || sddc !== currentSddc) {
          currentSdyd = sdyd;
          currentSddc = sddc;

          // Update only the marker trace (trace index 1)
          Plotly.restyle(plotEl, {
            x: [[sdyd, sdyd]],
            y: [[sddc, sddc]],
            z: [[0, getCost(sdyd, sddc) + markerOffset]]
          }, [1]);

          updateStatus(sdyd, sddc);
        }
      }
    }
  });

  updateStatus(currentSdyd, currentSddc);

  // Handle resize
  const resizeObserver = new ResizeObserver(() => {
    Plotly.Plots.resize(plotEl);
  });
  resizeObserver.observe(plotEl);

  return {
    destroy: () => {
      resizeObserver.disconnect();
      Plotly.purge(plotEl);
    }
  };
}
