from datetime import datetime, timezone
from typing import Any

from sqlmodel import Field, SQLModel


DEFAULT_BID_SEQUENCE = "000"
BID_STATUS_COLLECTED = "collected"
BID_STATUS_REVIEWING = "reviewing"
BID_STATUS_FAVORITE = "favorite"
BID_STATUS_SUBMITTED = "submitted"
BID_STATUS_WON = "won"
BID_STATUS_ARCHIVED = "archived"

ALLOWED_BID_STATUSES = {
    BID_STATUS_COLLECTED,
    BID_STATUS_REVIEWING,
    BID_STATUS_FAVORITE,
    BID_STATUS_SUBMITTED,
    BID_STATUS_WON,
    BID_STATUS_ARCHIVED,
}

BID_STATUS_LABELS = {
    BID_STATUS_COLLECTED: "수집완료",
    BID_STATUS_REVIEWING: "검토중",
    BID_STATUS_FAVORITE: "관심",
    BID_STATUS_SUBMITTED: "투찰완료",
    BID_STATUS_WON: "낙찰",
    BID_STATUS_ARCHIVED: "보관",
}

BID_STATUS_VARIANTS = {
    BID_STATUS_COLLECTED: "secondary",
    BID_STATUS_REVIEWING: "primary",
    BID_STATUS_FAVORITE: "warning",
    BID_STATUS_SUBMITTED: "success",
    BID_STATUS_WON: "success",
    BID_STATUS_ARCHIVED: "dark",
}

BID_STATUS_OPTIONS = [
    (code, BID_STATUS_LABELS[code])
    for code in (
        BID_STATUS_COLLECTED,
        BID_STATUS_REVIEWING,
        BID_STATUS_FAVORITE,
        BID_STATUS_SUBMITTED,
        BID_STATUS_WON,
        BID_STATUS_ARCHIVED,
    )
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_bid_seq(value: Any) -> str:
    if value is None:
        return DEFAULT_BID_SEQUENCE
    digits = str(value).strip()
    if not digits:
        return DEFAULT_BID_SEQUENCE
    return digits.zfill(3)


def build_bid_id(bid_no: Any, bid_seq: Any) -> str | None:
    bid_no_text = optional_str(bid_no)
    if bid_no_text is None:
        return None
    return f"{bid_no_text}-{normalize_bid_seq(bid_seq)}"


def optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def get_bid_status_label(status: str | None) -> str:
    normalized = optional_str(status)
    if normalized is None:
        return BID_STATUS_LABELS[BID_STATUS_COLLECTED]
    return BID_STATUS_LABELS.get(normalized, normalized)


def get_bid_status_variant(status: str | None) -> str:
    normalized = optional_str(status)
    if normalized is None:
        return BID_STATUS_VARIANTS[BID_STATUS_COLLECTED]
    return BID_STATUS_VARIANTS.get(
        normalized, BID_STATUS_VARIANTS[BID_STATUS_COLLECTED]
    )


class TimestampedModel(SQLModel):
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
