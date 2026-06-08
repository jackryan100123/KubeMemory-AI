"""LangGraph / AnalysisResult schema tests."""
from apps.agents.schemas import AnalysisResult


def test_analysis_result_schema() -> None:
    data = {
        "confidence_score": 0.85,
        "severity": "high",
        "root_cause_hypothesis": "OOM after deploy",
        "affected_services": ["payment"],
        "recommended_actions": ["Increase memory limit"],
        "runbook_steps": ["kubectl describe pod"],
    }
    result = AnalysisResult.model_validate(data)
    assert result.confidence_score == 0.85
    assert result.severity == "high"
    assert len(result.recommended_actions) == 1
