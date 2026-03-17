from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from sqlmodel import Session, select

from app.clients import G2BBidPublicInfoClient
from app.models import Bid, build_bid_id
from app.services.g2b_bid_sync_service import (
    BUSINESS_TYPE_BY_OPERATION,
    DEFAULT_BID_PUBLIC_INFO_OPERATIONS,
)


class G2BBidSearchService:
    def __init__(
        self,
        *,
        client: G2BBidPublicInfoClient,
        session: Session | None = None,
    ) -> None:
        self.client = client
        self.session = session

    def search_bids(
        self,
        *,
        search_query: str | None = None,
        org: str | None = None,
        closed_from: str | None = None,
        closed_to: str | None = None,
        sort: str = "updated_at",
        limit: int = 50,
        operations: Sequence[str] = DEFAULT_BID_PUBLIC_INFO_OPERATIONS,
    ) -> list[dict[str, Any]]:
        normalized_query = (search_query or "").strip()
        normalized_org = (org or "").strip().lower()
        exact_bid_no = self._extract_bid_no(normalized_query)

        items: list[dict[str, Any]] = []
        if exact_bid_no:
            for operation_name in operations:
                fetched = self.client.fetch_bid_list(
                    operation_name,
                    inqry_div=2,
                    bid_ntce_no=exact_bid_no,
                    num_of_rows=min(max(limit, 20), 100),
                )
                items.extend(
                    self._normalize_item(item, operation_name) for item in fetched
                )
        else:
            begin_dt, end_dt = self._build_date_window(closed_from, closed_to)
            row_budget = min(max(limit * 2, 50), 200)
            for operation_name in operations:
                fetched = self.client.fetch_bid_list(
                    operation_name,
                    inqry_div=1,
                    inqry_bgn_dt=begin_dt.strftime("%Y%m%d%H%M"),
                    inqry_end_dt=end_dt.strftime("%Y%m%d%H%M"),
                    num_of_rows=row_budget,
                )
                items.extend(
                    self._normalize_item(item, operation_name) for item in fetched
                )

        deduped = self._dedupe_items(items)
        filtered = [
            item
            for item in deduped
            if self._matches_query(item, normalized_query, exact_bid_no)
            and self._matches_org(item, normalized_org)
            and self._matches_closed_range(item, closed_from, closed_to)
        ]
        self._mark_favorites(filtered)
        filtered.sort(key=lambda item: self._sort_key(item, sort))
        if sort not in {"closed_at_asc", "notice_org", "title"}:
            filtered.reverse()
        for index, item in enumerate(filtered[:limit], start=1):
            item["row_number"] = index
        return filtered[:limit]

    def _build_date_window(
        self, closed_from: str | None, closed_to: str | None
    ) -> tuple[datetime, datetime]:
        now = datetime.now()
        begin_dt = self._parse_datetime_value(closed_from) or (now - timedelta(days=30))
        end_dt = self._parse_datetime_value(closed_to) or (now + timedelta(days=30))
        if begin_dt > end_dt:
            begin_dt, end_dt = end_dt, begin_dt
        return begin_dt, end_dt

    def _normalize_item(
        self, item: dict[str, Any], operation_name: str
    ) -> dict[str, Any]:
        bid_no = str(item.get("bidNtceNo") or "").strip()
        bid_seq = str(item.get("bidNtceOrd") or "000").strip().zfill(3)
        bid_id = build_bid_id(bid_no, bid_seq) or bid_no
        posted_at = self._parse_datetime_value(
            item.get("bidNtceDt") or item.get("rgstDt")
        )
        closed_at = self._parse_datetime_value(item.get("bidClseDt"))
        opened_at = self._parse_datetime_value(item.get("opengDt"))
        changed_at = self._parse_datetime_value(
            item.get("chgDt") or item.get("opengDt")
        )
        budget_value = self._parse_amount(
            item.get("asignBdgtAmt") or item.get("bdgtAmt") or item.get("presmptPrce")
        )
        return {
            "bid_id": bid_id,
            "bid_no": bid_no,
            "bid_seq": bid_seq,
            "display_bid_no": bid_id,
            "title": str(item.get("bidNtceNm") or "제목없음 공고"),
            "notice_org": str(item.get("ntceInsttNm") or "-"),
            "demand_org": str(item.get("dminsttNm") or "-"),
            "business_type": str(
                item.get("bsnsDivNm")
                or item.get("bidNtceBssCdNm")
                or BUSINESS_TYPE_BY_OPERATION.get(operation_name, "미분류")
            ),
            "posted_at": self._format_datetime(posted_at),
            "closed_at": self._format_datetime(closed_at),
            "opened_at": self._format_datetime(opened_at),
            "last_changed_at": changed_at,
            "budget_amount": self._format_amount(budget_value),
            "budget_amount_value": budget_value,
            "detail_url": str(item.get("bidNtceDtlUrl") or "").strip(),
            "source_api_name": operation_name,
            "favorite": False,
            "raw_notice_version_type": str(item.get("ntceKindNm") or "").strip(),
            "raw_version_reason": str(
                item.get("chgNtceRsn") or item.get("rmrk") or ""
            ).strip(),
        }

    def _dedupe_items(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: dict[str, dict[str, Any]] = {}
        for item in items:
            bid_id = str(item.get("bid_id") or "")
            if not bid_id:
                continue
            current = deduped.get(bid_id)
            if current is None:
                deduped[bid_id] = item
                continue
            current_changed = current.get("last_changed_at") or datetime.min
            incoming_changed = item.get("last_changed_at") or datetime.min
            if incoming_changed >= current_changed:
                deduped[bid_id] = item
        return list(deduped.values())

    def _mark_favorites(self, items: list[dict[str, Any]]) -> None:
        if self.session is None or not items:
            return
        bid_ids = [str(item.get("bid_id") or "") for item in items]
        favorites = {
            bid.bid_id: bid
            for bid in self.session.exec(
                select(Bid).where(Bid.bid_id.in_(bid_ids))
            ).all()
        }
        for item in items:
            bid = favorites.get(str(item.get("bid_id") or ""))
            if bid is None:
                continue
            item["favorite"] = bool(bid.is_favorite)
            item["saved_status"] = "관심 공고"

    def _matches_query(
        self, item: dict[str, Any], search_query: str, exact_bid_no: str | None
    ) -> bool:
        if not search_query:
            return True
        if exact_bid_no:
            return str(item.get("bid_no") or "").strip() == exact_bid_no
        normalized_query = search_query.lower()
        searchable = [
            str(item.get("bid_id") or "").lower(),
            str(item.get("bid_no") or "").lower(),
            str(item.get("title") or "").lower(),
            str(item.get("notice_org") or "").lower(),
            str(item.get("demand_org") or "").lower(),
        ]
        return any(normalized_query in value for value in searchable)

    def _matches_org(self, item: dict[str, Any], org: str) -> bool:
        if not org:
            return True
        return (
            org in str(item.get("notice_org") or "").lower()
            or org in str(item.get("demand_org") or "").lower()
        )

    def _matches_closed_range(
        self, item: dict[str, Any], closed_from: str | None, closed_to: str | None
    ) -> bool:
        closed_at = self._parse_datetime_value(item.get("closed_at"))
        if closed_at is None:
            return not closed_from and not closed_to
        from_dt = self._parse_datetime_value(closed_from)
        to_dt = self._parse_datetime_value(closed_to)
        if from_dt is not None and closed_at < from_dt:
            return False
        if to_dt is not None and closed_at > to_dt:
            return False
        return True

    def _sort_key(self, item: dict[str, Any], sort: str) -> tuple[Any, ...]:
        if sort == "closed_at_asc":
            return (self._parse_datetime_value(item.get("closed_at")) or datetime.max,)
        if sort == "closed_at_desc":
            return (self._parse_datetime_value(item.get("closed_at")) or datetime.min,)
        if sort == "notice_org":
            return (str(item.get("notice_org") or ""),)
        if sort == "title":
            return (str(item.get("title") or ""),)
        if sort == "posted_at":
            return (self._parse_datetime_value(item.get("posted_at")) or datetime.min,)
        return (
            self._parse_datetime_value(item.get("last_changed_at")) or datetime.min,
        )

    def _extract_bid_no(self, query: str) -> str | None:
        if not query:
            return None
        candidate = query.strip().split("-")[0]
        if len(candidate) < 8:
            return None
        if any(char.isspace() for char in candidate):
            return None
        if not any(char.isdigit() for char in candidate):
            return None
        return candidate

    def _parse_datetime_value(self, value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if value in (None, "", "-"):
            return None
        text = str(value).strip()
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%dT%H:%M",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
            "%Y%m%d%H%M%S",
            "%Y%m%d%H%M",
        ):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        return None

    def _format_datetime(self, value: datetime | None) -> str:
        if value is None:
            return "-"
        return value.strftime("%Y-%m-%d %H:%M")

    def _parse_amount(self, value: Any) -> int | None:
        if value is None:
            return None
        digits = str(value).replace(",", "").strip()
        return int(digits) if digits.isdigit() else None

    def _format_amount(self, value: int | None) -> str:
        if value is None:
            return "-"
        return f"{value:,}"
