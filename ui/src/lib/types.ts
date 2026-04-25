export type Tone = "navy" | "teal" | "coral" | "green" | "violet" | "gold" | "pink" | "muted";
export type RoleType = "editor-admin" | "data-scientist";

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

export interface ReviewQueueItem {
  id: string;
  label: string;
  title: string;
  confidence: number;
  margin: number;
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

export interface AdminOpsScreen {
  screen: string;
  chips: Chip[];
  heading: string;
  subheading: string;
  sidebar: SidebarData;
  users: Array<{ name: string; role: string; queue: string; status: string }>;
  routingRules: ProgressDatum[];
  auditLog: string[];
  deploymentSnapshot: Array<{ label: string; value: string }>;
  candidateModelRun: { id: string; backbone: string; uploaded: string; f1: number; state: string } | null;
  thresholds: {
    auto_approve: number;
    review_floor: number;
  };
}

export interface MonitoringScreen {
  screen: string;
  chips: Chip[];
  heading: string;
  subheading: string;
  sidebar: SidebarData;
  stats: StatCardData[];
  macroSeries: number[];
  labelScores: ProgressDatum[];
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
  activeLearning: Array<{ title: string; value: string; body: string; pill: string; tone: Tone }>;
  priorityLabels: string[];
}

export interface LoginResponse {
  token: string;
  email: string;
  role: RoleType;
  redirect: string;
  activeModel: string;
}

export interface SessionState extends LoginResponse {}

export interface InferenceResponse {
  request_id: string;
  model_version: string;
  label: string;
  confidence: number;
  margin: number;
  candidates: Array<{ label: string; score: number }>;
  rationale_keywords: string[];
  auto_decision: string;
  latency_ms: number;
}

export interface WorkerJobResponse {
  status: string;
  jobId: string;
  jobType: string;
}
