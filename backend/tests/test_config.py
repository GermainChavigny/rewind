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


def test_hand_edit_is_reloaded(tmp_path):
    import os

    from rewind.config import ConfigStore

    path = tmp_path / "config.toml"
    store = ConfigStore(path)
    store.save(store.get())
    path.write_text('[admin]\npin = "4321"\n')
    os.utime(path, ns=(1, 1))  # a different mtime, whatever the clock resolution
    assert store.get().admin.pin == "4321"
    path.write_text("[admin\n")  # half-typed: the last good config stays
    os.utime(path, ns=(2, 2))
    assert store.get().admin.pin == "4321"


def test_subtitle_languages_are_checked():
    import pytest
    from pydantic import ValidationError

    from rewind.config import OpenSubtitlesConfig

    assert OpenSubtitlesConfig(languages=["es", "fr"]).languages == ["es", "fr"]
    with pytest.raises(ValidationError):
        OpenSubtitlesConfig(languages=["klingon"])


def test_subtitle_languages_default_to_the_interface_language():
    from rewind.config import Config, GeneralConfig

    # Nobody's personal choice by default: the interface language.
    assert Config().opensubtitles.languages == []
    assert Config().subtitle_languages == ["fr"]
    assert Config(general=GeneralConfig(language="pt-BR")).subtitle_languages == ["pt"]
    assert Config(general=GeneralConfig(language="xx")).subtitle_languages == []
    cfg = Config()
    cfg.opensubtitles.languages = ["ja", "en"]
    assert cfg.subtitle_languages == ["ja", "en"]


def test_embedded_subtitle_tags_cover_every_language():
    from rewind.library.transcoder import SUB_LANGS

    assert SUB_LANGS["fre"] == SUB_LANGS["fra"] == SUB_LANGS["fr"] == "fr"
    assert SUB_LANGS["jpn"] == "ja" and SUB_LANGS["chi"] == "zh"


def test_admin_knows_the_same_subtitle_languages():
    import re
    from pathlib import Path

    from rewind.config import SUBTITLE_LANGUAGES

    helpers = Path(__file__).parents[2] / "frontend/src/admin/helpers.ts"
    block = re.search(r"SUBTITLE_CODES = \[(.*?)\]", helpers.read_text(), re.S)
    assert block, "SUBTITLE_CODES not found in admin/helpers.ts"
    assert sorted(re.findall(r"'([a-z]{2})'", block.group(1))) == sorted(SUBTITLE_LANGUAGES)
