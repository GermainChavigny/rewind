"""
Configuration: one `config.toml` file, validated by pydantic models.

The file is meant to be edited from the phone admin UI, but stays readable and
hand-editable. It holds API keys, so it is written with mode 0600.

Secret fields are flagged with `secret()`: the admin API masks them on read and
keeps the stored value when the client sends the mask back unchanged.
"""

from __future__ import annotations

import os
import threading
import tomllib
from pathlib import Path
from typing import Any, Literal

import tomli_w
from pydantic import BaseModel, ConfigDict, Field

MASK = "********"


def secret(default: str = "", **kwargs: Any) -> Any:
    return Field(default=default, json_schema_extra={"secret": True}, **kwargs)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


# --- Sections -----------------------------------------------------------------


class GeneralConfig(_Model):
    language: str = "fr"
    timezone: str | None = None  # None = system timezone


class DisplayConfig(_Model):
    output: str | None = None  # e.g. "HDMI-A-2"; None = auto-detect
    mode: str | None = None  # e.g. "720x576"; None = output's preferred mode
    crt_effects: bool = True


class AudioConfig(_Model):
    # Delay applied to the audio output to compensate for a video path that lags
    # (e.g. an HDMI → SCART converter). Positive = audio later.
    av_offset_ms: int = Field(default=0, ge=-2000, le=2000)
    output_port: str | None = None  # e.g. "analog-output-headphones"


# Remote keymap: action → list of `KeyboardEvent.key` values. The defaults fit
# the HAOBO USB air-mouse remote on an AZERTY layout, plus plain digits.
DEFAULT_KEYMAP: dict[str, list[str]] = {
    "channel_1": ["&", "1"],
    "channel_2": ["é", "2"],
    "channel_3": ['"', "3"],
    "channel_4": ["'", "4"],
    "channel_5": ["(", "5"],
    "channel_6": ["-", "6"],
    "channel_7": ["è", "7"],
    "channel_8": ["_", "8"],
    "channel_9": ["ç", "9"],
    "alarm_toggle": ["à", "0"],
    "alarm_later": ["ArrowUp"],
    "alarm_earlier": ["ArrowDown"],
    "tv_power": ["AudioVolumeMute"],
    "play_pause": ["MediaPlayPause", " "],
    "next": ["MediaTrackNext"],
    "previous": ["MediaTrackPrevious"],
    "seek_forward": ["ArrowRight"],
    "seek_backward": ["ArrowLeft"],
    "volume_up": ["AudioVolumeUp"],
    "volume_down": ["AudioVolumeDown"],
    "darker": ["PageUp"],
    "brighter": ["PageDown"],
}


class RemoteConfig(_Model):
    keys: dict[str, list[str]] = Field(default_factory=lambda: dict(DEFAULT_KEYMAP))


class PowerConfig(_Model):
    """TV power control (the TV is plugged into a smart plug)."""

    provider: Literal["none", "shelly", "fake"] = "none"
    shelly_host: str | None = None
    shelly_switch_id: int = 0


class WeatherConfig(_Model):
    location_name: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class AlarmConfig(_Model):
    step_minutes: int = Field(default=10, ge=1, le=60)
    sound_ramp_s: int = 30  # alarm sound volume 0 → 1
    video_delay_s: int = 20  # before the alarm channel starts fading in
    video_ramp_s: int = 15
    max_duration_s: int = 300


class Channel(_Model):
    """A TV channel. Its position in the list is its number on the remote."""

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    name: str
    show_name: bool = False  # display the name as text next to/instead of the logo
    logo: str | None = None  # logo id, see /api/logos
    kind: Literal["youtube", "library"] = "youtube"
    playlist_id: str | None = None  # YouTube playlist (kind = youtube)
    save_progress: bool = True  # False = always restart (e.g. news)
    alarm: bool = False  # the channel played by the alarm


class LibraryConfig(_Model):
    enabled: bool = True
    download_slots: int = Field(default=3, ge=1, le=10)
    # BitTorrent listen port; the magnet probe uses port + 8.
    torrent_port: int = Field(default=6891, ge=1024, le=65000)


