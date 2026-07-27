"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { loadChallengeConfig } = require("./config");

test("defaults to click-only challenge parameters", () => {
  assert.deepEqual(loadChallengeConfig({}), {
    challengeCount: 1,
    challengeDifficulty: 1,
  });
});

test("accepts positive integer overrides", () => {
  assert.deepEqual(
    loadChallengeConfig({
      CAP_CHALLENGE_COUNT: "50",
      CAP_CHALLENGE_DIFFICULTY: "4",
    }),
    {
      challengeCount: 50,
      challengeDifficulty: 4,
    },
  );
});

test("rejects invalid challenge parameters", () => {
  for (const value of ["0", "-1", "1.5", "invalid"]) {
    assert.throws(
      () => loadChallengeConfig({ CAP_CHALLENGE_COUNT: value }),
      /CAP_CHALLENGE_COUNT must be a positive integer/,
    );
  }
});
