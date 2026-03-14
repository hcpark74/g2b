from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from app.config import settings


class G2BIndustryInfoClient:
    def __init__(self, http_client: httpx.Client | None = None) -> None:
        self._owns_client = http_client is None
        self.http_client = http_client or httpx.Client(
            base_url=settings.g2b_api_industry_base_url,
            timeout=30.0,
        )

    def close(self) -> None:
        if self._owns_client:
            self.http_client.close()

    def fetch_industry_base_law(
        self,
        *,
        industry_name: str,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[dict[str, Any]]:
        params = {
            "serviceKey": self._get_service_key(),
            "pageNo": page_no,
            "numOfRows": num_of_rows,
            "type": "json",
            "indstrytyNm": industry_name,
        }
        response = self.http_client.get("industryBaseLaw", params=params)
        response.raise_for_status()
        payload = response.json()
        return self._extract_items(payload)

    def _get_service_key(self) -> str:
        service_key = (
            settings.g2b_api_service_key_decoded or settings.g2b_api_service_key_encoded
        )
        if not service_key:
            raise ValueError("G2B API service key is not configured")
        return service_key

    def _extract_items(self, payload: Mapping[str, Any]) -> list[dict[str, Any]]:
        body = payload.get("response", {}).get("body", {})
        items = body.get("items", [])
        if isinstance(items, Mapping):
            if "item" in items:
                return self._coerce_item_list(items["item"])
            return [dict(items)]
        return self._coerce_item_list(items)

    def _coerce_item_list(self, value: Any) -> list[dict[str, Any]]:
        if value in (None, ""):
            return []
        if isinstance(value, list):
            return [dict(item) for item in value if isinstance(item, Mapping)]
        if isinstance(value, Mapping):
            return [dict(value)]
        return []
