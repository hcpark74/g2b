from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, cast

import httpx
from sqlmodel import Session, select

from app.config import settings
from app.models import SyncJobLog


def log_sync_job(
    *,
    session: Session,
    job_type: str,
    target: str,
    status: str,
    started_at: datetime,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> SyncJobLog:
    log = SyncJobLog(
        job_type=job_type,
        target=target,
        status=status,
        started_at=started_at,
        finished_at=datetime.now(),
        message=message,
        metadata_json=(
            json.dumps(metadata, ensure_ascii=False, sort_keys=True)
            if metadata is not None
            else None
        ),
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    if status == "failed":
        notify_failed_job(log)
    return log


def notify_failed_job(log: SyncJobLog) -> None:
    webhook_url = settings.ops_slack_webhook_url.strip()
    if not webhook_url:
        return

    payload = {
        "text": (
            f"[{settings.app_name}:{settings.app_env}] sync failure\n"
            f"job_type={log.job_type}\n"
            f"target={log.target}\n"
            f"started_at={log.started_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"message={log.message}"
        )
    }

    try:
        httpx.post(webhook_url, json=payload, timeout=5.0)
    except Exception:
        return


def build_health_report(session: Session) -> dict[str, Any]:
    latest_job = session.exec(
        select(SyncJobLog).order_by(cast(Any, SyncJobLog.started_at).desc())
    ).first()
    failure_threshold = datetime.now() - timedelta(
        hours=settings.ops_health_recent_failure_hours
    )
    recent_failures = session.exec(
        select(SyncJobLog).where(
            SyncJobLog.status == "failed",
            SyncJobLog.started_at >= failure_threshold,
        )
    ).all()

    status = "ok"
    if latest_job is not None and latest_job.status == "failed":
        status = "degraded"

    return {
        "status": status,
        "app": settings.app_name,
        "env": settings.app_env,
        "database": "ok",
        "recent_failed_jobs": len(recent_failures),
        "latest_job": (
            {
                "job_type": latest_job.job_type,
                "target": latest_job.target,
                "status": latest_job.status,
                "started_at": latest_job.started_at.strftime("%Y-%m-%d %H:%M"),
                "finished_at": (
                    latest_job.finished_at.strftime("%Y-%m-%d %H:%M")
                    if latest_job.finished_at is not None
                    else None
                ),
            }
            if latest_job is not None
            else None
        ),
    }
