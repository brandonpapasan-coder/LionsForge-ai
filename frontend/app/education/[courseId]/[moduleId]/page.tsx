import { cookies } from "next/headers";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { LessonAssessment } from "@/components/lesson-assessment";
import type { LessonDetail } from "@/lib/education";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

async function getLesson(courseId: string, moduleId: string): Promise<LessonDetail | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get("lionsforge_session")?.value;
  if (!token) redirect("/login");

  const response = await fetch(
    `${backendUrl}/api/v1/education/courses/${encodeURIComponent(courseId)}/modules/${encodeURIComponent(moduleId)}`,
    { headers: { authorization: `Bearer ${token}` }, cache: "no-store" },
  );
  if (response.status === 404) return null;
  if (!response.ok) redirect("/education");
  return (await response.json()) as LessonDetail;
}

export default async function LessonPage({ params }: { params: Promise<{ courseId: string; moduleId: string }> }) {
  const { courseId, moduleId } = await params;
  const lesson = await getLesson(courseId, moduleId);
  if (!lesson) notFound();

  return (
    <main>
      <Link href="/education" className="back-link">← Back to education</Link>
      <header className="lesson-header">
        <div>
          <p className="eyebrow">{lesson.course_title}</p>
          <h1>{lesson.title}</h1>
          <p className="lede">{lesson.summary}</p>
        </div>
        <aside className={`lesson-status ${lesson.completed ? "completed" : ""}`}>
          <strong>{lesson.completed ? "Completed" : "In progress"}</strong>
          <span>{lesson.estimated_minutes} minutes</span>
        </aside>
      </header>

      <section className="lesson-content-grid">
        <article>
          <h2>Learning objectives</h2>
          <ul>{lesson.objectives.map((objective) => <li key={objective}>{objective}</li>)}</ul>
        </article>
        <article>
          <h2>Key points</h2>
          <ul>{lesson.key_points.map((point) => <li key={point}>{point}</li>)}</ul>
        </article>
      </section>

      <LessonAssessment
        courseId={lesson.course_id}
        moduleId={lesson.module_id}
        question={lesson.assessment.question}
        options={lesson.assessment.options}
        completed={lesson.completed}
      />
    </main>
  );
}
