import argparse
from datetime import datetime

from sqlmodel import Session

from app.db import engine, init_db
from app.models import SyncJobLog
from app.services import G2BBidCrawlService
from app.services.g2b_bid_page_crawler import G2BBidPageCrawler
from app.services.sync_logging import build_sync_failure_message


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Crawl bid detail pages with Playwright."
    )
    parser.add_argument(
        "--bid-id",
        action="append",
        dest="bid_ids",
        required=True,
        help="Specific bid_id to crawl. Can be passed multiple times.",
    )
    args = parser.parse_args()

    init_db()
    started_at = datetime.now()
    crawler = G2BBidPageCrawler()
    selected_bid_ids = list(args.bid_ids or [])

    try:
        with Session(engine) as session:
            service = G2BBidCrawlService(session=session, crawler=crawler)
            result = service.crawl_bids(bid_ids=selected_bid_ids)
            session.add(
                SyncJobLog(
                    job_type="bid_page_crawl",
                    target=",".join(selected_bid_ids),
                    status="completed",
                    started_at=started_at,
                    finished_at=datetime.now(),
                    message=(
                        f"processed {len(result.processed_bid_ids)} bids, "
                        f"stored {result.attachment_count} attachments"
                    ),
                )
            )
            session.commit()
    except Exception as exc:
        with Session(engine) as session:
            session.add(
                SyncJobLog(
                    job_type="bid_page_crawl",
                    target=",".join(selected_bid_ids),
                    status="failed",
                    started_at=started_at,
                    finished_at=datetime.now(),
                    message=build_sync_failure_message(exc),
                )
            )
            session.commit()
        raise


if __name__ == "__main__":
    main()
