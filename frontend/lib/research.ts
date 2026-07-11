export type ResearchProject = {
  id: number;
  title: string;
  description: string | null;
  objective: string | null;
  status: string;
  context: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type ResearchSession = {
  id: number;
  project_id: number;
  title: string;
  objective: string | null;
  summary: string | null;
  status: string;
  context: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};
