export type DashboardMetric = {
  label: string;
  value: number;
  detail: string;
};

export type DashboardAction = {
  title: string;
  reason: string;
  href: string;
  priority: string;
};

export type DashboardActivity = {
  kind: string;
  title: string;
  summary: string | null;
  href: string;
  updated_at: string;
};

export type ExecutiveDashboard = {
  greeting: string;
  briefing: string;
  metrics: DashboardMetric[];
  next_actions: DashboardAction[];
  recent_activity: DashboardActivity[];
};
