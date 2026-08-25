#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const DATA_DIR = "/var/lib/cap";
const LEDGER = path.join(DATA_DIR, "tokensList.json");
const CAP_UID = 10001;
const CAP_GID = 10001;

if (process.getuid() !== 0) {
  console.error("cap migration must run as root inside the isolated helper container");
  process.exit(1);
}

const root = fs.lstatSync(DATA_DIR);
if (!root.isDirectory() || root.isSymbolicLink()) {
  throw new Error(`${DATA_DIR} must be a real directory`);
}
const entries = fs.readdirSync(DATA_DIR);
const unexpected = entries.filter((entry) => entry !== "tokensList.json");
if (unexpected.length > 0) {
  throw new Error(`unexpected CAP data entries: ${unexpected.join(", ")}`);
}

let checksum = "absent";
if (fs.existsSync(LEDGER)) {
  const ledger = fs.lstatSync(LEDGER);
  if (!ledger.isFile() || ledger.isSymbolicLink()) {
    throw new Error(`${LEDGER} must be a regular file`);
  }
  const contents = fs.readFileSync(LEDGER);
  if (contents.length === 0) {
    throw new Error(`${LEDGER} must not be empty`);
  }
  const parsed = JSON.parse(contents.toString("utf8"));
  if (parsed === null || Array.isArray(parsed) || typeof parsed !== "object") {
    throw new Error(`${LEDGER} must contain a JSON object`);
  }
  checksum = crypto.createHash("sha256").update(contents).digest("hex");
  fs.chownSync(LEDGER, CAP_UID, CAP_GID);
  fs.chmodSync(LEDGER, 0o600);
  const after = crypto.createHash("sha256").update(fs.readFileSync(LEDGER)).digest("hex");
  if (after !== checksum) throw new Error("CAP ledger content changed during metadata migration");
}

fs.chownSync(DATA_DIR, CAP_UID, CAP_GID);
fs.chmodSync(DATA_DIR, 0o700);
console.log(`cap-data-migrated ledger_sha256=${checksum}`);
