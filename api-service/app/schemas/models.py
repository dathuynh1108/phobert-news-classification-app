from typing import Literal

from pydantic import BaseModel, Field


RoleType = Literal["editor-admin", "data-scientist"]


class LoginRequest(BaseModel):
    email: str
    password: str
    role: RoleType


class InferenceRequest(BaseModel):
    title: str
    content: str
    source_url: str | None = None
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
    f1: float = Field(default=0.0, ge=0.0, le=1.0)
    uploaded_label: str = "manual upload"
