from app.models import (
    build_bid_id,
    get_bid_status_label,
    get_bid_status_variant,
    normalize_bid_seq,
    optional_str,
)


def test_normalize_bid_seq_zero_pads_values() -> None:
    assert normalize_bid_seq("1") == "001"
    assert normalize_bid_seq(12) == "012"
    assert normalize_bid_seq("000") == "000"


def test_build_bid_id_returns_none_without_bid_number() -> None:
    assert build_bid_id(None, "1") is None
    assert build_bid_id("", "1") is None


def test_build_bid_id_combines_bid_number_and_sequence() -> None:
    assert build_bid_id("R26BK00000123", "1") == "R26BK00000123-001"


def test_optional_str_strips_empty_values() -> None:
    assert optional_str("  test  ") == "test"
    assert optional_str("   ") is None


def test_bid_status_helpers_return_shared_label_and_variant() -> None:
    assert get_bid_status_label("reviewing") == "검토중"
    assert get_bid_status_variant("reviewing") == "primary"
    assert get_bid_status_label(None) == "수집완료"
