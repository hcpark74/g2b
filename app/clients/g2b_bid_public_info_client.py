from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from app.config import settings


class G2BBidPublicInfoClient:
    def __init__(self, http_client: httpx.Client | None = None) -> None:
        self._owns_client = http_client is None
        self.http_client = http_client or httpx.Client(
            base_url=settings.g2b_api_bid_public_info_base_url,
            timeout=30.0,
        )

    def close(self) -> None:
        if self._owns_client:
            self.http_client.close()

    def fetch_bid_list(
        self,
        operation_name: str,
        *,
        inqry_div: int = 1,
        page_no: int = 1,
        num_of_rows: int = 100,
        inqry_bgn_dt: str | None = None,
        inqry_end_dt: str | None = None,
        bid_ntce_no: str | None = None,
    ) -> list[dict[str, Any]]:
        params = {
            "serviceKey": self._get_service_key(),
            "pageNo": page_no,
            "numOfRows": num_of_rows,
            "type": "json",
            "inqryDiv": str(inqry_div),
        }

        if inqry_div in {1, 3}:
            if not inqry_bgn_dt or not inqry_end_dt:
                raise ValueError(
                    "inqry_bgn_dt and inqry_end_dt are required when inqry_div is 1 or 3"
                )
            params["inqryBgnDt"] = inqry_bgn_dt
            params["inqryEndDt"] = inqry_end_dt

        if inqry_div == 2:
            if not bid_ntce_no:
                raise ValueError("bid_ntce_no is required when inqry_div is 2")
            params["bidNtceNo"] = bid_ntce_no

        response = self.http_client.get(operation_name, params=params)
        response.raise_for_status()
        payload = response.json()
        return self._extract_items(payload)

    def fetch_bid_detail_list(
        self,
        operation_name: str,
        *,
        bid_ntce_no: str,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> list[dict[str, Any]]:
        return self.fetch_bid_list(
            operation_name,
            inqry_div=2,
            bid_ntce_no=bid_ntce_no,
            page_no=page_no,
            num_of_rows=num_of_rows,
        )

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
