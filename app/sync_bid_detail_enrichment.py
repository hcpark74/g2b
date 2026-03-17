import argparse
from datetime import datetime

from sqlmodel import Session

from app.clients import G2BBidPublicInfoClient
from app.db import engine, init_db
from app.services.operations_runtime import log_sync_job
from app.services.g2b_bid_detail_enrichment_service import G2BBidDetailEnrichmentService
from app.services.g2b_sync_plan import PHASE2_DETAIL_ENRICHMENT_OPERATIONS
from app.services.sync_logging import build_sync_failure_message


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enrich bid details from G2B detail operations."
    )
    parser.add_argument("--rows", type=int, default=100, help="Rows per API call.")
    parser.add_argument(
        "--operation",
        action="append",
        dest="operations",
        help="Specific detail enrichment operation. Can be passed multiple times.",
    )
    parser.add_argument(
        "--bid-id",
        action="append",
        dest="bid_ids",
        help="Specific bid_id to enrich. Can be passed multiple times.",
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
    args = parser.parse_args()

    init_db()
    started_at = datetime.now()
    client = G2BBidPublicInfoClient()
    selected_operations = (
        tuple(args.operations)
        if args.operations
        else PHASE2_DETAIL_ENRICHMENT_OPERATIONS
    )
    selected_bid_ids = list(args.bid_ids or [])

    try:
        with Session(engine) as session:
            service = G2BBidDetailEnrichmentService(session=session, client=client)
            result = service.enrich_bids(
                bid_ids=selected_bid_ids or None,
                operations=selected_operations,
                num_of_rows=args.rows,
                selection_mode=args.selection_mode,
                recent_days=args.recent_days,
            )
            log_sync_job(
                session=session,
                job_type="bid_detail_enrichment",
                target=",".join(selected_bid_ids) if selected_bid_ids else "all-bids",
                status="completed",
                started_at=started_at,
                message=(
                    f"operations={','.join(selected_operations)} "
                    f"selection_mode={args.selection_mode} "
                    f"processed {len(result.processed_bid_ids)} bids, "
                    f"fetched {result.fetched_item_count} items"
                ),
            )
    except Exception as exc:
        with Session(engine) as session:
            log_sync_job(
                session=session,
                job_type="bid_detail_enrichment",
                target=",".join(selected_bid_ids) if selected_bid_ids else "all-bids",
                status="failed",
                started_at=started_at,
                message=(
                    f"operations={','.join(selected_operations)} "
                    f"selection_mode={args.selection_mode} "
                    f"{build_sync_failure_message(exc)}"
                ),
            )
        raise
    finally:
        client.close()

    print(f"processed bids: {len(result.processed_bid_ids)}")
    print(f"fetched detail items: {result.fetched_item_count}")


if __name__ == "__main__":
    main()
