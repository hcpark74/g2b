# pyright: reportIncompatibleVariableOverride=false

from typing import ClassVar, Optional

from sqlmodel import Field

from app.models.common import TimestampedModel


class BidPurchaseItem(TimestampedModel, table=True):
    __tablename__: ClassVar[str] = "bid_purchase_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    bid_id: str = Field(foreign_key="bids.bid_id", index=True)
    item_name: str = Field(index=True)
    item_code: Optional[str] = Field(default=None, index=True)
    quantity: Optional[str] = None
    delivery_condition: Optional[str] = None
    source_api_name: Optional[str] = None
    collected_at: Optional[str] = Field(default=None, index=True)
