from pydantic import BaseModel

from app.presentation.viewmodels.bids import BidListItemVM
from app.presentation.viewmodels.dashboard import DashboardSummaryVM


class FavoritesPageVM(BaseModel):
    title: str
    description: str
    active_nav: str
    last_synced_at: str
    summary: DashboardSummaryVM
    items: list[BidListItemVM]
