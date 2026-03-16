from typing import Any

from app.repositories import BidListPage, BidRepository, SampleBidRepository


class BidQueryService:
    def __init__(self, repository: BidRepository | None = None) -> None:
        self.repository = repository or SampleBidRepository()

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
        sort: str = "updated_at",
        order: str = "desc",
    ) -> list[dict[str, Any]]:
        return self.repository.list_bids(
            search_query=search_query,
            status=status,
            favorites_only=favorites_only,
            include_versions=include_versions,
            keyword=keyword,
            org=org,
            budget_min=budget_min,
            budget_max=budget_max,
            closed_from=closed_from,
            closed_to=closed_to,
            sort=sort,
            order=order,
        )

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
        sort: str = "updated_at",
        order: str = "desc",
    ) -> BidListPage:
        return self.repository.list_bids_page(
            page=page,
            page_size=page_size,
            search_query=search_query,
            status=status,
            favorites_only=favorites_only,
            include_versions=include_versions,
            keyword=keyword,
            org=org,
            budget_min=budget_min,
            budget_max=budget_max,
            closed_from=closed_from,
            closed_to=closed_to,
            sort=sort,
            order=order,
        )

    def get_bid(self, bid_id: str) -> dict[str, Any]:
        return self.repository.get_bid(bid_id)

    def update_bid_status(self, bid_id: str, status: str) -> dict[str, Any]:
        return self.repository.update_bid_status(bid_id, status)

    def set_bid_favorite(self, bid_id: str, favorite: bool) -> dict[str, Any]:
        return self.repository.set_bid_favorite(bid_id, favorite)
