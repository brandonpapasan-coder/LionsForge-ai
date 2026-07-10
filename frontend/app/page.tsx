import Link from "next/link";

import { getBackendReadiness } from "@/lib/backend";

const modules = [
  "Research workspace",
  "Evidence validation",
  "Adaptive education",
  "Knowledge intelligence",
];

export default async function HomePage() {
  const readiness = await getBackendReadiness();
  const online = readiness?.status === "ready" || readiness?.status === "available";

  return (
    <main>
      <header className="topbar">
        <div>
          <p className="eyebrow">LIONSFORGE AI</p>
          <h1>Research intelligence built for evidence, clarity, and mastery.</h1>
        </div>
        <div className={`status ${online ? "online" : "offline"}`}>
          <span aria-hidden="true" />
          {online ? "Backend ready" : "Backend unavailable"}
        </div>
      </header>

      <section className="hero">
        <div>
          <p className="eyebrow">PRODUCTION FOUNDATION</p>
          <h2>Your command center for research and learning.</h2>
          <p className="lede">
            Create evidence-backed research, validate competing claims, and build financial expertise in one connected workspace.
          </p>
          <div className="actions">
            <Link href="/login">Start research</Link>
            <Link href="/register" className="secondary">Create account</Link>
          </div>
        </div>
        <aside className="readiness-card" aria-label="Backend readiness">
          <p className="eyebrow">SYSTEM READINESS</p>
          <dl>
            <div><dt>Application</dt><dd>{readiness?.status ?? "unknown"}</dd></div>
            <div><dt>Database</dt><dd>{readiness?.database ?? "unknown"}</dd></div>
            <div><dt>Market data</dt><dd>{readiness?.market_data ?? "unknown"}</dd></div>
            <div><dt>Provider</dt><dd>{readiness?.primary_provider ?? "not connected"}</dd></div>
          </dl>
        </aside>
      </section>

      <section className="module-grid" aria-label="Platform modules">
        {modules.map((module, index) => (
          <article key={module}>
            <span>0{index + 1}</span>
            <h3>{module}</h3>
            <p>Production module foundation ready for end-to-end backend integration.</p>
          </article>
        ))}
      </section>
    </main>
  );
}
