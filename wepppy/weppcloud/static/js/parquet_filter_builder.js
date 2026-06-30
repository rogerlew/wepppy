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
  wrapper.className = "parquet-filter-builder pure-form";

  const title = document.createElement("summary");
  title.textContent = "Parquet Data Filter";
  title.className = "parquet-filter-builder__summary";

  const body = document.createElement("div");
  body.className = "parquet-filter-builder__body";

  const controls = document.createElement("div");
  controls.className = "parquet-filter-builder__controls";

  const applyButton = document.createElement("button");
  applyButton.type = "button";
  applyButton.textContent = "Apply Filter";
  applyButton.className = "pure-button parquet-filter-builder__button parquet-filter-builder__apply";

  const clearButton = document.createElement("button");
  clearButton.type = "button";
  clearButton.textContent = "Clear Filter";
  clearButton.className = "pure-button pure-button-secondary parquet-filter-builder__button";

  const status = document.createElement("span");
  status.className = "parquet-filter-builder__status";

  controls.appendChild(applyButton);
  controls.appendChild(clearButton);
  controls.appendChild(status);

  const treeHost = document.createElement("div");
  treeHost.className = "parquet-filter-builder__tree";

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
    label.className = "parquet-filter-builder__node-label";
    return label;
  }

  function makeNodeControls(node, parent, index, depth) {
    const row = document.createElement("div");
    row.className = `parquet-filter-builder__node parquet-filter-builder__node--${node.kind}`;
    if (depth > 0) {
      row.classList.add("parquet-filter-builder__node--child");
    }

    if (node.kind === "group") {
      const header = document.createElement("div");
      header.className = "parquet-filter-builder__node-header";

      const logicSelect = document.createElement("select");
      logicSelect.className = "wc-field__control parquet-filter-builder__select parquet-filter-builder__logic";
      logicSelect.setAttribute("aria-label", "Filter group logic");
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
      addConditionBtn.className = "pure-button pure-button-secondary parquet-filter-builder__button";
      addConditionBtn.addEventListener("click", () => {
        node.children.push(createCondition());
        markFilterDirty();
        render();
      });

      const addGroupBtn = document.createElement("button");
      addGroupBtn.type = "button";
      addGroupBtn.textContent = "+ Group";
      addGroupBtn.className = "pure-button pure-button-secondary parquet-filter-builder__button";
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
        removeBtn.className = "pure-button pure-button-secondary parquet-filter-builder__button";
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
    fieldInput.className = "wc-field__control parquet-filter-builder__input parquet-filter-builder__input--field";
    fieldInput.setAttribute("aria-label", "Filter field");
    fieldInput.addEventListener("input", () => {
      node.field = fieldInput.value;
      markFilterDirty();
    });

    const operatorSelect = document.createElement("select");
    operatorSelect.className = "wc-field__control parquet-filter-builder__select parquet-filter-builder__operator";
    operatorSelect.setAttribute("aria-label", "Filter operator");
    OPERATORS.forEach((operator) => {
      const opt = document.createElement("option");
      opt.value = operator;
      opt.textContent = operator;
      if (node.operator === operator) {
        opt.selected = true;
      }
      operatorSelect.appendChild(opt);
    });
    operatorSelect.addEventListener("change", () => {
      node.operator = operatorSelect.value;
      markFilterDirty();
    });

    const valueInput = document.createElement("input");
    valueInput.type = "text";
    valueInput.placeholder = "value";
    valueInput.value = node.value || "";
    valueInput.className = "wc-field__control parquet-filter-builder__input parquet-filter-builder__input--value";
    valueInput.setAttribute("aria-label", "Filter value");
    valueInput.addEventListener("input", () => {
      node.value = valueInput.value;
      markFilterDirty();
    });

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.textContent = "Remove";
    removeBtn.className = "pure-button pure-button-secondary parquet-filter-builder__button";
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
