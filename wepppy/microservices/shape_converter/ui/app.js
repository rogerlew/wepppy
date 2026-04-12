"use strict";

(function bootstrapShapeConverterUi() {
  const inspectForm = document.getElementById("inspect-form");
  const convertForm = document.getElementById("convert-form");
  if (!(inspectForm instanceof HTMLFormElement) || !(convertForm instanceof HTMLFormElement)) {
    return;
  }

  const inspectArchiveInput = document.getElementById("inspect-archive");
  const convertArchiveInput = document.getElementById("convert-archive");
  const outputFormatSelect = document.getElementById("output-format");
  const targetCrsSelect = document.getElementById("target-crs");

  const inspectStatus = document.getElementById("inspect-status");
  const convertStatus = document.getElementById("convert-status");

  const projectionStatus = document.getElementById("projection-status");
  const detectedCrs = document.getElementById("detected-crs");
  const outputCrs = document.getElementById("output-crs");

  const featureCount = document.getElementById("feature-count");
  const geometryTypes = document.getElementById("geometry-types");
  const bbox = document.getElementById("bbox");
  const schemaTableBody = document.getElementById("schema-table-body");

  const warningsList = document.getElementById("warnings-list");
  const advisoryList = document.getElementById("advisory-list");

  const errorPanel = document.getElementById("error-panel");
  const errorTitle = document.getElementById("error-title");
  const errorMessage = document.getElementById("error-message");
  const errorGuidance = document.getElementById("error-guidance");
  const errorDetails = document.getElementById("error-details");

  const inspectSubmit = document.getElementById("inspect-submit");
  const convertSubmit = document.getElementById("convert-submit");

  inspectForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearErrorPanel();

    if (!(inspectArchiveInput instanceof HTMLInputElement) || !inspectArchiveInput.files || inspectArchiveInput.files.length === 0) {
      setStatus(inspectStatus, "Select a ZIP file before inspect.", "error");
      return;
    }

    setStatus(inspectStatus, "Inspect request running...", "neutral");
    setButtonState(inspectSubmit, true);

    try {
      const formData = new FormData();
      formData.append("archive", inspectArchiveInput.files[0]);

      const response = await fetch(resolveApiUrl("v1/inspect"), {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const apiError = await parseApiError(response);
        renderApiError(apiError, "inspect");
        setStatus(inspectStatus, buildUserFacingStatus(apiError, "inspect"), "error");
        return;
      }

      const payload = await response.json();
      renderInspectMetadata(payload);
      setStatus(
        inspectStatus,
        "Inspect complete. Metadata panels updated.",
        "success"
      );
    } catch (error) {
      const networkError = buildNetworkApiError(error);
      renderApiError(networkError, "inspect");
      setStatus(inspectStatus, buildUserFacingStatus(networkError, "inspect"), "error");
    } finally {
      setButtonState(inspectSubmit, false);
    }
  });

  convertForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearErrorPanel();

    if (!(convertArchiveInput instanceof HTMLInputElement) || !convertArchiveInput.files || convertArchiveInput.files.length === 0) {
      setStatus(convertStatus, "Select a ZIP file before convert.", "error");
      return;
    }

    if (!(outputFormatSelect instanceof HTMLSelectElement) || !(targetCrsSelect instanceof HTMLSelectElement)) {
      setStatus(convertStatus, "Convert controls are unavailable.", "error");
      return;
    }

    setStatus(convertStatus, "Convert request running...", "neutral");
    setButtonState(convertSubmit, true);

    try {
      const formData = new FormData();
      formData.append("archive", convertArchiveInput.files[0]);
      formData.append("output_format", outputFormatSelect.value);
      formData.append("target_crs", targetCrsSelect.value);
      formData.append("response_mode", "download");

      const response = await fetch(resolveApiUrl("v1/convert"), {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const apiError = await parseApiError(response);
        renderApiError(apiError, "convert");
        setStatus(convertStatus, buildUserFacingStatus(apiError, "convert"), "error");
        return;
      }

      const contentDisposition = response.headers.get("Content-Disposition") || "";
      const filename = parseDownloadFilename(contentDisposition) || "shape_converter_output.bin";
      const blob = await response.blob();
      triggerDownload(blob, filename);

      const metadataPath = response.headers.get("X-Shape-Converter-Metadata-Path");
      if (!metadataPath) {
        setStatus(
          convertStatus,
          "Convert completed and downloaded, but metadata path header was missing.",
          "error"
        );
        return;
      }

      const metadataResponse = await fetch(resolveMetadataUrl(metadataPath), {
        method: "GET",
      });
      if (!metadataResponse.ok) {
        const metadataError = await parseApiError(metadataResponse);
        renderApiError(metadataError, "convert metadata fetch");
        setStatus(
          convertStatus,
          `Download completed, but metadata fetch failed. ${buildUserFacingStatus(metadataError, "convert")}`,
          "error"
        );
        return;
      }

      const metadataPayload = await metadataResponse.json();
      renderConvertMetadata(metadataPayload);
      setStatus(
        convertStatus,
        "Convert complete. Download started and metadata panels updated.",
        "success"
      );
    } catch (error) {
      const networkError = buildNetworkApiError(error);
      renderApiError(networkError, "convert");
      setStatus(convertStatus, buildUserFacingStatus(networkError, "convert"), "error");
    } finally {
      setButtonState(convertSubmit, false);
    }
  });

  function setButtonState(buttonNode, disabled) {
    if (buttonNode instanceof HTMLButtonElement) {
      buttonNode.disabled = disabled;
    }
  }

  function setStatus(node, message, type) {
    if (!(node instanceof HTMLElement)) {
      return;
    }

    node.textContent = message;
    node.classList.remove("success", "error");
    if (type === "success") {
      node.classList.add("success");
    }
    if (type === "error") {
      node.classList.add("error");
    }
  }

  function resolveApiUrl(path) {
    const sanitizedPath = String(path || "").replace(/^\/+/, "");
    return new URL(sanitizedPath, window.location.href).toString();
  }

  function resolveMetadataUrl(path) {
    const value = String(path || "").trim();
    if (!value) {
      return "";
    }

    if (value.startsWith("http://") || value.startsWith("https://")) {
      return value;
    }

    if (value.startsWith("/")) {
      return `${window.location.origin}${value}`;
    }

    return new URL(value, window.location.href).toString();
  }

  function formatCrs(crsPayload) {
    if (!crsPayload || typeof crsPayload !== "object") {
      return "unknown";
    }

    const authority = typeof crsPayload.authority === "string" ? crsPayload.authority : "";
    if (authority) {
      return authority;
    }

    const wkt = typeof crsPayload.wkt === "string" ? crsPayload.wkt.trim() : "";
    if (!wkt) {
      return "known (identifier unavailable)";
    }

    if (wkt.length > 120) {
      return `${wkt.slice(0, 117)}...`;
    }

    return wkt;
  }

  function formatBbox(bboxPayload) {
    if (!Array.isArray(bboxPayload) || bboxPayload.length !== 4) {
      return "n/a";
    }

    const parsed = bboxPayload.map((value) => Number(value));
    if (parsed.some((value) => !Number.isFinite(value))) {
      return "n/a";
    }

    return `[${parsed.map((value) => value.toFixed(6)).join(", ")}]`;
  }

  function renderInspectMetadata(payload) {
    if (!(payload && typeof payload === "object")) {
      return;
    }

    if (projectionStatus instanceof HTMLElement) {
      projectionStatus.textContent = String(payload.projection_status || "unknown");
    }
    if (detectedCrs instanceof HTMLElement) {
      detectedCrs.textContent = formatCrs(payload.detected_crs);
    }
    if (outputCrs instanceof HTMLElement) {
      outputCrs.textContent = "pending convert request";
    }
    if (featureCount instanceof HTMLElement) {
      featureCount.textContent = String(payload.feature_count ?? "n/a");
    }
    if (geometryTypes instanceof HTMLElement) {
      const values = Array.isArray(payload.geometry_types) ? payload.geometry_types : [];
      geometryTypes.textContent = values.length > 0 ? values.join(", ") : "n/a";
    }
    if (bbox instanceof HTMLElement) {
      bbox.textContent = formatBbox(payload.bbox);
    }

    renderSchema(payload.attribute_schema);
    renderWarnings(payload.warnings);
  }

  function renderConvertMetadata(payload) {
    if (!(payload && typeof payload === "object")) {
      return;
    }

    const sourceCrs = payload.detected_crs;
    const targetCrs = payload.output_crs;

    if (projectionStatus instanceof HTMLElement) {
      projectionStatus.textContent = sourceCrs ? "known" : "unknown";
    }
    if (detectedCrs instanceof HTMLElement) {
      detectedCrs.textContent = formatCrs(sourceCrs);
    }
    if (outputCrs instanceof HTMLElement) {
      outputCrs.textContent = formatCrs(targetCrs);
    }

    if (featureCount instanceof HTMLElement) {
      featureCount.textContent = String(payload.feature_count ?? "n/a");
    }
    if (geometryTypes instanceof HTMLElement) {
      const values = Array.isArray(payload.geometry_types) ? payload.geometry_types : [];
      geometryTypes.textContent = values.length > 0 ? values.join(", ") : "n/a";
    }
    if (bbox instanceof HTMLElement) {
      bbox.textContent = formatBbox(payload.bbox);
    }

    renderWarnings(payload.warnings);
  }

  function renderSchema(schemaPayload) {
    if (!(schemaTableBody instanceof HTMLElement)) {
      return;
    }

    const schemaRows = Array.isArray(schemaPayload) ? schemaPayload : [];
    schemaTableBody.textContent = "";

    if (schemaRows.length === 0) {
      schemaTableBody.appendChild(buildSchemaPlaceholderRow("No attribute schema available from this response."));
      return;
    }

    for (const row of schemaRows) {
      const tr = document.createElement("tr");
      tr.appendChild(buildCell(asDisplayString(row && row.name)));
      tr.appendChild(buildCell(asDisplayString(row && row.type)));
      tr.appendChild(buildCell(asDisplayString(row && row.width)));
      tr.appendChild(buildCell(asDisplayString(row && row.precision)));
      schemaTableBody.appendChild(tr);
    }
  }

  function buildSchemaPlaceholderRow(text) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = 4;
    td.textContent = text;
    tr.appendChild(td);
    return tr;
  }

  function buildCell(value) {
    const td = document.createElement("td");
    td.textContent = value;
    return td;
  }

  function asDisplayString(value) {
    if (value === null || value === undefined || value === "") {
      return "-";
    }
    return String(value);
  }

  function renderWarnings(warningsPayload) {
    const warnings = Array.isArray(warningsPayload)
      ? warningsPayload.filter((warning) => typeof warning === "string" && warning.trim().length > 0)
      : [];

    if (warningsList instanceof HTMLElement) {
      warningsList.textContent = "";
      if (warnings.length === 0) {
        const empty = document.createElement("li");
        empty.textContent = "No warnings reported.";
        warningsList.appendChild(empty);
      } else {
        for (const warning of warnings) {
          const item = document.createElement("li");
          item.textContent = warning;
          warningsList.appendChild(item);
        }
      }
    }

    renderAdvisories(warnings);
  }

  function renderAdvisories(warnings) {
    if (!(advisoryList instanceof HTMLElement)) {
      return;
    }

    advisoryList.textContent = "";

    const normalized = warnings.map((warning) => warning.toLowerCase());
    const includesShpXml = normalized.some((warning) => warning.includes(".shp.xml"));
    const includesProjectedGeojsonWarning = normalized.some(
      (warning) => warning.includes("rfc 7946") || warning.includes("projected crs")
    );

    if (includesShpXml) {
      advisoryList.appendChild(
        buildAdvisory(
          ".shp.xml removal advisory",
          "This archive included .shp.xml metadata sidecars. The service removes them and warns because these files often leak usernames, paths, or processing history."
        )
      );
    }

    if (includesProjectedGeojsonWarning) {
      advisoryList.appendChild(
        buildAdvisory(
          "Projected GeoJSON compatibility warning",
          "Projected GeoJSON is non-RFC 7946 output. Use this only when your downstream tooling explicitly supports projected coordinates in GeoJSON."
        )
      );
    }
  }

  function buildAdvisory(title, message) {
    const wrapper = document.createElement("section");
    wrapper.className = "advisory";

    const heading = document.createElement("strong");
    heading.textContent = title;
    wrapper.appendChild(heading);

    const body = document.createElement("p");
    body.textContent = message;
    wrapper.appendChild(body);
    return wrapper;
  }

  function clearErrorPanel() {
    if (errorPanel instanceof HTMLElement) {
      errorPanel.hidden = true;
    }
    if (errorTitle instanceof HTMLElement) {
      errorTitle.textContent = "Request failed";
    }
    if (errorMessage instanceof HTMLElement) {
      errorMessage.textContent = "";
    }
    if (errorGuidance instanceof HTMLElement) {
      errorGuidance.textContent = "";
    }
    if (errorDetails instanceof HTMLElement) {
      errorDetails.textContent = "";
    }
  }

  function renderApiError(apiError, contextLabel) {
    if (!(errorPanel instanceof HTMLElement)) {
      return;
    }

    const context = String(contextLabel || "request");
    errorPanel.hidden = false;
    errorPanel.removeAttribute("hidden");

    if (errorTitle instanceof HTMLElement) {
      errorTitle.textContent = `${context} failed`;
    }
    if (errorMessage instanceof HTMLElement) {
      errorMessage.textContent = buildUserFacingStatus(apiError, context);
    }
    if (errorGuidance instanceof HTMLElement) {
      errorGuidance.textContent = buildErrorGuidance(apiError, context);
    }
    if (errorDetails instanceof HTMLElement) {
      errorDetails.textContent = buildErrorDetails(apiError);
    }
    errorPanel.scrollIntoView({ block: "start", behavior: "smooth" });
  }

  function buildUserFacingStatus(apiError, operationName) {
    const quickAction = buildQuickActionHint(apiError, operationName);
    if (quickAction) {
      return quickAction;
    }

    return buildDefaultActionHint(operationName);
  }

  function buildNetworkApiError(error) {
    return {
      status: 0,
      code: "network_error",
      message: "Network request failed before the service returned a response.",
      details: String(error),
      requestId: "n/a",
      retryAfter: null,
    };
  }

  function buildErrorGuidance(apiError, operationName) {
    const actionHint = buildQuickActionHint(apiError, operationName);
    if (actionHint) {
      return actionHint;
    }

    return "If this keeps failing, share the Request ID below with support.";
  }

  function buildQuickActionHint(apiError, operationName) {
    const retryAction = retryActionText(operationName);
    const status = Number(apiError && apiError.status);
    const code = String(apiError && apiError.code ? apiError.code : "");
    const messageText = String(apiError && apiError.message ? apiError.message : "");
    const messageLower = messageText.toLowerCase();
    const detailsText = String(apiError && apiError.details ? apiError.details : "");
    const detailsLower = detailsText.toLowerCase();

    if (status === 429 || code === "rate_limited") {
      const retryAfter = apiError && apiError.retryAfter ? String(apiError.retryAfter) : "";
      return retryAfter
        ? `Too many requests right now. Wait ${retryAfter} seconds, then ${retryAction}`
        : `Too many requests right now. Wait a moment, then ${retryAction}`;
    }

    if (status === 503 || code === "service_saturated") {
      return `The converter is busy right now. Wait a moment, then ${retryAction}`;
    }

    if (code === "invalid_archive" && detailsLower.includes("unsupported file extension")) {
      const entryName = extractEntryName(detailsText);
      const extension = extractExtension(detailsText);
      const entryLabel = entryName ? ` (${entryName})` : "";
      if (extension) {
        return (
          `This ZIP has an unsupported file${entryLabel}. Remove ${extension} files, keep only shapefile files ` +
          "(.shp/.shx/.dbf + optional .prj/.cpg/.sbn/.sbx/.qix), zip again, then " +
          retryAction
        );
      }
      return (
        "This ZIP has unsupported extra files. Keep only shapefile files " +
        "(.shp/.shx/.dbf + optional .prj/.cpg/.sbn/.sbx/.qix), zip again, then " +
        retryAction
      );
    }

    if (code === "invalid_archive" && (messageLower.includes("zip extension") || detailsLower.includes("zip extension"))) {
      return `Please upload a .zip file, then ${retryAction}`;
    }

    if (code === "invalid_archive" && (messageLower.includes("signature") || detailsLower.includes("signature"))) {
      return `That file is not a valid ZIP archive. Export a real ZIP and then ${retryAction}`;
    }

    if (code === "invalid_archive" && (messageLower.includes("encrypted") || detailsLower.includes("encrypted"))) {
      return `This ZIP is password-protected. Create an unencrypted ZIP, then ${retryAction}`;
    }

    if (code === "invalid_archive" && (messageLower.includes("nested archive") || detailsLower.includes("nested archive"))) {
      return `ZIP-inside-ZIP is not supported. Put shapefile files directly in one ZIP, then ${retryAction}`;
    }

    if (code === "invalid_archive" && (messageLower.includes("no entries") || detailsLower.includes("empty"))) {
      return `This ZIP is empty. Add shapefile files (.shp/.shx/.dbf), zip again, then ${retryAction}`;
    }

    if (code === "missing_required_sidecar") {
      return (
        "Your ZIP is missing required shapefile files. Include matching .shp, .shx, and .dbf files " +
        "(same filename base), zip again, then " +
        retryAction
      );
    }

    if (code === "unknown_source_crs") {
      return (
        "This file has no usable coordinate system. Add a valid .prj file, or choose target CRS " +
        "same_as_shapefile, then " +
        retryAction
      );
    }

    if (code === "archive_path_traversal") {
      return `This ZIP folder structure is invalid. Re-create the ZIP from a normal folder, then ${retryAction}`;
    }

    if (code === "utm_not_supported_for_extent") {
      return `This area cannot use UTM automatically. Choose wgs84 or same_as_shapefile, then ${retryAction}`;
    }

    if (code === "request_timeout") {
      return `This file took too long to process. Try a smaller ZIP, then ${retryAction}`;
    }

    if (code === "response_mode_not_supported") {
      return "This mode is not available yet. Use download mode for now.";
    }

    if (code === "invalid_archive") {
      return (
        "We could not read this ZIP. Keep only one shapefile set: required .shp/.shx/.dbf, " +
        "optional .prj/.cpg/.sbn/.sbx/.qix; zip again, then " +
        retryAction
      );
    }

    if (code === "invalid_shapefile") {
      return `This shapefile set is invalid or incomplete. Re-export the shapefile and then ${retryAction}`;
    }

    return "";
  }

  function buildErrorDetails(apiError) {
    const lines = [
      `Request ID: ${apiError.requestId || "n/a"}`,
      `Error code: ${apiError.code || "request_failed"}`,
    ];

    const detailText = String(apiError.details || "").trim();
    if (detailText) {
      lines.push(`Technical detail: ${truncateText(detailText, 320)}`);
    }

    if (apiError.retryAfter) {
      lines.push(`Retry after: ${apiError.retryAfter} seconds`);
    }

    return lines.join("\n");
  }

  function truncateText(value, maxChars) {
    const text = String(value || "");
    if (text.length <= maxChars) {
      return text;
    }
    return `${text.slice(0, maxChars - 3)}...`;
  }

  function normalizeOperationLabel(operationName) {
    const value = String(operationName || "").toLowerCase();
    if (value.includes("convert")) {
      return "Convert";
    }
    return "Inspect";
  }

  function retryActionText(operationName) {
    const operation = normalizeOperationLabel(operationName).toLowerCase();
    return operation === "convert" ? "click Convert again." : "click Inspect again.";
  }

  function buildDefaultActionHint(operationName) {
    const operation = normalizeOperationLabel(operationName).toLowerCase();
    if (operation === "convert") {
      return (
        "Convert could not run. Check the ZIP has one shapefile set (.shp/.shx/.dbf, optional .prj), " +
        "confirm target CRS, then click Convert again."
      );
    }

    return (
      "Inspect could not run. Check the ZIP has one shapefile set (.shp/.shx/.dbf, optional .prj), " +
      "remove extra file types, then click Inspect again."
    );
  }

  function extractEntryName(detailsText) {
    const match = String(detailsText || "").match(/Entry '([^']+)'/i);
    return match && match[1] ? match[1] : "";
  }

  function extractExtension(detailsText) {
    const match = String(detailsText || "").match(/extension '([^']+)'/i);
    return match && match[1] ? match[1] : "";
  }

  async function parseApiError(response) {
    let rawBody = "";
    try {
      rawBody = await response.text();
    } catch (_error) {
      rawBody = "";
    }

    let payload = null;
    try {
      payload = rawBody ? JSON.parse(rawBody) : null;
    } catch (_error) {
      payload = null;
    }

    const errorObject = payload && typeof payload === "object" ? payload.error : null;
    const code = errorObject && typeof errorObject.code === "string" ? errorObject.code : "request_failed";
    const message =
      errorObject && typeof errorObject.message === "string"
        ? errorObject.message
        : `Request failed with HTTP ${response.status}.`;
    const details = errorObject && typeof errorObject.details === "string" ? errorObject.details : "n/a";
    const requestId = errorObject && typeof errorObject.request_id === "string" ? errorObject.request_id : null;
    const retryAfter = response.headers.get("Retry-After") || response.headers.get("retry-after");
    return {
      status: response.status,
      code,
      message,
      details,
      requestId,
      retryAfter,
    };
  }

  function parseDownloadFilename(contentDisposition) {
    const value = String(contentDisposition || "");
    const quotedMatch = value.match(/filename\*=UTF-8''([^;]+)|filename="([^"]+)"/i);
    if (quotedMatch) {
      const encodedName = quotedMatch[1];
      const quotedName = quotedMatch[2];
      if (typeof encodedName === "string" && encodedName) {
        try {
          return decodeURIComponent(encodedName);
        } catch (_error) {
          return encodedName;
        }
      }
      if (typeof quotedName === "string" && quotedName) {
        return quotedName;
      }
    }

    const plainMatch = value.match(/filename=([^;]+)/i);
    if (plainMatch && plainMatch[1]) {
      return plainMatch[1].trim();
    }

    return null;
  }

  function triggerDownload(blob, filename) {
    const objectUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = filename;
    anchor.style.display = "none";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(objectUrl);
  }
})();
