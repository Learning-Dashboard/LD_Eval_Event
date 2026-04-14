from types import SimpleNamespace

import ld_refresh


class FakeCollection:
    def __init__(self, docs=None):
        self.docs = list(docs or [])
        self.deleted_ids = []

    def estimated_document_count(self):
        return len(self.docs)

    def find(self, query):
        allowed_students = set(query["student_name"]["$nin"])
        return [
            doc
            for doc in list(self.docs)
            if "student_name" in doc and doc["student_name"] not in allowed_students
        ]

    def delete_one(self, query):
        self.deleted_ids.append(query["_id"])
        self.docs = [doc for doc in self.docs if doc["_id"] != query["_id"]]


class FakeDb:
    def __init__(self, collections=None):
        self.collections = dict(collections or {})
        self.dropped = []

    def list_collection_names(self):
        return list(self.collections)

    def drop_collection(self, collection_name):
        self.dropped.append(collection_name)
        self.collections.pop(collection_name, None)

    def __getitem__(self, collection_name):
        return self.collections[collection_name]


def test_team_is_active_checks_metrics_collection(monkeypatch):
    fake_db = FakeDb({"metrics.Team1": FakeCollection([{"_id": 1}])})
    monkeypatch.setattr(ld_refresh, "db", fake_db)

    assert ld_refresh.team_is_active("Team1") is True
    assert ld_refresh.team_is_active("Team2") is False


def test_trigger_team_event_posts_expected_payload(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["timeout"] = timeout
        return SimpleNamespace(status_code=202)

    monkeypatch.setattr(ld_refresh.requests, "post", fake_post)
    monkeypatch.setattr(ld_refresh, "API_URL", "http://service.test/api/event")
    monkeypatch.setattr(ld_refresh, "QM_MAP", {"Team1": "amep"})
    monkeypatch.setattr(ld_refresh, "choose_qualitymodel", lambda *_args: "amep")

    ld_refresh.trigger_team_event("Team1", "push")

    assert captured == {
        "url": "http://service.test/api/event",
        "json": {
            "event_type": "push",
            "prj": "Team1",
            "author_login": "system",
            "quality_model": "amep",
        },
        "timeout": (0.2, 1),
    }


def test_delete_orphan_collections_drops_missing_team_collections(monkeypatch):
    fake_db = FakeDb(
        {
            "metrics.Team1": FakeCollection(),
            "metrics.Legacy": FakeCollection(),
            "factors.Legacy": FakeCollection(),
            "strategic_indicators.Legacy": FakeCollection(),
            "misc.Legacy": FakeCollection(),
        }
    )
    monkeypatch.setattr(ld_refresh, "db", fake_db)

    ld_refresh.delete_orphan_collections_from_mongo(["Team1"])

    assert set(fake_db.dropped) == {
        "metrics.Legacy",
        "factors.Legacy",
        "strategic_indicators.Legacy",
    }
    assert "misc.Legacy" not in fake_db.dropped


def test_delete_orphan_student_documents_removes_unknown_students(monkeypatch):
    metrics_collection = FakeCollection(
        [
            {"_id": 1, "student_name": "alice"},
            {"_id": 2, "student_name": "ghost"},
            {"_id": 3, "metric_name": "team-metric"},
        ]
    )
    factors_collection = FakeCollection(
        [
            {"_id": 4, "student_name": "ghost"},
            {"_id": 5, "student_name": "bob"},
        ]
    )
    indicators_collection = FakeCollection([{"_id": 6, "student_name": "ghost"}])
    fake_db = FakeDb(
        {
            "metrics.Team1": metrics_collection,
            "factors.Team1": factors_collection,
            "strategic_indicators.Team1": indicators_collection,
        }
    )
    monkeypatch.setattr(ld_refresh, "db", fake_db)

    ld_refresh.delete_orphan_student_documents(
        {
            "Team1": {
                "EXCEL": ["Alice Example"],
                "GITHUB": ["alice"],
                "TAIGA": ["bob"],
            }
        }
    )

    assert metrics_collection.deleted_ids == [2]
    assert factors_collection.deleted_ids == [4]
    assert indicators_collection.deleted_ids == [6]


def test_run_daily_refresh_triggers_every_available_event(monkeypatch):
    delete_calls = []
    trigger_calls = []
    team_students = {
        "Team1": {"GITHUB": ["alice"]},
        "Team2": {"GITHUB": ["bob"]},
    }

    monkeypatch.setattr(ld_refresh, "build_team_students_map", lambda: team_students)
    monkeypatch.setattr(
        ld_refresh,
        "delete_orphan_collections_from_mongo",
        lambda actual_teams: delete_calls.append(actual_teams),
    )
    monkeypatch.setattr(
        ld_refresh, "get_available_events", lambda: ["push", "task", "userstory"]
    )
    monkeypatch.setattr(
        ld_refresh,
        "trigger_team_event",
        lambda team_id, event_type: trigger_calls.append((team_id, event_type)),
    )

    ld_refresh.run_daily_refresh()

    assert delete_calls == [["Team1", "Team2"]]
    assert trigger_calls == [
        ("Team1", "push"),
        ("Team1", "task"),
        ("Team1", "userstory"),
        ("Team2", "push"),
        ("Team2", "task"),
        ("Team2", "userstory"),
    ]
