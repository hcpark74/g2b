from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

import httpx
from sqlmodel import Session, select

from app.clients import G2BBidPublicInfoClient
from app.models import (
    BID_STATUS_COLLECTED,
    BID_STATUS_FAVORITE,
    Bid,
    BidDetail,
    build_bid_id,
    normalize_bid_seq,
    optional_str,
)


class BidPublicInfoClientProtocol(Protocol):
    def fetch_bid_list(
        self, operation_name: str, **kwargs: Any
    ) -> list[dict[str, Any]]: ...


DEFAULT_BID_PUBLIC_INFO_OPERATIONS = (
    "getBidPblancListInfoServc",
    "getBidPblancListInfoThng",
    "getBidPblancListInfoCnstwk",
    "getBidPblancListInfoFrgcpt",
)

BUSINESS_TYPE_BY_OPERATION = {
    "getBidPblancListInfoServc": "용역",
    "getBidPblancListInfoThng": "물품",
    "getBidPblancListInfoCnstwk": "공사",
    "getBidPblancListInfoFrgcpt": "외자",
    "getBidPblancListInfoEtc": "기타",
}


@dataclass(slots=True)
class BidPublicInfoSyncResult:
    fetched_count: int
    upserted_count: int
    bid_ids: list[str]


class BidPublicInfoSyncOperationError(RuntimeError):
    def __init__(
        self, operation_name: str, cause: Exception, *, retry_count: int = 0
    ) -> None:
        self.operation_name = operation_name
        self.cause = cause
        self.retry_count = retry_count
        self.status_code = self._extract_status_code(cause)
        message = (
            f"operation={operation_name} exception_type={type(cause).__name__} "
            f"retry_count={retry_count}"
        )
        if self.status_code is not None:
            message += f" status_code={self.status_code}"
        message += f" detail={cause}"
        super().__init__(message)

    def _extract_status_code(self, cause: Exception) -> int | None:
        if isinstance(cause, httpx.HTTPStatusError):
            return cause.response.status_code
        return None


