import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const root = process.cwd();

describe("learner competency gap plan", () => {
  it("uses the authenticated education proxy", () => {
    const client = readFileSync(join(root, "lib/competency-gap-plan.ts"), "utf8");
    const proxy = readFileSync(join(root, "app/api/education/practica/[...path]/route.ts"), "utf8");

    expect(client).toContain('fetch("/api/education/practica/competency-gap-plan"');
    expect(client).toContain('window.location.href = "/login"');
    expect(proxy).toContain('cookieStore.get("lionsforge_session")');
  });

  it("shows filters, provenance, rationale, accessible states, and deterministic export", () => {
    const workspace = readFileSync(join(root, "components/learner-competency-gap-plan.tsx"), "utf8");

    expect(workspace).toContain("Competency development roadmap");
    expect(workspace).toContain('aria-label="Filter competency roadmap"');
    expect(workspace).toContain('aria-live="polite"');
    expect(workspace).toContain('role="alert"');
    expect(workspace).toContain("Demonstrated");
    expect(workspace).toContain("Developing");
    expect(workspace).toContain("Not yet demonstrated");
    expect(workspace).toContain("Plan digest");
    expect(workspace).toContain("Source portfolio digest");
    expect(workspace).toContain("Adds a competency not yet demonstrated");
    expect(workspace).toContain("Strengthens a developing competency");
    expect(workspace).toContain("Export deterministic JSON");
    expect(workspace).toContain("learner-competency-gap-plan-");
    expect(workspace).toContain("No active practica are recommended");
  });

  it("keeps educational, non-credential, non-advice, and privacy guardrails visible", () => {
    const workspace = readFileSync(join(root, "components/learner-competency-gap-plan.tsx"), "utf8");

    expect(workspace).toContain("not accreditation, licensing, degree equivalence, professional certification, employment qualification, individualized financial advice, or autonomous competency approval");
    expect(workspace).toContain("excludes research content, reflections, prompts, reviewer notes, credentials, answer material, private user content, and hidden assessment metadata");
  });

  it("integrates the roadmap into the authenticated education page", () => {
    const page = readFileSync(join(root, "app/education/page.tsx"), "utf8");

    expect(page).toContain("LearnerCompetencyGapPlan");
    expect(page).toContain('redirect("/login")');
  });
});
