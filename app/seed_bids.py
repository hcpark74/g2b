import argparse
import json
import logging
from datetime import datetime

from sqlmodel import Session, select

from app.db import engine, init_db
from app.models.bid import Bid
from app.models.bid_license_limit import BidLicenseLimit
from app.models.bid_participation_region import BidParticipationRegion
from app.models.bid_reference_info import BidReferenceInfo
from app.models.common import (
    BID_STATUS_COLLECTED,
    BID_STATUS_LABELS,
    normalize_bid_seq,
)
from app.sample_data import get_sample_bids


def _parse_datetime(value: object) -> datetime | None:
    if not value or not isinstance(value, str) or value == "없음":
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _parse_amount(value: object) -> int | None:
    if not value or not isinstance(value, str):
        return None
    digits = value.replace(",", "").strip()
    return int(digits) if digits.isdigit() else None


def seed_bids() -> int:
    init_db()
    raw_bids = get_sample_bids()

    with Session(engine) as session:
        count = 0
        for item in raw_bids:
            bid_id = str(item["bid_id"])
            bid = session.get(Bid, bid_id)
            if bid is None:
                bid = Bid(
                    bid_id=bid_id,
                    bid_no=str(item["bid_no"]),
                    bid_seq=normalize_bid_seq(item.get("bid_seq")),
                    title=str(item["title"]),
                )

            bid.demand_org = str(item.get("demand_org") or "") or None
            bid.notice_org = str(item.get("notice_org") or "") or None
            bid.category = str(item.get("business_type") or "") or None
            bid.status = _map_status(str(item.get("status") or ""))
            bid.posted_at = _parse_datetime(item.get("posted_at"))
            bid.closed_at = _parse_datetime(item.get("closed_at"))
            bid.budget_amount = _parse_amount(item.get("budget_amount"))
            bid.is_favorite = bool(item.get("favorite", False))
            bid.last_synced_at = _parse_datetime(item.get("posted_at"))

            session.add(bid)

            qualification = item.get("qualification")
            if isinstance(qualification, dict):
                existing_license_limits = session.exec(
                    select(BidLicenseLimit).where(BidLicenseLimit.bid_id == bid_id)
                ).all()
                for row in existing_license_limits:
                    session.delete(row)

                existing_regions = session.exec(
                    select(BidParticipationRegion).where(
                        BidParticipationRegion.bid_id == bid_id
                    )
                ).all()
                for row in existing_regions:
                    session.delete(row)

                existing_references = session.exec(
                    select(BidReferenceInfo).where(BidReferenceInfo.bid_id == bid_id)
                ).all()
                for row in existing_references:
                    session.delete(row)

                for license_name in qualification.get("license_limits", []):
                    session.add(
                        BidLicenseLimit(
                            bid_id=bid_id,
                            license_name=str(license_name),
                            source_api_name="seed",
                        )
                    )

                for region_name in qualification.get("regions", []):
                    session.add(
                        BidParticipationRegion(
                            bid_id=bid_id,
                            region_name=str(region_name),
                            source_api_name="seed",
                        )
                    )

                for reference in qualification.get("reference_infos", []):
                    if not isinstance(reference, dict):
                        continue
                    session.add(
                        BidReferenceInfo(
                            bid_id=bid_id,
                            reference_key=str(
                                reference.get("code")
                                or reference.get("law_name")
                                or reference.get("name")
                                or ""
                            ),
                            reference_name=str(reference.get("name") or ""),
                            source_api_name=str(
                                reference.get("source_api_name") or "seed"
                            ),
                            raw_data=json.dumps(
                                {
                                    "indstrytyCd": str(reference.get("code") or ""),
                                    "lawNm": str(reference.get("law_name") or ""),
                                },
                                ensure_ascii=False,
                                sort_keys=True,
                            ),
                        )
                    )

            count += 1

        session.commit()
        return count


def _map_status(status: str) -> str:
    mapping = {label: code for code, label in BID_STATUS_LABELS.items()}
    return mapping.get(status, BID_STATUS_COLLECTED)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed sample bids into the configured database."
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress SQLAlchemy engine logs during seeding.",
    )
    args = parser.parse_args()

    if args.quiet:
        logging.disable(logging.INFO)

    inserted = seed_bids()
    print(f"seeded bids: {inserted}")
