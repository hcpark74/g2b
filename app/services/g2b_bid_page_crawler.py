# pyright: reportMissingImports=false, reportMissingModuleSource=false

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Any, Protocol

from app.config import settings


PLAYWRIGHT_ATTACHMENT_SOURCE = "playwright_detail"


@dataclass(slots=True)
class CrawledAttachment:
    name: str
    url: str
    source: str = PLAYWRIGHT_ATTACHMENT_SOURCE


@dataclass(slots=True)
class CrawledBidPage:
    page_title: str
    detail_html: str
    text_summary: str
    attachments: list[CrawledAttachment]

    def to_payload(self) -> dict[str, Any]:
        return {
            "page_title": self.page_title,
            "detail_html": self.detail_html,
            "text_summary": self.text_summary,
            "attachments": [asdict(item) for item in self.attachments],
        }


class BidPageCrawlerProtocol(Protocol):
    def crawl_bid_page(self, detail_url: str) -> CrawledBidPage: ...


class G2BBidPageCrawler:
    def __init__(self, *, headless: bool | None = None) -> None:
        self.headless = settings.playwright_headless if headless is None else headless

    def crawl_bid_page(self, detail_url: str) -> CrawledBidPage:
        try:
            from playwright.sync_api import sync_playwright  # pyright: ignore[reportMissingImports]
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Playwright is not installed. Run `pip install -e .` after adding the dependency and `playwright install chromium`."
            ) from exc

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch_persistent_context(
                user_data_dir=str(self._user_data_dir()),
                headless=self.headless,
            )
            try:
                page = browser.new_page()
                page.goto(detail_url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(1000)

                content_html = self._first_html(
                    page,
                    ["#container", "#content", "main", "body"],
                )
                text_summary = self._first_text(
                    page,
                    ["#container", "#content", "main", "body"],
                )
                attachments = self._extract_attachments(page)

                return CrawledBidPage(
                    page_title=page.title(),
                    detail_html=content_html,
                    text_summary=text_summary[:4000],
                    attachments=attachments,
                )
            finally:
                browser.close()

    def _user_data_dir(self) -> Path:
        path = Path(settings.playwright_user_data_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _first_html(self, page: Any, selectors: list[str]) -> str:
        for selector in selectors:
            locator = page.locator(selector)
            if locator.count() > 0:
                return locator.first.inner_html()
        return ""

    def _first_text(self, page: Any, selectors: list[str]) -> str:
        for selector in selectors:
            locator = page.locator(selector)
            if locator.count() > 0:
                return " ".join(locator.first.inner_text().split())
        return ""

    def _extract_attachments(self, page: Any) -> list[CrawledAttachment]:
        attachment_selectors = [
            "[atch_file_nm]",
            "a[href*='download']",
            "a[href*='Down']",
            "a[href$='.pdf']",
            "a[href$='.hwp']",
            "a[href$='.zip']",
        ]
        seen: set[tuple[str, str]] = set()
        attachments: list[CrawledAttachment] = []

        for selector in attachment_selectors:
            locator = page.locator(selector)
            count = locator.count()
            for index in range(count):
                item = locator.nth(index)
                name = " ".join((item.inner_text() or "").split())
                href = item.get_attribute("href") or ""
                onclick = item.get_attribute("onclick") or ""
                attr_file_name = item.get_attribute("atch_file_nm") or ""
                original_file_name = self._extract_onclick_value(
                    onclick, "orgnlAtchFileNm"
                )
                name = original_file_name or name or attr_file_name
                url = href or (f"javascript:{onclick}" if onclick else "")
                if not name or not url:
                    continue
                key = (name, url)
                if key in seen:
                    continue
                seen.add(key)
                attachments.append(CrawledAttachment(name=name, url=url))

        return attachments

    def _extract_onclick_value(self, onclick: str, key: str) -> str:
        pattern = rf"'{re.escape(key)}':'([^']+)"
        match = re.search(pattern, onclick)
        if match:
            return match.group(1).strip()
        return ""
