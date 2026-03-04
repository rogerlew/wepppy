(function () {
  const schemaCache = new Map();

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function collapsePanel(panel, link) {
    panel.setAttribute("hidden", "");
    panel.innerHTML = '<span class="parquet-schema-panel"></span>';
    if (link) {
      link.setAttribute("aria-expanded", "false");
    }
  }

  function collapseOtherPanels(targetPanelId) {
    document.querySelectorAll("a[data-parquet-schema-link='1']").forEach((candidateLink) => {
      const candidatePanelId = candidateLink.dataset.schemaTarget || "";
      if (!candidatePanelId || candidatePanelId === targetPanelId) {
        return;
      }
      const candidatePanel = document.getElementById(candidatePanelId);
      if (!candidatePanel) {
        return;
      }
      collapsePanel(candidatePanel, candidateLink);
    });
  }

  function renderSchemaTable(panel, payload) {
    const columns = Array.isArray(payload.columns) ? payload.columns : [];
    const rows = columns
      .map((column) => {
        const name = escapeHtml(column && column.name ? column.name : "");
        const type = escapeHtml(column && column.type ? column.type : "");
        return `<tr><td>${name}</td><td>${type}</td></tr>`;
      })
      .join("");

    if (!rows) {
      panel.innerHTML =
        '<span class="parquet-schema-panel"><span class="parquet-schema-empty">No columns found.</span></span>';
      return;
    }

    panel.innerHTML =
      '<span class="parquet-schema-panel">' +
      '<table class="parquet-schema-table">' +
      "<thead><tr><th>Column</th><th>Type</th></tr></thead>" +
      `<tbody>${rows}</tbody>` +
      "</table>" +
      "</span>";
  }

  async function fetchSchema(schemaUrl) {
    if (!schemaUrl) {
      throw new Error("Missing schema endpoint.");
    }
    if (schemaCache.has(schemaUrl)) {
      return schemaCache.get(schemaUrl);
    }
    const request = fetch(schemaUrl, {
      headers: {
        Accept: "application/json",
      },
    }).then(async (response) => {
      if (!response.ok) {
        const errorText = (await response.text()).trim();
        throw new Error(errorText || `Schema request failed (${response.status}).`);
      }
      return response.json();
    });
    schemaCache.set(schemaUrl, request);
    try {
      return await request;
    } catch (error) {
      schemaCache.delete(schemaUrl);
      throw error;
    }
  }

  function ensurePanelForLink(link) {
    let panelId = link.dataset.schemaTarget || "";
    let panel = panelId ? document.getElementById(panelId) : null;
    if (panel) {
      return panel;
    }

    if (!panelId) {
      panelId = `parquet-schema-panel-${Math.random().toString(36).slice(2, 10)}`;
      link.dataset.schemaTarget = panelId;
    }

    panel = document.createElement("span");
    panel.id = panelId;
    panel.className = "parquet-schema-row";
    panel.setAttribute("hidden", "");
    panel.innerHTML = '<span class="parquet-schema-panel"></span>';

    const row = link.closest("span.odd-row, span.even-row");
    if (row && row.parentNode) {
      row.insertAdjacentElement("afterend", panel);
    }

    return panel;
  }

  document.addEventListener("click", async (event) => {
    const link = event.target.closest("a[data-parquet-schema-link='1']");
    if (!link) {
      return;
    }

    const panel = ensurePanelForLink(link);
    if (!panel) {
      return;
    }
    const panelId = panel.id;

    event.preventDefault();

    const isExpanded = link.getAttribute("aria-expanded") === "true";
    if (isExpanded && !panel.hasAttribute("hidden")) {
      collapsePanel(panel, link);
      return;
    }

    collapseOtherPanels(panelId);
    panel.removeAttribute("hidden");
    link.setAttribute("aria-expanded", "true");
    panel.innerHTML =
      '<span class="parquet-schema-panel"><span class="parquet-schema-loading">Loading schema...</span></span>';

    try {
      const payload = await fetchSchema(link.dataset.schemaUrl || link.getAttribute("href") || "");
      renderSchemaTable(panel, payload || {});
    } catch (error) {
      const message = error && error.message ? error.message : "Schema preview failed.";
      panel.innerHTML =
        '<span class="parquet-schema-panel">' +
        `<span class="parquet-schema-error">${escapeHtml(message)}</span>` +
        "</span>";
    }
  });
})();
