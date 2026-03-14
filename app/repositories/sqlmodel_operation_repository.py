from sqlmodel import Session, select

from app.models import SyncJobLog
from app.repositories.operation_repository import OperationRepository


class SqlModelOperationRepository(OperationRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_operations(self) -> list[dict[str, str]]:
        logs = self.session.exec(
            select(SyncJobLog).order_by(SyncJobLog.started_at.desc())
        ).all()
        return [
            {
                "job_type": log.job_type,
                "target": log.target,
                "status": log.status,
                "started_at": self._format_datetime(log.started_at),
                "finished_at": self._format_datetime(log.finished_at),
                "message": log.message,
            }
            for log in logs
        ]

    def _format_datetime(self, value) -> str:
        if value is None:
            return "-"
        return value.strftime("%Y-%m-%d %H:%M")
