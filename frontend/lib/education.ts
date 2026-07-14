export type Lesson = {
  slug: string;
  title: string;
  description: string;
  level: string;
  competency: string;
  estimated_minutes: number;
  status: string;
  score: number | null;
  completed_at: string | null;
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
