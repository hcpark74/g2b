from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class BidListPage:
    items: list[dict[str, Any]]
    total: int


class BidRepository(ABC):
    @abstractmethod
    def list_bids(
        self,
        *,
        search_query: str | None = None,
        status: str | None = None,
        favorites_only: bool = False,
        include_versions: bool = False,
        keyword: str | None = None,
        org: str | None = None,
        budget_min: int | None = None,
        budget_max: int | None = None,
        closed_from: str | None = None,
        closed_to: str | None = None,
        sort: str = "posted_at",
        order: str = "desc",
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def list_bids_page(
        self,
        *,
        page: int,
        page_size: int,
        search_query: str | None = None,
        status: str | None = None,
        favorites_only: bool = False,
        include_versions: bool = False,
        keyword: str | None = None,
        org: str | None = None,
        budget_min: int | None = None,
        budget_max: int | None = None,
        closed_from: str | None = None,
        closed_to: str | None = None,
        sort: str = "posted_at",
        order: str = "desc",
    ) -> BidListPage:
        raise NotImplementedError

    @abstractmethod
    def get_bid(self, bid_id: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def update_bid_status(self, bid_id: str, status: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def set_bid_favorite(self, bid_id: str, favorite: bool) -> dict[str, Any]:
        raise NotImplementedError
