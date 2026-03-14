from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from sqlmodel import Session, select

from app.clients import G2BIndustryInfoClient
from app.models import BidLicenseLimit, BidReferenceInfo, optional_str


class ReferenceEnrichmentClientProtocol(Protocol):
    def fetch_industry_base_law(
        self,
        *,
        industry_name: str,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[dict[str, Any]]: ...


@dataclass(slots=True)
class ReferenceEnrichmentResult:
    processed_bid_ids: list[str]
    fetched_item_count: int


class G2BReferenceEnrichmentService:
    def __init__(
        self,
        session: Session,
        client: ReferenceEnrichmentClientProtocol | G2BIndustryInfoClient,
    ) -> None:
        self.session = session
        self.client = client

    def enrich_bids(
        self,
        *,
        bid_ids: list[str] | None,
        num_of_rows: int = 100,
    ) -> ReferenceEnrichmentResult:
        if not bid_ids:
            return ReferenceEnrichmentResult(processed_bid_ids=[], fetched_item_count=0)

        processed_bid_ids: list[str] = []
        fetched_item_count = 0

        for bid_id in bid_ids:
            reference_names = self._load_reference_names(bid_id)
            self._delete_existing_reference_items(bid_id)

            for reference_name in reference_names:
                items = self.client.fetch_industry_base_law(
                    industry_name=reference_name,
                    num_of_rows=num_of_rows,
                )
                fetched_item_count += len(items)
                self._store_reference_items(bid_id, reference_name, items)

            processed_bid_ids.append(bid_id)

        self.session.commit()
        return ReferenceEnrichmentResult(
            processed_bid_ids=processed_bid_ids,
            fetched_item_count=fetched_item_count,
        )

    def _load_reference_names(self, bid_id: str) -> list[str]:
        rows = self.session.exec(
            select(BidLicenseLimit).where(BidLicenseLimit.bid_id == bid_id)
        ).all()
        names: list[str] = []
        for row in rows:
            name = optional_str(row.license_name)
            if name and name not in names:
                names.append(name)
        return names

    def _delete_existing_reference_items(self, bid_id: str) -> None:
        rows = self.session.exec(
            select(BidReferenceInfo).where(BidReferenceInfo.bid_id == bid_id)
        )
        for row in rows:
            self.session.delete(row)

    def _store_reference_items(
        self, bid_id: str, reference_name: str, items: list[dict[str, Any]]
    ) -> None:
        collected_at = datetime.now(timezone.utc).isoformat()
        for item in items:
            reference_key = optional_str(
                item.get("indstrytyCd")
                or item.get("indstrytyNo")
                or item.get("lawNm")
                or reference_name
            )
            if not reference_key:
                continue
            self.session.add(
                BidReferenceInfo(
                    bid_id=bid_id,
                    reference_key=reference_key,
                    reference_name=reference_name,
                    source_api_name="industryBaseLaw",
                    raw_data=json.dumps(item, ensure_ascii=False, sort_keys=True),
                    collected_at=collected_at,
                )
            )
