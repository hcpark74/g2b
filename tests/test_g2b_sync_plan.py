from app.services.g2b_sync_plan import (
    PHASE2_BASE_LIST_OPERATIONS,
    PHASE2_DETAIL_ENRICHMENT_OPERATIONS,
    PHASE2_SYNC_SEQUENCE,
    extract_connection_keys,
    should_run_detail_enrichment,
)


def test_phase2_operation_groups_expose_expected_defaults() -> None:
    assert PHASE2_BASE_LIST_OPERATIONS == (
        "getBidPblancListInfoServc",
        "getBidPblancListInfoThng",
        "getBidPblancListInfoCnstwk",
        "getBidPblancListInfoFrgcpt",
    )
    assert "getBidPblancListInfoLicenseLimit" in PHASE2_DETAIL_ENRICHMENT_OPERATIONS
    assert PHASE2_SYNC_SEQUENCE[0] == "base_list"


def test_extract_connection_keys_picks_known_fields() -> None:
    keys = extract_connection_keys(
        {
            "bidNtceNo": "R26BK00001234",
            "bfSpecRgstNo": "R26BD00010001",
            "orderPlanNo": "PLAN-1",
            "orderPlanUntyNo": "UNTY-2",
            "prcrmntReqNo": "REQ-3",
        }
    )

    assert keys.bid_ntce_no == "R26BK00001234"
    assert keys.bf_spec_rgst_no == "R26BD00010001"
    assert keys.order_plan_no == "PLAN-1"
    assert keys.order_plan_unty_no == "UNTY-2"
    assert keys.prcrmnt_req_no == "REQ-3"


def test_should_run_detail_enrichment_uses_selection_rules() -> None:
    assert should_run_detail_enrichment(
        status="collected",
        is_favorite=True,
        changed_recently=False,
        is_new_bid=False,
    )
    assert should_run_detail_enrichment(
        status="reviewing",
        is_favorite=False,
        changed_recently=False,
        is_new_bid=False,
    )
    assert not should_run_detail_enrichment(
        status="collected",
        is_favorite=False,
        changed_recently=False,
        is_new_bid=False,
    )
