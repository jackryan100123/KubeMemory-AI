"""Celery signals that persist task failures and retries to TaskLog."""
from __future__ import annotations

import logging

from celery.signals import task_failure, task_retry, task_success

from .models import TaskLog

logger = logging.getLogger(__name__)


def _task_name(sender) -> str:
    return getattr(sender, "name", None) or str(sender)


@task_failure.connect
def on_task_failure(
    sender=None,
    task_id=None,
    exception=None,
    traceback=None,
    **kwargs,
) -> None:
    """Log Celery task failures to the database."""
    try:
        TaskLog.objects.create(
            task_id=str(task_id or ""),
            task_name=_task_name(sender),
            status=TaskLog.Status.FAILURE,
            error_message=str(exception or "")[:4000],
        )
    except Exception as exc:
        logger.warning("TaskLog write failed on task_failure: %s", exc)


@task_retry.connect
def on_task_retry(sender=None, task_id=None, reason=None, **kwargs) -> None:
    """Log Celery task retries to the database."""
    try:
        TaskLog.objects.create(
            task_id=str(task_id or ""),
            task_name=_task_name(sender),
            status=TaskLog.Status.RETRY,
            error_message=str(reason or "")[:4000],
        )
    except Exception as exc:
        logger.warning("TaskLog write failed on task_retry: %s", exc)


@task_success.connect
def on_task_success(sender=None, result=None, **kwargs) -> None:
    """Optional success logging — only for ingest/analysis tasks to limit volume."""
    name = _task_name(sender)
    if "ingest_incident" not in name and "run_ai_analysis" not in name:
        return
    try:
        task_id = kwargs.get("task_id") or ""
        TaskLog.objects.create(
            task_id=str(task_id),
            task_name=name,
            status=TaskLog.Status.SUCCESS,
            error_message="",
        )
    except Exception:
        pass
