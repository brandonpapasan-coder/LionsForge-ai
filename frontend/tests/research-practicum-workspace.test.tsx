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

  it("surfaces learner reflection, evidence references, deterministic readiness, and human review history", () => {
    const workspace = readFileSync(join(root, "components/research-practicum-workspace.tsx"), "utf8");

    expect(workspace).toContain("Learner reflection");
    expect(workspace).toContain("Attach evidence");
    expect(workspace).toContain("Readiness summary");
    expect(workspace).toContain("Human review history");
    expect(workspace).toContain("Submit for review");
  });

  it("integrates the practicum into the authenticated education page", () => {
    const page = readFileSync(join(root, "app/education/page.tsx"), "utf8");

    expect(page).toContain("ResearchPracticumWorkspace");
    expect(page).toContain('redirect("/login")');
  });
});
