#!/usr/bin/env node

import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const lockPath = resolve(process.cwd(), "package-lock.json");
const packagePath = resolve(process.cwd(), "package.json");
const postcssTarget = {
  version: "8.5.18",
  resolved: "https://registry.npmjs.org/postcss/-/postcss-8.5.18.tgz",
  integrity:
    "sha512-xdB1oSLHbz1vRWgCDalrCqEFTWzFlhqFC5tIHLMOSUIjhm3XXQ1qrFy8S/ESr1JYRRXqM3c1QFiMZUJdUTqyMQ==",
};
const braceExpansionTarget = {
  version: "5.0.8",
  resolved: "https://registry.npmjs.org/brace-expansion/-/brace-expansion-5.0.8.tgz",
};

const packageJson = JSON.parse(readFileSync(packagePath, "utf8"));
if (packageJson.overrides?.postcss !== postcssTarget.version) {
  throw new Error(
    `package.json must pin overrides.postcss to ${postcssTarget.version}`,
  );
}
if (packageJson.overrides?.["brace-expansion"] !== braceExpansionTarget.version) {
  throw new Error(
    `package.json must pin overrides.brace-expansion to ${braceExpansionTarget.version}`,
  );
}

const lock = JSON.parse(readFileSync(lockPath, "utf8"));
if (lock.lockfileVersion !== 3 || typeof lock.packages !== "object") {
  throw new Error("package-lock.json must use lockfileVersion 3 with a packages object");
}

const postcssEntry = lock.packages["node_modules/postcss"];
if (!postcssEntry || typeof postcssEntry !== "object") {
  throw new Error("package-lock.json is missing node_modules/postcss");
}

const allowedPostcssVersions = new Set(["8.5.12", postcssTarget.version]);
if (!allowedPostcssVersions.has(postcssEntry.version)) {
  throw new Error(`unexpected locked PostCSS version: ${postcssEntry.version}`);
}

postcssEntry.version = postcssTarget.version;
postcssEntry.resolved = postcssTarget.resolved;
postcssEntry.integrity = postcssTarget.integrity;
postcssEntry.dependencies = {
  nanoid: "^3.3.12",
  picocolors: "^1.1.1",
  "source-map-js": "^1.2.1",
};

const braceExpansionEntries = Object.entries(lock.packages).filter(([path]) =>
  path.endsWith("node_modules/brace-expansion"),
);
if (braceExpansionEntries.length === 0) {
  throw new Error("package-lock.json is missing brace-expansion entries");
}

const allowedBraceExpansionVersions = new Set([
  "1.1.12",
  "2.0.2",
  "5.0.7",
  braceExpansionTarget.version,
]);
for (const [path, entry] of braceExpansionEntries) {
  if (!entry || typeof entry !== "object") {
    throw new Error(`invalid brace-expansion lock entry: ${path}`);
  }
  if (!allowedBraceExpansionVersions.has(entry.version)) {
    throw new Error(`unexpected locked brace-expansion version at ${path}: ${entry.version}`);
  }
  entry.version = braceExpansionTarget.version;
  entry.resolved = braceExpansionTarget.resolved;
  delete entry.integrity;
  entry.license = "MIT";
  entry.dependencies = {
    "balanced-match": "^4.0.0",
  };
  entry.engines = {
    node: "18 || 20 || >=22",
  };
}

writeFileSync(lockPath, `${JSON.stringify(lock, null, 2)}\n`, "utf8");
console.log(`Normalized PostCSS lock entry to ${postcssTarget.version}`);
console.log(
  `Normalized ${braceExpansionEntries.length} brace-expansion lock entries to ${braceExpansionTarget.version}`,
);
