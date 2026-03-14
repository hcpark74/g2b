import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, cast

from sqlmodel import Session, delete, select

from app.config import settings
from app.db import engine, init_db
from app.models import SyncJobLog


@dataclass(slots=True)
class JobLogCleanupResult:
    deleted_count: int
    cutoff_at: datetime


def cleanup_job_logs(
    *,
    older_than_days: int | None = None,
    status: str | None = None,
    job_type: str | None = None,
    dry_run: bool = False,
) -> JobLogCleanupResult:
    init_db()
    retention_days = older_than_days or settings.job_log_retention_days
    cutoff_at = datetime.now() - timedelta(days=retention_days)

    with Session(engine) as session:
        statement = select(SyncJobLog).where(SyncJobLog.started_at < cutoff_at)  # type: ignore[operator]
        if status:
            statement = statement.where(SyncJobLog.status == status)  # type: ignore[operator]
        if job_type:
            statement = statement.where(SyncJobLog.job_type == job_type)  # type: ignore[operator]

        logs = list(session.exec(statement).all())
        deleted_count = len(logs)

        if not dry_run and deleted_count:
            log_id_column = cast(Any, SyncJobLog.id)
            session.exec(
                delete(SyncJobLog).where(
                    log_id_column.in_([log.id for log in logs if log.id is not None])
                )
            )
            session.commit()

    return JobLogCleanupResult(deleted_count=deleted_count, cutoff_at=cutoff_at)


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete old sync job logs.")
    parser.add_argument(
        "--days",
        type=int,
        default=settings.job_log_retention_days,
        help="Delete logs older than this many days.",
    )
    parser.add_argument("--status", help="Only delete logs with this status.")
    parser.add_argument("--job-type", help="Only delete logs with this job type.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show how many logs would be deleted without deleting them.",
    )
    args = parser.parse_args()

    result = cleanup_job_logs(
        older_than_days=args.days,
        status=args.status,
        job_type=args.job_type,
        dry_run=args.dry_run,
    )

    action = "would delete" if args.dry_run else "deleted"
    print(f"{action} logs: {result.deleted_count}")
    print(f"cutoff_at: {result.cutoff_at.strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
