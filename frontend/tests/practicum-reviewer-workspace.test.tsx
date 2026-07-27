import { readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const root = join(process.cwd());

describe("practicum reviewer workspace", () => {
  it("keeps reviewer requests behind the authenticated same-origin proxy", () => {
    const client = readFileSync(join(root, "lib/research-practicum.ts"), "utf8");
    const proxy = readFileSync(join(root, "app/api/education/practica/[...path]/route.ts"), "utf8");

    expect(client).toContain('practicumRequest<PracticumReviewerQueue>(`/reviewer/queue');
    expect(client).toContain("expected_enrollment_updated_at");
    expect(client).toContain("PracticumRequestError");
    expect(client).toContain('params.set("learner_query"');
    expect(proxy).toContain('cookieStore.get("lionsforge_session")');
  });

  it("surfaces queue filters, provenance, readiness, evidence, and human decisions", () => {
    const workspace = readFileSync(join(root, "components/practicum-reviewer-workspace.tsx"), "utf8");

    expect(workspace).toContain("Review queue filters");
    expect(workspace).toContain("Learner search");
    expect(workspace).toContain('aria-live="polite"');
    expect(workspace).toContain("Learner-authored reflection");
    expect(workspace).toContain("Linked research records");
    expect(workspace).toContain("Deterministic workflow evaluation");
    expect(workspace).toContain("Human review history");
    expect(workspace).toContain("human review decision");
    expect(workspace).toContain("Approve");
    expect(workspace).toContain("Request revision");
    expect(workspace).toContain("Revision requests require reviewer notes");
  });

  it("recovers stale decisions and preserves completed detail", () => {
    const workspace = readFileSync(join(root, "components/practicum-reviewer-workspace.tsx"), "utf8");

    expect(workspace).toContain("reason.status === 409");
    expect(workspace).toContain("The latest review detail has been reloaded");
    expect(workspace).toContain('current.enrollment.status === "completed"');
    expect(workspace).toContain('role="status"');
  });

  it("keeps reviewer controls accessible, responsive, and reduced-motion safe", () => {
    const styles = readFileSync(join(root, "app/education/reviewer/reviewer.css"), "utf8");

    expect(styles).toContain("min-height:44px");
    expect(styles).toContain(":focus-visible");
    expect(styles).toContain(".reviewer-success");
    expect(styles).toContain(".reviewer-history");
    expect(styles).toContain("@media(max-width:600px)");
    expect(styles).toContain("@media(prefers-reduced-motion:reduce)");
  });

  it("protects the reviewer page with the existing authenticated session", () => {
    const page = readFileSync(join(root, "app/education/reviewer/page.tsx"), "utf8");

    expect(page).toContain("PracticumReviewerWorkspace");
    expect(page).toContain('redirect("/login")');
  });
});
