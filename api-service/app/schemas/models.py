from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


RoleType = Literal["editor", "admin", "data-scientist"]
Tone = Literal["navy", "teal", "coral", "green", "violet", "gold", "pink", "muted"]


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def todict(self) -> dict[str, Any]:
        return self.to_dict()


class LoginRequest(BaseModel):
    email: str
    password: str
    role: RoleType


class InferenceRequest(BaseModel):
    title: str
    content: str
    source_url: str | None = None
    top_k: int = Field(default=3, ge=1, le=5)


class ArticleUrlInferenceRequest(BaseModel):
    source_url: str
    top_k: int = Field(default=3, ge=1, le=5)


class DecisionRequest(BaseModel):
    action: Literal["approve", "override", "escalate"]
    selected_label: str | None = None
    notes: str | None = None


class ThresholdUpdateRequest(BaseModel):
    auto_approve: float = Field(default=0.75, ge=0.5, le=0.99)
    review_floor: float = Field(default=0.68, ge=0.3, le=0.95)


class UserInviteRequest(BaseModel):
    email: str
    name: str
    role: RoleType
    queue: str = "All queues"
    password: str = Field(min_length=8)


class UserUpdateRequest(BaseModel):
    name: str | None = None
    role: RoleType | None = None
    queue: str | None = None
    status: Literal["Active", "Standby"] | None = None
    password: str | None = Field(default=None, min_length=8)


class ArticleIngestRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    source_url: str | None = None
    source: str = "VietnamNet"
    label_hint: str | None = None
    run_inference: bool = True


class ModelRunCreateRequest(BaseModel):
    run_id: str
    backbone: str = "vinai/phobert-base-v2"
    uploaded_label: str = "manual upload"


class ChipResponse(ApiModel):
    label: str
    tone: Tone


class SidebarItemResponse(ApiModel):
    id: str
    label: str
    active: bool


class SidebarResponse(ApiModel):
    brand: str
    current_role: str
    active_model: str
    items: list[SidebarItemResponse]
    summary_title: str
    summary_value: str
    summary_body: str


class StatCardResponse(ApiModel):
    label: str
    value: str
    delta: str
    tone: Tone


class ProgressDatumResponse(ApiModel):
    label: str
    value: float
    tone: Tone


class ConfusionMatrixResponse(ApiModel):
    labels: list[str] = Field(default_factory=list)
    matrix: list[list[int]] = Field(default_factory=list)


class PerClassMetricResponse(ApiModel):
    label: str
    precision: float
    recall: float
    f1: float
    support: int
    tp: int
    fp: int
    fn: int


class CandidateResponse(ApiModel):
    label: str
    score: float


class ReviewQueueItemResponse(ApiModel):
    id: str
    label: str
    title: str
    confidence: float
    margin: float
    status: str | None = None


class ReviewQueueResponse(ApiModel):
    items: list[ReviewQueueItemResponse]
    summary: str
    page: int
    total_pages: int


class ConfidenceSummaryResponse(ApiModel):
    value: float | None
    label: str


class PillSignalResponse(ApiModel):
    label: str
    pill: str
    tone: Tone


class FeedbackLoopResponse(ApiModel):
    title: str
    body: str
    pill: str
    tone: Tone


class BaseScreenResponse(ApiModel):
    screen: str
    chips: list[ChipResponse]
    heading: str
    subheading: str
    sidebar: SidebarResponse


class EditorDashboardResponse(BaseScreenResponse):
    stats: list[StatCardResponse]
    review_queue: ReviewQueueResponse
    category_distribution: list[ProgressDatumResponse]
    confidence_summary: ConfidenceSummaryResponse
    shared_signals: list[PillSignalResponse]
    feedback_loop: list[FeedbackLoopResponse]


class ReviewListResponse(BaseScreenResponse):
    stats: list[StatCardResponse]
    items: list[ReviewQueueItemResponse]
    summary: str
    page: int
    total_pages: int


class ArticleBodyResponse(ApiModel):
    id: str
    title: str
    source: str
    paragraphs: list[str]
    url: str
    rationale_blocks: list[dict[str, Any]]
    similar_articles: list[dict[str, Any]]


class PredictionSummaryResponse(ApiModel):
    label: str
    confidence: float
    package: str
    decision: str


class ThresholdBandResponse(ApiModel):
    label: str
    tone: Tone


class DecisionControlsResponse(ApiModel):
    primary_label: str
    history: str
    labels: list[str]


