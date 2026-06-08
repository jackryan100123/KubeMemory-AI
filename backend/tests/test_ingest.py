"""Ingest task happy-path tests (DB row created)."""
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.incidents.models import Incident
from apps.incidents.tasks import ingest_incident_task


@pytest.mark.django_db
@patch("apps.incidents.tasks.send_notification.delay")
@patch("apps.incidents.tasks.run_ai_analysis_task.delay")
@patch("apps.memory.graph_builder.KubeGraphBuilder")
@patch("apps.memory.vector_store.IncidentVectorStore")
def test_ingest_creates_incident(
    mock_vs_cls: MagicMock,
    mock_graph_cls: MagicMock,
    mock_analysis: MagicMock,
    mock_notify: MagicMock,
) -> None:
    mock_vs = mock_vs_cls.return_value
    mock_vs.embed_incident.return_value = "chroma-1"
    mock_graph = mock_graph_cls.return_value
    mock_graph.ingest_incident.return_value = "neo4j-1"

    result = ingest_incident_task(
        {
            "pod_name": "api-7f8b",
            "namespace": "default",
            "incident_type": "CrashLoopBackOff",
            "severity": "high",
            "description": "backoff",
            "occurred_at": timezone.now().isoformat(),
        }
    )
    assert result["status"] == "created"
    assert Incident.objects.count() == 1
    inc = Incident.objects.get()
    assert inc.chroma_id == "chroma-1"
    assert inc.neo4j_id == "neo4j-1"
