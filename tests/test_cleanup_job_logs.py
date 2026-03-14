from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.cleanup_job_logs import cleanup_job_logs
from app.db import engine, init_db
from app.models import SyncJobLog


def _insert_log(*, days_ago: int, status: str, job_type: str) -> None:
    now = datetime.now()
    started_at = now - timedelta(days=days_ago)
    with Session(engine) as session:
        session.add(
            SyncJobLog(
                job_type=job_type,
                target="test-target",
                status=status,
                started_at=started_at,
                finished_at=started_at,
                message="test",
            )
        )
        session.commit()


def test_cleanup_job_logs_deletes_old_logs(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "cleanup.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")

    import importlib
    import app.config
    import app.db
    import app.cleanup_job_logs

    importlib.reload(app.config)
    importlib.reload(app.db)
    importlib.reload(app.cleanup_job_logs)

    from app.cleanup_job_logs import cleanup_job_logs as run_cleanup
    from app.db import engine as test_engine, init_db as test_init_db
    from app.models import SyncJobLog as TestSyncJobLog

    test_init_db()
    now = datetime.now()
    with Session(test_engine) as session:
        session.add(
            TestSyncJobLog(
                job_type="bid_resync",
                target="old",
                status="completed",
                started_at=now - timedelta(days=40),
                finished_at=now - timedelta(days=40),
                message="old",
            )
        )
        session.add(
            TestSyncJobLog(
                job_type="bid_resync",
                target="new",
                status="completed",
                started_at=now - timedelta(days=5),
                finished_at=now - timedelta(days=5),
                message="new",
            )
        )
        session.commit()

    result = run_cleanup(older_than_days=30)

    assert result.deleted_count == 1
    with Session(test_engine) as session:
        logs = list(session.exec(select(TestSyncJobLog)).all())
    assert [log.target for log in logs] == ["new"]


def test_cleanup_job_logs_supports_dry_run(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "cleanup-dry-run.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")

    import importlib
    import app.config
    import app.db
    import app.cleanup_job_logs

    importlib.reload(app.config)
    importlib.reload(app.db)
    importlib.reload(app.cleanup_job_logs)

    from app.cleanup_job_logs import cleanup_job_logs as run_cleanup
    from app.db import engine as test_engine, init_db as test_init_db
    from app.models import SyncJobLog as TestSyncJobLog

    test_init_db()
    now = datetime.now()
    with Session(test_engine) as session:
        session.add(
            TestSyncJobLog(
                job_type="bid_resync",
                target="old",
                status="failed",
                started_at=now - timedelta(days=60),
                finished_at=now - timedelta(days=60),
                message="old",
            )
        )
        session.commit()

    result = run_cleanup(older_than_days=30, status="failed", dry_run=True)

    assert result.deleted_count == 1
    with Session(test_engine) as session:
        logs = list(session.exec(select(TestSyncJobLog)).all())
    assert len(logs) == 1
