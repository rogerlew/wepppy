/* PARAMETERS: tune appearance and performance of the diff viewer here */
const DiffViewerParameters = Object.freeze({
  ROW_HEIGHT: 20, // px, keep in sync with --diff-row-height
  FONT_SIZE: 14, // px for diff content
  LINE_NUMBER_WIDTH: 64, // px for line number gutter
  DIGIT_PIXEL_WIDTH: 8, // px estimate per digit for dynamic gutter sizing
  OVERSCAN_ROWS: 160, // extra rows to render above/below viewport
  TOKEN_BOUNDARY_REGEX: /(\s+|[,:;=(){}\[\]\|])/, // tokenizer for per-line highlights
  TOKEN_DIFF_MAX_LENGTH: 6000, // skip token diff if combined line length exceeds this
  TAB_REPLACEMENT: '    ', // replace tabs with spaces for consistent layout
  CHAR_PIXEL_WIDTH: 7.1, // estimated monospace char width in px for width hints
  LEFT_COLUMN_MIN_CHARS: 80,
  RIGHT_COLUMN_MIN_CHARS: 80,
  MAX_COLUMN_WIDTH_CHARS: 140,
  COLUMN_PADDING_PX: 32,
  PANE_GAP_PX: 48,
  FETCH_TIMEOUT_MS: 20000 // abort fetch after this many milliseconds
});

