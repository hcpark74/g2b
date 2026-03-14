# pyright: reportIncompatibleVariableOverride=false

from typing import ClassVar, Optional

from sqlmodel import Field, SQLModel

from app.models.common import TimestampedModel


class BidDetail(TimestampedModel, table=True):
    __tablename__: ClassVar[str] = "bid_details"

    bid_id: str = Field(primary_key=True, foreign_key="bids.bid_id")
    description_text: Optional[str] = None
    detail_url: Optional[str] = None
    raw_api_data: Optional[str] = None
    crawl_data: Optional[str] = None
    detail_hash: Optional[str] = Field(default=None, index=True)
    collected_at: Optional[str] = Field(default=None, index=True)
