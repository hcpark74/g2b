# pyright: reportIncompatibleVariableOverride=false

from typing import ClassVar, Optional

from sqlmodel import Field

from app.models.common import TimestampedModel


class ContractProcessIntegration(TimestampedModel, table=True):
    __tablename__: ClassVar[str] = "contract_process_integrations"

    id: Optional[int] = Field(default=None, primary_key=True)
    bid_id: str = Field(foreign_key="bids.bid_id", index=True)
    inqry_div: int = Field(index=True)
    source_key: str = Field(index=True)
    award_company: Optional[str] = None
    award_amount: Optional[str] = None
    contract_no: Optional[str] = None
    contract_name: Optional[str] = None
    contract_date: Optional[str] = None
    raw_data: Optional[str] = None
    source_api_name: str = Field(default="contractProcessIntegration")
    collected_at: Optional[str] = Field(default=None, index=True)
