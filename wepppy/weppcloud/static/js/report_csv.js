(function () {
  "use strict";

  function init() {
    document.querySelectorAll('[data-report-csv]').forEach((button) => {
      button.addEventListener('click', () => downloadCsv(button));
    });
  }

  async function downloadCsv(button) {
    const targetTableId = button.getAttribute('data-report-csv');
    const url = button.getAttribute('data-report-url');
    if (!url) {
      console.warn('report_csv: missing data-report-url attribute');
      return;
    }

    button.disabled = true;
    button.classList.add('is-loading');

    try {
      let requestUrl = url;
      const table = button.getAttribute('data-report-table');
      if (table) {
        const urlObj = new URL(url, window.location.origin);
        urlObj.searchParams.set('table', table);
        requestUrl = urlObj.toString();
      }

      const response = await fetch(requestUrl, { headers: { 'Accept': 'text/csv' } });
      if (!response.ok) {
        throw new Error(`CSV request failed: ${response.status}`);
      }
      const blob = await response.blob();
      const filename = response.headers.get('Content-Disposition')?.split('filename=')?.[1]?.replace(/"/g, '') || 'report.csv';

      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      URL.revokeObjectURL(link.href);
      document.body.removeChild(link);
    } catch (error) {
      console.error('Failed to download CSV', error);
      alert('Unable to download CSV for this report.');
    } finally {
      button.disabled = false;
      button.classList.remove('is-loading');
    }
  }

  document.addEventListener('DOMContentLoaded', init, { once: true });
})();
