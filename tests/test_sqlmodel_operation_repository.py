from datetime import datetime

from sqlmodel import Session, SQLModel, create_engine

from app.models import SyncJobLog
from app.repositories.sqlmodel_operation_repository import SqlModelOperationRepository


def test_sqlmodel_operation_repository_lists_latest_first() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            SyncJobLog(
                job_type="sync",
                target="older",
                status="completed",
                started_at=datetime(2026, 3, 13, 5, 0),
                finished_at=datetime(2026, 3, 13, 5, 5),
                message="older log",
            )
        )
        session.add(
            SyncJobLog(
                job_type="sync",
                target="newer",
                status="failed",
                started_at=datetime(2026, 3, 13, 6, 0),
                finished_at=datetime(2026, 3, 13, 6, 1),
                message="newer log",
            )
        )
        session.commit()

        items = SqlModelOperationRepository(session).list_operations()

    assert [item["target"] for item in items] == ["newer", "older"]
    assert items[0]["finished_at"] == "2026-03-13 06:01"
