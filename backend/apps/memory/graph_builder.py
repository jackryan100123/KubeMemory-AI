"""
Neo4j graph database operations for KubeMemory.
Builds a causal knowledge graph of cluster incidents.
All connection config from environment variables.
"""
import logging
import os
from typing import Any

import neo4j

from apps.incidents.models import Incident

logger = logging.getLogger(__name__)


class KubeGraphBuilder:
    """Neo4j graph builder for pods, incidents, fixes, and deployments."""

    def __init__(self) -> None:
        uri = os.environ.get("NEO4J_URI") or "bolt://localhost:7687"
        user = os.environ.get("NEO4J_USER") or "neo4j"
        password = os.environ.get("NEO4J_PASSWORD")
        if not password:
            logger.warning("NEO4J_PASSWORD not set; Neo4j operations may fail.")
        self._driver = neo4j.GraphDatabase.driver(uri, auth=(user, password or ""))
        self._verify_connectivity()

    def _verify_connectivity(self) -> None:
        """Verify Neo4j is reachable; log warning if not, don't crash."""
        try:
            self._driver.verify_connectivity()
        except Exception as e:
            logger.warning("Neo4j unreachable: %s. Graph operations may fail.", e)

    def close(self) -> None:
        """Close the Neo4j driver connection."""
        self._driver.close()

    def ingest_incident(self, incident: Incident) -> str:
        """
        Create/merge Pod, Service, Node, Incident nodes and relationships in one transaction.
        Optionally link to a Deployment that happened within 2 hours before.
        Returns Neo4j internal node ID (elementId) of the Incident node as string.
        """
        # Optional Pod fields not on Incident model
        image = getattr(incident, "image", None) or ""
        restart_count = getattr(incident, "restart_count", None)
        if restart_count is None:
            restart_count = 0

        timestamp = incident.occurred_at
        if hasattr(timestamp, "isoformat"):
            timestamp = timestamp.isoformat()

        with self._driver.session() as session:
            result = session.run(
                """
                MERGE (p:Pod {name: $pod_name, namespace: $namespace})
                SET p.image = $image, p.restart_count = $restart_count

                MERGE (svc:Service {name: $service_name, namespace: $namespace})
                MERGE (n:Node {name: $node_name})

                MERGE (p)-[:BELONGS_TO]->(svc)
                MERGE (p)-[:RUNS_ON]->(n)

                CREATE (i:Incident {
                    id: $incident_id,
                    db_id: $db_id,
                    type: $incident_type,
                    timestamp: datetime($timestamp),
                    severity: $severity,
                    description: $description,
                    resolved: false
                })

                MERGE (i)-[:AFFECTED]->(p)

                RETURN elementId(i) AS neo4j_id
                """,
                pod_name=incident.pod_name or "",
                namespace=incident.namespace or "",
                image=str(image),
                restart_count=int(restart_count),
                service_name=incident.service_name or incident.pod_name or "unknown",
                node_name=incident.node_name or "unknown",
                incident_id=f"incident_{incident.id}",
                db_id=incident.id,
                incident_type=incident.incident_type or "Unknown",
                timestamp=timestamp,
                severity=incident.severity or "medium",
                description=(incident.description or "")[:10000],
            )
            record = result.single()
            neo4j_id = record["neo4j_id"] if record else ""

            # Link Deployment that happened within 2 hours before this incident
            session.run(
                """
                MATCH (i:Incident {db_id: $db_id})
                MATCH (d:Deployment {namespace: $namespace})
                WHERE d.timestamp <= datetime($incident_ts)
                  AND duration.between(d.timestamp, datetime($incident_ts)).seconds <= 7200
                MERGE (d)-[:TRIGGERED]->(i)
                """,
                db_id=incident.id,
                namespace=incident.namespace or "",
                incident_ts=timestamp,
            )

        return neo4j_id

    def record_deployment(
        self,
        service_name: str,
        namespace: str,
        version: str,
        timestamp: str,
    ) -> None:
        """Create a Deployment node for correlating future crashes."""
        with self._driver.session() as session:
            session.run(
                """
                CREATE (d:Deployment {
                    service: $service_name,
                    namespace: $namespace,
                    version: $version,
                    timestamp: datetime($timestamp)
                })
                """,
                service_name=service_name,
                namespace=namespace,
                version=version,
                timestamp=timestamp,
            )

    def clear_all(self) -> None:
        """
        Remove all graph data (Pods, Services, Nodes, Incidents, Fixes, Deployments).
        Used when disconnecting cluster and clearing incident history.
        """
        with self._driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        logger.info("Neo4j graph cleared.")

    def resolve_incident(self, neo4j_id: str, fix_description: str) -> None:
        """Set resolved: true on Incident and create Fix node with RESOLVED_BY relationship."""
        with self._driver.session() as session:
            session.run(
                """
                MATCH (i:Incident)
                WHERE elementId(i) = $neo4j_id
                SET i.resolved = true
                CREATE (f:Fix {description: $fix_description})
                MERGE (i)-[:RESOLVED_BY]->(f)
                """,
                neo4j_id=neo4j_id,
                fix_description=fix_description[:10000],
            )

    def find_causal_patterns(
        self,
        pod_name: str,
        namespace: str,
    ) -> list[dict[str, Any]]:
        """Return incident types, frequency, sample fixes, deploy versions, last_seen for pod."""
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (p:Pod {name: $pod_name, namespace: $namespace})<-[:AFFECTED]-(i:Incident)
                OPTIONAL MATCH (i)-[:RESOLVED_BY]->(f:Fix)
                OPTIONAL MATCH (d:Deployment)-[:TRIGGERED]->(i)
                RETURN
                    i.type AS incident_type,
                    count(i) AS frequency,
                    collect(f.description)[0..3] AS fixes_that_worked,
                    collect(DISTINCT d.version) AS deploy_versions,
                    max(i.timestamp) AS last_seen
                ORDER BY frequency DESC
                LIMIT 10
                """,
                pod_name=pod_name,
                namespace=namespace,
            )
            rows = list(result)
        out: list[dict[str, Any]] = []
        for r in rows:
            last_seen = r["last_seen"]
            if last_seen is not None and hasattr(last_seen, "isoformat"):
                last_seen = last_seen.isoformat()
            out.append({
                "incident_type": r["incident_type"],
                "frequency": r["frequency"],
                "fixes_that_worked": r["fixes_that_worked"] or [],
                "deploy_versions": [v for v in (r["deploy_versions"] or []) if v],
                "last_seen": last_seen,
            })
        return out

    def find_blast_radius(
        self,
        pod_name: str,
        namespace: str,
    ) -> list[dict[str, Any]]:
        """Find pods that had incidents within ±5 minutes of this pod's incidents."""
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (p:Pod {name: $pod_name, namespace: $namespace})<-[:AFFECTED]-(i1:Incident)
                MATCH (i2:Incident)-[:AFFECTED]->(p2:Pod)
                WHERE abs(duration.between(i1.timestamp, i2.timestamp).seconds) < 300
                  AND (p2.name <> $pod_name OR p2.namespace <> $namespace)
                RETURN
                    p2.name AS affected_pod,
                    p2.namespace AS namespace,
                    count(*) AS co_occurrence,
                    collect(DISTINCT i2.type) AS incident_types
                ORDER BY co_occurrence DESC
                LIMIT 10
                """,
                pod_name=pod_name,
                namespace=namespace,
            )
            rows = list(result)
        return [
            {
                "affected_pod": r["affected_pod"],
                "namespace": r["namespace"],
                "co_occurrence": r["co_occurrence"],
                "incident_types": r["incident_types"] or [],
            }
            for r in rows
        ]

    def get_graph_data_for_namespace(self, namespace: str) -> dict[str, Any]:
        """
        Return {nodes: [...], links: [...]} for React Force Graph.
        Nodes: Pods, Services, Incidents, Fixes in namespace.
        Each node: {id, name, type, severity (for incidents), resolved}.
        Each link: {source, target, relationship}.
        """
        with self._driver.session() as session:
            # No WHERE in Cypher (Neo4j 5 syntax); nulls filtered in Python below
            result = session.run(
                """
                MATCH (p:Pod {namespace: $namespace})
                OPTIONAL MATCH (p)-[:BELONGS_TO]->(svc:Service)
                OPTIONAL MATCH (p)<-[:AFFECTED]-(i:Incident)
                OPTIONAL MATCH (i)-[:RESOLVED_BY]->(f:Fix)
                WITH collect(DISTINCT p) + collect(DISTINCT svc) + collect(DISTINCT i) + collect(DISTINCT f) AS node_list
                UNWIND node_list AS n
                RETURN DISTINCT n
                """,
                namespace=namespace,
            )
            nodes_list = list(result)
            node_ids: set[str] = set()
            nodes_out: list[dict[str, Any]] = []
            for rec in nodes_list:
                n = rec["n"]
                if n is None:
                    continue
                eid = getattr(n, "element_id", None) or str(id(n))
                if eid in node_ids:
                    continue
                node_ids.add(eid)
                labels = list(n.labels)
                node_type = labels[0] if labels else "Unknown"
                props = dict(n)
                name = props.get("name") or props.get("type") or props.get("description") or str(eid)
                if node_type == "Incident":
                    name = f"Incident {props.get('db_id', '')}"
                node_entry: dict[str, Any] = {
                    "id": eid,
                    "name": str(name)[:200],
                    "type": node_type,
                }
                if node_type == "Incident":
                    node_entry["severity"] = props.get("severity", "")
                    node_entry["resolved"] = props.get("resolved", False)
                    node_entry["db_id"] = props.get("db_id")
                nodes_out.append(node_entry)

            # Links: relationships in same namespace scope (Neo4j 5: no pattern inside WHERE, use UNION of simpler MATCHes)
            links_result = session.run(
                """
                MATCH (a)-[r]->(b)
                WHERE (a:Pod AND a.namespace = $namespace)
                   OR (b:Pod AND b.namespace = $namespace)
                   OR (a:Incident AND EXISTS { (a)-[:AFFECTED]->(p:Pod {namespace: $namespace}) })
                   OR (b:Incident AND EXISTS { (b)-[:AFFECTED]->(p:Pod {namespace: $namespace}) })
                RETURN elementId(a) AS source, elementId(b) AS target, type(r) AS relationship
                LIMIT 1000
                """,
                namespace=namespace,
            )
            links_out = [
                {
                    "source": r["source"],
                    "target": r["target"],
                    "relationship": r["relationship"],
                }
                for r in links_result
            ]
        return {"nodes": nodes_out, "links": links_out}

    def get_deploy_correlation_for_incident(self, incident_db_id: int) -> dict[str, Any] | None:
        """
        If this incident was linked to a Deployment (deployed within 2h before),
        return {service, version, minutes_before_crash}; else None.
        """
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (i:Incident {db_id: $db_id})
                MATCH (d:Deployment)-[:TRIGGERED]->(i)
                RETURN d.service AS service, d.version AS version,
                       duration.between(d.timestamp, i.timestamp).seconds / 60.0 AS minutes_before_crash
                LIMIT 1
                """,
                db_id=incident_db_id,
            )
            record = result.single()
            if not record or record["service"] is None:
                return None
            return {
                "service": record["service"],
                "version": record["version"] or "",
                "minutes_before_crash": float(record["minutes_before_crash"] or 0),
            }

    def find_deploy_to_crash_correlation(self) -> list[dict[str, Any]]:
        """Find deployment → crash patterns across the cluster."""
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (d:Deployment)-[:TRIGGERED]->(i:Incident)
                RETURN
                    d.service AS service,
                    count(i) AS crash_count,
                    collect(DISTINCT i.type) AS crash_types,
                    avg(duration.between(d.timestamp, i.timestamp).seconds) / 60.0 AS avg_minutes_to_crash
                ORDER BY crash_count DESC
                """
            )
            rows = list(result)
        return [
            {
                "service": r["service"],
                "crash_count": r["crash_count"],
                "crash_types": r["crash_types"] or [],
                "avg_minutes_to_crash": r["avg_minutes_to_crash"],
            }
            for r in rows
        ]
