#!/usr/bin/env node
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");

function prng(seed, length) {
  let hash = 2166136261;
  for (let index = 0; index < seed.length; index += 1) {
    hash ^= seed.charCodeAt(index);
    hash += (hash << 1) + (hash << 4) + (hash << 7) + (hash << 8) + (hash << 24);
  }
  let state = hash >>> 0;
  let result = "";
  while (result.length < length) {
    state ^= state << 13;
    state ^= state >>> 17;
    state ^= state << 5;
    result += (state >>> 0).toString(16).padStart(8, "0");
  }
  return result.substring(0, length);
}

function solve(token, challenge) {
  if (!Number.isInteger(challenge.c) || challenge.c < 1 || challenge.c > 8 ||
      !Number.isInteger(challenge.s) || challenge.s < 1 || challenge.s > 64 ||
      !Number.isInteger(challenge.d) || challenge.d < 1 || challenge.d > 6) {
    throw new Error("challenge parameters exceed canary safety bounds");
  }
  const solutions = [];
  for (let index = 1; index <= challenge.c; index += 1) {
    const salt = prng(`${token}${index}`, challenge.s);
    const target = prng(`${token}${index}d`, challenge.d);
    let candidate = 0;
    while (crypto.createHash("sha256").update(salt + candidate).digest("hex").startsWith(target) === false) {
      candidate += 1;
      if (candidate > 2000000) throw new Error("challenge work exceeds canary safety bound");
    }
    solutions.push(candidate);
  }
  return solutions;
}

async function post(url, body) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10000);
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: controller.signal,
  });
  clearTimeout(timer);
  if (!response.ok) throw new Error(`${url} returned HTTP ${response.status}`);
  return response.json();
}

async function main() {
  const siteKey = process.env.CAP_SITE_KEY;
  const secret = fs.readFileSync(process.env.CAP_SECRET_FILE, "utf8").trim();
  const base = `http://127.0.0.1:${process.env.CAP_PORT || process.env.PORT || 3000}/cap/${siteKey}`;
  const created = await post(`${base}/challenge`, {});
  const redeemed = await post(`${base}/redeem`, {
    token: created.token,
    solutions: solve(created.token, created.challenge),
  });
  if (!redeemed.success || !redeemed.token) throw new Error("challenge redemption failed");
  const verified = await post(`${base}/siteverify`, { secret, response: redeemed.token });
  if (!verified.success) throw new Error("siteverify failed");
  console.log("cap-functional-canary: challenge/redeem/siteverify passed");
}

main().catch((error) => {
  console.error(`cap-functional-canary: ${error.message}`);
  process.exit(1);
});
