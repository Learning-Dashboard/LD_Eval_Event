import textwrap

from logic.factors_logic.factor_event_mapping import (
    build_factors_index_per_qm,
    load_required_fields_factor,
)
from logic.indicators_logic.indicator_event_mapping import (
    build_indicators_index_per_qm,
    load_required_fields_indicator,
)
from logic.metrics_logic.metric_event_mapping import (
    build_metrics_index_per_qm,
    load_required_fields_metrics,
)


def write_properties(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")
    return path


def test_load_required_fields_metrics_parses_supported_keys_and_params(tmp_path):
    properties_path = write_properties(
        tmp_path / "commits.properties",
        """
        name=commits
        relatedEvent=push, task
        scope=individual
        metric=commitsTotal / 2
        description=Commit ratio
        factors=activity, ownership
        weights=0.75,0.25
        param.threshold=3
        param.weight=2.5
        ignored=value
        """,
    )

    assert load_required_fields_metrics(str(properties_path)) == {
        "name": "commits",
        "relatedEvent": "push, task",
        "scope": "individual",
        "metric": "commitsTotal / 2",
        "description": "Commit ratio",
        "factors": "activity, ownership",
        "weights": "0.75,0.25",
        "params": {"threshold": 3, "weight": 2.5},
    }


def test_build_metrics_index_per_qm_indexes_definitions_by_related_event(tmp_path):
    properties_path = write_properties(
        tmp_path / "AMEP" / "metrics" / "commits.properties",
        """
        name=commits
        relatedEvent=push, task
        scope=team
        metric=commitsTotal
        factors=activity
        weights=1
        """,
    )

    all_by_qm, events_by_qm = build_metrics_index_per_qm(tmp_path)

    metric_def = all_by_qm["amep"][0]
    assert metric_def["filePath"] == str(properties_path)
    assert metric_def["quality_model"] == "amep"
    assert metric_def["factors"] == ["activity"]
    assert metric_def["weights"] == [1.0]
    assert [metric["name"] for metric in events_by_qm["amep"]["push"]] == ["commits"]
    assert [metric["name"] for metric in events_by_qm["amep"]["task"]] == ["commits"]


def test_build_factors_index_per_qm_parses_metric_lists_and_defaults(tmp_path):
    properties_path = write_properties(
        tmp_path / "DEFAULT" / "factors" / "delivery.properties",
        """
        name=delivery
        metric=commits, tasks
        weights=0.7,0.3
        relatedEvent=push
        """,
    )

    props = load_required_fields_factor(str(properties_path))
    all_by_qm, events_by_qm = build_factors_index_per_qm(tmp_path)

    assert props["metric"] == "commits, tasks"
    factor_def = all_by_qm["default"][0]
    assert factor_def["metric"] == ["commits", "tasks"]
    assert factor_def["weights"] == ["0.7", "0.3"]
    assert factor_def["category"] == "NoCategory"
    assert [factor["name"] for factor in events_by_qm["default"]["push"]] == [
        "delivery"
    ]


def test_build_indicators_index_per_qm_parses_factor_lists_and_defaults(tmp_path):
    properties_path = write_properties(
        tmp_path / "DEFAULT" / "indicators" / "health.properties",
        """
        name=health
        factor=delivery, planning
        weights=0.4,0.6
        relatedEvent=push
        """,
    )

    props = load_required_fields_indicator(str(properties_path))
    all_by_qm, events_by_qm = build_indicators_index_per_qm(tmp_path)

    assert props["factor"] == "delivery, planning"
    indicator_def = all_by_qm["default"][0]
    assert indicator_def["factor"] == ["delivery", "planning"]
    assert indicator_def["weights"] == ["0.4", "0.6"]
    assert indicator_def["category"] == "NoCategory"
    assert [indicator["name"] for indicator in events_by_qm["default"]["push"]] == [
        "health"
    ]
