"""'Test' buttons of the phone admin: one small real request per service, with
the settings as typed (not yet saved), answering ok + a short French message.
Also lists the models an AI provider offers."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import httpx

from rewind import __version__
from rewind.config import AdvisorProvider, Config, IndexerConfig
from rewind.library.advisor import AdvisorError, Provider
from rewind.library.sources import Tmdb
from rewind.library.subtitles import OpenSubtitles

TIMEOUT = 10


def _result(ok: bool, message: str) -> dict:
    return {"ok": ok, "message": message}


def _status_message(resp: httpx.Response) -> str:
    if resp.status_code in (401, 403):
        return "Clé refusée : vérifiez-la (copier-coller complet, sans espace)."
    if resp.status_code == 404:
        return "Adresse introuvable."
    if resp.status_code == 429:
        return "Trop de requêtes : réessayez dans une minute."
    return f"Erreur {resp.status_code}."


def check_tmdb(cfg: Config, http: httpx.Client) -> dict:
    if not cfg.tmdb.api_key:
        return _result(False, "Aucune clé.")
    try:
        resp = http.get(
            f"{Tmdb.BASE}/configuration", params={"api_key": cfg.tmdb.api_key}, timeout=TIMEOUT
        )
    except httpx.HTTPError:
        return _result(False, "TMDB ne répond pas (connexion Internet ?).")
    if resp.status_code == 200:
        return _result(True, "TMDB répond : la clé fonctionne.")
    return _result(False, _status_message(resp))


def check_opensubtitles(cfg: Config, http: httpx.Client) -> dict:
    os_cfg = cfg.opensubtitles
    if not os_cfg.api_key:
        return _result(False, "Aucune clé.")
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
                extra = f" ({left} téléchargements par jour)" if left else ""
                return _result(True, f"Clé et compte acceptés{extra}.")
            if resp.status_code == 401:
                return _result(False, "Identifiant ou mot de passe refusé.")
            return _result(False, _status_message(resp))
        resp = http.get(f"{OpenSubtitles.BASE}/infos/formats", headers=headers, timeout=TIMEOUT)
    except (httpx.HTTPError, ValueError):
        return _result(False, "OpenSubtitles ne répond pas.")
    if resp.status_code == 200:
        return _result(True, "La clé fonctionne. Ajoutez votre compte pour télécharger.")
    return _result(False, _status_message(resp))


def check_indexer(ix: IndexerConfig, http: httpx.Client) -> dict:
    url = f"{ix.url.rstrip('/')}/api/v2.0/indexers/{ix.indexer}/results/torznab/api"
    try:
        resp = http.get(url, params={"apikey": ix.api_key, "t": "caps"}, timeout=TIMEOUT)
    except httpx.HTTPError:
        return _result(False, "Jackett ne répond pas à cette adresse. Est-il démarré ?")
    if resp.status_code != 200:
        return _result(False, _status_message(resp))
    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError:
        return _result(False, "Réponse inattendue : est-ce bien Jackett ?")
    if root.tag == "error":
        return _result(False, f"Jackett : {root.get('description') or 'erreur'}.")
    if ix.indexer == "all" and (count := _configured_indexers(ix, http)) == 0:
        # Pre-installed Jackett: the key works but no site was added yet.
        return _result(
            False,
            "Jackett répond, mais aucun site n'est ajouté : ouvrez Jackett et "
            "cliquez sur « + Add indexer ».",
        )
    sites = f" ({count} site{'s' if count and count > 1 else ''})" if count else ""
    return _result(True, f"Jackett répond : la clé fonctionne{sites}.")


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


def check_advisor(p: AdvisorProvider, http: httpx.Client) -> dict:
    provider = Provider(p, http)
    provider.RETRIES = 0
    prompt = 'Answer with this exact JSON and nothing else: {"ok": true}'
    try:
        text = provider._call(prompt)  # one plain request, no recommendation parsing
    except AdvisorError as err:
        return _result(False, str(err).split(": ", 1)[-1])
    except Exception as err:  # _Transient and friends
        return _result(False, f"Indisponible : {err}")
    if "ok" in text.lower():
        return _result(True, f"{p.name} répond : la clé et le modèle fonctionnent.")
    return _result(False, "Réponse inattendue du modèle.")


def check_power(cfg: Config, http: httpx.Client) -> dict:
    host = cfg.power.shelly_host
    if not host:
        return _result(False, "Aucune adresse.")
    try:
        resp = http.get(
            f"http://{host}/rpc/Switch.GetStatus",
            params={"id": cfg.power.shelly_switch_id},
            timeout=5,
        )
        resp.raise_for_status()
        on = bool(resp.json()["output"])
    except (httpx.HTTPError, KeyError, ValueError):
        return _result(False, "La prise ne répond pas à cette adresse.")
    return _result(True, f"Prise trouvée : elle est {'allumée' if on else 'éteinte'}.")


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
