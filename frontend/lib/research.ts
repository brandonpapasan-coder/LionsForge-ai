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
