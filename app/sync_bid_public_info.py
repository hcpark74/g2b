import argparse
from datetime import datetime, timedelta

from sqlmodel import Session

from app.clients import G2BBidPublicInfoClient
from app.db import engine, init_db
from app.models import SyncJobLog
from app.services.g2b_bid_sync_service import (
    DEFAULT_BID_PUBLIC_INFO_OPERATIONS,
    BidPublicInfoSyncOperationError,
    G2BBidPublicInfoSyncService,
)
from app.services.sync_logging import build_sync_failure_message


def _default_begin_end() -> tuple[str, str]:
    end_at = datetime.now()
    begin_at = end_at - timedelta(days=1)
    return begin_at.strftime("%Y%m%d0000"), end_at.strftime("%Y%m%d%H%M")


def main() -> None:
    default_begin, default_end = _default_begin_end()
    parser = argparse.ArgumentParser(
        description="Sync bid public info notices from G2B API."
    )
    parser.add_argument(
        "--begin", default=default_begin, help="Start date/time in YYYYMMDDHHMM format."
    )
    parser.add_argument(
        "--end", default=default_end, help="End date/time in YYYYMMDDHHMM format."
    )
    parser.add_argument("--rows", type=int, default=100, help="Rows per API call.")
    parser.add_argument(
        "--operation",
        action="append",
        dest="operations",
        help="Specific operation to sync. Can be passed multiple times.",
    )
    args = parser.parse_args()

    init_db()
    started_at = datetime.now()
    client = G2BBidPublicInfoClient()
    selected_operations = (
        tuple(args.operations)
        if args.operations
        else DEFAULT_BID_PUBLIC_INFO_OPERATIONS
    )
    try:
        with Session(engine) as session:
            service = G2BBidPublicInfoSyncService(session=session, client=client)
            result = service.sync_bid_notices(
                inqry_bgn_dt=args.begin,
                inqry_end_dt=args.end,
                operations=selected_operations,
                num_of_rows=args.rows,
            )
            session.add(
                SyncJobLog(
                    job_type="bid_public_info_sync",
                    target=",".join(selected_operations),
                    status="completed",
                    started_at=started_at,
                    finished_at=datetime.now(),
                    message=f"fetched {result.fetched_count} bids, upserted {result.upserted_count} bids",
                )
            )
            session.commit()
    except Exception as exc:
        target = ",".join(selected_operations)
        message = build_sync_failure_message(exc)
        if isinstance(exc, BidPublicInfoSyncOperationError):
            target = exc.operation_name

        with Session(engine) as session:
            session.add(
                SyncJobLog(
                    job_type="bid_public_info_sync",
                    target=target,
                    status="failed",
                    started_at=started_at,
                    finished_at=datetime.now(),
                    message=message,
                )
            )
            session.commit()
        raise
    finally:
        client.close()

    print(f"fetched bids: {result.fetched_count}")
    print(f"upserted bids: {result.upserted_count}")


if __name__ == "__main__":
    main()
