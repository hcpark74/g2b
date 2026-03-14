from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings


LEGACY_SQLITE_COLUMN_MIGRATIONS: dict[str, dict[str, str]] = {
    "bids": {
        "notice_version_type": "TEXT",
        "is_latest_version": "INTEGER NOT NULL DEFAULT 0",
        "is_effective_version": "INTEGER NOT NULL DEFAULT 1",
        "parent_bid_id": "TEXT",
        "version_reason": "TEXT",
    },
    "bid_details": {
        "detail_url": "TEXT",
        "detail_hash": "TEXT",
        "collected_at": "TEXT",
    },
    "attachments": {
        "source": "TEXT",
        "file_size": "INTEGER",
        "content_hash": "TEXT",
        "collected_at": "TEXT",
    },
    "sync_job_logs": {
        "metadata_json": "TEXT",
    },
}


def _build_engine():
    connect_args = (
        {"check_same_thread": False}
        if settings.database_url.startswith("sqlite")
        else {}
    )
    return create_engine(
        settings.database_url, echo=settings.debug, connect_args=connect_args
    )


engine = _build_engine()


def _sync_sqlite_legacy_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    with engine.begin() as connection:
        for table_name, column_map in LEGACY_SQLITE_COLUMN_MIGRATIONS.items():
            rows = connection.exec_driver_sql(
                f"PRAGMA table_info({table_name})"
            ).fetchall()
            if not rows:
                continue

            existing_columns = {row[1] for row in rows}
            for column_name, column_type in column_map.items():
                if column_name in existing_columns:
                    continue
                connection.exec_driver_sql(
                    f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
                )


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    _sync_sqlite_legacy_columns()


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