const DiffViewer = (() => {
  const escapeMap = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  };

  const defaultEquals = (a, b) => a === b;
  const tabRegex = /\t/g;

  function escapeHtml(str) {
    return str.replace(/[&<>"']/g, (char) => escapeMap[char]);
  }

  function normaliseText(raw) {
    if (!raw) {
      return [];
    }
    const normalised = raw.replace(/\r\n?/g, '\n');
    const parts = normalised.split('\n');
    if (parts.length && parts[parts.length - 1] === '') {
      parts.pop();
    }
    return parts.map((line) => {
      if (DiffViewerParameters.TAB_REPLACEMENT) {
        return line.replace(tabRegex, DiffViewerParameters.TAB_REPLACEMENT);
      }
      return line;
    });
  }

  function diffCore(a, b, equals = defaultEquals) {
    const n = a.length;
    const m = b.length;
    const max = n + m;
    if (max === 0) {
      return [];
    }
    const v = new Map();
    v.set(1, 0);
    const trace = [];

    for (let d = 0; d <= max; d++) {
      const current = new Map();
      for (let k = -d; k <= d; k += 2) {
        const left = v.has(k - 1) ? v.get(k - 1) : -1;
        const right = v.has(k + 1) ? v.get(k + 1) : -1;
        let x;
        if (k === -d || (k !== d && left < right)) {
          x = right;
        } else {
          x = left + 1;
        }
        let y = x - k;
        while (x < n && y < m && equals(a[x], b[y])) {
          x += 1;
          y += 1;
        }
        current.set(k, x);
        if (x >= n && y >= m) {
          trace.push(current);
          return backtrack(trace, a, b);
        }
      }
      trace.push(current);
      v.clear();
      current.forEach((value, key) => {
        v.set(key, value);
      });
    }
    return [];
  }

  function backtrack(trace, a, b) {
    let x = a.length;
    let y = b.length;
    const moves = [];

    for (let d = trace.length - 1; d >= 0; d--) {
      const k = x - y;
      let prevK;
      if (d === 0) {
        prevK = 0;
      } else {
        const prev = trace[d - 1];
        const left = prev.has(k - 1) ? prev.get(k - 1) : Number.NEGATIVE_INFINITY;
        const right = prev.has(k + 1) ? prev.get(k + 1) : Number.NEGATIVE_INFINITY;
        if (k === -d || (k !== d && left < right)) {
          prevK = k + 1;
        } else {
          prevK = k - 1;
        }
      }

      const prevMap = d === 0 ? null : trace[d - 1];
      const prevX = d === 0 ? 0 : (prevMap.has(prevK) ? prevMap.get(prevK) : 0);
      const prevY = prevX - prevK;

      while (x > prevX && y > prevY) {
        moves.push('equal');
        x -= 1;
        y -= 1;
      }

      if (d === 0) {
        break;
      }

      if (x === prevX) {
        moves.push('insert');
        y -= 1;
      } else {
        moves.push('delete');
        x -= 1;
      }
    }

    moves.reverse();
    return compressMoves(moves);
  }

  function compressMoves(moves) {
    if (!moves.length) {
      return [];
    }
    const result = [];
    let currentType = moves[0];
    let count = 1;
    for (let i = 1; i < moves.length; i++) {
      const type = moves[i];
      if (type === currentType) {
        count += 1;
      } else {
        result.push({ type: currentType, length: count });
        currentType = type;
        count = 1;
      }
    }
    result.push({ type: currentType, length: count });
    return result;
  }

  function buildRows(leftLines, rightLines) {
    const operations = diffCore(leftLines, rightLines, defaultEquals);
    const rows = [];
    let leftIndex = 0;
    let rightIndex = 0;
    let leftBuffer = [];
    let rightBuffer = [];

    const flushBuffers = () => {
      const max = Math.max(leftBuffer.length, rightBuffer.length);
      for (let i = 0; i < max; i++) {
        const leftItem = leftBuffer[i] || null;
        const rightItem = rightBuffer[i] || null;
        const type = leftItem && rightItem ? 'replace' : leftItem ? 'delete' : 'insert';
        rows.push({
          type,
          leftNumber: leftItem ? leftItem.number : null,
          rightNumber: rightItem ? rightItem.number : null,
          leftText: leftItem ? leftItem.text : '',
          rightText: rightItem ? rightItem.text : '',
          leftLength: leftItem ? leftItem.text.length : 0,
          rightLength: rightItem ? rightItem.text.length : 0
        });
      }
      leftBuffer = [];
      rightBuffer = [];
    };

    for (const op of operations) {
      if (op.type === 'equal') {
        flushBuffers();
        for (let i = 0; i < op.length; i++) {
          const leftText = leftLines[leftIndex];
          const rightText = rightLines[rightIndex];
          rows.push({
            type: 'equal',
            leftNumber: leftIndex + 1,
            rightNumber: rightIndex + 1,
            leftText,
            rightText,
            leftLength: leftText.length,
            rightLength: rightText.length
          });
          leftIndex += 1;
          rightIndex += 1;
        }
      } else if (op.type === 'delete') {
        for (let i = 0; i < op.length; i++) {
          leftBuffer.push({
            number: leftIndex + 1,
            text: leftLines[leftIndex]
          });
          leftIndex += 1;
        }
      } else if (op.type === 'insert') {
        for (let i = 0; i < op.length; i++) {
          rightBuffer.push({
            number: rightIndex + 1,
            text: rightLines[rightIndex]
          });
          rightIndex += 1;
        }
      }
    }
    flushBuffers();
    return rows;
  }

  function tokenize(line) {
    if (!line) {
      return [];
    }
    const tokens = line.split(DiffViewerParameters.TOKEN_BOUNDARY_REGEX);
    if (tokens.length === 1 && tokens[0] === '') {
      return [];
    }
    return tokens.filter((token) => token !== '');
  }

  function highlightTokens(leftText, rightText) {
    if (leftText === rightText) {
      const safe = escapeHtml(leftText);
      return { leftHtml: safe, rightHtml: safe };
    }
    const totalLength = leftText.length + rightText.length;
    if (totalLength > DiffViewerParameters.TOKEN_DIFF_MAX_LENGTH) {
      return {
        leftHtml: `<span class="diff-token-delete">${escapeHtml(leftText)}</span>`,
        rightHtml: `<span class="diff-token-insert">${escapeHtml(rightText)}</span>`
      };
    }
    const leftTokens = tokenize(leftText);
    const rightTokens = tokenize(rightText);
    const operations = diffCore(leftTokens, rightTokens, defaultEquals);
    const leftParts = [];
    const rightParts = [];
    let leftIdx = 0;
    let rightIdx = 0;

    for (const op of operations) {
      if (op.type === 'equal') {
        for (let i = 0; i < op.length; i++) {
          const token = leftTokens[leftIdx];
          const escaped = escapeHtml(token);
          leftParts.push(escaped);
          rightParts.push(escaped);
          leftIdx += 1;
          rightIdx += 1;
        }
      } else if (op.type === 'delete') {
        let segment = '';
        for (let i = 0; i < op.length; i++) {
          segment += leftTokens[leftIdx];
          leftIdx += 1;
        }
        if (segment) {
          leftParts.push(`<span class="diff-token-delete">${escapeHtml(segment)}</span>`);
        }
      } else if (op.type === 'insert') {
        let segment = '';
        for (let i = 0; i < op.length; i++) {
          segment += rightTokens[rightIdx];
          rightIdx += 1;
        }
        if (segment) {
          rightParts.push(`<span class="diff-token-insert">${escapeHtml(segment)}</span>`);
        }
      }
    }

    if (leftIdx < leftTokens.length) {
      leftParts.push(`<span class="diff-token-delete">${escapeHtml(leftTokens.slice(leftIdx).join(''))}</span>`);
    }
    if (rightIdx < rightTokens.length) {
      rightParts.push(`<span class="diff-token-insert">${escapeHtml(rightTokens.slice(rightIdx).join(''))}</span>`);
    }

    return {
      leftHtml: leftParts.join(''),
      rightHtml: rightParts.join('')
    };
  }

  function decorateRows(rows) {
    for (const row of rows) {
      if (row.type === 'equal') {
        const safe = escapeHtml(row.leftText);
        row.leftHtml = safe;
        row.rightHtml = safe;
      } else if (row.type === 'delete') {
        row.leftHtml = escapeHtml(row.leftText);
        row.rightHtml = '';
      } else if (row.type === 'insert') {
        row.leftHtml = '';
        row.rightHtml = escapeHtml(row.rightText);
      } else if (row.type === 'replace') {
        const highlighted = highlightTokens(row.leftText, row.rightText);
        row.leftHtml = highlighted.leftHtml;
        row.rightHtml = highlighted.rightHtml;
      }
    }
    return rows;
  }

  function createRowElement(row, index) {
    const rowElement = document.createElement('div');
    let className = 'diff-row';
    if (row.type !== 'equal') {
      className += ` diff-row--${row.type}`;
    }
    rowElement.className = className;
    rowElement.dataset.rowType = row.type;
    rowElement.dataset.rowIndex = String(index);
    const leftNumber = row.leftNumber !== null ? row.leftNumber : '&nbsp;';
    const rightNumber = row.rightNumber !== null ? row.rightNumber : '&nbsp;';
    rowElement.innerHTML = `
      <div class="diff-line-number" data-side="left">${leftNumber}</div>
      <div class="diff-line-content" data-side="left"><div class="diff-line-content-inner">${row.leftHtml || ''}</div></div>
      <div class="diff-line-number" data-side="right">${rightNumber}</div>
      <div class="diff-line-content" data-side="right"><div class="diff-line-content-inner">${row.rightHtml || ''}</div></div>
    `;
    return rowElement;
  }

  function applyColumnWidthHints(rows, viewport) {
    let leftMax = 0;
    let rightMax = 0;
    for (const row of rows) {
      if (row.leftLength) {
        leftMax = Math.max(leftMax, row.leftLength);
      }
      if (row.rightLength) {
        rightMax = Math.max(rightMax, row.rightLength);
      }
    }

    const estimateWidth = (chars, minChars) => {
      const clamped = Math.min(
        DiffViewerParameters.MAX_COLUMN_WIDTH_CHARS,
        Math.max(minChars, chars)
      );
      return Math.round(clamped * DiffViewerParameters.CHAR_PIXEL_WIDTH + DiffViewerParameters.COLUMN_PADDING_PX);
    };

    const leftEstimate = estimateWidth(leftMax, DiffViewerParameters.LEFT_COLUMN_MIN_CHARS);
    const rightEstimate = estimateWidth(rightMax, DiffViewerParameters.RIGHT_COLUMN_MIN_CHARS);
    const paneWidth = Math.max(leftEstimate, rightEstimate);

    const computedStyles = getComputedStyle(document.documentElement);
    const lineNumberWidth = parseFloat(
      document.documentElement.style.getPropertyValue('--diff-line-number-width')
    ) || parseFloat(computedStyles.getPropertyValue('--diff-line-number-width')) || DiffViewerParameters.LINE_NUMBER_WIDTH;

    const viewportWidth = viewport?.clientWidth || window.innerWidth || 0;
    const halfViewport = viewportWidth > 0
      ? Math.max(240, Math.floor((viewportWidth - (2 * lineNumberWidth) - DiffViewerParameters.PANE_GAP_PX) / 2))
      : 0;

    const maxPanePx = DiffViewerParameters.MAX_COLUMN_WIDTH_CHARS * DiffViewerParameters.CHAR_PIXEL_WIDTH;
    const paneSize = Math.max(halfViewport, Math.min(paneWidth, maxPanePx));
    const totalWidth = paneSize * 2 + lineNumberWidth * 2 + DiffViewerParameters.PANE_GAP_PX;
    const minTotalWidth = viewportWidth > 0 ? Math.max(totalWidth, viewportWidth) : totalWidth;

    document.documentElement.style.setProperty('--diff-left-pane-width', `${paneSize}px`);
    document.documentElement.style.setProperty('--diff-right-pane-width', `${paneSize}px`);
    document.documentElement.style.setProperty('--diff-total-row-width', `${minTotalWidth}px`);
  }

  function applyLineNumberWidthHint(leftCount, rightCount) {
    const maxLines = Math.max(leftCount, rightCount, 1);
    const digits = String(maxLines).length;
    const width = Math.max(
      DiffViewerParameters.LINE_NUMBER_WIDTH,
      Math.round(digits * DiffViewerParameters.DIGIT_PIXEL_WIDTH + 24)
    );
    document.documentElement.style.setProperty('--diff-line-number-width', `${width}px`);
  }

  function applyFontSizing() {
    document.documentElement.style.setProperty('--diff-font-size', `${DiffViewerParameters.FONT_SIZE}px`);
    document.documentElement.style.setProperty('--diff-row-height', `${DiffViewerParameters.ROW_HEIGHT}px`);
  }

  function createRenderer(viewport, spacer, visibleLayer, initialRows, onRendered) {
    const state = {
      rows: initialRows,
      start: -1,
      end: -1,
      pendingFrame: null,
      rowHeight: DiffViewerParameters.ROW_HEIGHT
    };

    function updateSpacer() {
      const totalHeight = state.rows.length * state.rowHeight;
      spacer.style.height = `${totalHeight}px`;
    }

    let adjustHeightScheduled = false;

    function measureRowHeight() {
      if (adjustHeightScheduled) {
        return;
      }
      const sample = visibleLayer.firstElementChild;
      if (!sample) {
        return;
      }
      const measured = sample.getBoundingClientRect().height;
      if (!Number.isFinite(measured) || measured <= 0) {
        return;
      }
      if (Math.abs(measured - state.rowHeight) > 0.5) {
        adjustHeightScheduled = true;
        requestAnimationFrame(() => {
          state.rowHeight = measured;
          document.documentElement.style.setProperty('--diff-row-height', `${measured}px`);
          updateSpacer();
          adjustHeightScheduled = false;
          requestRender();
        });
      }
    }

    function renderRange() {
      state.pendingFrame = null;
      const { rowHeight } = state;
      const totalRows = state.rows.length;

      if (totalRows === 0) {
        visibleLayer.replaceChildren();
        visibleLayer.style.transform = 'translateY(0)';
        state.start = 0;
        state.end = 0;
        return;
      }

      const scrollTop = viewport.scrollTop;
      const viewportHeight = viewport.clientHeight || 0;

      let start = Math.max(0, Math.floor(scrollTop / rowHeight) - DiffViewerParameters.OVERSCAN_ROWS);
      let end = Math.min(
        totalRows,
        Math.ceil((scrollTop + viewportHeight) / rowHeight) + DiffViewerParameters.OVERSCAN_ROWS
      );

      if (totalRows <= DiffViewerParameters.OVERSCAN_ROWS * 2) {
        start = 0;
        end = totalRows;
      } else {
        if (start > totalRows - 1) {
          start = Math.max(0, totalRows - 1);
        }
        if (end < start + DiffViewerParameters.OVERSCAN_ROWS) {
          end = Math.min(totalRows, start + DiffViewerParameters.OVERSCAN_ROWS);
        }
      }

      if (start === state.start && end === state.end) {
        return;
      }

      state.start = start;
      state.end = end;

      const fragment = document.createDocumentFragment();
      for (let index = start; index < end; index++) {
        fragment.appendChild(createRowElement(state.rows[index], index));
      }
      visibleLayer.replaceChildren(fragment);
      visibleLayer.style.transform = `translateY(${start * rowHeight}px)`;
      measureRowHeight();
      if (typeof onRendered === 'function') {
        onRendered({ start, end, totalRows, rowHeight });
      }
    }

    function requestRender() {
      if (state.pendingFrame !== null) {
        return;
      }
      state.pendingFrame = requestAnimationFrame(renderRange);
    }

    updateSpacer();
    renderRange();

    const handleScroll = () => {
      requestRender();
    };
    const handleResize = () => {
      requestRender();
    };

    viewport.addEventListener('scroll', handleScroll, { passive: true });
    window.addEventListener('resize', handleResize);

    return {
      setRows(nextRows) {
        if (state.pendingFrame !== null) {
          cancelAnimationFrame(state.pendingFrame);
          state.pendingFrame = null;
        }
        state.rows = nextRows;
        state.start = -1;
        state.end = -1;
        updateSpacer();
        renderRange();
      },
      dispose() {
        if (state.pendingFrame !== null) {
          cancelAnimationFrame(state.pendingFrame);
        }
        viewport.removeEventListener('scroll', handleScroll);
        window.removeEventListener('resize', handleResize);
      }
    };
  }

  function setStatus(element, text, variant) {
    element.textContent = text;
    element.classList.remove('diff-status--loading', 'diff-status--match', 'diff-status--different');
    if (variant === 'match') {
      element.classList.add('diff-status--match');
    } else if (variant === 'different') {
      element.classList.add('diff-status--different');
    }
  }

  function setMetrics(container, metrics) {
    const leftSpan = container.querySelector('[data-role="left-lines"]');
    const rightSpan = container.querySelector('[data-role="right-lines"]');
    const changesSpan = container.querySelector('[data-role="changes-count"]');
    const displayedSpan = container.querySelector('[data-role="displayed-rows"]');
    if (leftSpan && typeof metrics.leftLines === 'number') {
      leftSpan.textContent = metrics.leftLines;
    }
    if (rightSpan && typeof metrics.rightLines === 'number') {
      rightSpan.textContent = metrics.rightLines;
    }
    if (changesSpan && typeof metrics.changedRows === 'number') {
      changesSpan.textContent = metrics.changedRows;
    }
    if (displayedSpan && typeof metrics.displayedRows === 'number') {
      displayedSpan.textContent = metrics.displayedRows;
    }
  }

  function setLoadingState(viewport, isLoading) {
    viewport.classList.toggle('diff-viewport--loading', isLoading);
  }

  async function fetchText(url, signal) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), DiffViewerParameters.FETCH_TIMEOUT_MS);
    try {
      const response = await fetch(url, {
        method: 'GET',
        credentials: 'same-origin',
        signal: combineSignals(signal, controller.signal),
        cache: 'no-store'
      });
      if (!response.ok) {
        throw new Error(`Request failed (${response.status})`);
      }
      const text = await response.text();
      return text;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  function combineSignals(external, internal) {
    if (!external) {
      return internal;
    }
    if (!internal) {
      return external;
    }
    if (typeof AbortController === 'undefined') {
      return internal;
    }
    const composite = new AbortController();

    if (external.aborted || internal.aborted) {
      composite.abort();
      return composite.signal;
    }

    const cleanup = () => {
      external.removeEventListener('abort', externalAbort);
      internal.removeEventListener('abort', internalAbort);
    };

    const abort = () => {
      if (!composite.signal.aborted) {
        composite.abort();
      }
    };

    const externalAbort = () => {
      cleanup();
      abort();
    };
    const internalAbort = () => {
      cleanup();
      abort();
    };

    external.addEventListener('abort', externalAbort);
    internal.addEventListener('abort', internalAbort);
    composite.signal.addEventListener('abort', cleanup, { once: true });

    return composite.signal;
  }

  function formatError(error) {
    if (error.name === 'AbortError') {
      return 'Request aborted while loading files.';
    }
    return error.message || 'Unexpected error while computing diff.';
  }

  async function init(bootstrap) {
    if (!bootstrap) {
      return;
    }
    applyFontSizing();

    const viewport = document.getElementById('diff-viewport');
    const spacer = document.getElementById('diff-spacer');
    const visibleLayer = document.getElementById('diff-visible-rows');
    const horizontal = document.getElementById('diff-horizontal');
    const statusEl = document.getElementById('diff-status');
    const metricsEl = document.getElementById('diff-metrics');
    const errorEl = document.getElementById('diff-error');
    const diffToggle = document.getElementById('diff-toggle-differences');
    const headerEl = document.querySelector('.diff-header');
    const toolbarEl = document.querySelector('.diff-toolbar');
    const rootStyle = document.documentElement.style;
    let pendingCentering = null;

    const scheduleCenter = () => {
      if (!horizontal) {
        return;
      }
      if (pendingCentering !== null) {
        cancelAnimationFrame(pendingCentering);
      }
      pendingCentering = requestAnimationFrame(() => {
        pendingCentering = null;
        horizontal.scrollLeft = 0;
      });
    };

    if (headerEl) {
      rootStyle.setProperty('--diff-header-height', `${headerEl.offsetHeight}px`);
    }
    if (toolbarEl) {
      rootStyle.setProperty('--diff-toolbar-height', `${toolbarEl.offsetHeight}px`);
    }

    const resizeObserver = typeof ResizeObserver !== 'undefined'
      ? new ResizeObserver((entries) => {
          for (const entry of entries) {
            if (entry.target === headerEl) {
              rootStyle.setProperty('--diff-header-height', `${entry.contentRect.height}px`);
            } else if (entry.target === toolbarEl) {
              rootStyle.setProperty('--diff-toolbar-height', `${entry.contentRect.height}px`);
            }
          }
        })
      : null;

    if (resizeObserver) {
      if (headerEl) {
        resizeObserver.observe(headerEl);
      }
      if (toolbarEl) {
        resizeObserver.observe(toolbarEl);
      }
    }

    setLoadingState(viewport, true);
    setStatus(statusEl, 'Loading…', 'loading');
    errorEl.classList.remove('diff-error--visible');
    errorEl.textContent = '';

    const abortController = new AbortController();

    try {
      const [leftText, rightText] = await Promise.all([
        fetchText(bootstrap.leftDownloadUrl, abortController.signal),
        fetchText(bootstrap.rightDownloadUrl, abortController.signal)
      ]);

      const leftLines = normaliseText(leftText);
      const rightLines = normaliseText(rightText);

      applyLineNumberWidthHint(leftLines.length, rightLines.length);

      const rawRows = buildRows(leftLines, rightLines);
      const decoratedRows = decorateRows(rawRows);

      applyColumnWidthHints(decoratedRows, viewport);

      const hasDifferences = decoratedRows.some((row) => row.type !== 'equal');
      const diffRows = decoratedRows.filter((row) => row.type !== 'equal');
      const baseMetrics = {
        leftLines: leftLines.length,
        rightLines: rightLines.length,
        changedRows: diffRows.length
      };

      setMetrics(metricsEl, { ...baseMetrics, displayedRows: decoratedRows.length });
      setStatus(statusEl, hasDifferences ? 'Differences detected' : 'All lines match', hasDifferences ? 'different' : 'match');

      const renderer = createRenderer(viewport, spacer, visibleLayer, decoratedRows, null);
      setLoadingState(viewport, false);

      const reflowColumns = () => {
        applyColumnWidthHints(decoratedRows, viewport);
        scheduleCenter();
      };
      window.addEventListener('resize', reflowColumns);

      scheduleCenter();

      if (diffToggle) {
        if (diffRows.length === 0) {
          diffToggle.disabled = true;
        }
        diffToggle.addEventListener('change', (event) => {
          const useDiffOnly = event.target.checked;
          if (useDiffOnly) {
            viewport.scrollTop = 0;
          }
          const nextRows = useDiffOnly ? diffRows : decoratedRows;
          applyColumnWidthHints(nextRows, viewport);
          renderer.setRows(nextRows);
          setMetrics(metricsEl, { ...baseMetrics, displayedRows: nextRows.length });
          scheduleCenter();
        });
      }

      return () => {
        renderer.dispose();
        window.removeEventListener('resize', reflowColumns);
        if (resizeObserver) {
          resizeObserver.disconnect();
        }
        if (pendingCentering !== null) {
          cancelAnimationFrame(pendingCentering);
        }
      };
    } catch (error) {
      setLoadingState(viewport, false);
      setStatus(statusEl, 'Failed to load diff', 'different');
      errorEl.textContent = formatError(error);
      errorEl.classList.add('diff-error--visible');
      console.error('Diff viewer error:', error);
      if (resizeObserver) {
        resizeObserver.disconnect();
      }
      if (pendingCentering !== null) {
        cancelAnimationFrame(pendingCentering);
      }
      return null;
    }
  }

  return { init };
})();

window.addEventListener('DOMContentLoaded', () => {
  if (window.DiffViewerBootstrap) {
    DiffViewer.init(window.DiffViewerBootstrap);
  }
});
