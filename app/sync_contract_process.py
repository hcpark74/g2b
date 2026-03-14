import argparse
from datetime import datetime

from sqlmodel import Session

from app.clients import G2BContractProcessClient
from app.db import engine, init_db
from app.models import SyncJobLog
from app.services.g2b_contract_process_service import G2BContractProcessService
from app.services.sync_logging import build_sync_failure_message


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enrich bid timelines from G2B contract process integration service."
    )
    parser.add_argument("--rows", type=int, default=100, help="Rows per API call.")
    parser.add_argument(
        "--bid-id",
        action="append",
        dest="bid_ids",
        help="Specific bid_id to enrich. Can be passed multiple times.",
    )
    args = parser.parse_args()

    init_db()
    started_at = datetime.now()
    client = G2BContractProcessClient()
    selected_bid_ids = list(args.bid_ids or [])

    try:
        with Session(engine) as session:
            service = G2BContractProcessService(session=session, client=client)
            result = service.enrich_timelines(
                bid_ids=selected_bid_ids or None,
                num_of_rows=args.rows,
            )
            session.add(
                SyncJobLog(
                    job_type="contract_process_sync",
                    target=",".join(selected_bid_ids)
                    if selected_bid_ids
                    else "all-bids",
                    status="completed",
                    started_at=started_at,
                    finished_at=datetime.now(),
                    message=(
                        f"processed {len(result.processed_bid_ids)} bids, "
                        f"fetched {result.fetched_item_count} items"
                    ),
                )
            )
            session.commit()
    except Exception as exc:
        with Session(engine) as session:
            session.add(
                SyncJobLog(
                    job_type="contract_process_sync",
                    target=",".join(selected_bid_ids)
                    if selected_bid_ids
                    else "all-bids",
                    status="failed",
                    started_at=started_at,
                    finished_at=datetime.now(),
                    message=build_sync_failure_message(exc),
                )
            )
            session.commit()
        raise
    finally:
        client.close()

    print(f"processed bids: {len(result.processed_bid_ids)}")
    print(f"fetched contract items: {result.fetched_item_count}")


if __name__ == "__main__":
    main()
