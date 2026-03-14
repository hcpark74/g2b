from typing import Any

from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Bid, SyncJobLog
from app.sync_contract_process import main as sync_contract_process_main


def test_contract_process_cli_records_completed_operation_log(monkeypatch) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Bid(
                bid_id="R26BK00001001-000",
                bid_no="R26BK00001001",
                bid_seq="000",
                title="계약과정 대상",
            )
        )
        session.commit()

    class StubClient:
        def fetch_contract_process(
            self,
            *,
            operation_name: str,
            inqry_div: int,
            value: str,
            page_no: int = 1,
            num_of_rows: int = 100,
        ) -> list[dict[str, Any]]:
            _ = (operation_name, inqry_div, value, page_no, num_of_rows)
            return []

        def close(self) -> None:
            return None

    monkeypatch.setattr("app.sync_contract_process.engine", engine)
    monkeypatch.setattr("app.sync_contract_process.init_db", lambda: None)
    monkeypatch.setattr(
        "app.sync_contract_process.G2BContractProcessClient", StubClient
    )
    monkeypatch.setattr(
        "sys.argv",
        ["app.sync_contract_process", "--bid-id", "R26BK00001001-000"],
    )

    sync_contract_process_main()

    with Session(engine) as session:
        logs = session.exec(select(SyncJobLog)).all()

    assert len(logs) == 1
    assert logs[0].job_type == "contract_process_sync"
    assert logs[0].status == "completed"
    assert logs[0].target == "R26BK00001001-000"
    assert logs[0].message == "processed 1 bids, fetched 0 items"


def test_contract_process_cli_records_failure_log(monkeypatch) -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Bid(
                bid_id="R26BK00001002-000",
                bid_no="R26BK00001002",
                bid_seq="000",
                title="계약과정 대상",
            )
        )
        session.commit()

    class FailingClient:
        def fetch_contract_process(
            self,
            *,
            operation_name: str,
            inqry_div: int,
            value: str,
            page_no: int = 1,
            num_of_rows: int = 100,
        ) -> list[dict[str, Any]]:
            _ = (operation_name, inqry_div, value, page_no, num_of_rows)
            raise RuntimeError("mock contract process failure")

        def close(self) -> None:
            return None

    monkeypatch.setattr("app.sync_contract_process.engine", engine)
    monkeypatch.setattr("app.sync_contract_process.init_db", lambda: None)
    monkeypatch.setattr(
        "app.sync_contract_process.G2BContractProcessClient", FailingClient
    )
    monkeypatch.setattr(
        "sys.argv",
        ["app.sync_contract_process", "--bid-id", "R26BK00001002-000"],
    )

    try:
        sync_contract_process_main()
    except RuntimeError as exc:
        assert "mock contract process failure" in str(exc)
    else:
        raise AssertionError("RuntimeError was not raised")

    with Session(engine) as session:
        logs = session.exec(select(SyncJobLog)).all()

    assert len(logs) == 1
    assert logs[0].job_type == "contract_process_sync"
    assert logs[0].status == "failed"
    assert logs[0].target == "R26BK00001002-000"
    assert "failure_category=unexpected" in logs[0].message
    assert "exception_type=RuntimeError" in logs[0].message
