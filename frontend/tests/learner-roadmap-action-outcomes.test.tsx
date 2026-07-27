import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const root = process.cwd();

describe("learner roadmap action outcomes", () => {
  it("uses the authenticated proxy and forwards bounded outcome filters", () => {
    const client = readFileSync(join(root, "lib/roadmap-action-outcomes.ts"), "utf8");
    const proxy = readFileSync(join(root, "app/api/education/practica/[...path]/route.ts"), "utf8");

    expect(client).toContain('fetch(`/api/education/practica${path}`');
    expect(client).toContain('"/roadmap-action-outcomes/validate"');
    expect(client).toContain('params.set("template_slug"');
    expect(client).toContain('params.set("reason_code"');
    expect(client).toContain('params.set("outcome_status"');
    expect(client).toContain('params.set("acted_after"');
    expect(client).toContain('params.set("acted_before"');
    expect(client).toContain('params.set("completed_after"');
    expect(client).toContain('params.set("completed_before"');
    expect(client).toContain('window.location.href = "/login"');
    expect(proxy).toContain('cookieStore.get("lionsforge_session")');
    expect(proxy).toContain("request.nextUrl.search");
  });

  it("shows accessible filters, loading, error, empty, validation, and exclusion states", () => {
    const workspace = readFileSync(join(root, "components/learner-roadmap-action-outcomes.tsx"), "utf8");

    expect(workspace).toContain("Roadmap action outcomes");
    expect(workspace).toContain('aria-label="Filter roadmap action outcomes"');
    expect(workspace).toContain('aria-live="polite"');
    expect(workspace).toContain('role="alert"');
    expect(workspace).toContain("Loading roadmap action outcomes");
    expect(workspace).toContain("No roadmap action outcomes match the current filters.");
    expect(workspace).toContain("stored record(s) were excluded");
    expect(workspace).toContain("Outcome bundle validation passed.");
    expect(workspace).toContain("Outcome bundle validation failed");
  });

  it("renders progression, completion provenance, enrollment links, and deterministic export", () => {
    const workspace = readFileSync(join(root, "components/learner-roadmap-action-outcomes.tsx"), "utf8");

    expect(workspace).toContain("Report digest");
    expect(workspace).toContain("Completed");
    expect(workspace).toContain("Action digest");
    expect(workspace).toContain("Completion record digest");
    expect(workspace).toContain("Research project ID");
    expect(workspace).toContain("Export deterministic outcome JSON");
    expect(workspace).toContain("learner-roadmap-action-outcomes-");
    expect(workspace).toContain("Open enrollment");
    expect(workspace).toContain("enrollment_id=");
  });

  it("keeps non-credential, non-advice, non-causation, and privacy guardrails visible", () => {
    const workspace = readFileSync(join(root, "components/learner-roadmap-action-outcomes.tsx"), "utf8");

    expect(workspace).toContain("not accreditation, licensing, degree equivalence, professional certification, employment verification, individualized financial advice, autonomous competency approval, or proof that learning caused an external outcome");
    expect(workspace).toContain("excludes project titles, research content, evidence summaries, reflections, prompts, reviewer notes, credentials, private user content, answer keys, and hidden assessment metadata");
  });

  it("integrates the outcome interface into the authenticated education page", () => {
    const page = readFileSync(join(root, "app/education/page.tsx"), "utf8");

    expect(page).toContain("LearnerRoadmapActionOutcomes");
    expect(page).toContain('redirect("/login")');
  });
});
