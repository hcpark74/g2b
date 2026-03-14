from typing import Optional

from pydantic import BaseModel

from app.presentation.viewmodels.bids import BidDrawerVM


class SecondaryPageVM(BaseModel):
    title: str
    description: str
    active_nav: str
    last_synced_at: str
    selected_bid: Optional[BidDrawerVM] = None
