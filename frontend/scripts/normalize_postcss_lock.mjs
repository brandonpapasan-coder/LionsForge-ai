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
  braceExpansion: "5.0.8",
};

if (packageJson.overrides?.postcss !== exactPins.postcss) {
  throw new Error(`package.json must pin overrides.postcss to ${exactPins.postcss}`);
}
if (packageJson.overrides?.["brace-expansion"] !== exactPins.braceExpansion) {
  throw new Error(
    `package.json must pin overrides.brace-expansion to ${exactPins.braceExpansion}`,
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

const expected = [
  ["node_modules/postcss", exactPins.postcss, "PostCSS"],
  ["node_modules/vitest", exactPins.vitest, "Vitest"],
  ["node_modules/@vitest/coverage-v8", exactPins.coverage, "@vitest/coverage-v8"],
  ["node_modules/brace-expansion", exactPins.braceExpansion, "brace-expansion"],
];
for (const [path, version, label] of expected) {
  const entry = lock.packages[path];
  if (!entry || entry.version !== version) {
    throw new Error(`package-lock.json must resolve ${label} ${version}`);
  }
}

for (const [path, entry] of Object.entries(lock.packages)) {
  if (!path.endsWith("node_modules/brace-expansion") || !entry?.version) {
    continue;
  }
  if (entry.version !== exactPins.braceExpansion) {
    throw new Error(
      `package-lock.json must resolve brace-expansion ${exactPins.braceExpansion} at ${path}`,
    );
  }
}

console.log(`Regenerated lock with PostCSS ${exactPins.postcss}`);
console.log(`Regenerated lock with Vitest ${exactPins.vitest}`);
console.log(`Regenerated lock with @vitest/coverage-v8 ${exactPins.coverage}`);
console.log(`Regenerated lock with brace-expansion ${exactPins.braceExpansion}`);
