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

