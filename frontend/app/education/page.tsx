import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import type { LearningDashboard } from "@/lib/education";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

async function getLearningDashboard(): Promise<LearningDashboard> {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) redirect("/login");

  const response = await fetch(`${backendUrl}/api/v1/education/dashboard`, {
    headers: { authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!response.ok) redirect("/dashboard");
  return (await response.json()) as LearningDashboard;
}

export default async function EducationPage() {
  const dashboard = await getLearningDashboard();
  const recommended = dashboard.courses.find((course) => course.course_id === dashboard.recommended_course_id);

  return (
    <main>
      <Link href="/dashboard" className="back-link">← Back to dashboard</Link>
      <header className="education-header">
        <div>
          <p className="eyebrow">LIONSFORGE EDUCATION</p>
          <h1>Build mastery through structured, evidence-based learning.</h1>
          <p className="lede">Recommended next: {recommended?.title ?? "Finance Foundations"}</p>
        </div>
        <aside className="learning-progress">
          <span>{dashboard.completed_modules}</span>
          <p>of {dashboard.total_modules} modules completed</p>
        </aside>
      </header>

      <section className="course-grid">
        {dashboard.courses.map((course) => (
          <article key={course.course_id}>
            <div className="report-meta">
              <span>{course.level}</span>
              <span>{course.modules.filter((module) => module.completed).length}/{course.modules.length} complete</span>
            </div>
            <h2>{course.title}</h2>
            <p>{course.description}</p>
            <div className="module-list">
              {course.modules.map((module) => (
                <div key={module.module_id} className={module.completed ? "module-completed" : ""}>
                  <div>
                    <h3>{module.title}</h3>
                    <p>{module.summary}</p>
                    <small>{module.estimated_minutes} min</small>
                  </div>
                  <Link className="open-lesson-link" href={`/education/${course.course_id}/${module.module_id}`}>
                    {module.completed ? "Review lesson" : "Open lesson"}
                  </Link>
                </div>
              ))}
            </div>
          </article>
        ))}
      </section>
    </main>
  );
}
