import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const root = process.cwd();

describe("learner competency gap plan", () => {
  it("uses the authenticated education proxy for roadmap reads and enrollment actions", () => {
    const client = readFileSync(join(root, "lib/competency-gap-plan.ts"), "utf8");
    const proxy = readFileSync(join(root, "app/api/education/practica/[...path]/route.ts"), "utf8");

    expect(client).toContain('fetch(`/api/education/practica${path}`');
    expect(client).toContain('"/competency-gap-plan"');
    expect(client).toContain('"/roadmap-practicum-enrollment"');
    expect(client).toContain("template_slug, template_version, research_project_id");
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

  it("requires explicit project selection and learner intent before enrollment", () => {
    const workspace = readFileSync(join(root, "components/learner-competency-gap-plan.tsx"), "utf8");

    expect(workspace).toContain("Start recommended practicum");
    expect(workspace).toContain('fetch("/api/research-projects"');
    expect(workspace).toContain('aria-label="Confirm recommended practicum enrollment"');
    expect(workspace).toContain("Select one of your research projects");
    expect(workspace).toContain('type="checkbox"');
    expect(workspace).toContain("I explicitly request this enrollment");
    expect(workspace).toContain("No enrollment occurs until you explicitly submit this form.");
    expect(workspace).toContain("Confirm and start practicum");
  });

  it("surfaces stale, prerequisite, duplicate, and success-refresh behavior through the action boundary", () => {
    const client = readFileSync(join(root, "lib/competency-gap-plan.ts"), "utf8");
    const workspace = readFileSync(join(root, "components/learner-competency-gap-plan.tsx"), "utf8");

    expect(client).toContain("Complete these prerequisite lessons first");
    expect(client).toContain("The roadmap action could not be completed.");
    expect(workspace).toContain("The server will regenerate the current roadmap");
    expect(workspace).toContain("verify prerequisites and project ownership, and prevent duplicate enrollment");
    expect(workspace).toContain("window.location.reload()");
    expect(workspace).toContain("Revalidating the current recommendation and enrollment requirements");
  });

  it("keeps educational, non-credential, non-advice, and privacy guardrails visible", () => {
    const workspace = readFileSync(join(root, "components/learner-competency-gap-plan.tsx"), "utf8");

    expect(workspace).toContain("not accreditation, licensing, degree equivalence, professional certification, employment qualification, individualized financial advice, or autonomous competency approval");
    expect(workspace).toContain("excludes research content, reflections, prompts, reviewer notes, credentials, answer material, private user content, and hidden assessment metadata");
    expect(workspace).toContain("not a credential or autonomous competency decision");
  });

  it("integrates the roadmap into the authenticated education page", () => {
    const page = readFileSync(join(root, "app/education/page.tsx"), "utf8");

    expect(page).toContain("LearnerCompetencyGapPlan");
    expect(page).toContain('redirect("/login")');
  });
});
