#!/usr/bin/env node

import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const lockPath = resolve(process.cwd(), "package-lock.json");
const packagePath = resolve(process.cwd(), "package.json");
const target = {
  version: "8.5.18",
  resolved: "https://registry.npmjs.org/postcss/-/postcss-8.5.18.tgz",
  integrity:
    "sha512-xdB1oSLHbz1vRWgCDalrCqEFTWzFlhqFC5tIHLMOSUIjhm3XXQ1qrFy8S/ESr1JYRRXqM3c1QFiMZUJdUTqyMQ==",
};

const packageJson = JSON.parse(readFileSync(packagePath, "utf8"));
if (packageJson.overrides?.postcss !== target.version) {
  throw new Error(`package.json must pin overrides.postcss to ${target.version}`);
}

const lock = JSON.parse(readFileSync(lockPath, "utf8"));
if (lock.lockfileVersion !== 3 || typeof lock.packages !== "object") {
  throw new Error("package-lock.json must use lockfileVersion 3 with a packages object");
}

const entry = lock.packages["node_modules/postcss"];
if (!entry || typeof entry !== "object") {
  throw new Error("package-lock.json is missing node_modules/postcss");
}

const allowedVersions = new Set(["8.5.12", target.version]);
if (!allowedVersions.has(entry.version)) {
  throw new Error(`unexpected locked PostCSS version: ${entry.version}`);
}

entry.version = target.version;
entry.resolved = target.resolved;
entry.integrity = target.integrity;
entry.dependencies = {
  nanoid: "^3.3.12",
  picocolors: "^1.1.1",
  "source-map-js": "^1.2.1",
};

writeFileSync(lockPath, `${JSON.stringify(lock, null, 2)}\n`, "utf8");
console.log(`Normalized PostCSS lock entry to ${target.version}`);
