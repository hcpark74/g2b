# pyright: reportArgumentType=false, reportAttributeAccessIssue=false, reportOptionalMemberAccess=false, reportOperatorIssue=false

from datetime import datetime
import json
from typing import Any, cast

from sqlalchemy import or_
from sqlmodel import Session, select

from app.models import get_bid_status_label, get_bid_status_variant
from app.models.attachment import Attachment
from app.models.bid import Bid
from app.models.bid_detail import BidDetail
from app.models.bid_license_limit import BidLicenseLimit
from app.models.bid_participation_region import BidParticipationRegion
from app.models.bid_purchase_item import BidPurchaseItem
from app.models.bid_reference_info import BidReferenceInfo
from app.models.bid_version_change import BidVersionChange
from app.models.contract_process_integration import ContractProcessIntegration
from app.models.timeline_stage_snapshot import TimelineStageSnapshot
from app.repositories.bid_repository import BidListPage, BidRepository


class SqlModelBidRepository(BidRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_bids(
        self,
        *,
        search_query: str | None = None,
        status: str | None = None,
        favorites_only: bool = False,
        include_versions: bool = False,
        keyword: str | None = None,
        org: str | None = None,
        budget_min: int | None = None,
        budget_max: int | None = None,
        closed_from: str | None = None,
        closed_to: str | None = None,
        sort: str = "posted_at",
        order: str = "desc",
    ) -> list[dict[str, Any]]:
        statement = self._list_statement(
            search_query=search_query,
            status=status,
            favorites_only=favorites_only,
            keyword=keyword,
            org=org,
            budget_min=budget_min,
            budget_max=budget_max,
            closed_from=closed_from,
            closed_to=closed_to,
            sort=sort,
            order=order,
        )
        bids = self._apply_version_selection(
            list(self.session.exec(statement).all()),
            search_query=search_query,
            include_versions=include_versions,
        )
        return [self._to_bid_payload(bid) for bid in bids]

    def list_bids_page(
        self,
        *,
        page: int,
        page_size: int,
        search_query: str | None = None,
        status: str | None = None,
        favorites_only: bool = False,
        include_versions: bool = False,
        keyword: str | None = None,
        org: str | None = None,
        budget_min: int | None = None,
        budget_max: int | None = None,
        closed_from: str | None = None,
        closed_to: str | None = None,
        sort: str = "posted_at",
        order: str = "desc",
    ) -> BidListPage:
        statement = self._list_statement(
            search_query=search_query,
            status=status,
            favorites_only=favorites_only,
            keyword=keyword,
            org=org,
            budget_min=budget_min,
            budget_max=budget_max,
            closed_from=closed_from,
            closed_to=closed_to,
            sort=sort,
            order=order,
        )
        all_bids = self._apply_version_selection(
            list(self.session.exec(statement).all()),
            search_query=search_query,
            include_versions=include_versions,
        )
        total = len(all_bids)
        start = (page - 1) * page_size
        end = start + page_size
        items = [self._to_bid_payload(bid) for bid in all_bids[start:end]]
        return BidListPage(items=items, total=total)

    def get_bid(self, bid_id: str) -> dict[str, Any]:
        return self._to_bid_payload(self._get_bid_or_raise(bid_id))

    def update_bid_status(self, bid_id: str, status: str) -> dict[str, Any]:
        bid = self._get_bid_or_raise(bid_id)
        bid.status = status
        self.session.add(bid)
        self.session.commit()
        self.session.refresh(bid)
        return self._to_bid_payload(bid)

    def set_bid_favorite(self, bid_id: str, favorite: bool) -> dict[str, Any]:
        bid = self._get_bid_or_raise(bid_id)
        bid.is_favorite = favorite
        self.session.add(bid)
        self.session.commit()
        self.session.refresh(bid)
        return self._to_bid_payload(bid)

    def _list_statement(
        self,
        *,
        search_query: str | None = None,
        status: str | None = None,
        favorites_only: bool = False,
        keyword: str | None = None,
        org: str | None = None,
        budget_min: int | None = None,
        budget_max: int | None = None,
        closed_from: str | None = None,
        closed_to: str | None = None,
        sort: str = "posted_at",
        order: str = "desc",
    ):
        statement = select(Bid)
        bid_id_col = cast(Any, getattr(Bid, "bid_id"))
        bid_no_col = cast(Any, getattr(Bid, "bid_no"))
        title_col = cast(Any, getattr(Bid, "title"))
        notice_org_col = cast(Any, getattr(Bid, "notice_org"))
        demand_org_col = cast(Any, getattr(Bid, "demand_org"))
        status_col = cast(Any, getattr(Bid, "status"))
        favorite_col = cast(Any, getattr(Bid, "is_favorite"))
        budget_amount_col = cast(Any, getattr(Bid, "budget_amount"))
        closed_at_col = cast(Any, getattr(Bid, "closed_at"))
        posted_at_col = cast(Any, getattr(Bid, "posted_at"))
        category_col = cast(Any, getattr(Bid, "category"))
        normalized_query = (search_query or "").strip().lower()
        normalized_status = (status or "").strip().lower()
        normalized_keyword = (keyword or "").strip().lower()
        normalized_org = (org or "").strip().lower()

        if normalized_query:
            pattern = f"%{normalized_query}%"
            statement = statement.where(
                or_(
                    bid_id_col.ilike(pattern),  # type: ignore[attr-defined]
                    bid_no_col.ilike(pattern),  # type: ignore[attr-defined]
                    title_col.ilike(pattern),  # type: ignore[attr-defined]
                    notice_org_col.ilike(pattern),  # type: ignore[attr-defined]
                    demand_org_col.ilike(pattern),  # type: ignore[attr-defined]
                )
            )

        if normalized_status:
            statement = statement.where(status_col == normalized_status)

        if favorites_only:
            statement = statement.where(favorite_col.is_(True))  # type: ignore[attr-defined]

        if normalized_keyword:
            pattern = f"%{normalized_keyword}%"
            detail_bid_ids = select(BidDetail.bid_id).where(
                BidDetail.description_text.ilike(pattern)  # type: ignore[attr-defined]
            )
            attachment_bid_ids = select(Attachment.bid_id).where(
                or_(
                    Attachment.name.ilike(pattern),  # type: ignore[attr-defined]
                    Attachment.download_url.ilike(pattern),  # type: ignore[attr-defined]
                )
            )
            license_bid_ids = select(BidLicenseLimit.bid_id).where(
                BidLicenseLimit.license_name.ilike(pattern)  # type: ignore[attr-defined]
            )
            region_bid_ids = select(BidParticipationRegion.bid_id).where(
                BidParticipationRegion.region_name.ilike(pattern)  # type: ignore[attr-defined]
            )
            purchase_bid_ids = select(BidPurchaseItem.bid_id).where(
                or_(
                    BidPurchaseItem.item_name.ilike(pattern),  # type: ignore[attr-defined]
                    BidPurchaseItem.item_code.ilike(pattern),  # type: ignore[attr-defined]
                    BidPurchaseItem.quantity.ilike(pattern),  # type: ignore[attr-defined]
                    BidPurchaseItem.delivery_condition.ilike(pattern),  # type: ignore[attr-defined]
                )
            )
            timeline_bid_ids = select(TimelineStageSnapshot.bid_id).where(
                or_(
                    TimelineStageSnapshot.stage.ilike(pattern),  # type: ignore[attr-defined]
                    TimelineStageSnapshot.status.ilike(pattern),  # type: ignore[attr-defined]
                    TimelineStageSnapshot.number.ilike(pattern),  # type: ignore[attr-defined]
                    TimelineStageSnapshot.occurred_at.ilike(pattern),  # type: ignore[attr-defined]
                    TimelineStageSnapshot.meta.ilike(pattern),  # type: ignore[attr-defined]
                )
            )
            contract_bid_ids = select(ContractProcessIntegration.bid_id).where(
                or_(
                    ContractProcessIntegration.source_key.ilike(pattern),  # type: ignore[attr-defined]
                    ContractProcessIntegration.award_company.ilike(pattern),  # type: ignore[attr-defined]
                    ContractProcessIntegration.award_amount.ilike(pattern),  # type: ignore[attr-defined]
                    ContractProcessIntegration.contract_no.ilike(pattern),  # type: ignore[attr-defined]
                    ContractProcessIntegration.contract_name.ilike(pattern),  # type: ignore[attr-defined]
                    ContractProcessIntegration.contract_date.ilike(pattern),  # type: ignore[attr-defined]
                    ContractProcessIntegration.raw_data.ilike(pattern),  # type: ignore[attr-defined]
                )
            )
            reference_bid_ids = select(BidReferenceInfo.bid_id).where(
                or_(
                    BidReferenceInfo.reference_name.ilike(pattern),  # type: ignore[attr-defined]
                    BidReferenceInfo.reference_key.ilike(pattern),  # type: ignore[attr-defined]
                    BidReferenceInfo.raw_data.ilike(pattern),  # type: ignore[attr-defined]
                )
            )
            statement = statement.where(
                or_(
                    title_col.ilike(pattern),  # type: ignore[attr-defined]
                    category_col.ilike(pattern),  # type: ignore[attr-defined]
                    bid_id_col.in_(detail_bid_ids),
                    bid_id_col.in_(attachment_bid_ids),
                    bid_id_col.in_(license_bid_ids),
                    bid_id_col.in_(region_bid_ids),
                    bid_id_col.in_(purchase_bid_ids),
                    bid_id_col.in_(timeline_bid_ids),
                    bid_id_col.in_(contract_bid_ids),
                    bid_id_col.in_(reference_bid_ids),
                )
            )

        if normalized_org:
            pattern = f"%{normalized_org}%"
            statement = statement.where(
                or_(
                    notice_org_col.ilike(pattern),  # type: ignore[attr-defined]
                    demand_org_col.ilike(pattern),  # type: ignore[attr-defined]
                )
            )

        if budget_min is not None:
            statement = statement.where(budget_amount_col >= budget_min)  # type: ignore[operator]

        if budget_max is not None:
            statement = statement.where(budget_amount_col <= budget_max)  # type: ignore[operator]

        closed_from_dt = self._parse_filter_datetime(closed_from)
        if closed_from_dt is not None:
            statement = statement.where(closed_at_col >= closed_from_dt)  # type: ignore[operator]

        closed_to_dt = self._parse_filter_datetime(closed_to)
        if closed_to_dt is not None:
            statement = statement.where(closed_at_col <= closed_to_dt)  # type: ignore[operator]

        sort_column = posted_at_col
        if sort == "closed_at":
            sort_column = closed_at_col
        elif sort == "budget_amount":
            sort_column = budget_amount_col

        if order == "asc":
            statement = statement.order_by(sort_column.asc(), bid_id_col.asc())  # type: ignore[attr-defined]
        else:
            statement = statement.order_by(sort_column.desc(), bid_id_col.desc())  # type: ignore[attr-defined]

        return statement

    def _apply_version_selection(
        self,
        bids: list[Bid],
        *,
        search_query: str | None = None,
        include_versions: bool = False,
    ) -> list[Bid]:
        if include_versions:
            return bids
        normalized_query = (search_query or "").strip().upper()
        if normalized_query and any(
            bid.bid_no.upper() == normalized_query for bid in bids
        ):
            return bids

        grouped: dict[str, list[Bid]] = {}
        ordered_bid_nos: list[str] = []
        for bid in bids:
            if bid.bid_no not in grouped:
                grouped[bid.bid_no] = []
                ordered_bid_nos.append(bid.bid_no)
            grouped[bid.bid_no].append(bid)

        selected: list[Bid] = []
        for bid_no in ordered_bid_nos:
            versions = grouped[bid_no]
            effective = next(
                (bid for bid in versions if not self._is_non_effective_version(bid)),
                None,
            )
            selected.append(effective or versions[0])
        return selected

    def _is_non_effective_version(self, bid: Bid) -> bool:
        return bid.status == "archived"

    def _is_latest_effective_version(self, bid: Bid, versions: list[Bid]) -> bool:
        effective = next(
            (item for item in versions if not self._is_non_effective_version(item)),
            None,
        )
        if effective is None:
            return versions[0].bid_id == bid.bid_id if versions else False
        return effective.bid_id == bid.bid_id

    def _version_label(self, bid: Bid, versions: list[Bid]) -> str:
        version_type = (bid.notice_version_type or "").strip().lower()
        if version_type == "cancellation":
            return "취소공고"
        if version_type == "rebid":
            return "재공고"
        if version_type == "revision":
            return "정정공고"
        if version_type == "original":
            return "최초공고"
        if self._is_non_effective_version(bid):
            return "취소공고"
        if len(versions) == 1:
            return "최초공고"
        if bid.bid_seq == min((item.bid_seq for item in versions), default=bid.bid_seq):
            return "최초공고"
        return "정정공고"

    def _version_variant(self, bid: Bid, versions: list[Bid]) -> str:
        label = self._version_label(bid, versions)
        if label == "취소공고":
            return "danger"
        if self._is_latest_effective_version(bid, versions):
            return "success"
        if label == "재공고":
            return "primary"
        if label == "정정공고":
            return "warning"
        return "secondary"

    def _version_summary(self, bid: Bid, versions: list[Bid]) -> str:
        label = self._version_label(bid, versions)
        if self._is_non_effective_version(bid):
            return "현재 보고 있는 공고는 취소공고입니다. 검토 시 최신 유효 차수를 함께 확인하세요."
        if label == "재공고":
            return "현재 보고 있는 공고는 재공고 차수입니다. 이전 유찰 이력과 재공고 사유를 함께 확인하세요."
        if self._is_latest_effective_version(bid, versions):
            return "현재 보고 있는 공고는 검토 기준이 되는 최신 유효 차수입니다."
        return "현재 보고 있는 공고는 이전 차수입니다. 최신 유효 차수와 변경 내용을 비교해 확인하세요."

    def _parse_filter_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None

    def _get_bid_or_raise(self, bid_id: str) -> Bid:
        bid = self.session.get(Bid, bid_id)
        if bid is None:
            raise KeyError(f"Bid not found: {bid_id}")
        return bid

    def _get_bid_detail(self, bid_id: str) -> BidDetail | None:
        return self.session.get(BidDetail, bid_id)

    def _list_attachments(self, bid_id: str) -> list[Attachment]:
        return list(
            self.session.exec(
                select(Attachment)
                .where(Attachment.bid_id == bid_id)
                .order_by(Attachment.attachment_id)
            ).all()
        )

    def _list_license_limits(self, bid_id: str) -> list[str]:
        return [
            item.license_name
            for item in self.session.exec(
                select(BidLicenseLimit).where(BidLicenseLimit.bid_id == bid_id)
            ).all()
        ]

    def _list_regions(self, bid_id: str) -> list[str]:
        return [
            item.region_name
            for item in self.session.exec(
                select(BidParticipationRegion).where(
                    BidParticipationRegion.bid_id == bid_id
                )
            ).all()
        ]

    def _list_purchase_items(self, bid_id: str) -> list[BidPurchaseItem]:
        return list(
            self.session.exec(
                select(BidPurchaseItem).where(BidPurchaseItem.bid_id == bid_id)
            ).all()
        )

    def _list_reference_infos(self, bid_id: str) -> list[BidReferenceInfo]:
        return list(
            self.session.exec(
                select(BidReferenceInfo)
                .where(BidReferenceInfo.bid_id == bid_id)
                .order_by(
                    BidReferenceInfo.reference_name, BidReferenceInfo.reference_key
                )
            ).all()
        )

    def _reference_info_payload(
        self, reference_infos: list[BidReferenceInfo]
    ) -> list[dict[str, str]]:
        items: list[dict[str, str]] = []
        for reference in reference_infos:
            raw_payload: dict[str, Any] = {}
            if reference.raw_data:
                try:
                    parsed = json.loads(reference.raw_data)
                    if isinstance(parsed, dict):
                        raw_payload = parsed
                except json.JSONDecodeError:
                    raw_payload = {}

            items.append(
                {
                    "name": reference.reference_name,
                    "code": str(
                        raw_payload.get("indstrytyCd")
                        or raw_payload.get("indstrytyNo")
                        or reference.reference_key
                    ),
                    "law_name": str(
                        raw_payload.get("lawNm")
                        or raw_payload.get("bsnsNm")
                        or reference.reference_key
                    ),
                    "source_api_name": reference.source_api_name or "-",
                }
            )
        return items

    def _list_timeline_snapshots(self, bid_id: str) -> list[TimelineStageSnapshot]:
        return list(
            self.session.exec(
                select(TimelineStageSnapshot).where(
                    TimelineStageSnapshot.bid_id == bid_id
                )
            ).all()
        )

    def _list_contract_integrations(
        self, bid_id: str
    ) -> list[ContractProcessIntegration]:
        return list(
            self.session.exec(
                select(ContractProcessIntegration).where(
                    ContractProcessIntegration.bid_id == bid_id
                )
            ).all()
        )

    def _list_bid_versions(self, bid_no: str) -> list[Bid]:
        return list(
            self.session.exec(
                select(Bid)
                .where(Bid.bid_no == bid_no)
                .order_by(cast(Any, getattr(Bid, "bid_seq")).desc())
            ).all()
        )

    def _list_bid_version_changes(self, bid_id: str) -> list[BidVersionChange]:
        return list(
            self.session.exec(
                select(BidVersionChange)
                .where(BidVersionChange.bid_id == bid_id)
                .order_by(
                    BidVersionChange.changed_at.desc(), BidVersionChange.change_id.asc()
                )
            ).all()
        )

    def _version_history_payload(
        self, bid: Bid, versions: list[Bid]
    ) -> list[dict[str, str | bool]]:
        latest_effective = next(
            (item for item in versions if not self._is_non_effective_version(item)),
            None,
        )
        return [
            {
                "bid_id": item.bid_id,
                "bid_seq": item.bid_seq,
                "title": item.title,
                "version_label": self._version_label(item, versions),
                "is_current": item.bid_id == bid.bid_id,
                "is_latest_effective": latest_effective is not None
                and latest_effective.bid_id == item.bid_id,
                "posted_at": self._format_datetime(item.posted_at),
            }
            for item in versions
        ]

    def _latest_effective_version(self, versions: list[Bid]) -> Bid | None:
        return next(
            (item for item in versions if not self._is_non_effective_version(item)),
            None,
        )

    def _to_bid_payload(self, bid: Bid) -> dict[str, Any]:
        bid_detail = self._get_bid_detail(bid.bid_id)
        crawl_payload = self._crawl_payload(bid_detail)
        attachments = self._list_attachments(bid.bid_id)
        license_limits = self._list_license_limits(bid.bid_id)
        regions = self._list_regions(bid.bid_id)
        purchase_items = self._list_purchase_items(bid.bid_id)
        reference_infos = self._list_reference_infos(bid.bid_id)
        timeline_snapshots = self._list_timeline_snapshots(bid.bid_id)
        contract_integrations = self._list_contract_integrations(bid.bid_id)
        version_changes = self._list_bid_version_changes(bid.bid_id)
        versions = self._list_bid_versions(bid.bid_no)
        status_label = self._status_label(bid.status)
        progress_label = self._progress_label(bid)
        business_type = bid.category or "미분류"
        version_label = self._version_label(bid, versions)
        version_variant = self._version_variant(bid, versions)
        version_summary = self._version_summary(bid, versions)
        latest_effective = self._latest_effective_version(versions)

        return {
            "bid_id": bid.bid_id,
            "bid_no": bid.bid_no,
            "display_bid_no": bid.bid_id,
            "bid_seq": bid.bid_seq,
            "title": bid.title,
            "notice_org": bid.notice_org or "-",
            "demand_org": bid.demand_org or "-",
            "status": status_label,
            "status_variant": self._status_variant(bid.status),
            "version_label": version_label,
            "version_variant": version_variant,
            "version_summary": version_summary,
            "is_latest_effective": self._is_latest_effective_version(bid, versions),
            "latest_effective_bid_id": (
                latest_effective.bid_id if latest_effective is not None else ""
            ),
            "latest_effective_title": (
                latest_effective.title if latest_effective is not None else ""
            ),
            "business_type": business_type,
            "domain_type": "내자",
            "notice_type": self._notice_type(bid),
            "budget_amount": self._format_amount(bid.budget_amount),
            "last_synced_at": self._format_datetime(bid.last_synced_at),
            "description_text": self._description_text(bid_detail, crawl_payload),
            "detail_url": self._detail_url(bid_detail),
            "crawl_excerpt": self._crawl_excerpt(crawl_payload),
            "posted_at": self._format_datetime(bid.posted_at),
            "closed_at": self._format_datetime(bid.closed_at),
            "opened_at": self._format_datetime(bid.last_changed_at),
            "stage_label": "입찰공고",
            "step_label": "공고등록",
            "progress_label": progress_label,
            "favorite": bid.is_favorite,
            "detail_rows": [
                {
                    "left_label": "공고종류",
                    "left_value": self._notice_type(bid),
                    "right_label": "게시일시",
                    "right_value": self._format_datetime(bid.posted_at),
                },
                {
                    "left_label": "입찰공고번호",
                    "left_value": bid.bid_id,
                    "right_label": "업무구분",
                    "right_value": business_type,
                },
                {
                    "left_label": "공고명",
                    "left_value": bid.title,
                    "right_label": "상태",
                    "right_value": status_label,
                },
                {
                    "left_label": "공고기관",
                    "left_value": bid.notice_org or "-",
                    "right_label": "수요기관",
                    "right_value": bid.demand_org or "-",
                },
                {
                    "left_label": "계약방법",
                    "left_value": self._contract_method_label(business_type),
                    "right_label": "마감일시",
                    "right_value": self._format_datetime(bid.closed_at),
                },
                {
                    "left_label": "추정가격",
                    "left_value": self._format_amount(bid.budget_amount),
                    "right_label": "최종 동기화",
                    "right_value": self._format_datetime(bid.last_synced_at),
                },
            ],
            "qualification": {
                "industry_limited": business_type in {"공사", "용역"},
                "international_bid": "국내입찰",
                "rebid_allowed": "허용",
                "bid_participation_limit": self._bid_participation_limit_label(
                    business_type
                ),
                "consortium_method": self._consortium_method_label(business_type),
                "license_limits": license_limits or self._license_limits(business_type),
                "permitted_industries": self._permitted_industries(business_type),
                "regions": regions or self._regions(business_type),
                "reference_infos": self._reference_info_payload(reference_infos),
                "qualification_summary": f"{business_type} 상세 자격 정보는 추후 세부 API 연동으로 보강 예정",
            },
            "business_info": self._business_info(business_type, purchase_items),
            "attachments": [
                {
                    "name": attachment.name,
                    "type": attachment.file_type or "일반",
                    "source": attachment.source or "DB 첨부",
                    "url": attachment.download_url or "#",
                }
                for attachment in attachments
            ],
            "timeline": self._timeline_payload(
                bid, timeline_snapshots, progress_label, version_changes
            ),
            "history": self._history_payload(
                bid, contract_integrations, version_changes
            ),
            "version_history": self._version_history_payload(bid, versions),
        }

    def _format_amount(self, amount: int | None) -> str:
        if amount is None:
            return "-"
        return f"{amount:,}"

    def _crawl_payload(self, bid_detail: BidDetail | None) -> dict[str, Any]:
        if bid_detail is None or not bid_detail.crawl_data:
            return {}
        try:
            payload = json.loads(bid_detail.crawl_data)
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _description_text(
        self, bid_detail: BidDetail | None, crawl_payload: dict[str, Any]
    ) -> str:
        crawled_summary = self._crawl_excerpt(crawl_payload)
        if crawled_summary:
            return crawled_summary
        if bid_detail is None:
            return "상세 본문은 추가 연동 예정"
        if bid_detail.description_text:
            return bid_detail.description_text
        return "상세 본문은 추가 연동 예정"

    def _crawl_excerpt(self, crawl_payload: dict[str, Any]) -> str:
        text_summary = crawl_payload.get("text_summary")
        if isinstance(text_summary, str) and text_summary.strip():
            return text_summary.strip()[:4000]
        return ""

    def _detail_url(self, bid_detail: BidDetail | None) -> str:
        if bid_detail is None:
            return ""
        return bid_detail.detail_url or ""

    def _format_datetime(self, value: Any) -> str:
        if value is None:
            return "-"
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M")
        return str(value)

    def _status_variant(self, status: str) -> str:
        return get_bid_status_variant(status)

    def _status_label(self, status: str) -> str:
        return get_bid_status_label(status)

    def _notice_type(self, bid: Bid) -> str:
        return "재공고" if bid.last_changed_at else "등록공고"

    def _progress_label(self, bid: Bid) -> str:
        if bid.closed_at is None:
            return "진행중"
        now = datetime.now()
        if bid.closed_at < now:
            return "마감"
        return "진행중"

    def _contract_method_label(self, business_type: str) -> str:
        mapping = {
            "용역": "제한경쟁",
            "물품": "총액계약",
            "공사": "제한경쟁",
        }
        return mapping.get(business_type, "미정")

    def _bid_participation_limit_label(self, business_type: str) -> str:
        mapping = {
            "용역": "실적 또는 사업자 등록 기준",
            "물품": "물품분류 또는 제조 등록 기준",
            "공사": "지역 및 면허 기준",
        }
        return mapping.get(business_type, "미정")

    def _consortium_method_label(self, business_type: str) -> str:
        mapping = {
            "용역": "공동수급불허",
            "물품": "공동수급가능",
            "공사": "(전자)공동이행 가능",
        }
        return mapping.get(business_type, "미정")

    def _license_limits(self, business_type: str) -> list[str]:
        mapping = {
            "용역": ["소프트웨어사업자(컴퓨터관련서비스사업)"],
            "공사": ["포장공사업", "토목공사업"],
        }
        return mapping.get(business_type, [])

    def _permitted_industries(self, business_type: str) -> list[str]:
        mapping = {
            "용역": ["데이터서비스"],
            "공사": ["도로유지보수공사"],
        }
        return mapping.get(business_type, [])

    def _regions(self, business_type: str) -> list[str]:
        if business_type == "공사":
            return ["전라남도"]
        return ["전국"]

    def _business_info(
        self, business_type: str, purchase_items: list[BidPurchaseItem]
    ) -> dict[str, str]:
        if business_type == "용역":
            if purchase_items:
                primary_item = purchase_items[0]
                return {
                    "service_division": "일반용역",
                    "public_procurement_cls": primary_item.item_name,
                    "tech_eval_rate": "80",
                    "price_eval_rate": "20",
                    "info_biz": "Y",
                }
            return {
                "service_division": "일반용역",
                "public_procurement_cls": "데이터서비스",
                "tech_eval_rate": "80",
                "price_eval_rate": "20",
                "info_biz": "Y",
            }
        if business_type == "물품":
            if purchase_items:
                primary_item = purchase_items[0]
                return {
                    "product_class_limited": "Y",
                    "manufacturing_required": "N",
                    "detail_product_no": primary_item.item_code or "미정",
                    "detail_product_name": primary_item.item_name,
                    "product_qty": primary_item.quantity or "미정",
                    "delivery_condition": primary_item.delivery_condition
                    or "수요기관 협의",
                }
            return {
                "product_class_limited": "Y",
                "manufacturing_required": "N",
                "detail_product_no": "미정",
                "detail_product_name": "추후 품목 API 연동",
                "product_qty": "미정",
                "delivery_condition": "수요기관 협의",
            }
        if business_type == "공사":
            if purchase_items:
                primary_item = purchase_items[0]
                return {
                    "main_construction_type": primary_item.item_name,
                    "construction_site_region": primary_item.delivery_condition
                    or "현장 정보 연동 예정",
                    "industry_eval_rate": "69.79",
                    "joint_contract_required": "N",
                    "construction_law_applied": "Y",
                    "market_entry_allowed": "N",
                }
            return {
                "main_construction_type": "포장공사업",
                "construction_site_region": "현장 정보 연동 예정",
                "industry_eval_rate": "69.79",
                "joint_contract_required": "N",
                "construction_law_applied": "Y",
                "market_entry_allowed": "N",
            }
        return {}

    def _timeline_payload(
        self,
        bid: Bid,
        timeline_snapshots: list[TimelineStageSnapshot],
        progress_label: str,
        version_changes: list[BidVersionChange],
    ) -> list[dict[str, str]]:
        version_events = self._version_timeline_events(bid, version_changes)
        if timeline_snapshots:
            return version_events + [
                {
                    "stage": item.stage,
                    "status": item.status,
                    "number": item.number or "없음",
                    "date": item.occurred_at or "-",
                    "meta": item.meta or "-",
                }
                for item in timeline_snapshots
            ]
        return version_events + [
            {
                "stage": "입찰공고",
                "status": "완료" if bid.posted_at else "미도달",
                "number": bid.bid_id,
                "date": self._format_datetime(bid.posted_at),
                "meta": f"마감 {self._format_datetime(bid.closed_at)}",
            },
            {
                "stage": "개찰/낙찰",
                "status": "미도달" if progress_label != "마감임박" else "확인 필요",
                "number": "없음",
                "date": self._format_datetime(bid.last_changed_at),
                "meta": "세부 결과 API 연동 예정",
            },
            {
                "stage": "계약",
                "status": "미도달",
                "number": "없음",
                "date": "-",
                "meta": "계약정보서비스 연동 예정",
            },
        ]

    def _version_timeline_events(
        self, bid: Bid, version_changes: list[BidVersionChange]
    ) -> list[dict[str, str]]:
        label = self._version_label(bid, self._list_bid_versions(bid.bid_no))
        if label == "최초공고":
            return []
        change_summary = self._version_change_summary(version_changes)
        return [
            {
                "stage": "공고 버전",
                "status": "확인 필요" if label == "취소공고" else "완료",
                "number": bid.bid_id,
                "date": self._format_datetime(bid.posted_at),
                "meta": (
                    f"{'취소 공고 게시' if label == '취소공고' else ('재공고 게시' if label == '재공고' else '정정 공고 게시')}"
                    + (f" · {change_summary}" if change_summary else "")
                ),
            }
        ]

    def _history_payload(
        self,
        bid: Bid,
        contract_integrations: list[ContractProcessIntegration],
        version_changes: list[BidVersionChange],
    ) -> list[dict[str, str]]:
        history: list[dict[str, str]] = self._version_history_events(bid)
        history.extend(self._version_change_history_items(version_changes))

        for integration in contract_integrations:
            changed_at = integration.collected_at or self._format_datetime(
                bid.last_synced_at
            )
            if integration.award_company:
                history.append(
                    {
                        "changed_at": changed_at,
                        "item": "낙찰업체",
                        "before": "-",
                        "after": integration.award_company,
                    }
                )
            if integration.award_amount:
                history.append(
                    {
                        "changed_at": changed_at,
                        "item": "낙찰금액",
                        "before": "-",
                        "after": integration.award_amount,
                    }
                )
            if integration.contract_no:
                history.append(
                    {
                        "changed_at": changed_at,
                        "item": "계약번호",
                        "before": "-",
                        "after": integration.contract_no,
                    }
                )
            if integration.contract_name:
                history.append(
                    {
                        "changed_at": changed_at,
                        "item": "계약명",
                        "before": "-",
                        "after": integration.contract_name,
                    }
                )
            if integration.contract_date:
                history.append(
                    {
                        "changed_at": changed_at,
                        "item": "계약일자",
                        "before": "-",
                        "after": integration.contract_date,
                    }
                )

        if history:
            return history

        if bid.last_synced_at:
            return [
                {
                    "changed_at": self._format_datetime(bid.last_synced_at),
                    "item": "최종 동기화",
                    "before": "-",
                    "after": self._format_datetime(bid.last_synced_at),
                }
            ]

        return []

    def _version_history_events(self, bid: Bid) -> list[dict[str, str]]:
        versions = self._list_bid_versions(bid.bid_no)
        label = self._version_label(bid, versions)
        if label == "최초공고":
            return []
        return [
            {
                "changed_at": self._format_datetime(bid.posted_at),
                "item": "공고 차수 상태",
                "before": "최초공고" if label in {"정정공고", "재공고"} else "정정공고",
                "after": label,
            }
        ]

    def _version_change_history_items(
        self, version_changes: list[BidVersionChange]
    ) -> list[dict[str, str]]:
        return [
            {
                "changed_at": self._format_datetime(change.changed_at),
                "item": change.change_item_name,
                "before": change.before_value or "-",
                "after": change.after_value or "-",
                "context": self._version_change_context(change),
            }
            for change in version_changes
        ]

    def _version_change_summary(self, version_changes: list[BidVersionChange]) -> str:
        if not version_changes:
            return ""
        names = []
        first = version_changes[0]
        if first.change_data_div_name:
            names.append(f"데이터구분 {first.change_data_div_name}")
        if first.rbid_no:
            names.append(f"재입찰번호 {first.rbid_no}")
        names.extend(
            change.change_item_name
            for change in version_changes[:3]
            if change.change_item_name
        )
        if not names:
            return ""
        return ", ".join(names)

    def _version_change_context(self, change: BidVersionChange) -> str:
        parts: list[str] = []
        if change.change_data_div_name:
            parts.append(f"데이터구분 {change.change_data_div_name}")
        if change.rbid_no:
            parts.append(f"재입찰번호 {change.rbid_no}")
        if change.license_limit_code_list_raw:
            parts.append(f"면허코드목록 {change.license_limit_code_list_raw}")
        return " / ".join(parts)
