from pydantic import BaseModel

from app.presentation.viewmodels.dashboard import DashboardSummaryVM


class OperationItemVM(BaseModel):
    job_type: str
    target: str
    status: str
    started_at: str
    finished_at: str
    message: str


class OperationsPageVM(BaseModel):
    title: str
    description: str
    active_nav: str
    last_synced_at: str
    summary: DashboardSummaryVM
    items: list[OperationItemVM]
