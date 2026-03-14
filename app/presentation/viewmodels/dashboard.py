from typing import Optional

from pydantic import BaseModel


class DashboardStatVM(BaseModel):
    label: str
    value: str
    hint: Optional[str] = None


class DashboardSummaryVM(BaseModel):
    items: list[DashboardStatVM]
    last_synced_at: str
