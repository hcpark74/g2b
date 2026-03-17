import argparse
from datetime import datetime

from sqlmodel import Session

from app.clients import (
    G2BBidPublicInfoClient,
    G2BContractProcessClient,
    G2BIndustryInfoClient,
)
from app.db import engine, init_db
from app.services import (
    G2BBidCrawlService,
    G2BBidChangeHistoryService,
    G2BBidDetailEnrichmentService,
    G2BReferenceEnrichmentService,
    G2BContractProcessService,
)
from app.services.operations_runtime import log_sync_job
from app.services.g2b_bid_page_crawler import G2BBidPageCrawler
from app.services.g2b_sync_plan import PHASE2_DETAIL_ENRICHMENT_OPERATIONS
from app.services.sync_logging import build_sync_failure_message


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Phase 2 detail enrichment, contract process sync, and crawl as one batch."
    )
    parser.add_argument("--rows", type=int, default=100, help="Rows per API call.")
    parser.add_argument(
        "--bid-id",
        action="append",
        dest="bid_ids",
        help="Specific bid_id to process. Can be passed multiple times.",
    )
    parser.add_argument(
        "--selection-mode",
        choices=("targeted", "all"),
        default="targeted",
        help="How to select bids when --bid-id is omitted.",
    )
    parser.add_argument(
        "--recent-days",
        type=int,
        default=7,
        help="Recent-change window used by targeted selection.",
    )
    parser.add_argument("--skip-detail", action="store_true")
    parser.add_argument("--skip-change-history", action="store_true")
    parser.add_argument("--skip-contract", action="store_true")
    parser.add_argument("--skip-crawl", action="store_true")
    parser.add_argument("--skip-reference", action="store_true")
    args = parser.parse_args()

    init_db()
    started_at = datetime.now()
    selected_bid_ids = list(args.bid_ids or [])

    detail_client = G2BBidPublicInfoClient()
    contract_client = G2BContractProcessClient()
    industry_client = G2BIndustryInfoClient()
    crawler = G2BBidPageCrawler()

    try:
        with Session(engine) as session:
            processed_bid_ids = list(selected_bid_ids)
            detail_processed = 0
            detail_items = 0
            change_history_items = 0
            contract_items = 0
            crawl_attachments = 0
            reference_items = 0

            if not args.skip_detail:
                detail_result = G2BBidDetailEnrichmentService(
                    session=session,
                    client=detail_client,
                ).enrich_bids(
                    bid_ids=selected_bid_ids or None,
                    operations=PHASE2_DETAIL_ENRICHMENT_OPERATIONS,
                    num_of_rows=args.rows,
                    selection_mode=args.selection_mode,
                    recent_days=args.recent_days,
                )
                processed_bid_ids = detail_result.processed_bid_ids
                detail_processed = len(detail_result.processed_bid_ids)
                detail_items = detail_result.fetched_item_count

            if args.skip_detail and not processed_bid_ids:
                raise ValueError(
                    "--skip-detail 사용 시에는 최소 하나 이상의 --bid-id가 필요합니다"
                )

            if not args.skip_change_history:
                change_history_result = G2BBidChangeHistoryService(
                    session=session,
                    client=detail_client,
                ).sync_change_history(
                    bid_ids=processed_bid_ids or None,
                    num_of_rows=args.rows,
                )
                change_history_items = change_history_result.fetched_item_count

            if not args.skip_contract:
                contract_result = G2BContractProcessService(
                    session=session,
                    client=contract_client,
                ).enrich_timelines(
                    bid_ids=processed_bid_ids or None,
                    num_of_rows=args.rows,
                )
                contract_items = contract_result.fetched_item_count

            if not args.skip_crawl:
                crawl_result = G2BBidCrawlService(
                    session=session,
                    crawler=crawler,
                ).crawl_bids(bid_ids=processed_bid_ids)
                crawl_attachments = crawl_result.attachment_count

            if not args.skip_reference:
                reference_result = G2BReferenceEnrichmentService(
                    session=session,
                    client=industry_client,
                ).enrich_bids(
                    bid_ids=processed_bid_ids,
                    num_of_rows=args.rows,
                )
                reference_items = reference_result.fetched_item_count

            log_sync_job(
                session=session,
                job_type="phase2_batch_sync",
                target=",".join(processed_bid_ids) if processed_bid_ids else "all-bids",
                status="completed",
                started_at=started_at,
                message=(
                    f"selection_mode={args.selection_mode} "
                    f"processed {len(processed_bid_ids)} bids "
                    f"detail_items={detail_items} "
                    f"change_history_items={change_history_items} "
                    f"contract_items={contract_items} "
                    f"crawl_attachments={crawl_attachments} "
                    f"reference_items={reference_items}"
                ),
            )
    except Exception as exc:
        with Session(engine) as session:
            log_sync_job(
                session=session,
                job_type="phase2_batch_sync",
                target=",".join(selected_bid_ids) if selected_bid_ids else "all-bids",
                status="failed",
                started_at=started_at,
                message=(
                    f"selection_mode={args.selection_mode} "
                    f"{build_sync_failure_message(exc)}"
                ),
            )
        raise
    finally:
        detail_client.close()
        contract_client.close()
        industry_client.close()

    print(f"processed bids: {len(processed_bid_ids)}")
    print(f"detail items: {detail_items}")
    print(f"change history items: {change_history_items}")
    print(f"contract items: {contract_items}")
    print(f"crawl attachments: {crawl_attachments}")
    print(f"reference items: {reference_items}")


if __name__ == "__main__":
    main()
