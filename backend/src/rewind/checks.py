"""'Test' buttons of the phone admin: one small real request per service, with
the settings as typed (not yet saved), answering ok + a short message in the
interface language. Also lists the models an AI provider offers."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from rewind import __version__
from rewind.config import AdvisorProvider, Config, IndexerConfig
from rewind.library.advisor import AdvisorError, Provider
from rewind.library.sources import Tmdb
from rewind.library.subtitles import OpenSubtitles

TIMEOUT = 10


# Messages: id → (English, French). Other languages fall back to English.
MESSAGES: dict[str, tuple[str, str]] = {
    "refused": (
        "Key refused: check it (full copy and paste, no spaces).",
        "Clé refusée : vérifiez-la (copier-coller complet, sans espace).",
    ),
    "not_found": ("Address not found.", "Adresse introuvable."),
    "too_many": (
        "Too many requests: try again in a minute.",
        "Trop de requêtes : réessayez dans une minute.",
    ),
    "error": ("Error {code}.", "Erreur {code}."),
    "no_key": ("No key.", "Aucune clé."),
    "no_address": ("No address.", "Aucune adresse."),
    "tmdb_down": (
        "TMDB is not responding (Internet connection?).",
        "TMDB ne répond pas (connexion Internet ?).",
    ),
    "tmdb_ok": ("TMDB answers: the key works.", "TMDB répond : la clé fonctionne."),
    "os_account_ok": ("Key and account accepted{extra}.", "Clé et compte acceptés{extra}."),
    "os_per_day": (" ({n} downloads per day)", " ({n} téléchargements par jour)"),
    "os_login": ("Username or password refused.", "Identifiant ou mot de passe refusé."),
    "os_down": ("OpenSubtitles is not responding.", "OpenSubtitles ne répond pas."),
    "os_key_ok": (
        "The key works. Add your account to download.",
        "La clé fonctionne. Ajoutez votre compte pour télécharger.",
    ),
    "jackett_down": (
        "Jackett is not responding at this address. Is it running?",
        "Jackett ne répond pas à cette adresse. Est-il démarré ?",
    ),
    "jackett_odd": (
        "Unexpected answer: is it really Jackett?",
        "Réponse inattendue : est-ce bien Jackett ?",
    ),
    "jackett_error": ("Jackett: {error}.", "Jackett : {error}."),
    "jackett_no_sites": (
        "Jackett answers, but no site is added: open Jackett and click “+ Add indexer”.",
        "Jackett répond, mais aucun site n'est ajouté : ouvrez Jackett et "
        "cliquez sur « + Add indexer ».",
    ),
    "jackett_sites": (" ({n} sites)", " ({n} sites)"),
    "jackett_site": (" (1 site)", " (1 site)"),
    "jackett_ok": (
        "Jackett answers: the key works{sites}.",
        "Jackett répond : la clé fonctionne{sites}.",
    ),
    "ai_unavailable": ("Unavailable: {error}", "Indisponible : {error}"),
    "ai_ok": (
        "{name} answers: the key and the model work.",
        "{name} répond : la clé et le modèle fonctionnent.",
    ),
    "ai_odd": ("Unexpected answer from the model.", "Réponse inattendue du modèle."),
    "plug_down": (
        "The plug is not responding at this address.",
        "La prise ne répond pas à cette adresse.",
    ),
    "plug_on": ("Plug found: it is on.", "Prise trouvée : elle est allumée."),
    "plug_off": ("Plug found: it is off.", "Prise trouvée : elle est éteinte."),
}


def msg(lang: str, key: str, **values: object) -> str:
    en, fr = MESSAGES[key]
    return (fr if lang == "fr" else en).format(**values)


def _result(ok: bool, message: str) -> dict:
    return {"ok": ok, "message": message}


def _status_message(resp: httpx.Response, lang: str) -> str:
    if resp.status_code in (401, 403):
        return msg(lang, "refused")
    if resp.status_code == 404:
        return msg(lang, "not_found")
    if resp.status_code == 429:
        return msg(lang, "too_many")
    return msg(lang, "error", code=resp.status_code)


def check_tmdb(cfg: Config, http: httpx.Client) -> dict:
    lang = cfg.ui_language
    if not cfg.tmdb.api_key:
        return _result(False, msg(lang, "no_key"))
    try:
        resp = http.get(
            f"{Tmdb.BASE}/configuration", params={"api_key": cfg.tmdb.api_key}, timeout=TIMEOUT
        )
    except httpx.HTTPError:
        return _result(False, msg(lang, "tmdb_down"))
    if resp.status_code == 200:
        return _result(True, msg(lang, "tmdb_ok"))
    return _result(False, _status_message(resp, lang))


def check_opensubtitles(cfg: Config, http: httpx.Client) -> dict:
    os_cfg = cfg.opensubtitles
    lang = cfg.ui_language
    if not os_cfg.api_key:
        return _result(False, msg(lang, "no_key"))
    headers = {
        "Api-Key": os_cfg.api_key,
        "User-Agent": f"rewind v{__version__}",
        "Accept": "application/json",
    }
    try:
        if os_cfg.username and os_cfg.password:
            resp = http.post(
                f"{OpenSubtitles.BASE}/login",
                headers=headers,
                json={"username": os_cfg.username, "password": os_cfg.password},
                timeout=TIMEOUT,
            )
            if resp.status_code == 200:
                left = (resp.json().get("user") or {}).get("allowed_downloads")
                extra = msg(lang, "os_per_day", n=left) if left else ""
                return _result(True, msg(lang, "os_account_ok", extra=extra))
            if resp.status_code == 401:
                return _result(False, msg(lang, "os_login"))
            return _result(False, _status_message(resp, lang))
        resp = http.get(f"{OpenSubtitles.BASE}/infos/formats", headers=headers, timeout=TIMEOUT)
    except (httpx.HTTPError, ValueError):
        return _result(False, msg(lang, "os_down"))
    if resp.status_code == 200:
        return _result(True, msg(lang, "os_key_ok"))
    return _result(False, _status_message(resp, lang))


def check_indexer(ix: IndexerConfig, http: httpx.Client, lang: str = "en") -> dict:
    url = f"{ix.url.rstrip('/')}/api/v2.0/indexers/{ix.indexer}/results/torznab/api"
    try:
        resp = http.get(url, params={"apikey": ix.api_key, "t": "caps"}, timeout=TIMEOUT)
    except httpx.HTTPError:
        return _result(False, msg(lang, "jackett_down"))
    if resp.status_code != 200:
        return _result(False, _status_message(resp, lang))
    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError:
        return _result(False, msg(lang, "jackett_odd"))
    if root.tag == "error":
        return _result(False, msg(lang, "jackett_error", error=root.get("description") or "error"))
    if ix.indexer == "all" and (count := _configured_indexers(ix, http)) == 0:
        # Pre-installed Jackett: the key works but no site was added yet.
        return _result(False, msg(lang, "jackett_no_sites"))
    sites = msg(lang, "jackett_sites", n=count) if count and count > 1 else ""
    if count == 1:
        sites = msg(lang, "jackett_site")
    return _result(True, msg(lang, "jackett_ok", sites=sites))


def _configured_indexers(ix: IndexerConfig, http: httpx.Client) -> int | None:
    """How many sites Jackett has (None: could not tell)."""
    url = f"{ix.url.rstrip('/')}/api/v2.0/indexers/all/results/torznab/api"
    try:
        resp = http.get(
            url,
            params={"apikey": ix.api_key, "t": "indexers", "configured": "true"},
            timeout=TIMEOUT,
        )
        root = ET.fromstring(resp.content)
    except (httpx.HTTPError, ET.ParseError):
        return None
    if root.tag != "indexers":
        return None
    return len(root.findall("indexer"))


def check_advisor(p: AdvisorProvider, http: httpx.Client, lang: str = "en") -> dict:
    provider = Provider(p, http)
    provider.RETRIES = 0
    prompt = 'Answer with this exact JSON and nothing else: {"ok": true}'
    try:
        text = provider._call(prompt)  # one plain request, no recommendation parsing
    except AdvisorError as err:
        return _result(False, str(err).split(": ", 1)[-1])
    except Exception as err:  # _Transient and friends
        return _result(False, msg(lang, "ai_unavailable", error=err))
    if "ok" in text.lower():
        return _result(True, msg(lang, "ai_ok", name=p.name))
    return _result(False, msg(lang, "ai_odd"))


def check_power(cfg: Config, http: httpx.Client) -> dict:
    host = cfg.power.shelly_host
    lang = cfg.ui_language
    if not host:
        return _result(False, msg(lang, "no_address"))
    try:
        resp = http.get(
            f"http://{host}/rpc/Switch.GetStatus",
            params={"id": cfg.power.shelly_switch_id},
            timeout=5,
        )
        resp.raise_for_status()
        on = bool(resp.json()["output"])
    except (httpx.HTTPError, KeyError, ValueError):
        return _result(False, msg(lang, "plug_down"))
    return _result(True, msg(lang, "plug_on" if on else "plug_off"))


def list_models(p: AdvisorProvider, http: httpx.Client) -> list[str]:
    """Model ids the provider offers (text generation only for Gemini)."""
    if p.kind == "gemini":
        base = (p.base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        resp = http.get(
            f"{base}/models", headers={"x-goog-api-key": p.api_key}, params={"pageSize": 200},
            timeout=TIMEOUT,
        )  # fmt: skip
        resp.raise_for_status()
        return sorted(
            m["name"].removeprefix("models/")
            for m in resp.json().get("models", [])
            if "generateContent" in m.get("supportedGenerationMethods", [])
        )
    headers = {"Authorization": f"Bearer {p.api_key}"} if p.api_key else {}
    resp = http.get(f"{(p.base_url or '').rstrip('/')}/models", headers=headers, timeout=TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("data", data.get("models", [])) if isinstance(data, dict) else data
    return sorted({m["id"] if isinstance(m, dict) else str(m) for m in items})
