const express = require("express");
const path = require("node:path");
const fs = require("node:fs");
const Cap = require("@cap.js/server");
const { loadChallengeConfig } = require("./config");

const PORT = Number(process.env.CAP_PORT || process.env.PORT || 3000);
const SITE_KEY = process.env.CAP_SITE_KEY;
const SECRET_PATH = process.env.CAP_SECRET_FILE;
let SECRET = process.env.CAP_SECRET;
if (SECRET && SECRET_PATH) {
  console.error("[cap] Configure CAP_SECRET_FILE or CAP_SECRET, not both");
  process.exit(1);
}
if (!SECRET && SECRET_PATH) {
  try {
    SECRET = fs.readFileSync(SECRET_PATH, "utf8").trim();
  } catch (error) {
    console.error(`[cap] Failed to read CAP_SECRET_FILE at ${SECRET_PATH}`, error);
    process.exit(1);
  }
}
const currentSecret = () => {
  if (!SECRET_PATH) return SECRET;
  return fs.readFileSync(SECRET_PATH, "utf8").trim();
};
const CORS_ORIGIN = process.env.CAP_CORS_ORIGIN || "*";
const DATA_DIR = process.env.CAP_DATA_DIR || "/var/lib/cap";
const ASSET_ROOT = process.env.CAP_ASSET_ROOT || "/workdir/cap";
const CHALLENGE_CONFIG = loadChallengeConfig();

const WIDGET_PATH =
  process.env.CAP_WIDGET_PATH || path.join(ASSET_ROOT, "widget/src/cap.min.js");
const FLOATING_PATH =
  process.env.CAP_FLOATING_PATH ||
  path.join(ASSET_ROOT, "widget/src/cap-floating.min.js");
const WASM_JS_PATH =
  process.env.CAP_WASM_JS_PATH ||
  path.join(ASSET_ROOT, "wasm/src/browser/cap_wasm.js");
const WASM_BG_PATH =
  process.env.CAP_WASM_BG_PATH ||
  path.join(ASSET_ROOT, "wasm/src/browser/cap_wasm_bg.wasm");

const requireEnv = (name, value) => {
  if (!value) {
    console.error(`[cap] Missing required env: ${name}`);
    process.exit(1);
  }
};

const requireFile = (label, filePath) => {
  if (!fs.existsSync(filePath)) {
    console.error(`[cap] Missing ${label} at ${filePath}`);
    process.exit(1);
  }
};

const validatePersistence = (dataDir) => {
  fs.mkdirSync(dataDir, { recursive: true });
  const directory = fs.lstatSync(dataDir);
  if (!directory.isDirectory() || directory.isSymbolicLink()) {
    throw new Error(`CAP_DATA_DIR must be a real directory: ${dataDir}`);
  }
  fs.accessSync(dataDir, fs.constants.R_OK | fs.constants.W_OK | fs.constants.X_OK);

  const ledgerPath = path.join(dataDir, "tokensList.json");
  if (fs.existsSync(ledgerPath)) {
    const ledger = fs.lstatSync(ledgerPath);
    if (!ledger.isFile() || ledger.isSymbolicLink()) {
      throw new Error(`CAP token ledger must be a regular file: ${ledgerPath}`);
    }
    fs.accessSync(ledgerPath, fs.constants.R_OK | fs.constants.W_OK);
    const parsed = JSON.parse(fs.readFileSync(ledgerPath, "utf8"));
    if (parsed === null || Array.isArray(parsed) || typeof parsed !== "object") {
      throw new Error("CAP token ledger must contain a JSON object");
    }
  }

  const probePath = path.join(dataDir, `.cap-write-probe-${process.pid}`);
  const descriptor = fs.openSync(probePath, "wx", 0o600);
  try {
    fs.fsyncSync(descriptor);
  } finally {
    fs.closeSync(descriptor);
    fs.unlinkSync(probePath);
  }
};

requireEnv("CAP_SITE_KEY", SITE_KEY);
requireEnv("CAP_SECRET (or CAP_SECRET_FILE)", SECRET);

