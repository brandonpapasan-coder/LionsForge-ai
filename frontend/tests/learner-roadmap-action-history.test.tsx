import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const root = process.cwd();

describe("learner roadmap action history", () => {
  it("uses the authenticated proxy and forwards bounded ledger filters", () => {
    const client = readFileSync(join(root, "lib/roadmap-action-ledger.ts"), "utf8");
    const proxy = readFileSync(join(root, "app/api/education/practica/[...path]/route.ts"), "utf8");

    expect(client).toContain('fetch(`/api/education/practica${path}`');
    expect(client).toContain('"/roadmap-action-ledger/validate"');
    expect(client).toContain('params.set("template_slug"');
    expect(client).toContain('params.set("reason_code"');
    expect(client).toContain('params.set("acted_after"');
    expect(client).toContain('params.set("acted_before"');
    expect(client).toContain('window.location.href = "/login"');
    expect(proxy).toContain('cookieStore.get("lionsforge_session")');
    expect(proxy).toContain("request.nextUrl.search");
  });

  it("shows accessible filters, empty, loading, error, validation, and excluded-record states", () => {
    const workspace = readFileSync(join(root, "components/learner-roadmap-action-history.tsx"), "utf8");

    expect(workspace).toContain("Roadmap action history");
    expect(workspace).toContain('aria-label="Filter roadmap action history"');
    expect(workspace).toContain('aria-live="polite"');
    expect(workspace).toContain('role="alert"');
    expect(workspace).toContain("Loading roadmap action history");
    expect(workspace).toContain("No roadmap actions match the current filters.");
    expect(workspace).toContain("stored record(s) were excluded");
    expect(workspace).toContain("Ledger bundle validation passed.");
    expect(workspace).toContain("Ledger bundle validation failed");
  });

  it("renders privacy-safe provenance, enrollment links, and deterministic export", () => {
    const workspace = readFileSync(join(root, "components/learner-roadmap-action-history.tsx"), "utf8");

    expect(workspace).toContain("Ledger digest");
    expect(workspace).toContain("Action digest");
    expect(workspace).toContain("Research project ID");
    expect(workspace).toContain("recommendation_reason_codes");
    expect(workspace).toContain("Export deterministic ledger JSON");
    expect(workspace).toContain("learner-roadmap-action-ledger-");
    expect(workspace).toContain("Open enrollment");
    expect(workspace).toContain("enrollment_id=");
  });

  it("keeps non-credential, non-advice, and private-content guardrails visible", () => {
    const workspace = readFileSync(join(root, "components/learner-roadmap-action-history.tsx"), "utf8");

    expect(workspace).toContain("not accreditation, licensing, degree equivalence, professional certification, employment verification, individualized financial advice, or autonomous competency approval");
    expect(workspace).toContain("excludes project titles, research content, evidence summaries, reflections, prompts, reviewer notes, credentials, private user content, answer keys, and hidden assessment metadata");
  });

  it("integrates the history interface into the authenticated education page", () => {
    const page = readFileSync(join(root, "app/education/page.tsx"), "utf8");

    expect(page).toContain("LearnerRoadmapActionHistory");
    expect(page).toContain('redirect("/login")');
  });
});
