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

export type ResearchReportDetail = ResearchReportSummary & {
  id: number;
  user_id: number;
  version: number;
  template_version: string;
  model_version: string;
  data_snapshot_id: string;
  report_payload: {
    sections?: Array<{
      title: string;
      summary: string;
      bullets?: string[];
    }>;
    bull_case?: string[];
    bear_case?: string[];
    risks?: string[];
    opportunities?: string[];
    assumptions?: string[];
  };
  evidence_payload: Array<Record<string, unknown>>;
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
