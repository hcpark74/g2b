from app.services import BidQueryService


def test_list_bids_returns_sample_bids() -> None:
    service = BidQueryService()

    bids = service.list_bids()

    assert len(bids) >= 3
    assert bids[0]["bid_id"] == "R26BK00000002-000"


def test_get_bid_returns_matching_bid() -> None:
    service = BidQueryService()

    bid = service.get_bid("R26BK00000003-000")

    assert bid["business_type"] == "공사"
    assert bid["notice_type"] == "재공고"


def test_list_bids_filters_by_search_query() -> None:
    service = BidQueryService()

    bids = service.list_bids(search_query="구급소모품")

    assert len(bids) == 1
    assert bids[0]["bid_id"] == "R26BK00000002-000"


def test_list_bids_filters_favorites_only() -> None:
    service = BidQueryService()

    bids = service.list_bids(favorites_only=True)

    assert len(bids) == 2
    assert all(bid["favorite"] for bid in bids)
