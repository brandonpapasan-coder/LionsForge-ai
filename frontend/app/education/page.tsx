import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { AdaptiveLearningPlan } from "@/components/adaptive-learning-plan";
import { CompetencyTrends } from "@/components/competency-trends";
import { EducationHub } from "@/components/education-hub";
import { LearnerCompetencyGapPlan } from "@/components/learner-competency-gap-plan";
import { LearnerCompetencyPortfolio } from "@/components/learner-competency-portfolio";
import { LearnerRoadmapActionHistory } from "@/components/learner-roadmap-action-history";
import { LearnerRoadmapActionOutcomes } from "@/components/learner-roadmap-action-outcomes";
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
      <LearnerCompetencyGapPlan />
      <LearnerRoadmapActionHistory />
      <LearnerRoadmapActionOutcomes />
      <CompetencyTrends />
    </>
  );
}
