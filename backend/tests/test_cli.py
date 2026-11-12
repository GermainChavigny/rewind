from rewind.cli import main
from rewind.config import Config, ConfigStore


def test_config_get(paths, monkeypatch, capsys):
    monkeypatch.setenv("REWIND_CONFIG_DIR", str(paths.config))
    cfg = Config()
    cfg.display.mode = "720x576"
    cfg.audio.av_offset_ms = 200
    ConfigStore(paths.config / "config.toml").save(cfg)
    for key, expected in [
        ("display.mode", "720x576"),
        ("audio.av_offset_ms", "200"),
        ("display.output", ""),
        ("nope.x", ""),
    ]:
        assert main(["config-get", key]) == 0
        assert capsys.readouterr().out.strip() == expected


def test_setup_indexer_adds_then_updates(paths, monkeypatch, capsys):
    monkeypatch.setenv("REWIND_CONFIG_DIR", str(paths.config))
    monkeypatch.setenv("REWIND_DATA_DIR", str(paths.data))
    store = ConfigStore(paths.config / "config.toml")
    assert main(["setup-indexer", "--api-key", "k1"]) == 0
    [ix] = store.get().indexers
    assert (ix.url, ix.api_key, ix.systemd_unit) == (
        "http://127.0.0.1:9117",
        "k1",
        "jackett.service",
    )
    # Re-run (reinstall): same indexer, new key, no duplicate.
    assert main(["setup-indexer", "--api-key", "k2", "--url", "http://127.0.0.1:9117/"]) == 0
    [ix] = store.get().indexers
    assert ix.api_key == "k2"
    assert "key updated" in capsys.readouterr().out
