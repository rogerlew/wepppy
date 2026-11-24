/**
 * Sidebar layer list and legend rendering for gl-dashboard.
 * DOM-only: receives callbacks/state setters to trigger data/deck updates.
 */

import { createLegendsPanel } from './legends.js';
import { buildLayerSections } from './layer-sections.js';
import { renderRusleTolerance } from './rusle-tolerance.js';

export function createLayerRenderer({
  getState,
  setValue,
  layerUtils,
  domRefs,
  yearSlider,
  deselectAllSubcatchmentOverlays,
  activateWeppYearlyLayer,
  activateWeppYearlyChannelLayer,
  refreshWeppStatisticData,
  refreshRapData,
  refreshOpenetData,
  refreshWeppEventData,
  loadRapTimeseriesData,
  loadWeppYearlyTimeseriesData,
  loadOpenetTimeseriesData,
  applyLayers,
  syncGraphLayout,
  clearGraphModeOverride,
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

  const CHANNEL_GROUP_KEYS = ['channelsLayers', 'weppChannelLayers', 'weppYearlyChannelLayers'];
  const layerSectionOpen = new Set();

  const updateLegendsPanel = createLegendsPanel({
    getState, setValue, layerUtils, legendsContentEl, legendEmptyEl, soilColorForValue, constants, applyLayers,
  });

  function resetChannelGroups(exceptKey) {
    CHANNEL_GROUP_KEYS.forEach((key) => {
      if (key === exceptKey) return;
      const overlays = (getState()[key] || []).map((overlay) => ({
        ...overlay,
        visible: false,
      }));
      setValue(key, overlays);
    });
  }

  function setLayerLabelContent(label, { name, path, nameFontSize }) {
    const nameSpan = document.createElement('span');
    nameSpan.className = 'gl-layer-name';
    nameSpan.textContent = name;
    if (nameFontSize) {
      nameSpan.style.fontSize = nameFontSize;
    }
    label.replaceChildren(nameSpan);
    const pathText = String(path || '').trim();
    if (pathText) {
      label.title = pathText;
    } else {
      label.removeAttribute('title');
    }
  }

  function renderRapSection(details, section) {
    const state = getState();
    const rapDatasetPath =
      Array.isArray(section.items) && section.items.length
        ? String(section.items[0].path || '').trim()
        : '';
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
      deselectAllSubcatchmentOverlays({ skipUpdate: true });
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
      updateLayerList();
    });
    const cumulativeLabel = document.createElement('label');
    cumulativeLabel.setAttribute('for', 'layer-RAP-cumulative');
    cumulativeLabel.innerHTML = '<span class="gl-layer-name">Cumulative Cover</span>';
    if (rapDatasetPath) {
      cumulativeLabel.title = rapDatasetPath;
    }
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
      const bandPath = String(layer.path || '').trim() || rapDatasetPath;
      setLayerLabelContent(label, { name, path: bandPath, nameFontSize: '0.85rem' });
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
    // Date input block
    const dateBlock = document.createElement('div');
    dateBlock.className = 'gl-wepp-event-date-row';
    const dateLabel = document.createElement('label');
    dateLabel.textContent = 'Event Date:';
    dateLabel.className = 'gl-wepp-event-date-label';
    const dateInput = document.createElement('input');
    dateInput.type = 'date';
    dateInput.id = 'gl-wepp-event-date';
    dateInput.className = 'gl-wepp-event-date-input gl-custom-select__trigger';
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
    dateBlock.appendChild(dateLabel);
    dateBlock.appendChild(dateInput);
    details.appendChild(dateBlock);

    const parseIsoDate = (value) => {
      if (!value) return null;
      const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
      if (!match) return null;
      return {
        year: Number(match[1]),
        month: Number(match[2]),
        day: Number(match[3]),
      };
    };

    const formatIsoDate = (year, month, day) =>
      `${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

    const clampDate = (date, minDate, maxDate) => {
      if (minDate && date < minDate) return minDate;
      if (maxDate && date > maxDate) return maxDate;
      return date;
    };

    const resolveBaseParts = () => {
      const current = parseIsoDate(dateInput.value);
      if (current) return current;
      const minParts = parseIsoDate(dateInput.min);
      if (minParts) return minParts;
      const maxParts = parseIsoDate(dateInput.max);
      if (maxParts) return maxParts;
      const now = new Date();
      return { year: now.getUTCFullYear(), month: now.getUTCMonth() + 1, day: now.getUTCDate() };
    };

    const stepWeppEventDate = ({ days = 0, months = 0, years = 0 }) => {
      const base = resolveBaseParts();
      const baseMonthIndex = base.month - 1;
      let totalMonths = base.year * 12 + baseMonthIndex + months + years * 12;
      let targetYear = Math.floor(totalMonths / 12);
      let targetMonthIndex = totalMonths % 12;
      if (targetMonthIndex < 0) {
        targetMonthIndex += 12;
        targetYear -= 1;
      }
      const lastDay = new Date(Date.UTC(targetYear, targetMonthIndex + 1, 0)).getUTCDate();
      const targetDay = Math.min(base.day, lastDay);
      let nextDate = new Date(Date.UTC(targetYear, targetMonthIndex, targetDay));
      if (days) {
        nextDate = new Date(Date.UTC(
          nextDate.getUTCFullYear(),
          nextDate.getUTCMonth(),
          nextDate.getUTCDate() + days,
        ));
      }
      const minDate = dateInput.min ? new Date(`${dateInput.min}T00:00:00Z`) : null;
      const maxDate = dateInput.max ? new Date(`${dateInput.max}T00:00:00Z`) : null;
      const clamped = clampDate(nextDate, minDate, maxDate);
      return formatIsoDate(clamped.getUTCFullYear(), clamped.getUTCMonth() + 1, clamped.getUTCDate());
    };

    const quickControls = document.createElement('div');
    quickControls.className = 'gl-wepp-event-controls';
    const controls = [
      { label: '- Y', years: -1 },
      { label: '- M', months: -1 },
      { label: '- D', days: -1 },
      { label: '+ D', days: 1 },
      { label: '+ M', months: 1 },
      { label: '+ Y', years: 1 },
    ];
    controls.forEach(({ label, ...delta }) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'gl-wepp-event-control-btn';
      btn.textContent = label;
      btn.addEventListener('click', () => {
        const nextValue = stepWeppEventDate(delta);
        if (!nextValue) return;
        dateInput.value = nextValue;
        dateInput.dispatchEvent(new Event('change', { bubbles: true }));
      });
      quickControls.appendChild(btn);
    });
    details.appendChild(quickControls);

    // Separator
    const separator = document.createElement('div');
    separator.className = 'gl-wepp-event-separator';
    details.appendChild(separator);

    const itemList = document.createElement('ul');
    itemList.className = 'gl-layer-items';

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
        deselectAllSubcatchmentOverlays({ skipUpdate: true });
        const nextLayers = (getState().weppEventLayers || []).map((overlay) => ({
          ...overlay,
          visible: overlay.key === layer.key,
        }));
        setValue('weppEventLayers', nextLayers);
        input.checked = true;
        setGraphFocus(false);
        if (getState().weppEventSelectedDate) {
          await refreshWeppEventData();
        }
        applyLayers();
        updateLayerList();
      });
      const label = document.createElement('label');
      label.setAttribute('for', input.id);
      const name = layer.label || layer.key;
      const path = layer.path || '';
      setLayerLabelContent(label, { name, path });
      li.appendChild(input);
      li.appendChild(label);
      itemList.appendChild(li);
    });

    details.appendChild(itemList);
  }

  function renderChannelItems(details, section) {
    const refresh = section.isWeppYearly ? activateWeppYearlyChannelLayer : refreshWeppStatisticData;
    const subheading = document.createElement('div');
    subheading.textContent = 'Channels';
    subheading.style.cssText =
      'margin:0.5rem 0 0.25rem 0;font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;color:var(--wc-color-text-muted);';
    details.appendChild(subheading);

    const channelList = document.createElement('ul');
    channelList.className = 'gl-layer-items';
    const channelStateKey = section.channelStateKey;

    section.channelItems.forEach((layer) => {
      const li = document.createElement('li');
      li.className = 'gl-layer-item';
      const input = document.createElement('input');
      input.type = 'radio';
      input.name = 'wepp-channel-overlay';
      input.checked = layer.visible;
      input.id = `layer-${section.idPrefix || section.title}-Channel-${layer.key}`;
      input.addEventListener('change', async () => {
        if (!input.checked) return;
        if (channelStateKey) {
          const overlays = (getState()[channelStateKey] || []).map((overlay) => ({
            ...overlay,
            visible: overlay.key === layer.key,
          }));
          setValue(channelStateKey, overlays);
        } else {
          layer.visible = true;
        }
        resetChannelGroups(channelStateKey);
        input.checked = true;
        if (typeof refresh === 'function') {
          await refresh();
        }
        applyLayers();
        updateLayerList();
      });
      const label = document.createElement('label');
      label.setAttribute('for', input.id);
      const name = layer.label || layer.key;
      const path = layer.path || '';
      setLayerLabelContent(label, { name, path });
      li.appendChild(input);
      li.appendChild(label);
      channelList.appendChild(li);
    });

    details.appendChild(channelList);
  }

  function renderLayerItems(details, section) {
    const itemList = document.createElement('ul');
    itemList.className = 'gl-layer-items';

    section.items.forEach((layer) => {
      const li = document.createElement('li');
      li.className = 'gl-layer-item';
      const input = document.createElement('input');
      const isRaster = layer.isRaster === true;
      const hasRadioGroup = !!(section.radioGroupName && !isRaster);
      if (section.isSubcatchment && !isRaster) {
        input.type = 'radio';
        input.name = 'subcatchment-overlay';
      } else if (hasRadioGroup) {
        input.type = 'radio';
        input.name = section.radioGroupName;
      } else {
        input.type = 'checkbox';
      }
      input.checked = layer.visible;
      const idPrefix = section.idPrefix || section.title;
      input.id = `layer-${idPrefix}-${layer.key}`;
      const stateKey = section.stateKey;
      const selectSubcatchmentLayer = async () => {
        deselectAllSubcatchmentOverlays({ skipApply: true, skipUpdate: true });
        if (stateKey) {
          const overlays = (getState()[stateKey] || []).map((overlay) => ({
            ...overlay,
            visible: overlay.key === layer.key,
          }));
          setValue(stateKey, overlays);
        } else {
          layer.visible = true;
        }
        input.checked = true;
        if (section.isWeppYearly) {
          await activateWeppYearlyLayer();
        }
      };
      input.addEventListener('change', async () => {
        if (section.isSubcatchment && !isRaster) {
          await selectSubcatchmentLayer();
          if (section.isOpenet && layer.datasetKey) {
            setValue('openetSelectedDatasetKey', layer.datasetKey);
            if (typeof refreshOpenetData === 'function') {
              await refreshOpenetData();
              updateLegendsPanel();
            }
          }
          if (section.isOpenet && getState().activeGraphKey === 'wepp-yearly') {
            setValue('activeGraphKey', null);
          }
        } else if (hasRadioGroup) {
          if (!input.checked) return;
          if (stateKey) {
            const overlays = (getState()[stateKey] || []).map((overlay) => ({
              ...overlay,
              visible: overlay.key === layer.key,
            }));
            setValue(stateKey, overlays);
          } else {
            layer.visible = true;
          }
          if (section.isChannels) {
            setValue('channelsVisible', true);
            resetChannelGroups(stateKey);
          }
          input.checked = true;
        } else {
          const target = layer.rasterRef || layer;
          target.visible = input.checked;
          layer.visible = input.checked;
        }
        applyLayers();
        syncGraphLayout && syncGraphLayout();
        updateLayerList();
        if (section.isSubcatchment && !section.isRap && !section.isWeppYearly && !section.isOpenet) {
          clearGraphModeOverride && clearGraphModeOverride();
          setValue('activeGraphKey', null);
          setGraphFocus(false, { force: true, skipModeSync: true });
          setGraphCollapsed(true, { focusOnExpand: false });
          syncGraphLayout && syncGraphLayout();
          return;
        }
        const graphEl = document.getElementById('gl-graph');
        const graphVisible = graphEl && !graphEl.classList.contains('is-collapsed');
        if (section.isWeppYearly && layer.visible) {
          await loadWeppYearlyTimeseriesData();
        } else if (section.isOpenet && layer.visible) {
          await loadOpenetTimeseriesData();
        } else if (
          graphVisible &&
          !section.isSubcatchment &&
          (getState().rapCumulativeMode || getState().rapLayers.some((l) => l.visible))
        ) {
          await loadRapTimeseriesData();
        }
      });
      const label = document.createElement('label');
      label.setAttribute('for', input.id);
      const name = layer.label || layer.key;
      const path = layer.path || '';
      setLayerLabelContent(label, { name, path });
      li.appendChild(input);
      li.appendChild(label);
      itemList.appendChild(li);
    });

    details.appendChild(itemList);
  }

  function renderWeppStatistic(details, weppStatistic) {
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
        // Read current state value, don't use captured weppStatistic from closure
        const currentStat = getState().weppStatistic;
        if (nextStat === currentStat) return;
        setValue('weppStatistic', nextStat);
        await refreshWeppStatisticData();
      });
    });
    details.appendChild(statWrapper);
  }

  function updateLayerList() {
    if (!layerListEl) return;
    layerListEl.querySelectorAll('details.gl-layer-details').forEach((detailsEl) => {
      if (!detailsEl.open) return;
      const summary = detailsEl.querySelector('summary');
      const title = summary && summary.textContent ? summary.textContent.trim() : '';
      if (title) {
        layerSectionOpen.add(title);
      }
    });
    const state = getState();
    const { rapCumulativeMode, weppStatistic } = state;
    layerListEl.innerHTML = '';
    const sections = buildLayerSections(state);
    if (!sections.length) {
      if (layerEmptyEl) {
        layerEmptyEl.hidden = false;
      }
      return;
    }
    if (layerEmptyEl) {
      layerEmptyEl.hidden = true;
    }
    const groupHeader = document.createElement('li');
    groupHeader.className = 'gl-layer-group-header';
    groupHeader.textContent = 'Subcatchment Overlays';
    layerListEl.appendChild(groupHeader);
    sections.forEach((section, idx) => {
      const details = document.createElement('details');
      details.className = 'gl-layer-details';
      const hasVisibleItem =
        section.items.some((l) => l.visible) ||
        (Array.isArray(section.channelItems) && section.channelItems.some((l) => l.visible));
      details.open = layerSectionOpen.has(section.title) || idx === 0 || hasVisibleItem || (section.isRap && rapCumulativeMode);
      details.addEventListener('toggle', () => {
        if (details.open) {
          layerSectionOpen.add(section.title);
        } else {
          layerSectionOpen.delete(section.title);
        }
      });

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
        renderWeppStatistic(details, weppStatistic);
      }
      if (section.title === 'RUSLE') {
        renderRusleTolerance(details, section.items, state, { setValue, applyLayers, updateLegendsPanel });
      }

      renderLayerItems(details, section);
      if (Array.isArray(section.channelItems) && section.channelItems.length) {
        renderChannelItems(details, section);
      }

      layerListEl.appendChild(details);
    });
  }

  return {
    updateLayerList,
    updateLegendsPanel,
  };
}
