"""
Pydantic schemas for structured agent output.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AnalysisResult(BaseModel):
    """Structured output from the LangGraph recommender node."""

    confidence_score: float = Field(ge=0.0, le=1.0)
    severity: Literal["low", "medium", "high", "critical"]
    root_cause_hypothesis: str
    affected_services: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    runbook_steps: list[str] = Field(default_factory=list)

    @field_validator("confidence_score", mode="before")
    @classmethod
    def clamp_confidence(cls, value: float) -> float:
        try:
            v = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, v))
