export type LearningModule = {
  module_id: string;
  title: string;
  summary: string;
  estimated_minutes: number;
  completed: boolean;
  attempt_count: number;
  best_score: number | null;
};

export type CourseCatalogItem = {
  course_id: string;
  title: string;
  level: string;
  description: string;
  modules: LearningModule[];
};

export type LearningDashboard = {
  learner_email: string;
  recommended_course_id: string;
  completed_modules: number;
  total_modules: number;
  mastery_average: number | null;
  courses: CourseCatalogItem[];
};

export type LessonDetail = {
  course_id: string;
  module_id: string;
  course_title: string;
  title: string;
  summary: string;
  estimated_minutes: number;
  objectives: string[];
  key_points: string[];
  assessment: {
    question: string;
    options: string[];
    passing_score: number;
  };
  completed: boolean;
  attempt_count: number;
  best_score: number | null;
};

export type AssessmentResult = {
  score: number;
  passed: boolean;
  explanation: string;
  completed_at: string | null;
  attempt_count: number;
  best_score: number;
};
