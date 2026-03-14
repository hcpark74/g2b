# pyright: reportIncompatibleVariableOverride=false

from datetime import datetime
from typing import ClassVar, Optional

from sqlmodel import Field, SQLModel

from app.models.common import (
    BID_STATUS_COLLECTED,
    DEFAULT_BID_SEQUENCE,
    TimestampedModel,
)


class Bid(TimestampedModel, table=True):
    __tablename__: ClassVar[str] = "bids"

    bid_id: str = Field(primary_key=True, index=True)
    bid_no: str = Field(index=True)
    bid_seq: str = Field(default=DEFAULT_BID_SEQUENCE, index=True)
    title: str
    demand_org: Optional[str] = Field(default=None, index=True)
    notice_org: Optional[str] = Field(default=None, index=True)
    category: Optional[str] = None
    status: str = Field(default=BID_STATUS_COLLECTED, index=True)
    posted_at: Optional[datetime] = Field(default=None, index=True)
    closed_at: Optional[datetime] = Field(default=None, index=True)
    budget_amount: Optional[int] = Field(default=None, index=True)
    is_favorite: bool = Field(default=False, index=True)
    favorite_memo: Optional[str] = None
    source_api_name: Optional[str] = None
    notice_version_type: Optional[str] = Field(default=None, index=True)
    is_latest_version: bool = Field(default=False, index=True)
    is_effective_version: bool = Field(default=True, index=True)
    parent_bid_id: Optional[str] = Field(default=None, index=True)
    version_reason: Optional[str] = None
    view_count: int = 0
    last_synced_at: Optional[datetime] = None
    last_changed_at: Optional[datetime] = None


class BidRead(SQLModel):
    bid_id: str
    bid_no: str
    bid_seq: str
    title: str
    demand_org: Optional[str] = None
    notice_org: Optional[str] = None
    status: str
    notice_version_type: Optional[str] = None
    is_latest_version: bool = False
    is_effective_version: bool = True
    parent_bid_id: Optional[str] = None
    version_reason: Optional[str] = None
    posted_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    budget_amount: Optional[int] = None
    is_favorite: bool
    last_synced_at: Optional[datetime] = None
