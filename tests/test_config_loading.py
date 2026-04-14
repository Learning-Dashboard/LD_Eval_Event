import json

from config.load_config_file import (
    get_available_events,
    get_event_meta,
    load_sources_config,
)
from config.quality_model_config import choose_qualitymodel, load_qualitymodel_map


def test_sources_config_helpers_use_env_override(tmp_path, monkeypatch):
    config_path = tmp_path / "sources.json"
    config_data = {
        "push": {"data_source": "GITHUB", "collection_suffix": "commits"},
        "task": {"data_source": "TAIGA", "collection_suffix": "tasks"},
    }
    config_path.write_text(json.dumps(config_data), encoding="utf-8")
    monkeypatch.setenv("SOURCES_CONFIG", str(config_path))

    assert load_sources_config() == config_data
    assert get_event_meta("push") == config_data["push"]
    assert set(get_available_events()) == {"push", "task"}


def test_load_qualitymodel_map_inverts_and_lowercases_values(tmp_path):
    config_path = tmp_path / "quality_models.json"
    config_path.write_text(
        json.dumps({"AMEP": ["TeamA", "TeamB"], "DEFAULT": ["TeamC"]}),
        encoding="utf-8",
    )

    assert load_qualitymodel_map(str(config_path)) == {
        "TeamA": "amep",
        "TeamB": "amep",
        "TeamC": "default",
    }


def test_choose_qualitymodel_prefers_explicit_then_mapping_then_default():
    qm_map = {"TeamA": "amep"}

    assert choose_qualitymodel("TeamA", "DEFAULT", qm_map) == "default"
    assert choose_qualitymodel("TeamA", None, qm_map) == "amep"
    assert choose_qualitymodel("UnknownTeam", None, qm_map) == "default"
