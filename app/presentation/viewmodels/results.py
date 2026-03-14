from pydantic import BaseModel

from app.presentation.viewmodels.dashboard import DashboardSummaryVM


class ResultItemVM(BaseModel):
    bid_no: str
    title: str
    business_type: str
    winner: str
    award_amount: str
    award_rate: str
    contract_amount: str
    contract_date: str
    notice_org: str
    demand_org: str


class ResultsPageVM(BaseModel):
    title: str
    description: str
    active_nav: str
    last_synced_at: str
    summary: DashboardSummaryVM
    items: list[ResultItemVM]
