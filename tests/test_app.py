import importlib
import sys
from types import ModuleType

import pytest


@pytest.fixture
def app_module(monkeypatch):
    import API_calls.StudentDatafromLDRESTAPI as student_api
    import config.load_config_file as load_config_file
    import config.quality_model_config as quality_model_config
    import ld_refresh
    import logic.factors_logic.factor_event_mapping as factor_event_mapping
    import logic.indicators_logic.indicator_event_mapping as indicator_event_mapping
    import logic.metrics_logic.metric_event_mapping as metric_event_mapping

    monkeypatch.setattr(
        metric_event_mapping, "build_metrics_index_per_qm", lambda *_: ({}, {})
    )
    monkeypatch.setattr(
        factor_event_mapping, "build_factors_index_per_qm", lambda *_: ({}, {})
    )
    monkeypatch.setattr(
        indicator_event_mapping, "build_indicators_index_per_qm", lambda *_: ({}, {})
    )
    monkeypatch.setattr(
        student_api,
        "build_team_students_map",
        lambda: {
            "team-1": {
                "EXCEL": ["Alice", "Bob"],
                "GITHUB": ["alice", "bob"],
                "TAIGA": ["alice-taiga"],
            }
        },
    )
    monkeypatch.setattr(
        quality_model_config, "load_qualitymodel_map", lambda: {"team-1": "amep"}
    )
    monkeypatch.setattr(
        quality_model_config,
        "choose_qualitymodel",
        lambda external_id, explicit_qm, qm_map: (
            explicit_qm or qm_map.get(external_id, "default")
        ).lower(),
    )
    monkeypatch.setattr(
        load_config_file, "get_event_meta", lambda _event_type: {"data_source": "GITHUB"}
    )
    monkeypatch.setattr(ld_refresh, "run_daily_refresh", lambda: None)

    fake_background_module = ModuleType("apscheduler.schedulers.background")

    class FakeBackgroundScheduler:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def add_job(self, *args, **kwargs):
            return None

        def start(self):
            return None

    fake_background_module.BackgroundScheduler = FakeBackgroundScheduler
    monkeypatch.setitem(sys.modules, "apscheduler", ModuleType("apscheduler"))
    monkeypatch.setitem(
        sys.modules, "apscheduler.schedulers", ModuleType("apscheduler.schedulers")
    )
    monkeypatch.setitem(
        sys.modules, "apscheduler.schedulers.background", fake_background_module
    )

    sys.modules.pop("app", None)
    module = importlib.import_module("app")
    yield module
    sys.modules.pop("app", None)


def test_handle_event_returns_200_and_starts_thread(app_module, monkeypatch):
    payload = {"event_type": "push", "prj": "team-1", "author_login": "alice"}
    started = {}

    class FakeThread:
        def __init__(self, target, args=(), kwargs=None):
            started["target"] = target
            started["args"] = args
            started["kwargs"] = kwargs or {}

        def start(self):
            started["started"] = True

    monkeypatch.setattr(app_module.threading, "Thread", FakeThread)

    response = app_module.app.test_client().post("/api/event", json=payload)

    assert response.status_code == 200
    assert response.get_json() == {"status": "received"}
    assert started["target"] is app_module.background_process_event
    assert started["args"] == (payload,)
    assert started["kwargs"] == {}
    assert started["started"] is True


