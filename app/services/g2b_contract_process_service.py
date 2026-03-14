from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

import httpx
from sqlmodel import Session, select

from app.clients import G2BContractProcessClient
from app.models import (
    Bid,
    BidDetail,
    ContractProcessIntegration,
    TimelineStageSnapshot,
)
from app.services.retry import RetryPolicy, run_with_retry


class ContractProcessClientProtocol(Protocol):
    def fetch_contract_process(
        self,
        *,
        operation_name: str,
        inqry_div: int,
        value: str,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[dict[str, Any]]: ...


@dataclass(slots=True)
class ContractProcessSyncResult:
    processed_bid_ids: list[str]
    fetched_item_count: int


class G2BContractProcessService:
    def __init__(
        self,
        session: Session,
        client: ContractProcessClientProtocol | G2BContractProcessClient,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.session = session
        self.client = client
        self.retry_policy = retry_policy or RetryPolicy()

    def enrich_timelines(
        self,
        *,
        bid_ids: list[str] | None = None,
        num_of_rows: int = 100,
    ) -> ContractProcessSyncResult:
        bids = self._load_bids(bid_ids)
        processed_bid_ids: list[str] = []
        fetched_item_count = 0

        for bid in bids:
            lookup_chain = self._lookup_chain_for_bid(bid)
            items: list[dict[str, Any]] = []
            used_div = None
            used_value = None
            for inqry_div, lookup_value in lookup_chain:
                fetched = run_with_retry(
                    operation_name=self._operation_name_for_bid(bid),
                    policy=self.retry_policy,
                    should_retry=self._should_retry_exception,
                    func=lambda bid=bid, inqry_div=inqry_div, lookup_value=lookup_value: (
                        self.client.fetch_contract_process(
                            operation_name=self._operation_name_for_bid(bid),
                            inqry_div=inqry_div,
                            value=lookup_value,
                            num_of_rows=num_of_rows,
                        )
                    ),
                )
                if fetched:
                    items = fetched
                    used_div = inqry_div
                    used_value = lookup_value
                    break

            if items and used_div is not None and used_value is not None:
                fetched_item_count += len(items)
                self._replace_integrations(bid.bid_id, used_div, used_value, items)
                self._replace_timeline_snapshots(bid, items)
                bid.last_synced_at = datetime.now(timezone.utc)
                self.session.add(bid)
            processed_bid_ids.append(bid.bid_id)

        self.session.commit()
        return ContractProcessSyncResult(
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
            "용역": "getCntrctProcssIntgOpenServc",
            "물품": "getCntrctProcssIntgOpenThng",
            "공사": "getCntrctProcssIntgOpenCnstwk",
            "외자": "getCntrctProcssIntgOpenFrgcpt",
        }
        return mapping.get(bid.category or "", "getCntrctProcssIntgOpenServc")

    def _lookup_chain_for_bid(self, bid: Bid) -> list[tuple[int, str]]:
        values = self._connection_key_values(bid.bid_id)
        chain: list[tuple[int, str]] = []
        if bid.bid_no:
            chain.append((1, bid.bid_no))
        if values.get("bfSpecRgstNo"):
            chain.append((2, values["bfSpecRgstNo"]))
        if values.get("orderPlanNo"):
            chain.append((3, values["orderPlanNo"]))
        if values.get("prcrmntReqNo"):
            chain.append((4, values["prcrmntReqNo"]))
        return chain

    def _connection_key_values(self, bid_id: str) -> dict[str, str]:
        bid_detail = self.session.get(BidDetail, bid_id)
        if bid_detail is None or not bid_detail.raw_api_data:
            return {}
        try:
            payload = json.loads(bid_detail.raw_api_data)
        except json.JSONDecodeError:
            return {}
        values: dict[str, str] = {}
        for key in ("bfSpecRgstNo", "orderPlanNo", "prcrmntReqNo"):
            value = payload.get(key)
            if value is not None and str(value).strip():
                values[key] = str(value).strip()
        return values

    def _replace_integrations(
        self,
        bid_id: str,
        inqry_div: int,
        source_key: str,
        items: list[dict[str, Any]],
    ) -> None:
        existing_items = self.session.exec(
            select(ContractProcessIntegration).where(
                ContractProcessIntegration.bid_id == bid_id
            )  # pyright: ignore[reportArgumentType]
        )
        for existing_item in existing_items:
            self.session.delete(existing_item)

        collected_at = datetime.now(timezone.utc).isoformat()
        for item in items:
            self.session.add(
                ContractProcessIntegration(
                    bid_id=bid_id,
                    inqry_div=inqry_div,
                    source_key=source_key,
                    award_company=self._text(
                        item, "bidwinrCmpnyNm", "sucsfbidLwfrmpnyNm"
                    ),
                    award_amount=self._text(item, "sucsfbidAmt", "cntrctAmt"),
                    contract_no=self._text(item, "cntrctNo"),
                    contract_name=self._text(item, "cntrctNm"),
                    contract_date=self._text(item, "cntrctDate", "cntrctDt"),
                    raw_data=json.dumps(item, sort_keys=True),
                    collected_at=collected_at,
                )
            )

    def _replace_timeline_snapshots(
        self, bid: Bid, items: list[dict[str, Any]]
    ) -> None:
        existing_items = self.session.exec(
            select(TimelineStageSnapshot).where(
                TimelineStageSnapshot.bid_id == bid.bid_id
            )  # pyright: ignore[reportArgumentType]
        )
        for existing_item in existing_items:
            self.session.delete(existing_item)

        first_item = items[0] if items else {}
        award_company = self._text(first_item, "bidwinrCmpnyNm", "sucsfbidLwfrmpnyNm")
        contract_no = self._text(first_item, "cntrctNo")
        contract_name = self._text(first_item, "cntrctNm")

        snapshots = [
            TimelineStageSnapshot(
                bid_id=bid.bid_id,
                stage="입찰공고",
                status="완료" if bid.posted_at else "미도달",
                number=bid.bid_id,
                occurred_at=self._format_datetime(bid.posted_at),
                meta=f"마감 {self._format_datetime(bid.closed_at)}",
            ),
            TimelineStageSnapshot(
                bid_id=bid.bid_id,
                stage="개찰/낙찰",
                status="완료" if award_company else "미도달",
                number=award_company,
                occurred_at=self._text(first_item, "opengDate", "sucsfbidDate"),
                meta=self._text(first_item, "sucsfbidAmt") or "낙찰 정보 연동 예정",
            ),
            TimelineStageSnapshot(
                bid_id=bid.bid_id,
                stage="계약",
                status="완료" if contract_no else "미도달",
                number=contract_no,
                occurred_at=self._text(first_item, "cntrctDate", "cntrctDt"),
                meta=contract_name or "계약정보 연동 예정",
            ),
        ]
        for snapshot in snapshots:
            self.session.add(snapshot)

    def _text(self, item: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = item.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return None

    def _format_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.strftime("%Y-%m-%d %H:%M")

    def _should_retry_exception(self, exc: Exception) -> bool:
        if isinstance(exc, httpx.TimeoutException):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            return exc.response.status_code >= 500 or exc.response.status_code == 429
        return False
