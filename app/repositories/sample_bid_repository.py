from typing import Any

from app.models import BID_STATUS_LABELS
from app.repositories.bid_repository import BidListPage, BidRepository
from app.sample_data import get_sample_bids


_status_overrides: dict[str, str] = {}
_favorite_overrides: dict[str, bool] = {}


class SampleBidRepository(BidRepository):
    def _status_label(self, value: str) -> str:
        return BID_STATUS_LABELS.get(value, value)

    def _with_overrides(self, bid: dict[str, Any]) -> dict[str, Any]:
        payload = dict(bid)
        bid_id = str(payload.get("bid_id", ""))
        status_override = _status_overrides.get(bid_id)
        favorite_override = _favorite_overrides.get(bid_id)
        if status_override is not None:
            payload["status"] = self._status_label(status_override)
        if favorite_override is not None:
            payload["favorite"] = favorite_override
        return payload

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
        bids = [self._with_overrides(item) for item in get_sample_bids()]
        normalized_query = (search_query or "").strip().lower()
        normalized_status = (status or "").strip()
        expected_status = self._status_label(normalized_status)
        normalized_keyword = (keyword or "").strip().lower()
        normalized_org = (org or "").strip().lower()

        if normalized_query:
            bids = [
                bid
                for bid in bids
                if normalized_query in str(bid.get("bid_id", "")).lower()
                or normalized_query in str(bid.get("title", "")).lower()
                or normalized_query in str(bid.get("notice_org", "")).lower()
                or normalized_query in str(bid.get("demand_org", "")).lower()
            ]

        if normalized_status:
            bids = [
                bid
                for bid in bids
                if str(bid.get("status", "")).strip() == expected_status
            ]

        if favorites_only:
            bids = [bid for bid in bids if bool(bid.get("favorite", False))]

        if normalized_keyword:
            bids = [
                bid for bid in bids if self._matches_keyword(bid, normalized_keyword)
            ]

        if normalized_org:
            bids = [
                bid
                for bid in bids
                if normalized_org in str(bid.get("notice_org", "")).lower()
                or normalized_org in str(bid.get("demand_org", "")).lower()
            ]

        if budget_min is not None:
            bids = [
                bid
                for bid in bids
                if self._parse_amount(bid.get("budget_amount")) >= budget_min
            ]

        if budget_max is not None:
            bids = [
                bid
                for bid in bids
                if self._parse_amount(bid.get("budget_amount")) <= budget_max
            ]

        if closed_from:
            closed_from_value = self._parse_datetime(closed_from)
            bids = [
                bid
                for bid in bids
                if self._parse_datetime(bid.get("closed_at")) >= closed_from_value
            ]

        if closed_to:
            closed_to_value = self._parse_datetime(closed_to)
            bids = [
                bid
                for bid in bids
                if self._parse_datetime(bid.get("closed_at")) <= closed_to_value
            ]

        bids.sort(key=lambda bid: self._sort_key(bid, sort), reverse=(order == "desc"))

        return bids

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
        items = self.list_bids(
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
        total = len(items)
        start = (page - 1) * page_size
        return BidListPage(items=items[start : start + page_size], total=total)

    def _matches_keyword(self, bid: dict[str, Any], keyword: str) -> bool:
        values = [
            str(bid.get("title", "")),
            str(bid.get("description_text", "")),
            str(bid.get("business_type", "")),
            str(bid.get("notice_type", "")),
        ]
        qualification = bid.get("qualification", {})
        if isinstance(qualification, dict):
            values.append(str(qualification.get("qualification_summary", "")))
            for key in ("license_limits", "permitted_industries", "regions"):
                value = qualification.get(key, [])
                if isinstance(value, list):
                    values.extend(str(item) for item in value)
        business_info = bid.get("business_info", {})
        if isinstance(business_info, dict):
            values.extend(str(value) for value in business_info.values())
        return any(keyword in value.lower() for value in values)

    def _parse_amount(self, value: Any) -> int:
        if not isinstance(value, str):
            return 0
        digits = value.replace(",", "").strip()
        return int(digits) if digits.isdigit() else 0

    def _parse_datetime(self, value: Any) -> str:
        if not isinstance(value, str):
            return ""
        return value

    def _sort_key(self, bid: dict[str, Any], sort: str) -> tuple[Any, str]:
        if sort == "closed_at":
            return (
                self._parse_datetime(bid.get("closed_at")),
                str(bid.get("bid_id", "")),
            )
        if sort == "budget_amount":
            return (
                self._parse_amount(bid.get("budget_amount")),
                str(bid.get("bid_id", "")),
            )
        return (self._parse_datetime(bid.get("posted_at")), str(bid.get("bid_id", "")))

    def get_bid(self, bid_id: str) -> dict[str, Any]:
        bids = self.list_bids()
        return next((bid for bid in bids if str(bid["bid_id"]) == bid_id), bids[0])

    def update_bid_status(self, bid_id: str, status: str) -> dict[str, Any]:
        bids = self.list_bids()
        matched_bid = next((bid for bid in bids if str(bid["bid_id"]) == bid_id), None)
        if matched_bid is None:
            raise KeyError(f"Bid not found: {bid_id}")

        _status_overrides[bid_id] = status
        updated_bid = dict(matched_bid)
        updated_bid["status"] = self._status_label(status)
        return updated_bid

    def set_bid_favorite(self, bid_id: str, favorite: bool) -> dict[str, Any]:
        bids = self.list_bids()
        matched_bid = next((bid for bid in bids if str(bid["bid_id"]) == bid_id), None)
        if matched_bid is None:
            raise KeyError(f"Bid not found: {bid_id}")

        _favorite_overrides[bid_id] = favorite
        updated_bid = dict(matched_bid)
        updated_bid["favorite"] = favorite
        return updated_bid
