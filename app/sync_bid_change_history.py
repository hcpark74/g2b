import argparse
from datetime import datetime

from sqlmodel import Session

from app.clients import G2BBidPublicInfoClient
from app.db import engine, init_db
from app.models import SyncJobLog
from app.services.g2b_bid_change_history_service import G2BBidChangeHistoryService
from app.services.sync_logging import build_sync_failure_message


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync bid change history from G2B bid public info service."
    )
    parser.add_argument("--rows", type=int, default=100, help="Rows per API call.")
    parser.add_argument(
        "--bid-id",
        action="append",
        dest="bid_ids",
        help="Specific bid_id to sync. Can be passed multiple times.",
    )
    args = parser.parse_args()

    init_db()
    started_at = datetime.now()
    client = G2BBidPublicInfoClient()
    selected_bid_ids = list(args.bid_ids or [])

    try:
        with Session(engine) as session:
            service = G2BBidChangeHistoryService(session=session, client=client)
            result = service.sync_change_history(
                bid_ids=selected_bid_ids or None,
                num_of_rows=args.rows,
            )
            session.add(
                SyncJobLog(
                    job_type="bid_change_history_sync",
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
                    job_type="bid_change_history_sync",
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
    print(f"fetched change history items: {result.fetched_item_count}")


if __name__ == "__main__":
    main()
