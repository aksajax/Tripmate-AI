
"""Request and response schemas for itinerary approval."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
)

ApprovalDecision = Literal["approve", "reject"]

ApprovalComments = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=2000,
    ),
]


class ApprovalRequest(BaseModel):
    """Data submitted when a reviewer approves or rejects an itinerary."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    decision: ApprovalDecision = Field(
        description="Whether the reviewer approves or rejects the itinerary."
    )

    itinerary_version: int = Field(
        ge=1,
        description="The exact itinerary version being reviewed.",
    )

    comments: ApprovalComments | None = Field(
        default=None,
        description="Optional reviewer comments or rejection reason.",
    )


class ApprovalResponse(BaseModel):
    """Approval result returned by the backend."""

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
    )

    approval_id: str = Field(min_length=1, max_length=100)
    itinerary_id: str = Field(min_length=1, max_length=100)

    itinerary_version: int = Field(
        ge=1,
        description="The exact itinerary version this decision applies to.",
    )

    decision: ApprovalDecision

    reviewed_by: str = Field(
        min_length=1,
        max_length=100,
        description="Reviewer identity established by the backend.",
    )

    reviewed_at: datetime = Field(
        description="Timestamp when the decision was recorded.",
    )

    comments: str | None = Field(
        default=None,
        max_length=2000,
    )
