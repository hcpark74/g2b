import importlib
import sqlite3


def test_init_db_adds_missing_legacy_sqlite_columns(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "legacy.db"
    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        CREATE TABLE bids (
            created_at TEXT,
            updated_at TEXT,
            bid_id TEXT PRIMARY KEY,
            bid_no TEXT NOT NULL,
            bid_seq TEXT NOT NULL DEFAULT '00',
            title TEXT NOT NULL,
            demand_org TEXT,
            notice_org TEXT,
            category TEXT,
            status TEXT NOT NULL DEFAULT 'collected',
            posted_at TEXT,
            closed_at TEXT,
            budget_amount INTEGER,
            is_favorite INTEGER NOT NULL DEFAULT 0,
            favorite_memo TEXT,
            source_api_name TEXT,
            view_count INTEGER NOT NULL DEFAULT 0,
            last_synced_at TEXT,
            last_changed_at TEXT
        )
        """
    )
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
    bid_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(bids)").fetchall()
    }
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

    assert {
        "notice_version_type",
        "is_latest_version",
        "is_effective_version",
        "parent_bid_id",
        "version_reason",
    } <= bid_columns
    assert {"detail_url", "detail_hash", "collected_at"} <= bid_detail_columns
    assert {"source", "file_size", "content_hash", "collected_at"} <= attachment_columns
    assert {"metadata_json"} <= sync_job_log_columns


def test_init_db_creates_bid_version_changes_table(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "version-changes.db"

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("DEBUG", "false")

    import app.config
    import app.db

    importlib.reload(app.config)
    db_module = importlib.reload(app.db)
    db_module.init_db()

    connection = sqlite3.connect(db_path)
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    columns = {
        row[1]
        for row in connection.execute(
            "PRAGMA table_info(bid_version_changes)"
        ).fetchall()
    }
    connection.close()

    assert "bid_version_changes" in tables
    assert {
        "change_id",
        "bid_id",
        "bid_no",
        "bid_seq",
        "change_data_div_name",
        "change_item_name",
        "before_value",
        "after_value",
        "changed_at",
        "rbid_no",
        "license_limit_code_list_raw",
        "source_api_name",
        "raw_data",
    } <= columns
