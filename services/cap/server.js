const express = require("express");
const path = require("node:path");
const fs = require("node:fs");
const Cap = require("@cap.js/server");

const PORT = Number(process.env.CAP_PORT || process.env.PORT || 3000);
const SITE_KEY = process.env.CAP_SITE_KEY;
const SECRET = process.env.CAP_SECRET;
const CORS_ORIGIN = process.env.CAP_CORS_ORIGIN || "*";
const DATA_DIR = process.env.CAP_DATA_DIR || "/var/lib/cap";
const ASSET_ROOT = process.env.CAP_ASSET_ROOT || "/workdir/cap";

const WIDGET_PATH =
  process.env.CAP_WIDGET_PATH || path.join(ASSET_ROOT, "widget/src/src/cap.js");
const FLOATING_PATH =
  process.env.CAP_FLOATING_PATH ||
  path.join(ASSET_ROOT, "widget/src/src/cap-floating.js");
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

requireEnv("CAP_SITE_KEY", SITE_KEY);
requireEnv("CAP_SECRET", SECRET);

requireFile("widget.js", WIDGET_PATH);
requireFile("floating.js", FLOATING_PATH);
requireFile("cap_wasm.js", WASM_JS_PATH);
requireFile("cap_wasm_bg.wasm", WASM_BG_PATH);

fs.mkdirSync(DATA_DIR, { recursive: true });

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
    const challenge = await cap.createChallenge();
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
  if (secret !== SECRET) {
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
