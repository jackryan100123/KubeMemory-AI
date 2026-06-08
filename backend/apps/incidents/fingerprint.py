"""
Incident fingerprinting for deduplication within 5-minute windows.
"""
from __future__ import annotations

import hashlib
from datetime import datetime


def compute_incident_fingerprint(
    namespace: str,
    pod_name: str,
    incident_type: str,
    occurred_at: datetime,
    cluster_id: int | None = None,
) -> str:
    """
    SHA256(namespace + pod_name + incident_type + floor(timestamp / 300)).
    """
    ts_bucket = int(occurred_at.timestamp()) // 300
    raw = f"{namespace}|{pod_name}|{incident_type}|{ts_bucket}"
    if cluster_id is not None:
        raw = f"{raw}|{cluster_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
