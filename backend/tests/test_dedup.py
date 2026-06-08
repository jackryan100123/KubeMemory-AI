"""Incident fingerprint deduplication tests."""
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.incidents.fingerprint import compute_incident_fingerprint
from apps.incidents.models import Incident
from apps.incidents.tasks import ingest_incident_task


@pytest.mark.django_db
@patch("apps.incidents.tasks.send_notification.delay")
@patch("apps.incidents.tasks.run_ai_analysis_task.delay")
@patch("apps.memory.graph_builder.KubeGraphBuilder")
@patch("apps.memory.vector_store.IncidentVectorStore")
def test_fingerprint_dedup_increments_occurrence(
    mock_vs_cls: MagicMock,
    mock_graph_cls: MagicMock,
    mock_analysis: MagicMock,
    mock_notify: MagicMock,
) -> None:
    mock_vs_cls.return_value.embed_incident.return_value = "c1"
    mock_graph_cls.return_value.ingest_incident.return_value = "n1"
    occurred = timezone.now()
    data = {
        "pod_name": "pay-123",
        "namespace": "production",
        "incident_type": "CrashLoopBackOff",
        "severity": "high",
        "description": "crash",
        "occurred_at": occurred.isoformat(),
    }
    ingest_incident_task(data)
    ingest_incident_task(data)
    assert Incident.objects.count() == 1
    inc = Incident.objects.get()
    assert inc.occurrence_count == 2


@pytest.mark.django_db
def test_fingerprint_same_window() -> None:
    occurred = timezone.now()
    fp = compute_incident_fingerprint("ns", "pod", "OOMKill", occurred, None)
    fp2 = compute_incident_fingerprint(
        "ns", "pod", "OOMKill", occurred + timedelta(minutes=2), None
    )
    assert fp == fp2
