export type ResearchReportSummary = {
  report_id: string;
  symbol: string;
  title: string;
  status: string;
  confidence_level: string;
  confidence_score: string;
  executive_summary: string;
  created_at: string;
};

export type ResearchReportList = {
  symbol: string | null;
  reports: ResearchReportSummary[];
};

export type GeneratedResearchReport = {
  metadata: {
    report_id: string;
    symbol: string;
    confidence_level: string;
    confidence_score: string;
  };
  title: string;
  executive_summary: string;
};
