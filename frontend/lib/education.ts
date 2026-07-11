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
  mastery_percent: number;
};

export type EducationHubData = {
  completed_lessons: number;
  total_lessons: number;
  completion_percent: number;
  lessons: Lesson[];
  competencies: CompetencySummary[];
};
