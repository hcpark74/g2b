# pyright: reportIncompatibleVariableOverride=false

from typing import ClassVar, Optional

from sqlmodel import Field

from app.models.common import TimestampedModel


class Attachment(TimestampedModel, table=True):
    __tablename__: ClassVar[str] = "attachments"

    attachment_id: str = Field(primary_key=True)
    bid_id: str = Field(foreign_key="bids.bid_id", index=True)
    name: str
    file_type: Optional[str] = None
    source: Optional[str] = None
    download_url: Optional[str] = None
    local_path: Optional[str] = None
    file_size: Optional[int] = Field(default=None, index=True)
    content_hash: Optional[str] = Field(default=None, index=True)
    collected_at: Optional[str] = Field(default=None, index=True)
