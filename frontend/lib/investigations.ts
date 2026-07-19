export type InvestigationStatus = "open" | "in_review" | "validated" | "archived";

export type Investigation = {
  id: number;
  title: string;
  research_question: string;
  status: InvestigationStatus;
  created_at: string;
  updated_at: string;
};

export type InvestigationCreate = {
  title: string;
  research_question: string;
};

export type InvestigationUpdate = Partial<InvestigationCreate> & {
  status?: InvestigationStatus;
};