requireFile("widget.js", WIDGET_PATH);
requireFile("floating.js", FLOATING_PATH);
requireFile("cap_wasm.js", WASM_JS_PATH);
requireFile("cap_wasm_bg.wasm", WASM_BG_PATH);

try {
  validatePersistence(DATA_DIR);
} catch (error) {
  console.error(`[cap] Persistence readiness failed for ${DATA_DIR}`, error);
  process.exit(1);
}

const cap = new Cap({
  tokens_store_path: path.join(DATA_DIR, "tokensList.json"),
});

const allowedOrigins = CORS_ORIGIN.split(",")
  .map((origin) => origin.trim())
  .filter(Boolean);
const allowAllOrigins = allowedOrigins.length === 0 || allowedOrigins.includes("*");

const app = express();
app.disable("x-powered-by");
app.use(express.json({ limit: "1mb" }));
app.use(express.urlencoded({ extended: false }));
app.use((req, res, next) => {
  if (allowAllOrigins) {
    res.setHeader("Access-Control-Allow-Origin", "*");
  } else if (req.headers.origin && allowedOrigins.includes(req.headers.origin)) {
    res.setHeader("Access-Control-Allow-Origin", req.headers.origin);
    res.setHeader("Vary", "Origin");
  } else if (allowedOrigins.length > 0) {
    res.setHeader("Access-Control-Allow-Origin", allowedOrigins[0]);
  }
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") {
    res.sendStatus(204);
    return;
  }
  next();
});

const assertSiteKey = (req, res) => {
  if (req.params.siteKey !== SITE_KEY) {
    res.status(404).json({ success: false, message: "Unknown site key" });
    return false;
  }
  return true;
};

app.get("/cap/health", (req, res) => {
  res.json({ status: "ok" });
});

app.get("/cap/assets/widget.js", (req, res) => {
  res.type("application/javascript");
  res.sendFile(WIDGET_PATH);
});

app.get("/cap/assets/floating.js", (req, res) => {
  res.type("application/javascript");
  res.sendFile(FLOATING_PATH);
});

app.get("/cap/assets/cap_wasm.js", (req, res) => {
  res.type("application/javascript");
  res.sendFile(WASM_JS_PATH);
});

app.get("/cap/assets/cap_wasm_bg.wasm", (req, res) => {
  res.type("application/wasm");
  res.sendFile(WASM_BG_PATH);
});

app.post("/cap/:siteKey/challenge", async (req, res) => {
  if (!assertSiteKey(req, res)) {
    return;
  }
  try {
    const challenge = await cap.createChallenge(CHALLENGE_CONFIG);
    res.json(challenge);
  } catch (error) {
    console.error("[cap] challenge error", error);
    res.status(500).json({ success: false });
  }
});

app.post("/cap/:siteKey/redeem", async (req, res) => {
  if (!assertSiteKey(req, res)) {
    return;
  }
  const { token, solutions } = req.body || {};
  if (!token || !Array.isArray(solutions)) {
    res.status(400).json({ success: false, message: "Missing token or solutions" });
    return;
  }
  try {
    const result = await cap.redeemChallenge({ token, solutions });
    res.json(result);
  } catch (error) {
    console.error("[cap] redeem error", error);
    res.status(500).json({ success: false });
  }
});

app.post("/cap/:siteKey/siteverify", async (req, res) => {
  if (!assertSiteKey(req, res)) {
    return;
  }
  const { secret, response } = req.body || {};
  if (!secret || !response) {
    res.status(400).json({ success: false, message: "Missing secret or response" });
    return;
  }
  let expectedSecret;
  try {
    expectedSecret = currentSecret();
  } catch (error) {
    console.error("[cap] Failed to reload CAP_SECRET_FILE", error);
    res.status(500).json({ success: false });
    return;
  }
  if (secret !== expectedSecret) {
    res.status(403).json({ success: false, message: "Invalid secret" });
    return;
  }
  try {
    const result = await cap.validateToken(response);
    res.json(result);
  } catch (error) {
    console.error("[cap] siteverify error", error);
    res.status(500).json({ success: false });
  }
});

app.listen(PORT, "0.0.0.0", () => {
  console.log(`[cap] listening on 0.0.0.0:${PORT}`);
});
