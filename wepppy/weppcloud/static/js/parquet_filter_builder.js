(function () {
  const container = document.getElementById("parquet-filter-builder");
  if (!container) {
    return;
  }

  const OPERATORS = ["Equals", "NotEquals", "Contains", "GreaterThan", "LessThan"];
  const MAX_DEPTH = 6;
  const MAX_NODES = 50;

  const runid = container.dataset.runid || "";
  const config = container.dataset.config || "";
  const storageKey = `weppcloud:parquet-filter:${runid}:${config}`;

  function createCondition() {
    return {
      kind: "condition",
      field: "",
      operator: "Equals",
      value: "",
    };
  }

  function createGroup() {
    return {
      kind: "group",
      logic: "AND",
      children: [createCondition()],
    };
  }

  function encodePayload(node) {
    const json = JSON.stringify(node);
    return btoa(unescape(encodeURIComponent(json)))
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/g, "");
  }

  function decodePayload(raw) {
    if (!raw) {
      return null;
    }
    const padded = raw + "=".repeat((4 - (raw.length % 4)) % 4);
    const base64 = padded.replace(/-/g, "+").replace(/_/g, "/");
    const json = decodeURIComponent(escape(atob(base64)));
    return JSON.parse(json);
  }

  function clone(obj) {
    return JSON.parse(JSON.stringify(obj));
  }

  function getPayloadFromUrl() {
    const url = new URL(window.location.href);
    return (url.searchParams.get("pqf") || "").trim();
  }

  function setPayloadInUrl(payload) {
    const url = new URL(window.location.href);
    if (payload) {
      url.searchParams.set("pqf", payload);
    } else {
      url.searchParams.delete("pqf");
    }
    window.history.replaceState({}, "", url.pathname + url.search + url.hash);
  }

  function updateParquetLinks(payload) {
    const links = document.querySelectorAll('a[data-parquet-link="1"]');
    links.forEach((link) => {
      const href = link.getAttribute("href");
      if (!href) {
        return;
      }
      const url = new URL(href, window.location.origin);
      if (payload) {
        url.searchParams.set("pqf", payload);
      } else {
        url.searchParams.delete("pqf");
      }
      link.setAttribute("href", url.pathname + url.search + url.hash);
    });
  }

  function validateNode(node, depth, state) {
    if (!node || typeof node !== "object") {
      return "Each node must be an object.";
    }
    if (depth > MAX_DEPTH) {
      return `Filter depth cannot exceed ${MAX_DEPTH}.`;
    }
    state.count += 1;
    if (state.count > MAX_NODES) {
      return `Filter node count cannot exceed ${MAX_NODES}.`;
    }
    if (node.kind === "group") {
      if (!Array.isArray(node.children) || node.children.length === 0) {
        return "Groups must contain at least one condition or subgroup.";
      }
      if (node.logic !== "AND" && node.logic !== "OR") {
        return "Group logic must be AND or OR.";
      }
      for (const child of node.children) {
        const err = validateNode(child, depth + 1, state);
        if (err) {
          return err;
        }
      }
      return null;
    }
    if (node.kind === "condition") {
      if (!node.field || !String(node.field).trim()) {
        return "Condition field is required.";
      }
      if (!OPERATORS.includes(node.operator)) {
        return "Condition operator is invalid.";
      }
      if (typeof node.value !== "string") {
        return "Condition value must be text.";
      }
      return null;
    }
    return "Node kind must be group or condition.";
  }

  function readInitialTree() {
    const fromUrl = getPayloadFromUrl();
    if (fromUrl) {
      try {
        const parsed = decodePayload(fromUrl);
        if (parsed) {
          localStorage.setItem(storageKey, fromUrl);
          return parsed;
        }
      } catch (_err) {
        // Ignore malformed URL payload here; backend still validates on request.
      }
    }

    const fromDataAttr = (container.dataset.initialPqf || "").trim();
    if (fromDataAttr) {
      try {
        const parsed = decodePayload(fromDataAttr);
        if (parsed) {
          localStorage.setItem(storageKey, fromDataAttr);
          return parsed;
        }
      } catch (_err) {
        // Fall through to localStorage/default.
      }
    }

    const stored = (localStorage.getItem(storageKey) || "").trim();
    if (stored) {
      try {
        const parsed = decodePayload(stored);
        if (parsed) {
          if (!getPayloadFromUrl()) {
            setPayloadInUrl(stored);
          }
          return parsed;
        }
      } catch (_err) {
        localStorage.removeItem(storageKey);
      }
    }

    return createGroup();
  }

  let tree = readInitialTree();

  const wrapper = document.createElement("details");
  wrapper.open = false;
  wrapper.style.border = "1px solid #d0d0d0";
  wrapper.style.padding = "0.4rem 0.5rem";
  wrapper.style.background = "#fafafa";

  const title = document.createElement("summary");
  title.textContent = "Parquet Data Filter";
  title.style.fontWeight = "700";
  title.style.fontSize = "0.85rem";
  title.style.cursor = "pointer";
  title.style.userSelect = "none";

  const body = document.createElement("div");
  body.style.marginTop = "0.45rem";

  const controls = document.createElement("div");
  controls.style.marginBottom = "0.4rem";

  const applyButton = document.createElement("button");
  applyButton.type = "button";
  applyButton.textContent = "Apply Filter";
  applyButton.style.backgroundColor = "#1d6fdc";
  applyButton.style.border = "1px solid #1557ad";
  applyButton.style.color = "#fff";
  applyButton.style.fontWeight = "600";
  applyButton.style.borderRadius = "4px";
  applyButton.style.padding = "0.25rem 0.55rem";

  const clearButton = document.createElement("button");
  clearButton.type = "button";
  clearButton.textContent = "Clear Filter";
  clearButton.style.marginLeft = "0.5rem";

  const status = document.createElement("span");
  status.style.marginLeft = "0.75rem";
  status.style.whiteSpace = "normal";
  status.style.fontSize = "0.82rem";

  controls.appendChild(applyButton);
  controls.appendChild(clearButton);
  controls.appendChild(status);

  const treeHost = document.createElement("div");

  wrapper.appendChild(title);
  body.appendChild(controls);
  body.appendChild(treeHost);
  wrapper.appendChild(body);
  container.appendChild(wrapper);

  function hasActivePayload() {
    return Boolean(getPayloadFromUrl());
  }

  function markFilterDirty() {
    const activePayload = getPayloadFromUrl();
    if (activePayload) {
      status.textContent = "Filter changed. Click Apply Filter to update parquet links.";
      return;
    }
    status.textContent = "Filter edited. Click Apply Filter to add pqf to parquet links.";
  }

  function setInitialStatus() {
    if (hasActivePayload()) {
      status.textContent = "Active filter loaded.";
      return;
    }
    status.textContent = "No active filter.";
  }

  function createNodeLabel(text) {
    const label = document.createElement("span");
    label.textContent = text;
    label.style.fontSize = "0.78rem";
    label.style.fontWeight = "600";
    label.style.color = "#555";
    label.style.marginRight = "0.3rem";
    return label;
  }

  function makeNodeControls(node, parent, index, depth) {
    const row = document.createElement("div");
    row.style.borderLeft = "2px solid #c8c8c8";
    row.style.marginLeft = depth === 0 ? "0" : "0.75rem";
    row.style.paddingLeft = "0.6rem";
    row.style.marginBottom = "0.4rem";

    if (node.kind === "group") {
      const header = document.createElement("div");

      const logicSelect = document.createElement("select");
      ["AND", "OR"].forEach((logic) => {
        const opt = document.createElement("option");
        opt.value = logic;
        opt.textContent = logic;
        if (node.logic === logic) {
          opt.selected = true;
        }
        logicSelect.appendChild(opt);
      });
      logicSelect.addEventListener("change", () => {
        node.logic = logicSelect.value;
        markFilterDirty();
      });

      const addConditionBtn = document.createElement("button");
      addConditionBtn.type = "button";
      addConditionBtn.textContent = "+ Condition";
      addConditionBtn.style.marginLeft = "0.4rem";
      addConditionBtn.addEventListener("click", () => {
        node.children.push(createCondition());
        markFilterDirty();
        render();
      });

      const addGroupBtn = document.createElement("button");
      addGroupBtn.type = "button";
      addGroupBtn.textContent = "+ Group";
      addGroupBtn.style.marginLeft = "0.35rem";
      addGroupBtn.addEventListener("click", () => {
        node.children.push(createGroup());
        markFilterDirty();
        render();
      });

      header.appendChild(createNodeLabel("Group"));
      header.appendChild(logicSelect);
      header.appendChild(addConditionBtn);
      header.appendChild(addGroupBtn);

      if (parent) {
        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.textContent = "Remove";
        removeBtn.style.marginLeft = "0.35rem";
        removeBtn.addEventListener("click", () => {
          parent.children.splice(index, 1);
          markFilterDirty();
          render();
        });
        header.appendChild(removeBtn);
      }

      row.appendChild(header);

      node.children.forEach((child, childIdx) => {
        row.appendChild(makeNodeControls(child, node, childIdx, depth + 1));
      });

      return row;
    }

    const fieldInput = document.createElement("input");
    fieldInput.type = "text";
    fieldInput.placeholder = "field";
    fieldInput.value = node.field || "";
    fieldInput.style.width = "14rem";
    fieldInput.addEventListener("input", () => {
      node.field = fieldInput.value;
      markFilterDirty();
    });

    const operatorSelect = document.createElement("select");
    OPERATORS.forEach((operator) => {
      const opt = document.createElement("option");
      opt.value = operator;
      opt.textContent = operator;
      if (node.operator === operator) {
        opt.selected = true;
      }
      operatorSelect.appendChild(opt);
    });
    operatorSelect.style.marginLeft = "0.35rem";
    operatorSelect.addEventListener("change", () => {
      node.operator = operatorSelect.value;
      markFilterDirty();
    });

    const valueInput = document.createElement("input");
    valueInput.type = "text";
    valueInput.placeholder = "value";
    valueInput.value = node.value || "";
    valueInput.style.width = "14rem";
    valueInput.style.marginLeft = "0.35rem";
    valueInput.addEventListener("input", () => {
      node.value = valueInput.value;
      markFilterDirty();
    });

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.textContent = "Remove";
    removeBtn.style.marginLeft = "0.35rem";
    removeBtn.addEventListener("click", () => {
      if (parent) {
        parent.children.splice(index, 1);
        markFilterDirty();
        render();
      }
    });

    row.appendChild(createNodeLabel("Condition"));
    row.appendChild(fieldInput);
    row.appendChild(operatorSelect);
    row.appendChild(valueInput);
    if (parent) {
      row.appendChild(removeBtn);
    }

    return row;
  }

  function render() {
    treeHost.innerHTML = "";
    treeHost.appendChild(makeNodeControls(tree, null, -1, 0));
    updateParquetLinks(getPayloadFromUrl());
  }

  applyButton.addEventListener("click", () => {
    const err = validateNode(tree, 1, { count: 0 });
    if (err) {
      status.textContent = err;
      return;
    }
    const payload = encodePayload(tree);
    localStorage.setItem(storageKey, payload);
    setPayloadInUrl(payload);
    updateParquetLinks(payload);
    status.textContent = "Filter applied. Parquet links now carry pqf.";
  });

  clearButton.addEventListener("click", () => {
    tree = createGroup();
    localStorage.removeItem(storageKey);
    setPayloadInUrl("");
    updateParquetLinks("");
    status.textContent = "Filter cleared. Parquet links no longer carry pqf.";
    render();
  });

  setInitialStatus();
  render();
})();
