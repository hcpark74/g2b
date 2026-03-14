# pyright: reportMissingImports=false, reportMissingModuleSource=false

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from playwright.sync_api import Error as PlaywrightError  # pyright: ignore[reportMissingImports]
from sqlmodel import Session, select

from app.models import Attachment, Bid, BidDetail
from app.services.g2b_bid_page_crawler import (
    PLAYWRIGHT_ATTACHMENT_SOURCE,
    BidPageCrawlerProtocol,
)
from app.services.retry import RetryPolicy, run_with_retry


@dataclass(slots=True)
class BidCrawlResult:
    processed_bid_ids: list[str]
    attachment_count: int


class BidDetailPersistenceProtocol(Protocol):
    def crawl_bid_page(self, detail_url: str): ...


class G2BBidCrawlService:
    def __init__(
        self,
        session: Session,
        crawler: BidPageCrawlerProtocol,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.session = session
        self.crawler = crawler
        self.retry_policy = retry_policy or RetryPolicy(
            max_attempts=2, backoff_seconds=1.0
        )

    def crawl_bids(self, *, bid_ids: list[str]) -> BidCrawlResult:
        processed_bid_ids: list[str] = []
        attachment_count = 0

        for bid_id in bid_ids:
            bid = self.session.get(Bid, bid_id)
            bid_detail = self.session.get(BidDetail, bid_id)
            if bid is None or bid_detail is None or not bid_detail.detail_url:
                continue

            crawled_page = run_with_retry(
                operation_name="bid_page_crawl",
                policy=self.retry_policy,
                should_retry=self._should_retry_exception,
                func=lambda bid_detail=bid_detail: self.crawler.crawl_bid_page(
                    bid_detail.detail_url
                ),
            )
            payload = crawled_page.to_payload()
            payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            bid_detail.description_text = (
                crawled_page.text_summary or bid_detail.description_text
            )
            bid_detail.crawl_data = payload_json
            bid_detail.detail_hash = self._hash_text(payload_json)
            bid_detail.collected_at = datetime.now(timezone.utc).isoformat()
            self.session.add(bid_detail)

            existing = list(
                self.session.exec(
                    select(Attachment).where(
                        Attachment.bid_id == bid_id,
                        Attachment.source == PLAYWRIGHT_ATTACHMENT_SOURCE,
                    )
                ).all()
            )
            existing_by_key = {
                (item.name, item.download_url or ""): item for item in existing
            }
            seen: set[tuple[str, str]] = set()

            for index, attachment in enumerate(crawled_page.attachments, start=1):
                key = (attachment.name, attachment.url)
                seen.add(key)
                saved = existing_by_key.get(key)
                if saved is None:
                    saved = Attachment(
                        attachment_id=f"{bid_id}:crawl:{index}",
                        bid_id=bid_id,
                        name=attachment.name,
                    )
                saved.source = PLAYWRIGHT_ATTACHMENT_SOURCE
                saved.download_url = attachment.url
                saved.content_hash = self._hash_text(
                    f"{PLAYWRIGHT_ATTACHMENT_SOURCE}|{attachment.name}|{attachment.url}"
                )
                saved.collected_at = datetime.now(timezone.utc).isoformat()
                self.session.add(saved)
                attachment_count += 1

            for key, item in existing_by_key.items():
                if key not in seen:
                    self.session.delete(item)

            bid.last_synced_at = datetime.now(timezone.utc)
            self.session.add(bid)
            processed_bid_ids.append(bid_id)

        self.session.commit()
        return BidCrawlResult(
            processed_bid_ids=processed_bid_ids,
            attachment_count=attachment_count,
        )

    def _hash_text(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _should_retry_exception(self, exc: Exception) -> bool:
        return isinstance(exc, (TimeoutError, PlaywrightError))