def test_background_process_event_dispatches_metrics_factors_and_indicators(
    app_module, monkeypatch
):
    app_module.TEAM_STUDENTS_MAP = {"team-1": {"GITHUB": ["alice", "bob"]}}
    app_module.TEAM_QUALITYMODEL_MAP = {"team-1": "amep"}
    app_module.EVENT_METRICS_BY_QM = {
        "amep": {
            "push": [
                {"name": "student-activity", "scope": "individual"},
                {"name": "team-health", "scope": "team"},
                {"name": "author-activity", "scope": "individual_only"},
            ]
        }
    }
    app_module.EVENT_FACTORS_BY_QM = {
        "amep": {
            "push": [{"name": "delivery", "metric": ["metric-a", "metric-b"]}]
        }
    }
    app_module.EVENT_INDICATORS_BY_QM = {
        "amep": {"push": [{"name": "overall", "factor": ["delivery"]}]}
    }

    student_metric_calls = []
    team_metric_calls = []
    latest_metric_calls = []
    factor_calls = []
    latest_factor_calls = []
    indicator_calls = []

    monkeypatch.setattr(
        app_module, "get_event_meta", lambda _event_type: {"data_source": "GITHUB"}
    )

    def fake_compute_metric_for_student(
        metric_def, event_type, student_name, team_name
    ):
        student_metric_calls.append(
            (metric_def["name"], event_type, student_name, team_name)
        )

    def fake_compute_metric_for_team(metric_def, event_type, team_name, students):
        team_metric_calls.append((metric_def["name"], event_type, team_name, students))

    def fake_latest_metric_value(team_name, metric_name):
        latest_metric_calls.append((team_name, metric_name))
        return [(None, float(len(metric_name)))]

    def fake_compute_factor(team_name, factor_def, factor_values):
        factor_calls.append((team_name, factor_def["name"], factor_values))
        return 0.5, "ok"

    def fake_latest_factor_value(team_name, factor_name):
        latest_factor_calls.append((team_name, factor_name))
        return [(None, 0.5)]

    def fake_compute_indicator(team_name, indicator_def, indicator_values):
        indicator_calls.append((team_name, indicator_def["name"], indicator_values))
        return 0.5, "ok"

    monkeypatch.setattr(
        app_module, "compute_metric_for_student", fake_compute_metric_for_student
    )
    monkeypatch.setattr(
        app_module, "compute_metric_for_team", fake_compute_metric_for_team
    )
    monkeypatch.setattr(app_module, "latest_metric_value", fake_latest_metric_value)
    monkeypatch.setattr(app_module, "compute_factor", fake_compute_factor)
    monkeypatch.setattr(app_module, "latest_factor_value", fake_latest_factor_value)
    monkeypatch.setattr(app_module, "compute_indicator", fake_compute_indicator)

    app_module.background_process_event(
        {"event_type": "push", "prj": "team-1", "author_login": "carol"}
    )

    assert student_metric_calls == [
        ("student-activity", "push", "alice", "team-1"),
        ("student-activity", "push", "bob", "team-1"),
        ("author-activity", "push", "carol", "team-1"),
    ]
    assert team_metric_calls == [
        ("team-health", "push", "team-1", ["alice", "bob"])
    ]
    assert latest_metric_calls == [
        ("team-1", "metric-a"),
        ("team-1", "metric-b"),
    ]
    assert factor_calls == [
        (
            "team-1",
            "delivery",
            {"metric-a": [(None, 8.0)], "metric-b": [(None, 8.0)]},
        )
    ]
    assert latest_factor_calls == [("team-1", "delivery")]
    assert indicator_calls == [
        ("team-1", "overall", {"delivery": [(None, 0.5)]})
    ]


def test_handle_refresh_rebuilds_students_map_and_runs_refresh(app_module, monkeypatch):
    app_module.TEAM_STUDENTS_MAP = {
        "team-1": {"EXCEL": ["Alice"], "GITHUB": ["alice"], "TAIGA": []}
    }
    refresh_calls = []

    class FakeThread:
        def __init__(self, target, args=(), kwargs=None):
            self.target = target
            self.args = args
            self.kwargs = kwargs or {}

        def start(self):
            self.target(*self.args, **self.kwargs)

    monkeypatch.setattr(app_module.threading, "Thread", FakeThread)
    monkeypatch.setattr(
        app_module,
        "build_team_students_map",
        lambda: {"team-2": {"EXCEL": ["Carol"], "GITHUB": ["carol"], "TAIGA": []}},
    )
    monkeypatch.setattr(app_module, "run_daily_refresh", lambda: refresh_calls.append(True))

    response = app_module.app.test_client().post("/api/refresh")

    assert response.status_code == 200
    assert response.get_json() == {"status": "refresh started"}
    assert app_module.TEAM_STUDENTS_MAP == {
        "team-2": {"EXCEL": ["Carol"], "GITHUB": ["carol"], "TAIGA": []}
    }
    assert refresh_calls == [True]


def test_get_students_map_returns_debug_payload(app_module):
    response = app_module.app.test_client().get("/api/debug/students-map")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["total_teams"] == 1
    assert payload["TEAM_STUDENTS_MAP"]["team-1"]["total_students"] == 2
    assert payload["TEAM_STUDENTS_MAP"]["team-1"]["GITHUB"] == ["alice", "bob"]
    assert set(payload["worker_info"]) == {"process_id", "thread_id", "thread_name"}
