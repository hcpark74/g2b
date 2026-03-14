# pyright: reportIncompatibleVariableOverride=false

from typing import ClassVar, Optional

from sqlmodel import Field

from app.models.common import TimestampedModel


class BidReferenceInfo(TimestampedModel, table=True):
    __tablename__: ClassVar[str] = "bid_reference_infos"

    id: Optional[int] = Field(default=None, primary_key=True)
    bid_id: str = Field(foreign_key="bids.bid_id", index=True)
    reference_key: str = Field(index=True)
    reference_name: str = Field(index=True)
    source_api_name: Optional[str] = None
    raw_data: Optional[str] = None
    collected_at: Optional[str] = Field(default=None, index=True)
