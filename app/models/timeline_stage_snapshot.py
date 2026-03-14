# pyright: reportIncompatibleVariableOverride=false

from typing import ClassVar, Optional

from sqlmodel import Field

from app.models.common import TimestampedModel


class TimelineStageSnapshot(TimestampedModel, table=True):
    __tablename__: ClassVar[str] = "timeline_stage_snapshots"

    id: Optional[int] = Field(default=None, primary_key=True)
    bid_id: str = Field(foreign_key="bids.bid_id", index=True)
    stage: str = Field(index=True)
    status: str = Field(index=True)
    number: Optional[str] = None
    occurred_at: Optional[str] = Field(default=None, index=True)
    meta: Optional[str] = None
    source_api_name: str = Field(default="contractProcessIntegration")