class TmdbConfig(_Model):
    api_key: str = secret()
    language: str = "fr-FR"


class OpenSubtitlesConfig(_Model):
    api_key: str = secret()
    username: str = ""
    password: str = secret()
    languages: list[str] = Field(default_factory=lambda: ["fr", "en"])


class IndexerConfig(_Model):
    """A Torznab indexer (e.g. Jackett)."""

    name: str = "Jackett"
    url: str
    api_key: str = secret()
    indexer: str = "all"
    min_seeders: int = 1
    max_size_gb: float = 6
    timeout_s: float = 30  # Jackett's aggregate can take 20 s+ on slow trackers
    # systemd user unit started when the indexer doesn't answer (e.g. "jackett.service").
    systemd_unit: str | None = None


class AdvisorProvider(_Model):
    """An AI provider for the Movie Advisor. Tried in order; first answer wins."""

    name: str
    kind: Literal["gemini", "openai"] = "openai"  # openai = any OpenAI-compatible API
    base_url: str | None = None
    api_key: str = secret()
    model: str
    json_mode: bool = True


class AdminConfig(_Model):
    pin: str = secret()  # empty = no PIN on the admin API


class Config(_Model):
    general: GeneralConfig = Field(default_factory=GeneralConfig)
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    remote: RemoteConfig = Field(default_factory=RemoteConfig)
    power: PowerConfig = Field(default_factory=PowerConfig)
    weather: WeatherConfig = Field(default_factory=WeatherConfig)
    alarm: AlarmConfig = Field(default_factory=AlarmConfig)
    channels: list[Channel] = Field(default_factory=list, max_length=9)
    library: LibraryConfig = Field(default_factory=LibraryConfig)
    tmdb: TmdbConfig = Field(default_factory=TmdbConfig)
    opensubtitles: OpenSubtitlesConfig = Field(default_factory=OpenSubtitlesConfig)
    indexers: list[IndexerConfig] = Field(default_factory=list)
    advisor: list[AdvisorProvider] = Field(default_factory=list)
    admin: AdminConfig = Field(default_factory=AdminConfig)


# --- Secret masking -------------------------------------------------------------


def _is_secret(model: BaseModel, name: str) -> bool:
    extra = type(model).model_fields[name].json_schema_extra
    return isinstance(extra, dict) and bool(extra.get("secret"))


def masked(config: Config) -> dict:
    """Config as a dict, with non-empty secrets replaced by MASK."""

    def walk(model: BaseModel) -> dict:
        out = {}
        for name in type(model).model_fields:
            value = getattr(model, name)
            if _is_secret(model, name):
                out[name] = MASK if value else ""
            elif isinstance(value, BaseModel):
                out[name] = walk(value)
            elif isinstance(value, list) and value and isinstance(value[0], BaseModel):
                out[name] = [walk(v) for v in value]
            else:
                out[name] = value
        return out

    return walk(config)


def restore_secrets(new: Config, old: Config) -> Config:
    """Put back the stored secret wherever the client sent MASK unchanged."""

    def walk(n: BaseModel, o: BaseModel | None) -> None:
        for name in type(n).model_fields:
            value = getattr(n, name)
            old_value = getattr(o, name, None) if o is not None else None
            if _is_secret(n, name):
                if value == MASK:
                    setattr(n, name, old_value or "")
            elif isinstance(value, BaseModel):
                walk(value, old_value)
            elif isinstance(value, list) and value and isinstance(value[0], BaseModel):
                olds = old_value if isinstance(old_value, list) else []
                for i, item in enumerate(value):
                    walk(item, olds[i] if i < len(olds) else None)

    walk(new, old)
    return new


# --- Storage --------------------------------------------------------------------


class ConfigStore:
    """Loads and atomically saves config.toml; thread-safe."""

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self._config = self._load()

    def _load(self) -> Config:
        if not self.path.exists():
            return Config()
        with open(self.path, "rb") as f:
            return Config.model_validate(tomllib.load(f))

    def get(self) -> Config:
        return self._config

    def save(self, config: Config) -> None:
        data = tomli_w.dumps(config.model_dump(mode="json", exclude_none=True))
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".toml.tmp")
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
            self._config = config
