import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const root = process.cwd();

describe("learner competency portfolio", () => {
  it("uses the authenticated practicum proxy and forwards portfolio filters", () => {
    const client = readFileSync(join(root, "lib/research-practicum.ts"), "utf8");
    const proxy = readFileSync(join(root, "app/api/education/practica/[...path]/route.ts"), "utf8");

    expect(client).toContain('`/competency-portfolio${competencyPortfolioQuery(filters)}`');
    expect(client).toContain('params.set("competency_key"');
    expect(client).toContain('params.set("template_slug"');
    expect(proxy).toContain('cookieStore.get("lionsforge_session")');
  });

  it("shows provenance, accessible states, filters, and deterministic export", () => {
    const workspace = readFileSync(join(root, "components/learner-competency-portfolio.tsx"), "utf8");

    expect(workspace).toContain("Learner competency portfolio");
    expect(workspace).toContain('aria-label="Filter competency portfolio"');
    expect(workspace).toContain('aria-live="polite"');
    expect(workspace).toContain('role="alert"');
    expect(workspace).toContain("Export deterministic JSON");
    expect(workspace).toContain("learner-competency-portfolio-");
    expect(workspace).toContain("Portfolio digest");
    expect(workspace).toContain("Completion audit digest");
    expect(workspace).toContain("No completed, human-approved practica match");
  });

  it("keeps non-credential and privacy guardrails visible", () => {
    const workspace = readFileSync(join(root, "components/learner-competency-portfolio.tsx"), "utf8");

    expect(workspace).toContain("not accreditation, licensing, degree equivalence, professional certification, employment verification, or autonomous competency approval");
    expect(workspace).toContain("excludes research content, learner reflections, prompts, reviewer notes, credentials, answer material, and private user content");
  });

  it("integrates the portfolio into the authenticated education page", () => {
    const page = readFileSync(join(root, "app/education/page.tsx"), "utf8");

    expect(page).toContain("LearnerCompetencyPortfolio");
    expect(page).toContain('redirect("/login")');
  });
});
