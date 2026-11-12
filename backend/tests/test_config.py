import stat

import pytest
from pydantic import ValidationError

from rewind.config import (
    MASK,
    AdvisorProvider,
    Channel,
    Config,
    ConfigStore,
    IndexerConfig,
    masked,
    restore_secrets,
)


def test_defaults_are_valid_and_empty():
    c = Config()
    assert c.channels == [] and c.power.provider == "none"
    assert c.remote.keys["channel_1"] == ["&", "1"]


def test_roundtrip_and_file_mode(tmp_path):
    store = ConfigStore(tmp_path / "config.toml")
    cfg = Config(channels=[Channel(id="news", name="News", playlist_id="PL1")])
    cfg.tmdb.api_key = "k"
    cfg.indexers.append(IndexerConfig(url="http://127.0.0.1:9117", api_key="j"))
    store.save(cfg)
    assert stat.S_IMODE((tmp_path / "config.toml").stat().st_mode) == 0o600
    again = ConfigStore(tmp_path / "config.toml").get()
    assert again == cfg


def test_rejects_bad_values():
    with pytest.raises(ValidationError):
        Config.model_validate({"channels": [{"id": "Bad Id", "name": "x"}]})
    with pytest.raises(ValidationError):
        Config.model_validate({"unknown_section": {}})
    with pytest.raises(ValidationError):
        Config.model_validate({"channels": [{"id": f"c{i}", "name": "x"} for i in range(10)]})


def test_mask_and_restore_secrets():
    old = Config()
    old.tmdb.api_key = "tmdb-secret"
    old.advisor = [AdvisorProvider(name="G", kind="gemini", api_key="g-secret", model="m")]
    shown = masked(old)
    assert shown["tmdb"]["api_key"] == MASK
    assert shown["advisor"][0]["api_key"] == MASK
    assert shown["opensubtitles"]["password"] == ""  # empty secret stays empty

    shown["weather"]["latitude"] = 1.0
    new = restore_secrets(Config.model_validate(shown), old)
    assert new.tmdb.api_key == "tmdb-secret"
    assert new.advisor[0].api_key == "g-secret"
    assert new.weather.latitude == 1.0

    shown["tmdb"]["api_key"] = "changed"
    assert restore_secrets(Config.model_validate(shown), old).tmdb.api_key == "changed"


def test_old_image_logos_are_dropped():
    old = {"id": "news", "name": "News", "logo": "custom:newsTV.png", "show_name": True}
    assert Channel.model_validate(old).logo_style == 1
    assert Channel.model_validate({"id": "a", "name": "A", "logo": "retro:2"}).logo_style == 2
