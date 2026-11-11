"""
Movie Advisor: an AI recommends exactly 3 titles for the chosen criteria.

Providers are tried in order and the first that answers wins (free tiers are
often overloaded). Owned and "forgotten" titles are excluded. Every failure
becomes an AdvisorError with a message that can be shown on screen.
"""

from __future__ import annotations

import json
import logging
import re
import time

import httpx

from rewind.config import AdvisorProvider

log = logging.getLogger(__name__)

_PROMPT = """You are {role}.
Your role is to recommend exactly 3 {things}.
The user owns a personal library and wants recommendations according to the selected criteria.
Do not recommend {things} that appear in the excluded list.
Recommendations should be diverse.
Avoid suggesting three {things} that are too similar.
For each recommendation, write a short synopsis, with no spoiler
(maximum 120 characters) in {language}.

--------------------------------------------------

Selected criteria

{criteria}
{extra}
--------------------------------------------------

{Things} that must NEVER be recommended

{excluded}

--------------------------------------------------

Return ONLY valid JSON.

Schema:

{{
  "recommendations": [
    {{
      "title": "{Thing} title (in {language})",
      "year": 1999,
      "description": "Short synopsis, no spoiler (max 120 characters, {language})"
    }}
  ]
}}

Rules:

- Return exactly 3 recommendations.
- No markdown.
- No explanations outside the JSON.
- No comments.
- The JSON must be valid.
- Do not recommend excluded {things}.
- Prefer critically acclaimed {things}.
- The three {things} should not all come from the same franchise.
- Do not invent titles."""

CRITERIA = {
    "mood": "Mood",
    "pace": "Pace",
    "era": "Era",
    "scale": "Scale",
    "rating": "Rating",
    "length": "Length",
    "theme1": "Theme 1",
    "theme2": "Theme 2",
}

LANGUAGES = {"fr": "French", "en": "English"}

TRANSIENT = {429, 500, 502, 503, 504}


class AdvisorError(Exception):
    """A failure whose message can be shown to the user."""


class _Transient(Exception):
    """Overload / network: retry, then move on to the next provider."""


def build_prompt(
    criteria: dict, excluded: list[str], keywords: str = "", kind: str = "movie", lang: str = "fr"
) -> str:
    series = kind == "series"
    lines = [
        f"{label}: {criteria[key]}"
        for key, label in CRITERIA.items()
        if criteria.get(key) and criteria[key] != "Any"
    ]
    kw = (keywords or "").strip()[:200]
    return _PROMPT.format(
        role="Series Advisor" if series else "Movie Advisor",
        things="TV series" if series else "movies",
        Things="TV series" if series else "Movies",
        Thing="Series" if series else "Movie",
        language=LANGUAGES.get(lang, "English"),
        criteria="\n".join(lines) or "No preference (surprise the user)",
        extra=f"\nAdditional request from the user (take it into account):\n{kw}\n" if kw else "",
        excluded="\n".join(excluded) or "(none)",
    )


def parse(text: str) -> list[dict]:
    """The recommendations of a model answer (bare JSON, or JSON in a ``` block)."""
    match = re.search(r"\{.*\}", str(text), re.DOTALL)
    for candidate in (text, match.group(0) if match else None):
        if not candidate:
            continue
        try:
            data = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        recs = data.get("recommendations") if isinstance(data, dict) else None
        if isinstance(recs, list):
            return [r for r in recs if isinstance(r, dict) and r.get("title")]
    return []


def clip(text: str | None, limit: int = 140) -> str:
    """Shorten a synopsis on a word boundary (models overshoot 120 chars by ~10 %)."""
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"


def _error_message(resp: httpx.Response) -> str:
    try:
        body = resp.json()
        err = body.get("error") if isinstance(body, dict) else None
        message = err.get("message") if isinstance(err, dict) else (err or body.get("message"))
    except ValueError:
        message = None
    # Google appends "Learn more…" links; never echo URLs (they may carry keys).
    return str(message or f"error {resp.status_code}").split(". Learn more")[0].strip()[:200]


class Provider:
    RETRIES = 2
    BACKOFF_S = 1.5

    def __init__(self, cfg: AdvisorProvider, http: httpx.Client):
        self.cfg = cfg
        self.http = http

    @property
    def name(self) -> str:
        return self.cfg.name

    def available(self) -> bool:
        return bool(self.cfg.api_key and self.cfg.model)

    def recommend(self, prompt: str) -> list[dict]:
        for attempt in range(self.RETRIES + 1):
            try:
                text = self._call(prompt)
            except _Transient as err:
                log.info("advisor %s unavailable (try %d): %s", self.name, attempt + 1, err)
                if attempt < self.RETRIES:
                    time.sleep(self.BACKOFF_S * (attempt + 1))
                    continue
                raise AdvisorError(f"{self.name}: {err}") from err
            recs = parse(text)
            if not recs:
                raise AdvisorError(f"{self.name} returned unreadable JSON")
            return recs[:3]
        raise AdvisorError(f"{self.name}: unavailable")

    def _post(self, url: str, headers: dict, payload: dict) -> dict:
        try:
            resp = self.http.post(url, headers=headers, json=payload, timeout=25)
        except httpx.HTTPError as err:
            raise _Transient(f"network: {type(err).__name__}") from err
        if resp.status_code in TRANSIENT:
            raise _Transient(f"{resp.status_code}: {_error_message(resp)}")
        if resp.status_code != 200:
            raise AdvisorError(f"{self.name}: {_error_message(resp)}")
        try:
            return resp.json()
        except ValueError as err:
            raise AdvisorError(f"{self.name}: unexpected answer") from err

    def _call(self, prompt: str) -> str:
        cfg = self.cfg
        try:
            if cfg.kind == "gemini":
                # The key travels in a header, never in the URL (error messages echo URLs).
                base = cfg.base_url or "https://generativelanguage.googleapis.com/v1beta"
                data = self._post(
                    f"{base.rstrip('/')}/models/{cfg.model}:generateContent",
                    {"x-goog-api-key": cfg.api_key},
                    {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "responseMimeType": "application/json",
                            "temperature": 1.0,
                        },
                    },
                )
                return data["candidates"][0]["content"]["parts"][0]["text"]
            payload: dict = {
                "model": cfg.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 1.0,
            }
            if cfg.json_mode:
                payload["response_format"] = {"type": "json_object"}
            data = self._post(
                f"{(cfg.base_url or '').rstrip('/')}/chat/completions",
                {"Authorization": f"Bearer {cfg.api_key}"},
                payload,
            )
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as err:
            raise AdvisorError(f"{self.name}: unexpected answer") from err


class Advisor:
    def __init__(self, providers: list[AdvisorProvider], http: httpx.Client):
        self.providers = [Provider(p, http) for p in providers]

    def available(self) -> bool:
        return any(p.available() for p in self.providers)

    def recommend(self, prompt: str) -> list[dict]:
        last: AdvisorError | None = None
        for provider in self.providers:
            if not provider.available():
                continue
            try:
                recs = provider.recommend(prompt)
                log.info("advisor: answer from %s", provider.name)
                return recs
            except AdvisorError as err:
                last = err
                log.info("advisor: %s failed (%s), next provider", provider.name, err)
        raise last or AdvisorError("no advisor provider configured")
