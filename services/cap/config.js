"use strict";

const readPositiveInteger = (env, name, fallback) => {
  const raw = env[name];
  if (raw === undefined || raw.trim() === "") {
    return fallback;
  }
  const value = Number(raw);
  if (!Number.isInteger(value) || value < 1) {
    throw new Error(`[cap] ${name} must be a positive integer`);
  }
  return value;
};

const loadChallengeConfig = (env = process.env) => ({
  challengeCount: readPositiveInteger(env, "CAP_CHALLENGE_COUNT", 1),
  challengeDifficulty: readPositiveInteger(env, "CAP_CHALLENGE_DIFFICULTY", 1),
});

module.exports = { loadChallengeConfig, readPositiveInteger };
