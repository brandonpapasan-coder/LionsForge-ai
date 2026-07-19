export type Lesson = {
  slug: string;
  title: string;
  description: string;
  level: string;
  competency: string;
  estimated_minutes: number;
  prerequisites: string[];
  status: string;
  score: number | null;
  completed_at: string | null;
  path_state: "available" | "recommended" | "locked" | "completed" | "remediation";
  path_reason: string;
};

export type CompetencySummary = {
  competency: string;
  completed_lessons: number;
  total_lessons: number;
  assessed_lessons: number;
  average_score: number | null;
  mastery_percent: number;
  proficiency_band: string;
};

export type CompetencyTrend = {
  competency: string;
  attempt_count: number;
  recent_average: number | null;
  prior_average: number | null;
  direction: "improving" | "stable" | "declining" | "insufficient_evidence";
  explanation: string;
};

export type EducationHubData = {
  completed_lessons: number;
  total_lessons: number;
  assessed_lessons: number;
  completion_percent: number;
  average_score: number | null;
  mastery_percent: number;
  proficiency_band: string;
  recommended_lesson_slug: string | null;
  recommendation_reason: string;
  lessons: Lesson[];
  competencies: CompetencySummary[];
};

export type AssessmentQuestion = {
  id: string;
  prompt: string;
  options: string[];
  objective: string;
};

export type AdaptiveAssessment = {
  lesson_slug: string;
  competency: string;
  difficulty: string;
  difficulty_reason: string;
  question: AssessmentQuestion;
};

export type AssessmentAttempt = {
  id: number;
  lesson_slug: string;
  competency: string;
  difficulty: string;
  question_id: string;
  selected_option: number;
  score: number;
  passed: boolean;
  created_at: string;
};

export type AssessmentResult = {
  lesson_slug: string;
  competency: string;
  difficulty: string;
  score: number;
  passed: boolean;
  feedback: string;
  learning_objective: string;
  education_hub: EducationHubData;
};
