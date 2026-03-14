# pyright: reportIncompatibleVariableOverride=false

from datetime import datetime
from typing import ClassVar, Optional

from sqlmodel import Field

from app.models.common import TimestampedModel


class SyncJobLog(TimestampedModel, table=True):
    __tablename__: ClassVar[str] = "sync_job_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    job_type: str = Field(index=True)
    target: str = Field(index=True)
    status: str = Field(index=True)
    started_at: datetime
    finished_at: Optional[datetime] = None
    message: str
    metadata_json: Optional[str] = None
