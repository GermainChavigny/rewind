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
