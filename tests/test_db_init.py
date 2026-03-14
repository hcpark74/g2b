import importlib
import sqlite3


def test_init_db_adds_missing_legacy_sqlite_columns(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        CREATE TABLE bid_details (
            created_at TEXT,
            updated_at TEXT,
            bid_id TEXT PRIMARY KEY,
            description_text TEXT,
            raw_api_data TEXT,
            crawl_data TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE attachments (
            created_at TEXT,
            updated_at TEXT,
            attachment_id TEXT PRIMARY KEY,
            bid_id TEXT,
            name TEXT NOT NULL,
            file_type TEXT,
            download_url TEXT,
            local_path TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE sync_job_logs (
            created_at TEXT,
            updated_at TEXT,
            id INTEGER PRIMARY KEY,
            job_type TEXT NOT NULL,
            target TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            message TEXT NOT NULL
        )
        """
    )
    connection.commit()
    connection.close()

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("DEBUG", "false")

    import app.config
    import app.db

    importlib.reload(app.config)
    db_module = importlib.reload(app.db)
    db_module.init_db()

    connection = sqlite3.connect(db_path)
    bid_detail_columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(bid_details)").fetchall()
    }
    attachment_columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(attachments)").fetchall()
    }
    sync_job_log_columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(sync_job_logs)").fetchall()
    }
    connection.close()

    assert {"detail_url", "detail_hash", "collected_at"} <= bid_detail_columns
    assert {"source", "file_size", "content_hash", "collected_at"} <= attachment_columns
    assert {"metadata_json"} <= sync_job_log_columns
