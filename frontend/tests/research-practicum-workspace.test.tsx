import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const root = join(process.cwd());

describe("research practicum workspace", () => {
  it("keeps practicum requests behind the authenticated same-origin proxy", () => {
    const client = readFileSync(join(root, "lib/research-practicum.ts"), "utf8");
    const proxy = readFileSync(join(root, "app/api/education/practica/[...path]/route.ts"), "utf8");

    expect(client).toContain('fetch(`/api/education/practica${path}`');
    expect(proxy).toContain('cookieStore.get("lionsforge_session")');
    expect(proxy).toContain('/api/v1/education/practica/');
  });

  it("surfaces learner reflection, searchable evidence, deterministic readiness, and human review history", () => {
    const workspace = readFileSync(join(root, "components/research-practicum-workspace.tsx"), "utf8");

    expect(workspace).toContain("Learner reflection");
    expect(workspace).toContain("Search project evidence");
    expect(workspace).toContain('aria-live="polite"');
    expect(workspace).toContain("Attach evidence");
    expect(workspace).toContain("Readiness summary");
    expect(workspace).toContain("Human review history");
    expect(workspace).toContain("Submit for review");
  });

  it("keeps practicum controls keyboard-visible, touch-sized, responsive, and reduced-motion safe", () => {
    const styles = readFileSync(join(root, "app/education/education.css"), "utf8");

    expect(styles).toContain("min-height: 44px");
    expect(styles).toContain(":focus-visible");
    expect(styles).toContain("@media (max-width: 600px)");
    expect(styles).toContain("@media (prefers-reduced-motion: reduce)");
  });

  it("integrates the practicum into the authenticated education page", () => {
    const page = readFileSync(join(root, "app/education/page.tsx"), "utf8");

    expect(page).toContain("ResearchPracticumWorkspace");
    expect(page).toContain('redirect("/login")');
  });
});