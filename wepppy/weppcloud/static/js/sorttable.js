/*
 * sorttable-lite: minimal modern table sorter
 * Inspired by Stuart Langridge's original sorttable.js (2007)
 * (http://www.kryogenix.org/code/browser/sorttable/). As with that project,
 * this implementation is released into the public domain – use it however you
 * like.
 *
 * Registers a MutationObserver + click listeners for tables with the `sortable`
 * class, supporting numeric, date, and textual sorts. Cells may provide
 * overrides via the `sorttable_customkey` attribute; headers may define
 * `data-sort-type` (numeric|date|text) and `data-sort-default` (asc|desc).
 */
(function () {
  "use strict";

  const SORTABLE_SELECTOR = 'table.sortable';
  const CUSTOM_KEY_ATTR = 'sorttable_customkey';
  const TYPE_DATA_ATTR = 'sortType';
  const DEFAULT_DIR_ATTR = 'sortDefault';

  const TYPE_NUMERIC = 'numeric';
  const TYPE_DATE = 'date';
  const TYPE_TEXT = 'text';

  const DATE_PATTERNS = [
    // ISO
    /^\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*$/,
    // MM/DD/YYYY or DD/MM/YYYY fallback handled later
    /^\s*(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{2,4})\s*$/
  ];

  const observer = new MutationObserver(handleMutations);
  document.addEventListener('DOMContentLoaded', init, { once: true });

  function init() {
    document.querySelectorAll(SORTABLE_SELECTOR).forEach(prepareTable);
    observer.observe(document.body, { childList: true, subtree: true });
  }

  function handleMutations(mutations) {
    for (const mutation of mutations) {
      mutation.addedNodes.forEach((node) => {
        if (!(node instanceof HTMLElement)) {
          return;
        }
        if (node.matches && node.matches(SORTABLE_SELECTOR)) {
          prepareTable(node);
        } else {
          node.querySelectorAll?.(SORTABLE_SELECTOR).forEach(prepareTable);
        }
      });
    }
  }

  function prepareTable(table) {
    const thead = table.tHead || table.querySelector('thead');
    if (!thead || !thead.rows.length) {
      return;
    }

    const headerRow = thead.rows[0];
    Array.from(headerRow.cells).forEach((th, idx) => {
      if (th.dataset.sort === 'disabled' || th.classList.contains('sorttable_nosort')) {
        return;
      }
      th.tabIndex = 0;
      th.classList.add('sortable-header');
      th.setAttribute('role', 'button');
      th.setAttribute('aria-sort', 'none');
      th.appendChild(createIndicator());

      th.addEventListener('click', () => sortByColumn(table, idx, th));
      th.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          sortByColumn(table, idx, th);
        }
      });
    });
  }

  function sortByColumn(table, columnIndex, headerCell) {
    const tbody = table.tBodies[0];
    if (!tbody) {
      return;
    }

    const topRows = [];
    const bottomRows = [];
    const sortableRows = [];

    Array.from(tbody.rows).forEach((row) => {
      const position = (row.dataset.sortPosition || '').toLowerCase();
      if (position === 'top') {
        topRows.push(row);
      } else if (position === 'bottom') {
        bottomRows.push(row);
      } else {
        sortableRows.push(row);
      }
    });

    if (!sortableRows.length) {
      return;
    }

    const type = (headerCell.dataset[TYPE_DATA_ATTR] || TYPE_TEXT).toLowerCase();
    const currentDirection = headerCell.getAttribute('data-sort-direction');
    const defaultDirection = (headerCell.dataset[DEFAULT_DIR_ATTR] || 'asc').toLowerCase();

    const direction = currentDirection === 'asc' ? 'desc' : currentDirection === 'desc' ? 'asc' : defaultDirection;
    headerCell.setAttribute('data-sort-direction', direction);

    // clear other headers
    headerCell.parentElement.querySelectorAll('.sortable-header').forEach((th) => {
      if (th !== headerCell) {
        th.removeAttribute('data-sort-direction');
        th.setAttribute('aria-sort', 'none');
        updateIndicator(th, 'none');
      }
    });

    const multiplier = direction === 'desc' ? -1 : 1;
    const effectiveType = determineType(type, sortableRows, columnIndex);
    const accessor = createAccessor(effectiveType, columnIndex);

    sortableRows.sort((a, b) => {
      const av = accessor(a);
      const bv = accessor(b);
      if (av === bv) {
        return 0;
      }
      if (av === undefined || av === null) {
        return 1 * multiplier;
      }
      if (bv === undefined || bv === null) {
        return -1 * multiplier;
      }
      return av < bv ? -1 * multiplier : 1 * multiplier;
    });

    const fragment = document.createDocumentFragment();
    topRows.forEach((row) => fragment.appendChild(row));
    sortableRows.forEach((row) => fragment.appendChild(row));
    bottomRows.forEach((row) => fragment.appendChild(row));
    tbody.appendChild(fragment);
    headerCell.setAttribute('aria-sort', direction === 'desc' ? 'descending' : 'ascending');
    updateIndicator(headerCell, direction);
  }

  function createIndicator() {
    const span = document.createElement('span');
    span.className = 'sortable-indicator';
    span.setAttribute('aria-hidden', 'true');
    span.textContent = '↕';
    return span;
  }

  function updateIndicator(th, state) {
    const indicator = th.querySelector('.sortable-indicator');
    if (!indicator) {
      return;
    }
    switch (state) {
      case 'asc':
        indicator.textContent = '▲';
        break;
      case 'desc':
        indicator.textContent = '▼';
        break;
      default:
        indicator.textContent = '↕';
    }
  }

  function createAccessor(type, columnIndex) {
    switch (type) {
      case TYPE_NUMERIC:
        return (row) => parseNumeric(resolveCellValue(row.cells[columnIndex]));
      case TYPE_DATE:
        return (row) => parseDate(resolveCellValue(row.cells[columnIndex]))?.getTime?.();
      default:
        return (row) => normalizeText(resolveCellValue(row.cells[columnIndex]));
    }
  }

  function determineType(initialType, rows, columnIndex) {
    if (initialType !== TYPE_TEXT) {
      return initialType;
    }

    let numericHits = 0;
    let dateHits = 0;
    let total = 0;

    rows.forEach((row) => {
      const raw = resolveCellValue(row.cells[columnIndex]);
      if (raw === undefined || raw === null || String(raw).trim() === '') {
        return;
      }
      total += 1;
      if (parseNumeric(raw) !== undefined) {
        numericHits += 1;
        return;
      }
      if (parseDate(raw)) {
        dateHits += 1;
      }
    });

    if (numericHits >= Math.max(1, total * 0.6)) {
      return TYPE_NUMERIC;
    }
    if (dateHits >= Math.max(1, total * 0.6)) {
      return TYPE_DATE;
    }
    return initialType;
  }

  function resolveCellValue(cell) {
    if (!cell) {
      return '';
    }
    const custom = cell.getAttribute(CUSTOM_KEY_ATTR);
    if (custom !== null) {
      return custom;
    }
    return cell.textContent || cell.innerText || '';
  }

  function parseNumeric(value) {
    if (typeof value !== 'string') {
      return Number(value);
    }
    const cleaned = value.trim().replace(/[^0-9+\-.,eE]/g, '').replace(/,(?=\d{3}(\D|$))/g, '');
    const parsed = Number(cleaned);
    return Number.isNaN(parsed) ? undefined : parsed;
  }

  function parseDate(value) {
    if (typeof value !== 'string') {
      return value instanceof Date ? value : undefined;
    }
    const trimmed = value.trim();
    for (const pattern of DATE_PATTERNS) {
      const match = trimmed.match(pattern);
      if (!match) {
        continue;
      }
      if (pattern === DATE_PATTERNS[0]) {
        const [, y, m, d] = match;
        return new Date(Number(y), Number(m) - 1, Number(d));
      }
      const [, first, second, yearRaw] = match;
      const year = Number(yearRaw.length === 2 ? normalizeYear(yearRaw) : yearRaw);
      const a = Number(first);
      const b = Number(second);
      if (a > 12 && b <= 12) {
        return new Date(year, b - 1, a);
      }
      if (b > 12 && a <= 12) {
        return new Date(year, a - 1, b);
      }
      return new Date(year, a - 1, b);
    }
    const iso = Date.parse(trimmed);
    return Number.isNaN(iso) ? undefined : new Date(iso);
  }

  function normalizeYear(twoDigitYear) {
    const n = Number(twoDigitYear);
    return n + (n < 50 ? 2000 : 1900);
  }

  function normalizeText(value) {
    return typeof value === 'string' ? value.trim().toLowerCase() : value;
  }
})();
