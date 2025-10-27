#!/usr/bin/env node

/**
 * Append lint telemetry data to a JSONL file.
 * Usage: node docs_quality_telemetry.js <lintJsonPath> <outputPath> <commit> <durationMs> <timestamp>
 */

const fs = require("fs");
const path = require("path");

const [lintJsonPath, outputPath, commitSha, durationMs, timestamp] = process.argv.slice(2);

function exitOk(message) {
  if (message) {
    console.warn(`[telemetry] ${message}`);
  }
  process.exit(0);
}

if (!lintJsonPath || !outputPath || !commitSha || !durationMs || !timestamp) {
  exitOk("Missing arguments, skipping telemetry write.");
}

let summary = { files_scanned: 0, errors: 0, warnings: 0 };

try {
  const raw = fs.readFileSync(lintJsonPath, "utf8");
  const parsed = JSON.parse(raw);
  if (parsed && typeof parsed === "object" && parsed.summary) {
    summary = {
      files_scanned: Number(parsed.summary.files_scanned ?? 0),
      errors: Number(parsed.summary.errors ?? 0),
      warnings: Number(parsed.summary.warnings ?? 0),
    };
  }
} catch (error) {
  exitOk(`Failed to parse ${lintJsonPath}: ${error.message}`);
}

const record = {
  timestamp,
  commit: commitSha,
  lint: {
    duration_ms: Number(durationMs) || 0,
    files_scanned: summary.files_scanned,
    errors: summary.errors,
    warnings: summary.warnings,
  },
};

try {
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.appendFileSync(outputPath, JSON.stringify(record) + "\n", "utf8");
} catch (error) {
  exitOk(`Failed to append telemetry: ${error.message}`);
}

exitOk();
