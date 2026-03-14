# pyright: reportArgumentType=false

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
from typing import Any, Protocol

import httpx
from sqlmodel import Session, select

from app.clients import G2BBidPublicInfoClient
from app.models import (
    Attachment,
    Bid,
    BidDetail,
    BidLicenseLimit,
    BidParticipationRegion,
    BidPurchaseItem,
    optional_str,
)
from app.services.g2b_sync_plan import (
    PHASE2_DETAIL_ENRICHMENT_OPERATIONS,
    should_run_detail_enrichment,
)
from app.services.retry import RetryPolicy, run_with_retry


class BidDetailEnrichmentClientProtocol(Protocol):
    def fetch_bid_detail_list(
        self,
        operation_name: str,
        *,
        bid_ntce_no: str,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[dict[str, Any]]: ...


@dataclass(slots=True)
class BidDetailEnrichmentResult:
    processed_bid_ids: list[str]
    fetched_item_count: int


class G2BBidDetailEnrichmentService:
    def __init__(
        self,
        session: Session,
        client: BidDetailEnrichmentClientProtocol | G2BBidPublicInfoClient,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.session = session
        self.client = client
        self.retry_policy = retry_policy or RetryPolicy()

    def enrich_bids(
        self,
        *,
        bid_ids: list[str] | None = None,
        operations: tuple[str, ...] = PHASE2_DETAIL_ENRICHMENT_OPERATIONS,
        num_of_rows: int = 100,
        selection_mode: str = "targeted",
        recent_days: int = 7,
    ) -> BidDetailEnrichmentResult:
        bids = self._load_target_bids(
            bid_ids,
            selection_mode=selection_mode,
            recent_days=recent_days,
        )
        processed_bid_ids: list[str] = []
        fetched_item_count = 0

        for bid in bids:
            for operation_name in operations:
                items = self._fetch_items_for_bid(
                    bid,
                    operation_name=operation_name,
                    num_of_rows=num_of_rows,
                )
                fetched_item_count += len(items)
                self._apply_items(bid.bid_id, operation_name, items)
            bid.last_synced_at = datetime.now(timezone.utc)
            self.session.add(bid)
            processed_bid_ids.append(bid.bid_id)

        self.session.commit()
        return BidDetailEnrichmentResult(
            processed_bid_ids=processed_bid_ids,
            fetched_item_count=fetched_item_count,
        )

    def _load_target_bids(
        self,
        bid_ids: list[str] | None,
        *,
        selection_mode: str,
        recent_days: int,
    ) -> list[Bid]:
        if bid_ids:
            return [
                bid
                for bid in (self.session.get(Bid, bid_id) for bid_id in bid_ids)
                if bid
            ]
        all_bids = list(self.session.exec(select(Bid)).all())
        if selection_mode == "all":
            return all_bids
        return [
            bid
            for bid in all_bids
            if self._should_select_bid(bid, recent_days=recent_days)
        ]

    def _should_select_bid(self, bid: Bid, *, recent_days: int) -> bool:
        now = datetime.now(timezone.utc)
        recent_threshold = now - timedelta(days=recent_days)
        changed_recently = self._is_recent(bid.last_changed_at, recent_threshold)
        is_new_bid = self._is_recent(bid.created_at, recent_threshold)
        return should_run_detail_enrichment(
            status=bid.status,
            is_favorite=bid.is_favorite,
            changed_recently=changed_recently,
            is_new_bid=is_new_bid,
        )

    def _is_recent(self, value: datetime | None, threshold: datetime) -> bool:
        if value is None:
            return False
        comparable = value
        if comparable.tzinfo is None:
            comparable = comparable.replace(tzinfo=timezone.utc)
        return comparable >= threshold

    def _apply_items(
        self, bid_id: str, operation_name: str, items: list[dict[str, Any]]
    ) -> None:
        if operation_name == "getBidPblancListInfoLicenseLimit":
            self._replace_license_limits(bid_id, operation_name, items)
            return
        if operation_name == "getBidPblancListInfoPrtcptPsblRgn":
            self._replace_regions(bid_id, operation_name, items)
            return
        if operation_name == "getBidPblancListInfoEorderAtchFileInfo":
            self._replace_attachments(bid_id, operation_name, items)
            return
        if operation_name in {
            "getBidPblancListInfoThngPurchsObjPrdct",
            "getBidPblancListInfoServcPurchsObjPrdct",
            "getBidPblancListInfoFrgcptPurchsObjPrdct",
        }:
            self._replace_purchase_items(bid_id, operation_name, items)
            return

    def _fetch_items_for_bid(
        self,
        bid: Bid,
        *,
        operation_name: str,
        num_of_rows: int,
    ) -> list[dict[str, Any]]:
        for lookup_value in self._detail_lookup_values(bid):
            items = run_with_retry(
                operation_name=operation_name,
                policy=self.retry_policy,
                should_retry=self._should_retry_exception,
                func=lambda lookup_value=lookup_value: (
                    self.client.fetch_bid_detail_list(
                        operation_name,
                        bid_ntce_no=lookup_value,
                        num_of_rows=num_of_rows,
                    )
                ),
            )
            if items:
                return items
        return []

    def _detail_lookup_values(self, bid: Bid) -> list[str]:
        candidates: list[str] = []

        def _append(value: str | None) -> None:
            text = optional_str(value)
            if text and text not in candidates:
                candidates.append(text)

        _append(bid.bid_no)

        bid_detail = self.session.get(BidDetail, bid.bid_id)
        if bid_detail is None or not bid_detail.raw_api_data:
            return candidates

        try:
            payload = json.loads(bid_detail.raw_api_data)
        except json.JSONDecodeError:
            return candidates

        if isinstance(payload, dict):
            _append(payload.get("bidNtceNo"))
            _append(payload.get("untyNtceNo"))

        return candidates

    def _replace_license_limits(
        self, bid_id: str, operation_name: str, items: list[dict[str, Any]]
    ) -> None:
        existing_items = self.session.exec(
            select(BidLicenseLimit).where(BidLicenseLimit.bid_id == bid_id)  # pyright: ignore[reportArgumentType]
        )
        for existing_item in existing_items:
            self.session.delete(existing_item)
        collected_at = datetime.now(timezone.utc).isoformat()
        for item in items:
            license_name = optional_str(
                item.get("prtcptPsblIndstrytyNm")
                or item.get("licnsNm")
                or item.get("indstrytyNm")
            )
            if not license_name:
                continue
            self.session.add(
                BidLicenseLimit(
                    bid_id=bid_id,
                    license_name=license_name,
                    source_api_name=operation_name,
                    collected_at=collected_at,
                )
            )

    def _replace_regions(
        self, bid_id: str, operation_name: str, items: list[dict[str, Any]]
    ) -> None:
        existing_items = self.session.exec(
            select(BidParticipationRegion).where(  # pyright: ignore[reportArgumentType]
                BidParticipationRegion.bid_id == bid_id
            )
        )
        for existing_item in existing_items:
            self.session.delete(existing_item)
        collected_at = datetime.now(timezone.utc).isoformat()
        for item in items:
            region_name = optional_str(
                item.get("prtcptPsblRgnNm") or item.get("rgstRgnNm")
            )
            if not region_name:
                continue
            self.session.add(
                BidParticipationRegion(
                    bid_id=bid_id,
                    region_name=region_name,
                    source_api_name=operation_name,
                    collected_at=collected_at,
                )
            )

    def _replace_attachments(
        self, bid_id: str, operation_name: str, items: list[dict[str, Any]]
    ) -> None:
        existing = list(
            self.session.exec(
                select(Attachment).where(
                    Attachment.bid_id == bid_id,
                    Attachment.source == operation_name,
                )
            ).all()
        )
        existing_by_key = {
            (attachment.name, attachment.download_url or ""): attachment
            for attachment in existing
        }
        collected_at = datetime.now(timezone.utc).isoformat()

        seen_keys: set[tuple[str, str]] = set()
        for index, item in enumerate(items, start=1):
            name = optional_str(
                item.get("atchFileNm")
                or item.get("eorderAtchFileNm")
                or item.get("fileNm")
                or item.get("atchFileCn")
            )
            download_url = (
                optional_str(
                    item.get("dwnldUrl")
                    or item.get("atchFileUrl")
                    or item.get("eorderAtchFileUrl")
                )
                or ""
            )
            if not name:
                continue
            key = (name, download_url)
            seen_keys.add(key)
            attachment = existing_by_key.get(key)
            if attachment is None:
                attachment = Attachment(
                    attachment_id=f"{bid_id}:eorder:{index}",
                    bid_id=bid_id,
                    name=name,
                )
            attachment.file_type = optional_str(
                item.get("fileTypeNm")
                or item.get("atchFileTypeNm")
                or item.get("eorderDocDivNm")
            )
            attachment.source = operation_name
            attachment.download_url = download_url or None
            attachment.content_hash = self._hash_text(
                f"{operation_name}|{name}|{download_url}"
            )
            attachment.collected_at = collected_at
            self.session.add(attachment)

        for key, attachment in existing_by_key.items():
            if key not in seen_keys:
                self.session.delete(attachment)

    def _replace_purchase_items(
        self, bid_id: str, operation_name: str, items: list[dict[str, Any]]
    ) -> None:
        existing_items = self.session.exec(
            select(BidPurchaseItem).where(BidPurchaseItem.bid_id == bid_id)  # pyright: ignore[reportArgumentType]
        )
        for existing_item in existing_items:
            self.session.delete(existing_item)
        collected_at = datetime.now(timezone.utc).isoformat()
        for item in items:
            item_name = optional_str(
                item.get("prdctClsfcNoNm")
                or item.get("thngNm")
                or item.get("prdctNm")
                or item.get("itemNm")
            )
            if not item_name:
                continue
            self.session.add(
                BidPurchaseItem(
                    bid_id=bid_id,
                    item_name=item_name,
                    item_code=optional_str(
                        item.get("prdctClsfcNo") or item.get("itemNo")
                    ),
                    quantity=optional_str(item.get("purchsQty") or item.get("qty")),
                    delivery_condition=optional_str(
                        item.get("dlvrTmlmtCn") or item.get("dlvrCndtnNm")
                    ),
                    source_api_name=operation_name,
                    collected_at=collected_at,
                )
            )

    def _hash_text(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _should_retry_exception(self, exc: Exception) -> bool:
        if isinstance(exc, httpx.TimeoutException):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            return exc.response.status_code >= 500 or exc.response.status_code == 429
        return False
