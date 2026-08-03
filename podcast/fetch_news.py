"""Agente 1: busca notícias de IA em fontes confiáveis e remove repetidas.

Coleta itens dos feeds RSS configurados, filtra pela janela de tempo,
descarta tudo que já apareceu em episódios anteriores (histórico) e
devolve uma lista de candidatas para o roteirista.
"""

import hashlib
import json
import re
import time
from datetime import datetime, timedelta, timezone
from html import unescape

import feedparser
import requests

from config import (
    HISTORY_FILE,
    HISTORY_RETENTION_DAYS,
    MAX_CANDIDATES,
    NEWS_SOURCES,
    NEWS_WINDOW_HOURS,
)

USER_AGENT = "Mozilla/5.0 (compatible; IAHojePodcast/1.0; +https://github.com)"


def _strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _normalize_title(title: str) -> str:
    """Chave de deduplicação tolerante: minúsculas, sem pontuação/espaços."""
    return re.sub(r"[^a-z0-9]", "", title.lower())


def _item_key(url: str, title: str) -> str:
    base = (url or "") + "|" + _normalize_title(title)
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


def load_history() -> dict:
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    return {"items": {}}


def save_history(history: dict) -> None:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=HISTORY_RETENTION_DAYS)).isoformat()
    history["items"] = {
        k: v for k, v in history["items"].items() if v.get("seen_at", "") >= cutoff
    }
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _entry_datetime(entry) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            return datetime.fromtimestamp(time.mktime(parsed), tz=timezone.utc)
    return None


def fetch_candidates() -> list[dict]:
    """Retorna notícias novas (não repetidas) das últimas NEWS_WINDOW_HOURS horas."""
    history = load_history()
    seen_keys = set(history["items"].keys())
    seen_titles = {v.get("norm_title") for v in history["items"].values()}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=NEWS_WINDOW_HOURS)

    candidates: list[dict] = []
    batch_titles: set[str] = set()

    for source in NEWS_SOURCES:
        try:
            resp = requests.get(
                source["url"], headers={"User-Agent": USER_AGENT}, timeout=20
            )
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as exc:  # fonte fora do ar não derruba o pipeline
            print(f"[fetch] aviso: falha ao ler {source['name']}: {exc}")
            continue

        for entry in feed.entries[:20]:
            title = _strip_html(getattr(entry, "title", ""))
            url = getattr(entry, "link", "")
            if not title or not url:
                continue

            published = _entry_datetime(entry)
            if published is None or published < cutoff:
                continue

            key = _item_key(url, title)
            norm = _normalize_title(title)
            # repetida se já saiu em episódio anterior ou já entrou nesta rodada
            if key in seen_keys or norm in seen_titles or norm in batch_titles:
                continue

            summary = _strip_html(
                getattr(entry, "summary", "") or getattr(entry, "description", "")
            )[:600]

            candidates.append(
                {
                    "key": key,
                    "norm_title": norm,
                    "title": title,
                    "summary": summary,
                    "url": url,
                    "source": source["name"],
                    "published": published.isoformat(),
                }
            )
            batch_titles.add(norm)

    # mais recentes primeiro; limita o volume enviado ao roteirista
    candidates.sort(key=lambda c: c["published"], reverse=True)
    candidates = candidates[:MAX_CANDIDATES]
    print(f"[fetch] {len(candidates)} notícias novas encontradas")
    return candidates


def mark_as_reported(candidates: list[dict]) -> None:
    """Grava as candidatas no histórico para nunca repetir em dias seguintes."""
    history = load_history()
    now = datetime.now(timezone.utc).isoformat()
    for c in candidates:
        history["items"][c["key"]] = {
            "title": c["title"],
            "norm_title": c["norm_title"],
            "url": c["url"],
            "source": c["source"],
            "seen_at": now,
        }
    save_history(history)


if __name__ == "__main__":
    for c in fetch_candidates():
        print(f"- [{c['source']}] {c['title']} ({c['url']})")