class G2BBidPublicInfoSyncService:
    def __init__(
        self,
        session: Session,
        client: BidPublicInfoClientProtocol | G2BBidPublicInfoClient,
    ) -> None:
        self.session = session
        self.client = client

    def sync_bid_notices(
        self,
        *,
        inqry_bgn_dt: str,
        inqry_end_dt: str,
        operations: tuple[str, ...] = DEFAULT_BID_PUBLIC_INFO_OPERATIONS,
        num_of_rows: int = 100,
    ) -> BidPublicInfoSyncResult:
        fetched_count = 0
        upserted_count = 0
        bid_ids: list[str] = []

        for operation_name in operations:
            try:
                items = self.client.fetch_bid_list(
                    operation_name,
                    inqry_div=1,
                    inqry_bgn_dt=inqry_bgn_dt,
                    inqry_end_dt=inqry_end_dt,
                    num_of_rows=num_of_rows,
                )
            except Exception as exc:
                self.session.rollback()
                raise BidPublicInfoSyncOperationError(operation_name, exc) from exc

            fetched_count += len(items)
            for item in items:
                try:
                    bid_id = self._upsert_bid(item, operation_name)
                    if bid_id is None:
                        continue
                    upserted_count += 1
                    bid_ids.append(bid_id)
                except Exception as exc:
                    self.session.rollback()
                    raise BidPublicInfoSyncOperationError(operation_name, exc) from exc

        self.session.commit()
        return BidPublicInfoSyncResult(
            fetched_count=fetched_count,
            upserted_count=upserted_count,
            bid_ids=bid_ids,
        )

    def upsert_bid_item(
        self,
        *,
        item: dict[str, Any],
        operation_name: str,
        favorite: bool = False,
    ) -> str:
        bid_id = self._upsert_bid(item, operation_name)
        if bid_id is None:
            raise ValueError("Unable to build bid_id from search item")

        bid = self.session.get(Bid, bid_id)
        if bid is None:
            raise ValueError(f"Bid not found after upsert: {bid_id}")

        if favorite:
            bid.is_favorite = True
            if bid.status in {"", BID_STATUS_COLLECTED}:
                bid.status = BID_STATUS_FAVORITE
            self.session.add(bid)

        self.session.commit()
        return bid_id

    def _upsert_bid(self, item: dict[str, Any], operation_name: str) -> str | None:
        bid_id = self._build_bid_id(item)
        if bid_id is None:
            return None

        bid = self.session.get(Bid, bid_id)
        if bid is None:
            bid = Bid(
                bid_id=bid_id,
                bid_no=str(item.get("bidNtceNo") or bid_id),
                bid_seq=normalize_bid_seq(item.get("bidNtceOrd")),
                title=str(item.get("bidNtceNm") or "제목없음 공고"),
            )

        bid.title = str(item.get("bidNtceNm") or bid.title)
        bid.notice_org = self._optional_str(item.get("ntceInsttNm"))
        bid.demand_org = self._optional_str(item.get("dminsttNm"))
        bid.category = self._business_type(item, operation_name)
        bid.status = bid.status or BID_STATUS_COLLECTED
        bid.posted_at = self._parse_datetime(
            item.get("bidNtceDt")
        ) or self._parse_datetime(item.get("rgstDt"))
        bid.closed_at = self._parse_datetime(item.get("bidClseDt"))
        bid.budget_amount = self._parse_amount(
            item.get("asignBdgtAmt") or item.get("bdgtAmt") or item.get("presmptPrce")
        )
        bid.source_api_name = operation_name
        bid.notice_version_type = self._notice_version_type(item)
        bid.is_effective_version = bid.notice_version_type != "cancellation"
        bid.version_reason = self._version_reason(item)
        bid.last_synced_at = datetime.now(timezone.utc)
        bid.last_changed_at = self._parse_datetime(
            item.get("chgDt")
        ) or self._parse_datetime(item.get("opengDt"))
        self.session.add(bid)
        self.session.flush()

        bid.parent_bid_id = self._parent_bid_id(bid)
        self._refresh_version_group(bid.bid_no)

        bid_detail = self.session.get(BidDetail, bid_id)
        if bid_detail is None:
            bid_detail = BidDetail(bid_id=bid_id)

        bid_detail.raw_api_data = json.dumps(item, sort_keys=True)
        bid_detail.detail_url = optional_str(item.get("bidNtceDtlUrl"))
        bid_detail.collected_at = datetime.now(timezone.utc).isoformat()
        self.session.add(bid_detail)
        return bid_id

    def _build_bid_id(self, item: dict[str, Any]) -> str | None:
        return build_bid_id(item.get("bidNtceNo"), item.get("bidNtceOrd"))

    def _optional_str(self, value: Any) -> str | None:
        return optional_str(value)

    def _parse_amount(self, value: Any) -> int | None:
        if value is None:
            return None
        digits = str(value).replace(",", "").strip()
        return int(digits) if digits.isdigit() else None

    def _parse_datetime(self, value: Any) -> datetime | None:
        if value in (None, "", "없음"):
            return None

        text = str(value).strip()
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
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

    def _business_type(self, item: dict[str, Any], operation_name: str) -> str:
        return (
            self._optional_str(item.get("bsnsDivNm"))
            or self._optional_str(item.get("bidNtceBssCdNm"))
            or BUSINESS_TYPE_BY_OPERATION.get(operation_name, "미분류")
        )

    def _notice_version_type(self, item: dict[str, Any]) -> str:
        notice_kind = self._optional_str(item.get("ntceKindNm"))
        if notice_kind == "취소공고":
            return "cancellation"
        if notice_kind == "재공고":
            return "rebid"
        if notice_kind == "변경공고":
            return "revision"

        if self._is_cancellation_notice(item):
            return "cancellation"

        bid_seq = normalize_bid_seq(item.get("bidNtceOrd"))
        if bid_seq == "000":
            return "original"
        return "revision"

    def _is_cancellation_notice(self, item: dict[str, Any]) -> bool:
        for key in (
            "bidNtceCnclYn",
            "ntceCnclYn",
            "cancelYn",
            "cancYn",
            "prtcptCnclYn",
        ):
            value = self._optional_str(item.get(key))
            if value and value.upper() in {"Y", "TRUE", "1"}:
                return True

        for key in ("bidNtceNm", "ntceKindNm", "ntceNm"):
            value = self._optional_str(item.get(key))
            if value and "취소" in value:
                return True

        return False

    def _version_reason(self, item: dict[str, Any]) -> str | None:
        for key in (
            "chgNtceRsn",
            "bidNtceCnclRsn",
            "ntceRsn",
            "chgRsn",
            "rmrk",
            "noticeVersionReason",
        ):
            value = self._optional_str(item.get(key))
            if value:
                return value
        return None

    def _parent_bid_id(self, bid: Bid) -> str | None:
        siblings = list(
            self.session.exec(select(Bid).where(Bid.bid_no == bid.bid_no)).all()
        )
        earlier = [item for item in siblings if item.bid_seq < bid.bid_seq]
        if not earlier:
            return None
        earlier.sort(key=lambda item: item.bid_seq, reverse=True)
        return earlier[0].bid_id

    def _refresh_version_group(self, bid_no: str) -> None:
        versions = list(
            self.session.exec(select(Bid).where(Bid.bid_no == bid_no)).all()
        )
        if not versions:
            return

        versions.sort(key=lambda item: item.bid_seq, reverse=True)
        latest_effective_seen = False
        for index, version in enumerate(versions):
            version.is_latest_version = index == 0
            if version.is_effective_version and not latest_effective_seen:
                latest_effective_seen = True
            self.session.add(version)
