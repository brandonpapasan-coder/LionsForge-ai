#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const lockPath = resolve(process.cwd(), "package-lock.json");
const packagePath = resolve(process.cwd(), "package.json");
const packageJson = JSON.parse(readFileSync(packagePath, "utf8"));

const exactPins = {
  postcss: "8.5.18",
  vitest: "3.2.7",
  coverage: "3.2.7",
  testExclude: "8.0.0",
};

if (packageJson.overrides?.postcss !== exactPins.postcss) {
  throw new Error(`package.json must pin overrides.postcss to ${exactPins.postcss}`);
}
if (packageJson.overrides?.["test-exclude"] !== exactPins.testExclude) {
  throw new Error(
    `package.json must pin overrides.test-exclude to ${exactPins.testExclude}`,
  );
}
if (packageJson.devDependencies?.vitest !== exactPins.vitest) {
  throw new Error(`package.json must pin vitest to ${exactPins.vitest}`);
}
if (packageJson.devDependencies?.["@vitest/coverage-v8"] !== exactPins.coverage) {
  throw new Error(
    `package.json must pin @vitest/coverage-v8 to ${exactPins.coverage}`,
  );
}

execFileSync(
  "npm",
  ["install", "--package-lock-only", "--ignore-scripts", "--no-audit", "--no-fund"],
  { stdio: "inherit" },
);

const lock = JSON.parse(readFileSync(lockPath, "utf8"));
if (lock.lockfileVersion !== 3 || typeof lock.packages !== "object") {
  throw new Error("package-lock.json must use lockfileVersion 3 with a packages object");
}

const postcssEntry = lock.packages["node_modules/postcss"];
if (!postcssEntry || postcssEntry.version !== exactPins.postcss) {
  throw new Error(`package-lock.json must resolve PostCSS ${exactPins.postcss}`);
}

const vitestEntry = lock.packages["node_modules/vitest"];
if (!vitestEntry || vitestEntry.version !== exactPins.vitest) {
  throw new Error(`package-lock.json must resolve Vitest ${exactPins.vitest}`);
}

const coverageEntry = lock.packages["node_modules/@vitest/coverage-v8"];
if (!coverageEntry || coverageEntry.version !== exactPins.coverage) {
  throw new Error(
    `package-lock.json must resolve @vitest/coverage-v8 ${exactPins.coverage}`,
  );
}

const testExcludeEntries = Object.entries(lock.packages).filter(
  ([path, entry]) => path.endsWith("node_modules/test-exclude") && entry?.version,
);
if (testExcludeEntries.length === 0) {
  throw new Error("package-lock.json must resolve test-exclude");
}
for (const [path, entry] of testExcludeEntries) {
  if (entry.version !== exactPins.testExclude) {
    throw new Error(
      `package-lock.json must resolve test-exclude ${exactPins.testExclude} at ${path}`,
    );
  }
}

for (const [path, entry] of Object.entries(lock.packages)) {
  if (!path.endsWith("node_modules/brace-expansion") || !entry?.version) {
    continue;
  }
  const parts = entry.version.split(".").map((value) => Number.parseInt(value, 10));
  const [major = 0, minor = 0, patch = 0] = parts;
  const vulnerable = major === 5 && minor === 0 && patch <= 7;
  if (vulnerable) {
    throw new Error(`vulnerable brace-expansion version remains at ${path}: ${entry.version}`);
  }
}

console.log(`Regenerated lock with PostCSS ${exactPins.postcss}`);
console.log(`Regenerated lock with Vitest ${exactPins.vitest}`);
console.log(`Regenerated lock with @vitest/coverage-v8 ${exactPins.coverage}`);
console.log(
  `Verified ${testExcludeEntries.length} test-exclude lock entr${
    testExcludeEntries.length === 1 ? "y" : "ies"
  } at ${exactPins.testExclude}`,
);
