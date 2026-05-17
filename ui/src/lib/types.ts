export type Tone = "navy" | "teal" | "coral" | "green" | "violet" | "gold" | "pink" | "muted";
export type RoleType = "editor" | "admin" | "data-scientist";

export interface Chip {
  label: string;
  tone: Tone;
}

export interface SidebarItem {
  id: string;
  label: string;
  active: boolean;
}

export interface SidebarData {
  brand: string;
  currentRole: string;
  activeModel: string;
  items: SidebarItem[];
  summaryTitle: string;
  summaryValue: string;
  summaryBody: string;
}

export interface StatCardData {
  label: string;
  value: string;
  delta: string;
  tone: Tone;
}

export interface ProgressDatum {
  label: string;
  value: number;
  tone: Tone;
}

export interface PageMeta {
  page: number;
  totalPages: number;
  summary: string;
}

export interface ThresholdImpact {
  total: number;
  autoReady: number;
  needsReview: number;
  escalated: number;
  autoRate: number;
  reviewRate: number;
  escalationRate: number;
}

export interface ConfusionMatrixData {
  labels: string[];
  matrix: number[][];
}

export interface PerClassMetric {
  label: string;
  precision: number;
  recall: number;
  f1: number;
  support: number;
  tp: number;
  fp: number;
  fn: number;
}

export interface MacroSeriesPoint {
  id: number;
  value: number;
  createdAt: string;
}

export interface ReviewQueueItem {
  id: string;
  label: string;
  title: string;
  confidence: number;
  margin: number;
  status?: string;
}

export interface EditorDashboardScreen {
  screen: string;
  chips: Chip[];
  heading: string;
  subheading: string;
  sidebar: SidebarData;
  stats: StatCardData[];
  reviewQueue: {
    items: ReviewQueueItem[];
    summary: string;
    page: number;
    totalPages: number;
  };
  categoryDistribution: ProgressDatum[];
  confidenceSummary: {
    value: number | null;
    label: string;
  };
  sharedSignals: Array<{ label: string; pill: string; tone: Tone }>;
  feedbackLoop: Array<{ title: string; body: string; pill: string; tone: Tone }>;
}

export interface ReviewArticleScreen {
  screen: string;
  chips: Chip[];
  heading: string;
  subheading: string;
  sidebar: SidebarData;
  article: {
    id: string;
    title: string;
    source: string;
    paragraphs: string[];
    url: string;
    rationaleBlocks: Array<{
      title: string;
      body: string;
      chips: string[];
      bullets: string[];
    }>;
    similarArticles: Array<{ title: string; score: number; note: string }>;
  };
  predictionSummary: {
    label: string;
    confidence: number;
    package: string;
    decision: string;
  };
  candidateRanking: Array<{ label: string; score: number }>;
  thresholdBands: Array<{ label: string; tone: Tone }>;
  decisionControls: {
    primaryLabel: string;
    history: string;
    labels: string[];
  };
}

export interface ReviewListScreen {
  screen: string;
  chips: Chip[];
  heading: string;
  subheading: string;
  sidebar: SidebarData;
  stats: StatCardData[];
  items: ReviewQueueItem[];
  summary: string;
  page: number;
  totalPages: number;
}

export interface AdminOpsScreen {
  screen: string;
  chips: Chip[];
  heading: string;
  subheading: string;
  sidebar: SidebarData;
  users: Array<{ email: string; name: string; role: string; queue: string; status: string }>;
  userPagination: PageMeta;
  routingRules: ProgressDatum[];
  auditLog: string[];
  auditPagination: PageMeta;
  deploymentSnapshot: Array<{ label: string; value: string }>;
  candidateModelRun: { id: string; backbone: string; uploaded: string; f1: number; state: string } | null;
  thresholds: {
    autoApprove: number;
    reviewFloor: number;
  };
  thresholdImpact: ThresholdImpact;
}

export interface MonitoringScreen {
  screen: string;
  chips: Chip[];
  heading: string;
  subheading: string;
  sidebar: SidebarData;
  stats: StatCardData[];
  macroSeries: number[];
  macroSeriesPoints: MacroSeriesPoint[];
  labelScores: ProgressDatum[];
  confusionMatrix: ConfusionMatrixData;
  perClassMetrics: PerClassMetric[];
  articleAnalysis: Array<{ label: string; value: string; note: string }>;
  driftBreakdown: Array<{ label: string; detail: string; tone: Tone }>;
  lastRunAt: string | null;
}

export interface ModelVersionsScreen {
  screen: string;
  chips: Chip[];
  heading: string;
  subheading: string;
  sidebar: SidebarData;
  runs: Array<{ id: string; backbone: string; uploaded: string; f1: number; state: string }>;
  selectedRun: { id: string; backbone: string; uploaded: string; f1: number; state: string } | null;
  comparisonCards: Array<{ label: string; value: string; detail: string }>;
  confusionMatrix: number[][];
  confusionLabels: string[];
  packageDetails: Array<{ label: string; value: string }>;
  exports: string[];
}

export interface DatasetLabScreen {
  screen: string;
  chips: Chip[];
  heading: string;
  subheading: string;
  sidebar: SidebarData;
  stats: StatCardData[];
  imbalance: ProgressDatum[];
  hardSamples: Array<{ title: string; score: number }>;
  hardSamplePagination: PageMeta;
  activeLearning: Array<{ title: string; value: string; body: string; pill: string; tone: Tone }>;
  priorityLabels: string[];
}

export interface LoginResponse {
  token: string;
  email: string;
  name: string;
  role: RoleType;
  displayRole: string;
  redirect: string;
  activeModel: string;
}

export interface SessionState extends LoginResponse {}

export interface InferenceResponse {
  requestId: string;
  modelVersion: string;
  label: string;
  confidence: number;
  margin: number;
  candidates: Array<{ label: string; score: number }>;
  rationaleKeywords: string[];
  autoDecision: string;
  latencyMs: number;
}

export interface WorkerJobResponse {
  status: string;
  jobId: string;
  jobType: string;
}
