from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from sqlmodel import Session, select

from app.clients import G2BBidPublicInfoClient
from app.models import Bid, BidVersionChange, build_bid_id, normalize_bid_seq


class BidChangeHistoryClientProtocol(Protocol):
    def fetch_bid_change_history(
        self,
        operation_name: str,
        *,
        bid_ntce_no: str,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[dict[str, Any]]: ...


@dataclass(slots=True)
class BidChangeHistorySyncResult:
    processed_bid_ids: list[str]
    fetched_item_count: int


class G2BBidChangeHistoryService:
    def __init__(
        self,
        session: Session,
        client: BidChangeHistoryClientProtocol | G2BBidPublicInfoClient,
    ) -> None:
        self.session = session
        self.client = client

    def sync_change_history(
        self,
        *,
        bid_ids: list[str] | None = None,
        num_of_rows: int = 100,
    ) -> BidChangeHistorySyncResult:
        bids = self._load_bids(bid_ids)
        processed_bid_ids: list[str] = []
        fetched_item_count = 0

        for bid in bids:
            items = self.client.fetch_bid_change_history(
                self._operation_name_for_bid(bid),
                bid_ntce_no=bid.bid_no,
                num_of_rows=num_of_rows,
            )
            self._replace_changes(bid, items)
            processed_bid_ids.append(bid.bid_id)
            fetched_item_count += len(items)

        self.session.commit()
        return BidChangeHistorySyncResult(
            processed_bid_ids=processed_bid_ids,
            fetched_item_count=fetched_item_count,
        )

    def _load_bids(self, bid_ids: list[str] | None) -> list[Bid]:
        if bid_ids:
            return [
                bid
                for bid in (self.session.get(Bid, bid_id) for bid_id in bid_ids)
                if bid
            ]
        return list(self.session.exec(select(Bid)).all())

    def _operation_name_for_bid(self, bid: Bid) -> str:
        mapping = {
            "용역": "getBidPblancListInfoChgHstryServc",
            "물품": "getBidPblancListInfoChgHstryThng",
            "공사": "getBidPblancListInfoChgHstryCnstwk",
        }
        return mapping.get(bid.category or "", "getBidPblancListInfoChgHstryServc")

    def _replace_changes(self, bid: Bid, items: list[dict[str, Any]]) -> None:
        existing = self.session.exec(
            select(BidVersionChange).where(BidVersionChange.bid_id == bid.bid_id)
        )
        for row in existing:
            self.session.delete(row)

        collected_at = datetime.now(timezone.utc).isoformat()
        for index, item in enumerate(items, start=1):
            target_bid_id = (
                build_bid_id(
                    item.get("bidNtceNo") or bid.bid_no,
                    item.get("bidNtceOrd") or bid.bid_seq,
                )
                or bid.bid_id
            )
            if target_bid_id != bid.bid_id:
                continue
            self.session.add(
                BidVersionChange(
                    change_id=f"{bid.bid_id}:{index:03d}",
                    bid_id=bid.bid_id,
                    bid_no=bid.bid_no,
                    bid_seq=normalize_bid_seq(item.get("bidNtceOrd") or bid.bid_seq),
                    change_data_div_name=self._text(item, "chgDataDivNm"),
                    change_item_name=self._text(item, "chgItemNm") or "변경항목",
                    before_value=self._text(item, "bfchgVal", "chgBfCn", "beforeValue"),
                    after_value=self._text(item, "afchgVal", "chgAfCn", "afterValue"),
                    changed_at=self._text(item, "chgDt") or collected_at,
                    rbid_no=self._text(item, "rbidNo"),
                    license_limit_code_list_raw=self._text(item, "lcnsLmtCdRgstList"),
                    source_api_name=self._operation_name_for_bid(bid),
                    raw_data=json.dumps(item, sort_keys=True),
                )
            )

    def _text(self, item: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = item.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return None
