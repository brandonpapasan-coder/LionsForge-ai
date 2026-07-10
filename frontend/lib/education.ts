export type LearningModule = {
  module_id: string;
  title: string;
  summary: string;
  estimated_minutes: number;
  completed: boolean;
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
  courses: CourseCatalogItem[];
};
