import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { AdaptiveLearningPlan } from "@/components/adaptive-learning-plan";
import { CompetencyTrends } from "@/components/competency-trends";
import { EducationHub } from "@/components/education-hub";
import { LearnerCompetencyPortfolio } from "@/components/learner-competency-portfolio";
import { ResearchPracticumWorkspace } from "@/components/research-practicum-workspace";
import "./education.css";

export default async function EducationPage() {
  const cookieStore = await cookies();
  if (!cookieStore.get("lionsforge_session")?.value) redirect("/login");
  return (
    <>
      <EducationHub />
      <AdaptiveLearningPlan />
      <ResearchPracticumWorkspace />
      <LearnerCompetencyPortfolio />
      <CompetencyTrends />
    </>
  );
}
