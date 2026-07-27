import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const root = process.cwd();

describe("learner roadmap outcome insights", () => {
  it("uses the authenticated proxy and forwards all bounded filters", () => {
    const client = readFileSync(join(root, "lib/roadmap-outcome-insights.ts"), "utf8");
    const proxy = readFileSync(join(root, "app/api/education/practica/[...path]/route.ts"), "utf8");

    expect(client).toContain('fetch(`/api/education/practica${path}`');
    expect(client).toContain('"/roadmap-outcome-insights/validate"');
    for (const filter of ["template_slug", "reason_code", "outcome_status", "acted_after", "acted_before", "completed_after", "completed_before"]) {
      expect(client).toContain(`params.set("${filter}"`);
    }
    expect(client).toContain('window.location.href = "/login"');
    expect(proxy).toContain('cookieStore.get("lionsforge_session")');
  });

  it("renders accessible loading, error, empty, exclusion, validation, and suppression states", () => {
    const component = readFileSync(join(root, "components/learner-roadmap-outcome-insights.tsx"), "utf8");

    expect(component).toContain("Roadmap outcome insights");
    expect(component).toContain('aria-label="Filter roadmap outcome insights"');
    expect(component).toContain('aria-live="polite"');
    expect(component).toContain('role="alert"');
    expect(component).toContain("Loading roadmap outcome insights");
    expect(component).toContain("No roadmap outcome data matches the current filters.");
    expect(component).toContain("source record(s) were excluded");
    expect(component).toContain("Insight bundle validation passed.");
    expect(component).toContain("Insight bundle validation failed");
    expect(component).toContain("Rates and cycle-time statistics are hidden until this group has at least");
  });

  it("shows explanatory metrics, provenance, grouped insights, and deterministic export", () => {
    const component = readFileSync(join(root, "components/learner-roadmap-outcome-insights.tsx"), "utf8");

    expect(component).toContain("Completed-action rate");
    expect(component).toContain("Median completion time");
    expect(component).toContain("Insight digest");
    expect(component).toContain("Source report digest");
    expect(component).toContain("By practicum template");
    expect(component).toContain("By recommendation reason");
    expect(component).toContain("Export deterministic insight JSON");
    expect(component).toContain("learner-roadmap-outcome-insights-");
  });

  it("keeps non-causation, non-credentialing, non-ranking, and privacy guardrails visible", () => {
    const component = readFileSync(join(root, "components/learner-roadmap-outcome-insights.tsx"), "utf8");

    expect(component).toContain("not proof of learning effectiveness, causation, accreditation, licensing, degree equivalence, professional certification, employment qualification or verification, individualized financial advice, autonomous competency approval, ranking, or prediction");
    expect(component).toContain("excludes project titles, research content, evidence summaries or titles, reflections, prompts, reviewer notes, credentials, private user content, answer keys, and hidden assessment metadata");
  });

  it("integrates the insight interface into the authenticated education page", () => {
    const page = readFileSync(join(root, "app/education/page.tsx"), "utf8");

    expect(page).toContain("LearnerRoadmapOutcomeInsights");
    expect(page).toContain('redirect("/login")');
  });
});
