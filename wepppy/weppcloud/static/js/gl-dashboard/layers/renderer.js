/**
 * Sidebar layer list and legend rendering for gl-dashboard.
 * DOM-only: receives callbacks/state setters to trigger data/deck updates.
 */

import { resolveColormapName } from '../colors.js';

export function createLayerRenderer({
  getState,
  setValue,
  layerUtils,
  domRefs,
  yearSlider,
  deselectAllSubcatchmentOverlays,
  activateWeppYearlyLayer,
  refreshWeppStatisticData,
  refreshRapData,
  refreshWeppEventData,
  loadRapTimeseriesData,
  loadWeppYearlyTimeseriesData,
  applyLayers,
  setGraphFocus,
  setGraphCollapsed,
  pickActiveWeppEventLayer,
  soilColorForValue,
  constants,
}) {
  const {
    layerListEl,
    layerEmptyEl,
    legendsContentEl,
    legendEmptyEl,
  } = domRefs || {};

  const {
    COMPARISON_MEASURES,
    WATER_MEASURES,
    SOIL_MEASURES,
    RAP_BAND_LABELS,
    NLCD_COLORMAP,
    NLCD_LABELS,
  } = constants || {};

  // SBS burn class colors and labels (matches baer.py / disturbed.py)
  const SBS_CLASSES = [
    { color: '#00734A', label: 'Unburned' },
    { color: '#4DE600', label: 'Low' },
    { color: '#FFFF00', label: 'Moderate' },
    { color: '#FF0000', label: 'High' },
  ];

  // Units for continuous layers
  const LAYER_UNITS = {
    cancov: '%',
    inrcov: '%',
    rilcov: '%',
    clay: '%',
    sand: '%',
    rock: '%',
    bd: 'g/cm³',
    slope_scalar: 'rise/run',
    length: 'm',
    aspect: '°',
    runoff_volume: 'mm',
    subrunoff_volume: 'mm',
    baseflow_volume: 'mm',
    soil_loss: 't/ha',
    sediment_deposition: 't/ha',
    sediment_yield: 't/ha',
    wind_transport: 't/ha',
    water_transport: 't/ha',
    ash_transport: 't/ha',
    // WEPP Event metrics
    event_P: 'mm',
    event_Q: 'mm',
    event_ET: 'mm',
    event_peakro: 'm³/s',
    event_tdet: 'kg',
  };

  function renderRapSection(details, section) {
    const state = getState();
    const itemList = document.createElement('ul');
    itemList.className = 'gl-layer-items';

    // Cumulative Cover radio option
    const cumulativeLi = document.createElement('li');
    cumulativeLi.className = 'gl-layer-item';
    const cumulativeInput = document.createElement('input');
    cumulativeInput.type = 'radio';
    cumulativeInput.name = 'subcatchment-overlay';
    cumulativeInput.checked = !!state.rapCumulativeMode;
    cumulativeInput.id = 'layer-RAP-cumulative';
    cumulativeInput.addEventListener('change', async () => {
      if (!cumulativeInput.checked) return;
      deselectAllSubcatchmentOverlays();
      window.rapCumulativeMode = true;
      setValue('rapCumulativeMode', true);
      // Re-check the cumulative radio since deselectAll cleared it
      cumulativeInput.checked = true;
      setGraphFocus(false);
      setGraphCollapsed(false);
      const currentState = getState();
      const rapMeta = currentState.rapMetadata;
      if (rapMeta && rapMeta.years && rapMeta.years.length) {
        const minYear = rapMeta.years[0];
        const maxYear = rapMeta.years[rapMeta.years.length - 1];
        const nextYear =
          !currentState.rapSelectedYear || currentState.rapSelectedYear < minYear || currentState.rapSelectedYear > maxYear
            ? maxYear
            : currentState.rapSelectedYear;
        setValue('rapSelectedYear', nextYear);
        yearSlider.setRange(minYear, maxYear, nextYear);
      }
      yearSlider.show();
      await refreshRapData();
      applyLayers();
      const graphEl = document.getElementById('gl-graph');
      if (graphEl && !graphEl.classList.contains('is-collapsed')) {
        await loadRapTimeseriesData();
      }
    });
    const cumulativeLabel = document.createElement('label');
    cumulativeLabel.setAttribute('for', 'layer-RAP-cumulative');
    cumulativeLabel.innerHTML =
      '<span class="gl-layer-name">Cumulative Cover</span><br><span class="gl-layer-path">Sum of selected bands (0-100%)</span>';
    cumulativeLi.appendChild(cumulativeInput);
    cumulativeLi.appendChild(cumulativeLabel);
    itemList.appendChild(cumulativeLi);

    // Band checkboxes (indented under cumulative)
    const bandContainer = document.createElement('li');
    bandContainer.style.cssText = 'padding-left: 1.5rem; margin-top: 0.25rem;';
    const bandList = document.createElement('ul');
    bandList.className = 'gl-layer-items';
    bandList.style.cssText = 'gap: 0.15rem;';

    section.items.forEach((layer) => {
      const li = document.createElement('li');
      li.className = 'gl-layer-item';
      const input = document.createElement('input');
      input.type = 'checkbox';
      input.checked = layer.selected !== false;
      input.id = `layer-RAP-band-${layer.key}`;
      input.addEventListener('change', async () => {
        layer.selected = input.checked;
        const currentState = getState();
        if (currentState.rapCumulativeMode) {
          await refreshRapData();
          applyLayers();
          const graphEl = document.getElementById('gl-graph');
          if (graphEl && !graphEl.classList.contains('is-collapsed')) {
            await loadRapTimeseriesData();
          }
        }
      });
      const label = document.createElement('label');
      label.setAttribute('for', input.id);
      const name = layer.label || layer.key;
      label.innerHTML = `<span class="gl-layer-name" style="font-size:0.85rem;">${name}</span>`;
      li.appendChild(input);
      li.appendChild(label);
      bandList.appendChild(li);
    });

    bandContainer.appendChild(bandList);
    itemList.appendChild(bandContainer);

    details.appendChild(itemList);
  }

  function renderWeppEventSection(details, section) {
    const state = getState();
    const itemList = document.createElement('ul');
    itemList.className = 'gl-layer-items';

    // Date input row
    const dateLi = document.createElement('li');
    dateLi.className = 'gl-layer-item';
    dateLi.style.cssText = 'flex-direction: column; align-items: flex-start; gap: 0.25rem;';
    const dateLabel = document.createElement('label');
    dateLabel.textContent = 'Event Date:';
    dateLabel.style.cssText = 'font-size: 0.85rem; color: #8fa0c2;';
    const dateInput = document.createElement('input');
    dateInput.type = 'date';
    dateInput.id = 'gl-wepp-event-date';
    dateInput.style.cssText =
      'width: 100%; padding: 0.25rem; background: #1f2c44; border: 1px solid #3f5070; border-radius: 4px; color: #d0d7e8; font-size: 0.85rem;';
    if (state.weppEventSelectedDate) {
      dateInput.value = state.weppEventSelectedDate;
    }
    if (state.weppEventMetadata && state.weppEventMetadata.startDate) {
      dateInput.min = state.weppEventMetadata.startDate;
    }
    if (state.weppEventMetadata && state.weppEventMetadata.endDate) {
      dateInput.max = state.weppEventMetadata.endDate;
    }
    dateInput.addEventListener('change', async () => {
      setValue('weppEventSelectedDate', dateInput.value);
      const activeLayer = pickActiveWeppEventLayer();
      if (activeLayer && dateInput.value) {
        await refreshWeppEventData();
        applyLayers();
      }
    });
    dateLi.appendChild(dateLabel);
    dateLi.appendChild(dateInput);
    itemList.appendChild(dateLi);

    // Separator
    const separatorLi = document.createElement('li');
    separatorLi.style.cssText = 'border-top: 1px solid #1f2c44; margin: 0.5rem 0; padding: 0;';
    itemList.appendChild(separatorLi);

    // Radio options for each metric
    section.items.forEach((layer) => {
      const li = document.createElement('li');
      li.className = 'gl-layer-item';
      const input = document.createElement('input');
      input.type = 'radio';
      input.name = 'subcatchment-overlay';
      input.checked = layer.visible;
      input.id = `layer-WEPP-Event-${layer.key}`;
      input.addEventListener('change', async () => {
        if (!input.checked) return;
        deselectAllSubcatchmentOverlays();
        layer.visible = true;
        input.checked = true;
        setGraphFocus(false);
        if (getState().weppEventSelectedDate) {
          await refreshWeppEventData();
        }
        applyLayers();
      });
      const label = document.createElement('label');
      label.setAttribute('for', input.id);
      const name = layer.label || layer.key;
      const path = layer.path || '';
      label.innerHTML = `<span class="gl-layer-name">${name}</span><br><span class="gl-layer-path">${path}</span>`;
      li.appendChild(input);
      li.appendChild(label);
      itemList.appendChild(li);
    });

    details.appendChild(itemList);
  }

  function updateLayerList() {
    if (!layerListEl) return;
    const state = getState();
    const {
      landuseLayers = [],
      soilsLayers = [],
      hillslopesLayers = [],
      weppLayers = [],
      weppYearlyLayers = [],
      weppEventLayers = [],
      watarLayers = [],
      rapLayers = [],
      detectedLayers = [],
      rapCumulativeMode,
      weppStatistic,
    } = state;

    layerListEl.innerHTML = '';
    const subcatchmentSections = [];

    const landuseRasters = detectedLayers
      .filter((l) => l.key === 'landuse' || l.key === 'sbs')
      .map((r) => ({ ...r, isRaster: true, rasterRef: r }));
    const soilsRasters = detectedLayers
      .filter((l) => l.key === 'soils')
      .map((r) => ({ ...r, isRaster: true, rasterRef: r }));

    if (landuseLayers.length || landuseRasters.length) {
      subcatchmentSections.push({ title: 'Landuse', items: [...landuseLayers, ...landuseRasters], isSubcatchment: true });
    }
    if (soilsLayers.length || soilsRasters.length) {
      subcatchmentSections.push({ title: 'Soils', items: [...soilsLayers, ...soilsRasters], isSubcatchment: true });
    }
    if (rapLayers.length) {
      subcatchmentSections.push({ title: 'RAP', items: rapLayers, isSubcatchment: true, isRap: true });
    }
    if (weppLayers.length) {
      subcatchmentSections.push({ title: 'WEPP', items: weppLayers, isSubcatchment: true });
    }
    if (weppYearlyLayers.length) {
      subcatchmentSections.push({
        title: 'WEPP Yearly',
        idPrefix: 'WEPP-Yearly',
        items: weppYearlyLayers,
        isSubcatchment: true,
        isWeppYearly: true,
      });
    }
    if (weppEventLayers.length) {
      subcatchmentSections.push({ title: 'WEPP Event', items: weppEventLayers, isSubcatchment: true, isWeppEvent: true });
    }
    if (watarLayers.length) {
      subcatchmentSections.push({ title: 'WATAR', items: watarLayers, isSubcatchment: true });
    }
    const allSections = [...subcatchmentSections];
    if (!allSections.length) {
      if (layerEmptyEl) {
        layerEmptyEl.hidden = false;
      }
      return;
    }
    if (layerEmptyEl) {
      layerEmptyEl.hidden = true;
    }
    if (subcatchmentSections.length) {
      const groupHeader = document.createElement('li');
      groupHeader.className = 'gl-layer-group-header';
      groupHeader.textContent = 'Subcatchment Overlays';
      layerListEl.appendChild(groupHeader);
    }
    allSections.forEach((section, idx) => {
      const details = document.createElement('details');
      details.className = 'gl-layer-details';
      const hasVisibleItem = section.items.some((l) => l.visible);
      details.open = idx === 0 || hasVisibleItem || (section.isRap && rapCumulativeMode);

      const summary = document.createElement('summary');
      summary.className = 'gl-layer-group';
      summary.textContent = section.title;
      details.appendChild(summary);

      if (section.isRap) {
        renderRapSection(details, section);
        layerListEl.appendChild(details);
        return;
      }

      if (section.isWeppEvent) {
        renderWeppEventSection(details, section);
        layerListEl.appendChild(details);
        return;
      }

      if (section.title === 'WEPP') {
        const statWrapper = document.createElement('div');
        statWrapper.className = 'gl-wepp-stat';
        statWrapper.innerHTML = `
          <div class="gl-wepp-stat__label">Statistic</div>
          <div class="gl-wepp-stat__options">
            <label><input type="radio" name="wepp-stat" value="mean" ${weppStatistic === 'mean' ? 'checked' : ''}> Mean (Annual Average)</label>
            <label><input type="radio" name="wepp-stat" value="p90" ${weppStatistic === 'p90' ? 'checked' : ''}> 90th Percentile (Risk)</label>
            <label><input type="radio" name="wepp-stat" value="sd" ${weppStatistic === 'sd' ? 'checked' : ''}> Std. Deviation (Variability)</label>
            <label><input type="radio" name="wepp-stat" value="cv" ${weppStatistic === 'cv' ? 'checked' : ''}> CV % (Instability)</label>
          </div>
        `;
        const statInputs = statWrapper.querySelectorAll('input[name="wepp-stat"]');
        statInputs.forEach((inputEl) => {
          inputEl.addEventListener('change', async (event) => {
            const nextStat = event.target.value;
            if (nextStat === weppStatistic) return;
            setValue('weppStatistic', nextStat);
            await refreshWeppStatisticData();
          });
        });
        details.appendChild(statWrapper);
      }

      const itemList = document.createElement('ul');
      itemList.className = 'gl-layer-items';

      section.items.forEach((layer) => {
        const li = document.createElement('li');
        li.className = 'gl-layer-item';
        const input = document.createElement('input');
        const isRaster = layer.isRaster === true;
        input.type = section.isSubcatchment && !isRaster ? 'radio' : 'checkbox';
        if (section.isSubcatchment && !isRaster) {
          input.name = 'subcatchment-overlay';
        }
        input.checked = layer.visible;
        const idPrefix = section.idPrefix || section.title;
        input.id = `layer-${idPrefix}-${layer.key}`;
        input.addEventListener('change', async () => {
          if (section.isSubcatchment && !isRaster) {
            deselectAllSubcatchmentOverlays();
            layer.visible = true;
            input.checked = true;
            if (section.isWeppYearly) {
              await activateWeppYearlyLayer();
            }
          } else {
            const target = layer.rasterRef || layer;
            target.visible = input.checked;
            layer.visible = input.checked;
          }
          setGraphFocus(false);
        applyLayers();
        const graphEl = document.getElementById('gl-graph');
        // Collapse the graph when switching to non-timeseries overlays.
        if (section.isSubcatchment && !section.isRap && !section.isWeppYearly) {
          if (graphEl) {
            graphEl.classList.add('is-collapsed');
          }
          if (window.glDashboardSetGraphMode) {
            window.glDashboardSetGraphMode('minimized', { source: 'auto' });
          }
          setTimeout(() => {
            if (window.glDashboardSetGraphMode) {
              window.glDashboardSetGraphMode('minimized', { source: 'user' });
            }
          }, 0);
        }
        const graphVisible = graphEl && !graphEl.classList.contains('is-collapsed');
        if (graphVisible && section.isWeppYearly && layer.visible) {
          await loadWeppYearlyTimeseriesData();
        } else if (graphVisible && !section.isSubcatchment && (getState().rapCumulativeMode || getState().rapLayers.some((l) => l.visible))) {
          await loadRapTimeseriesData();
        }
      });
      const label = document.createElement('label');
      label.setAttribute('for', input.id);
      const name = layer.label || layer.key;
      const path = layer.path || '';
        label.innerHTML = `<span class="gl-layer-name">${name}</span><br><span class="gl-layer-path">${path}</span>`;
        li.appendChild(input);
        li.appendChild(label);
        itemList.appendChild(li);
      });

      details.appendChild(itemList);
      layerListEl.appendChild(details);
    });
  }

  function formatLegendValue(value, decimals = 1) {
    if (!Number.isFinite(value)) return '—';
    return value.toFixed(decimals);
  }

  function getUsedNlcdClasses(layer) {
    const classes = new Set();
    if (!layer || !layer.values) return [];
    const values = layer.values;
    for (let i = 0; i < values.length; i++) {
      const v = values[i];
      if (Number.isFinite(v) && v > 0 && NLCD_COLORMAP[v]) {
        classes.add(v);
      }
    }
    return Array.from(classes)
      .sort((a, b) => a - b)
      .map((code) => ({
        color: NLCD_COLORMAP[code],
        label: NLCD_LABELS[code] || `Class ${code}`,
      }));
  }

  function getUsedSoilClasses(layer) {
    const codes = new Set();
    if (!layer || !layer.values) return [];
    const values = layer.values;
    for (let i = 0; i < values.length; i++) {
      const v = values[i];
      if (Number.isFinite(v) && v > 0) {
        codes.add(v);
      }
    }
    if (codes.size === 0) return [];
    return Array.from(codes)
      .sort((a, b) => a - b)
      .map((code) => {
        const color = soilColorForValue(code);
        const label = String(code);
        return { color, label };
      });
  }

  function getUsedLanduseClasses(state) {
    const classMap = new Map();
    if (!state.landuseSummary) return classMap;
    for (const topazId of Object.keys(state.landuseSummary)) {
      const row = state.landuseSummary[topazId];
      if (!row) continue;
      const key = row.key ?? row._map;
      if (key == null || classMap.has(key)) continue;
      const color = row.color;
      const desc = row.desc || `Class ${key}`;
      classMap.set(key, { color, desc });
    }
    return classMap;
  }

  function getUsedSoilsClasses(state) {
    const classMap = new Map();
    if (!state.soilsSummary) return classMap;
    for (const topazId of Object.keys(state.soilsSummary)) {
      const row = state.soilsSummary[topazId];
      if (!row) continue;
      const mukey = row.mukey;
      if (mukey == null || classMap.has(mukey)) continue;
      const color = row.color;
      const desc = row.desc || mukey;
      classMap.set(mukey, { color, desc });
    }
    return classMap;
  }

  function renderCategoricalLegend(items) {
    const container = document.createElement('div');
    container.className = 'gl-legend-categorical';
    for (const item of items) {
      const row = document.createElement('div');
      row.className = 'gl-legend-categorical__item';
      const swatch = document.createElement('span');
      swatch.className = 'gl-legend-categorical__swatch';
      swatch.style.backgroundColor = item.color;
      const label = document.createElement('span');
      label.textContent = item.label;
      row.appendChild(swatch);
      row.appendChild(label);
      container.appendChild(row);
    }
    return container;
  }

  function renderContinuousLegend(minVal, maxVal, unit, colormap) {
    const container = document.createElement('div');
    container.className = 'gl-legend-continuous';

    const barWrapper = document.createElement('div');
    barWrapper.className = 'gl-legend-continuous__bar-wrapper';
    const bar = document.createElement('div');
    let barClass = 'gl-legend-continuous__bar';
    if (colormap === 'winter') {
      barClass += ' gl-legend-continuous__bar--winter';
    } else if (colormap === 'jet2') {
      barClass += ' gl-legend-continuous__bar--jet2';
    }
    bar.className = barClass;
    barWrapper.appendChild(bar);
    container.appendChild(barWrapper);

    const labels = document.createElement('div');
    labels.className = 'gl-legend-continuous__labels';
    const minLabel = document.createElement('span');
    minLabel.textContent = formatLegendValue(minVal);
    const maxLabel = document.createElement('span');
    maxLabel.textContent = formatLegendValue(maxVal);
    labels.appendChild(minLabel);
    labels.appendChild(maxLabel);
    container.appendChild(labels);

    if (unit) {
      const unitEl = document.createElement('div');
      unitEl.className = 'gl-legend-continuous__unit';
      unitEl.textContent = unit;
      container.appendChild(unitEl);
    }

    return container;
  }

  function renderDivergingLegend(unit, label, mode, rangeOverride, state) {
    const container = document.createElement('div');
    container.className = 'gl-legend-continuous gl-legend-diverging';

    const barWrapper = document.createElement('div');
    barWrapper.className = 'gl-legend-continuous__bar-wrapper';
    const bar = document.createElement('div');
    bar.className = 'gl-legend-continuous__bar gl-legend-diverging__bar';
    bar.style.background = 'linear-gradient(to right, #2166AC, #F7F7F7 50%, #B2182B)';
    barWrapper.appendChild(bar);
    container.appendChild(barWrapper);

    const range = rangeOverride || (mode ? state.comparisonDiffRanges[mode] : null);
    const hasRange = range && Number.isFinite(range.min) && Number.isFinite(range.max);

    function formatRangeValue(val) {
      const absVal = Math.abs(val);
      if (absVal >= 10000) return val.toFixed(0);
      if (absVal >= 100) return val.toFixed(1);
      if (absVal >= 1) return val.toFixed(2);
      return val.toFixed(3);
    }

    const labels = document.createElement('div');
    labels.className = 'gl-legend-continuous__labels';
    labels.style.justifyContent = 'space-between';

    const leftLabel = document.createElement('span');
    leftLabel.textContent = hasRange ? formatRangeValue(range.min) : 'Scenario > Base';
    leftLabel.style.color = '#2166AC';

    const centerLabel = document.createElement('span');
    centerLabel.textContent = '0';
    centerLabel.style.color = 'var(--gl-text-secondary, #8fa0c2)';

    const rightLabel = document.createElement('span');
    rightLabel.textContent = hasRange ? `+${formatRangeValue(range.max)}` : 'Base > Scenario';
    rightLabel.style.color = '#B2182B';

    labels.appendChild(leftLabel);
    labels.appendChild(centerLabel);
    labels.appendChild(rightLabel);
    container.appendChild(labels);

    if (unit) {
      const unitEl = document.createElement('div');
      unitEl.className = 'gl-legend-continuous__unit';
      unitEl.textContent = `Difference (${unit})`;
      container.appendChild(unitEl);
    }

    if (label) {
      const labelEl = document.createElement('div');
      labelEl.style.cssText =
        'font-size:0.7rem;color:var(--gl-text-secondary, #8fa0c2);margin-top:4px;text-align:center;';
      labelEl.textContent = label;
      container.appendChild(labelEl);
    }

    return container;
  }

  function renderAspectLegend() {
    const directions = [
      { label: 'N (0°)', degrees: 0 },
      { label: 'NE (45°)', degrees: 45 },
      { label: 'E (90°)', degrees: 90 },
      { label: 'SE (135°)', degrees: 135 },
      { label: 'S (180°)', degrees: 180 },
      { label: 'SW (225°)', degrees: 225 },
      { label: 'W (270°)', degrees: 270 },
      { label: 'NW (315°)', degrees: 315 },
    ];

    function aspectToRgb(degrees) {
      const hue = degrees % 360;
      const h = hue / 60;
      const c = 200;
      const x = c * (1 - Math.abs((h % 2) - 1));
      let r;
      let g;
      let b;
      if (h < 1) { r = c; g = x; b = 0; }
      else if (h < 2) { r = x; g = c; b = 0; }
      else if (h < 3) { r = 0; g = c; b = x; }
      else if (h < 4) { r = 0; g = x; b = c; }
      else if (h < 5) { r = x; g = 0; b = c; }
      else { r = c; g = 0; b = x; }
      return `rgb(${Math.round(r + 55)}, ${Math.round(g + 55)}, ${Math.round(b + 55)})`;
    }

    const items = directions.map((d) => ({
      label: d.label,
      color: aspectToRgb(d.degrees),
    }));

    return renderCategoricalLegend(items);
  }

  function renderLegendForLayer(layer, state) {
    const section = document.createElement('div');
    section.className = 'gl-legend-section';

    const title = document.createElement('h5');
    title.className = 'gl-legend-section__title';
    title.textContent = layer.label || layer.key;
    section.appendChild(title);

    const mode = layer.mode || '';
    const diffRangeOverride = layer.category === 'WEPP Yearly' ? state.weppYearlyDiffRanges[mode] : null;
    const divergingMode = diffRangeOverride ? mode : layer.category === 'WEPP Yearly' ? null : mode;
    if (state.comparisonMode && COMPARISON_MEASURES.includes(mode) && state.currentScenarioPath) {
      const unit = LAYER_UNITS[mode] || '';
      section.appendChild(renderDivergingLegend(unit, 'Base − Scenario', divergingMode, diffRangeOverride, state));
      return section;
    }

    if (mode === 'dominant' && layer.category === 'Landuse') {
      const classMap = getUsedLanduseClasses(state);
      const items = [];
      for (const [key, info] of classMap.entries()) {
        const colorCss = info.color || '#888888';
        items.push({ color: colorCss, label: info.desc || `Class ${key}` });
      }
      if (items.length) {
        section.appendChild(renderCategoricalLegend(items));
      }
      return section;
    }

    if (mode === 'dominant' && layer.category === 'Soils') {
      const classMap = getUsedSoilsClasses(state);
      const items = [];
      for (const [mukey, info] of classMap.entries()) {
        const colorCss = info.color || '#888888';
        items.push({ color: colorCss, label: info.desc || mukey });
      }
      if (items.length) {
        section.appendChild(renderCategoricalLegend(items));
      }
      return section;
    }

    if (layer.key === 'landuse' && layer.category === 'Raster') {
      const nlcdItems = getUsedNlcdClasses(layer);
      if (nlcdItems.length) {
        section.appendChild(renderCategoricalLegend(nlcdItems));
      } else {
        const note = document.createElement('p');
        note.style.cssText = 'font-size:0.75rem;color:#8fa0c2;margin:0;';
        note.textContent = 'NLCD land cover classes';
        section.appendChild(note);
      }
      return section;
    }

    if (layer.key === 'soils' && layer.category === 'Raster') {
      const soilItems = getUsedSoilClasses(layer);
      if (soilItems.length) {
        section.appendChild(renderCategoricalLegend(soilItems));
      } else {
        const note = document.createElement('p');
        note.style.cssText = 'font-size:0.75rem;color:#8fa0c2;margin:0;';
        note.textContent = 'SSURGO soil types';
        section.appendChild(note);
      }
      return section;
    }

    if (layer.key === 'sbs') {
      section.appendChild(renderCategoricalLegend(SBS_CLASSES));
      return section;
    }

    let minVal = 0;
    let maxVal = 100;
    let unit = LAYER_UNITS[mode] || '';

    if (['cancov', 'inrcov', 'rilcov'].includes(mode)) {
      minVal = 0;
      maxVal = 100;
      unit = '%';
    } else if (['clay', 'sand', 'rock'].includes(mode) && state.soilsSummary) {
      minVal = 0;
      maxVal = 100;
      unit = '%';
    } else if (mode === 'bd' && state.soilsSummary) {
      minVal = 0.5;
      maxVal = 2.0;
      unit = 'g/cm³';
    } else if (mode === 'soil_depth' && state.soilsSummary) {
      minVal = 0;
      maxVal = 2000;
      unit = 'mm';
    } else if (mode === 'slope_scalar' && state.hillslopesSummary) {
      minVal = 0;
      maxVal = 100;
      unit = '%';
    } else if (mode === 'length' && state.hillslopesSummary) {
      minVal = 0;
      maxVal = 1000;
      unit = 'm';
    } else if (mode === 'aspect' && state.hillslopesSummary) {
      section.appendChild(renderAspectLegend());
      return section;
    } else if (state.watarRanges && state.watarRanges[mode]) {
      minVal = state.watarRanges[mode].min;
      maxVal = state.watarRanges[mode].max;
    } else if (state.weppRanges && state.weppRanges[mode]) {
      minVal = state.weppRanges[mode].min;
      maxVal = state.weppRanges[mode].max;
    } else if (state.weppYearlyRanges && state.weppYearlyRanges[mode]) {
      minVal = state.weppYearlyRanges[mode].min;
      maxVal = state.weppYearlyRanges[mode].max;
    } else if (state.weppEventRanges && state.weppEventRanges[mode]) {
      minVal = state.weppEventRanges[mode].min;
      maxVal = state.weppEventRanges[mode].max;
      unit = LAYER_UNITS[mode] || '';
    } else if (layer.isCumulative) {
      minVal = 0;
      maxVal = 100;
      unit = '%';
    } else if (layer.bandKey && state.rapSummary) {
      minVal = 0;
      maxVal = 100;
      unit = '%';
    }

    const colormap = resolveColormapName(mode, layer.category, { WATER_MEASURES, SOIL_MEASURES });

    section.appendChild(renderContinuousLegend(minVal, maxVal, unit, colormap));
    return section;
  }

  function updateLegendsPanel() {
    const contentEl = legendsContentEl || document.getElementById('gl-legends-content');
    const emptyEl = legendEmptyEl || document.getElementById('gl-legend-empty');
    if (!contentEl) return;

    const state = getState();
    const activeLayers = layerUtils.getActiveLayersForLegend();

    const children = Array.from(contentEl.children);
    for (const child of children) {
      if (child.id !== 'gl-legend-empty') {
        child.remove();
      }
    }

    if (!activeLayers.length) {
      if (emptyEl) emptyEl.style.display = '';
      return;
    }

    if (emptyEl) emptyEl.style.display = 'none';

    for (const layer of activeLayers) {
      const legendSection = renderLegendForLayer(layer, state);
      contentEl.appendChild(legendSection);
    }
  }

  return {
    updateLayerList,
    updateLegendsPanel,
  };
}