class ReviewArticleResponse(BaseScreenResponse):
    article: ArticleBodyResponse
    prediction_summary: PredictionSummaryResponse
    candidate_ranking: list[CandidateResponse]
    threshold_bands: list[ThresholdBandResponse]
    decision_controls: DecisionControlsResponse


class UserResponse(ApiModel):
    email: str
    name: str
    role: str
    queue: str
    status: str


class InvitedUserResponse(UserResponse):
    pass


class PageMetaResponse(ApiModel):
    page: int
    total_pages: int
    summary: str


class ThresholdImpactResponse(ApiModel):
    total: int
    auto_ready: int
    needs_review: int
    escalated: int
    auto_rate: float
    review_rate: float
    escalation_rate: float


class ModelRunResponse(ApiModel):
    id: str
    backbone: str
    uploaded: str
    f1: float
    state: str


class AdminOpsResponse(BaseScreenResponse):
    users: list[UserResponse]
    user_pagination: PageMetaResponse
    routing_rules: list[ProgressDatumResponse]
    audit_log: list[str]
    audit_pagination: PageMetaResponse
    deployment_snapshot: list[dict[str, str]]
    candidate_model_run: ModelRunResponse | None
    thresholds: dict[str, float]
    threshold_impact: ThresholdImpactResponse


class MonitoringResponse(BaseScreenResponse):
    stats: list[StatCardResponse]
    macro_series: list[float]
    label_scores: list[ProgressDatumResponse]
    confusion_matrix: ConfusionMatrixResponse
    per_class_metrics: list[PerClassMetricResponse]
    article_analysis: list[dict[str, str]]
    drift_breakdown: list[dict[str, str]]
    last_run_at: str | None


class ComparisonCardResponse(ApiModel):
    label: str
    value: str
    detail: str


class ModelVersionsResponse(BaseScreenResponse):
    runs: list[ModelRunResponse]
    selected_run: ModelRunResponse | None
    comparison_cards: list[ComparisonCardResponse]
    confusion_matrix: list[list[float]]
    confusion_labels: list[str]
    package_details: list[dict[str, str]]
    exports: list[str]


class ActiveLearningResponse(ApiModel):
    title: str
    value: str
    body: str
    pill: str
    tone: Tone


class HardSampleResponse(ApiModel):
    title: str
    score: float


class DatasetLabResponse(BaseScreenResponse):
    stats: list[StatCardResponse]
    imbalance: list[ProgressDatumResponse]
    hard_samples: list[HardSampleResponse]
    hard_sample_pagination: PageMetaResponse
    active_learning: list[ActiveLearningResponse]
    priority_labels: list[str]


class LoginResponse(ApiModel):
    token: str
    email: str
    name: str
    role: RoleType
    display_role: str
    redirect: str
    active_model: str


class StatusResponse(ApiModel):
    status: str


class ThresholdResponse(ApiModel):
    auto_approve: float
    review_floor: float


class HealthResponse(StatusResponse):
    database: dict[str, Any]
    model_service: dict[str, Any]


class WorkerJobResponse(StatusResponse):
    job_id: str
    job_type: str
    payload: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    created_by: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    updated_at: str | None = None


class WorkerJobQueuedResponse(StatusResponse):
    job_id: str
    job_type: str


class WorkerJobListResponse(ApiModel):
    jobs: list[WorkerJobResponse]


class ArticleImportResponse(StatusResponse):
    article_id: str
    article: dict[str, Any]


class DecisionResponse(StatusResponse):
    article_id: str
    action: str
    selected_label: str | None = None
    notes: str | None = None


class ModelRunUploadResponse(StatusResponse):
    run: ModelRunResponse


class ModelActivationResponse(StatusResponse):
    active_model: str
    run_id: str
    active_artifact: str | None = None


class MonitoringRecomputeResponse(StatusResponse):
    id: int | None = None
    reason: str | None = None
    macro_f1: float | None = None
    error_share: float | None = None
    drift_score: float | None = None
    coverage: float | None = None
    label_scores: list[dict[str, Any]] = Field(default_factory=list)
    confusion_matrix: ConfusionMatrixResponse = Field(default_factory=ConfusionMatrixResponse)
    per_class_metrics: list[PerClassMetricResponse] = Field(default_factory=list)
    article_analysis: list[dict[str, Any]] = Field(default_factory=list)
    drift_breakdown: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str | None = None


class InferenceResponse(ApiModel):
    request_id: str
    model_version: str
    label: str
    confidence: float
    margin: float
    candidates: list[CandidateResponse]
    rationale_keywords: list[str]
    auto_decision: str
    latency_ms: int
