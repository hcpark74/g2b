# pyright: reportIncompatibleVariableOverride=false

from typing import ClassVar, Optional

from sqlmodel import Field

from app.models.common import TimestampedModel


class BidVersionChange(TimestampedModel, table=True):
    __tablename__: ClassVar[str] = "bid_version_changes"

    change_id: str = Field(primary_key=True, index=True)
    bid_id: str = Field(foreign_key="bids.bid_id", index=True)
    bid_no: str = Field(index=True)
    bid_seq: str = Field(index=True)
    change_item_name: str = Field(index=True)
    before_value: Optional[str] = None
    after_value: Optional[str] = None
    changed_at: Optional[str] = Field(default=None, index=True)
    source_api_name: str = Field(index=True)
    raw_data: Optional[str] = None
