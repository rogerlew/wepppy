import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export default {
    rootDir: resolve(__dirname, ".."),
    testEnvironment: "jsdom",
    testMatch: [
        "<rootDir>/controllers_js/__tests__/**/*.test.js",
        "<rootDir>/static/js/gl-dashboard/__tests__/**/*.test.js",
    ],
    moduleFileExtensions: ["js", "json"],
    transform: {}
};
