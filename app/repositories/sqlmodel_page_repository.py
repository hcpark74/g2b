import json
from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from app.models import (
    Bid,
    BidDetail,
    ContractProcessIntegration,
    get_bid_status_label,
    get_bid_status_variant,
)
from app.repositories.page_repository import PageRepository


class SqlModelPageRepository(PageRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_prespecs(
        self,
        *,
        q: str | None = None,
        stage: str | None = None,
        business_type: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict[str, str]]:
        bids = {bid.bid_id: bid for bid in self.session.exec(select(Bid)).all()}
        bid_details = {
            detail.bid_id: detail
            for detail in self.session.exec(select(BidDetail)).all()
        }
        integrations_by_bid_id: dict[str, list[ContractProcessIntegration]] = {}
        for integration in self.session.exec(select(ContractProcessIntegration)).all():
            integrations_by_bid_id.setdefault(integration.bid_id, []).append(
                integration
            )

        items: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for bid_id, bid in bids.items():
            detail = bid_details.get(bid_id)
            integrations = integrations_by_bid_id.get(bid_id, [])
            items.extend(self._build_prespec_rows(bid, detail, integrations, seen))

        items = self._filter_prespec_items(
            items,
            q=q,
            stage=stage,
            business_type=business_type,
            date_from=date_from,
            date_to=date_to,
        )
        return sorted(items, key=lambda item: (item["date"], item["key"]), reverse=True)

    def list_results(self) -> list[dict[str, str]]:
        bids = {bid.bid_id: bid for bid in self.session.exec(select(Bid)).all()}
        integrations = list(self.session.exec(select(ContractProcessIntegration)).all())

        items: list[dict[str, str]] = []
        for integration in integrations:
            bid = bids.get(integration.bid_id)
            if bid is None:
                continue
            award_amount = integration.award_amount or "-"
            contract_amount = integration.award_amount or "-"
            items.append(
                {
                    "bid_no": bid.bid_id,
                    "title": bid.title,
                    "business_type": bid.category or "미분류",
                    "status": get_bid_status_label(bid.status),
                    "status_variant": get_bid_status_variant(bid.status),
                    "version_label": self._version_label(bid),
                    "version_variant": self._version_variant(bid),
                    "winner": integration.award_company or "-",
                    "award_amount": award_amount,
                    "award_rate": "-",
                    "contract_amount": contract_amount,
                    "contract_date": integration.contract_date or "-",
                    "contract_name": integration.contract_name or "-",
                    "notice_org": bid.notice_org or "-",
                    "demand_org": bid.demand_org or "-",
                }
            )

        return items

    def _version_label(self, bid: Bid) -> str:
        version_type = (bid.notice_version_type or "").strip().lower()
        if version_type == "cancellation" or bid.status == "archived":
            return "취소공고"
        if version_type == "revision":
            return "정정공고"
        if version_type == "rebid":
            return "재공고"
        return "최초공고"

    def _version_variant(self, bid: Bid) -> str:
        label = self._version_label(bid)
        if label == "취소공고":
            return "dark"
        if label == "정정공고":
            return "primary"
        if label == "재공고":
            return "success"
        return "secondary"

    def _build_prespec_rows(
        self,
        bid: Bid,
        detail: BidDetail | None,
        integrations: list[ContractProcessIntegration],
        seen: set[tuple[str, str]],
    ) -> list[dict[str, str]]:
        detail_payload = self._load_json_dict(detail.raw_api_data if detail else None)
        integration_payloads = [
            self._load_json_dict(integration.raw_data) for integration in integrations
        ]
        rows: list[dict[str, str]] = []

        specs = [
            (
                "발주계획",
                "orderPlanNo",
                ("orderBizNm",),
                ("orderInsttNm",),
                ("orderInsttNm",),
                ("orderPlanDt", "orderPlanYmd", "orderYm"),
            ),
            (
                "사전규격",
                "bfSpecRgstNo",
                ("bfSpecBizNm",),
                ("bfSpecNtceInsttNm",),
                ("bfSpecDminsttNm",),
                ("bfSpecNtceDt", "opninRgstClseDt"),
            ),
            (
                "조달요청",
                "prcrmntReqNo",
                ("prcrmntReqNm", "bidNtceNm"),
                ("prcrmntReqInsttNm", "orderInsttNm"),
                ("dminsttNm", "bidDminsttNm"),
                ("prcrmntReqDt", "prcrmntReqYmd"),
            ),
        ]

        for stage, key_name, title_keys, org_keys, demand_org_keys, date_keys in specs:
            key_value = self._first_text(detail_payload, key_name)
            if not key_value:
                continue
            dedupe_key = (stage, key_value)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            title = (
                self._first_payload_text(integration_payloads, *title_keys) or bid.title
            )
            org = (
                self._first_payload_text(integration_payloads, *org_keys)
                or bid.notice_org
                or "-"
            )
            demand_org = (
                self._first_payload_text(integration_payloads, *demand_org_keys)
                or bid.demand_org
                or "-"
            )
            date = self._first_payload_text(
                integration_payloads, *date_keys
            ) or self._format_datetime(bid.posted_at)

            rows.append(
                {
                    "stage": stage,
                    "business_type": bid.category or "미분류",
                    "title": title,
                    "key": key_value,
                    "org": org,
                    "demand_org": demand_org,
                    "date": date,
                    "linked_bid": "연결됨",
                    "linked_bid_variant": "success",
                    "linked_bid_id": bid.bid_id,
                }
            )

        return rows

    def _load_json_dict(self, raw_value: str | None) -> dict[str, Any]:
        if not raw_value:
            return {}
        try:
            payload = json.loads(raw_value)
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _first_payload_text(self, payloads: list[dict[str, Any]], *keys: str) -> str:
        for payload in payloads:
            value = self._first_text(payload, *keys)
            if value:
                return value
        return ""

    def _first_text(self, payload: dict[str, Any], *keys: str) -> str:
        for key in keys:
            value = payload.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return ""

    def _format_datetime(self, value: datetime | None) -> str:
        if value is None:
            return "-"
        return value.strftime("%Y-%m-%d %H:%M")

    def _filter_prespec_items(
        self,
        items: list[dict[str, str]],
        *,
        q: str | None,
        stage: str | None,
        business_type: str | None,
        date_from: str | None,
        date_to: str | None,
    ) -> list[dict[str, str]]:
        filtered = items
        if q:
            query = q.strip().lower()
            filtered = [
                item
                for item in filtered
                if query in item["title"].lower()
                or query in item["org"].lower()
                or query in item["demand_org"].lower()
            ]
        if stage:
            filtered = [item for item in filtered if item["stage"] == stage]
        if business_type:
            filtered = [
                item for item in filtered if item["business_type"] == business_type
            ]
        if date_from:
            filtered = [item for item in filtered if item["date"][:10] >= date_from]
        if date_to:
            filtered = [item for item in filtered if item["date"][:10] <= date_to]
        return filtered
