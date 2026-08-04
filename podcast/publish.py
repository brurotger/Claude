"""Publicação: mantém o índice de episódios, o feed RSS do podcast e a página web.

O feed (docs/feed.xml) é servido pelo GitHub Pages e pode ser assinado em
qualquer aplicativo de podcast (AntennaPod, Pocket Casts, Apple Podcasts...).
"""

import json
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

from config import (
    EPISODES_DIR,
    EPISODES_INDEX,
    DOCS_DIR,
    MAX_EPISODES_KEPT,
    PODCAST_DESCRIPTION,
    PODCAST_LANGUAGE,
    PODCAST_TITLE,
    SITE_BASE_URL,
)


def load_episodes() -> list[dict]:
    if EPISODES_INDEX.exists():
        return json.loads(EPISODES_INDEX.read_text(encoding="utf-8"))
    return []


def register_episode(
    date_str: str,
    title: str,
    filename: str,
    duration_seconds: float,
    size_bytes: int,
    news: list[dict],
) -> None:
    episodes = load_episodes()
    episodes = [e for e in episodes if e["date"] != date_str]  # evita duplicar se já existir
    episodes.insert(
        0,
        {
            "date": date_str,
            "title": title,
            "file": filename,
            "duration": round(duration_seconds),
            "size": size_bytes,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "news": [
                {"title": n["title"], "source": n["source"], "url": n["url"]}
                for n in news
            ],
        },
    )

    # remove episódios antigos (arquivo e registro)
    for old in episodes[MAX_EPISODES_KEPT:]:
        old_file = EPISODES_DIR / old["file"]
        if old_file.exists():
            old_file.unlink()
            print(f"[publish] episódio antigo removido: {old['file']}")
    episodes = episodes[:MAX_EPISODES_KEPT]

    EPISODES_INDEX.parent.mkdir(parents=True, exist_ok=True)
    EPISODES_INDEX.write_text(
        json.dumps(episodes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_feed(episodes)
    write_index_page(episodes)


def _fmt_duration(seconds: int) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def write_feed(episodes: list[dict]) -> None:
    items = []
    for ep in episodes:
        audio_url = f"{SITE_BASE_URL}/episodes/{ep['file']}"
        pub_date = format_datetime(datetime.fromisoformat(ep["published_at"]))
        sources_html = "".join(
            f"<li><a href=\"{escape(n['url'])}\">{escape(n['title'])}</a>"
            f" ({escape(n['source'])})</li>"
            for n in ep["news"]
        )
        description = escape(
            f"Notícias de IA do dia {ep['date']}.<ul>{sources_html}</ul>"
        )
        items.append(f"""
    <item>
      <title>{escape(ep['title'])}</title>
      <description>{description}</description>
      <enclosure url="{escape(audio_url)}" length="{ep['size']}" type="audio/mpeg"/>
      <guid isPermaLink="false">{escape(ep['file'])}</guid>
      <pubDate>{pub_date}</pubDate>
      <itunes:duration>{_fmt_duration(ep['duration'])}</itunes:duration>
    </item>""")

    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{escape(PODCAST_TITLE)}</title>
    <link>{escape(SITE_BASE_URL)}</link>
    <atom:link href="{escape(SITE_BASE_URL)}/feed.xml" rel="self" type="application/rss+xml"/>
    <description>{escape(PODCAST_DESCRIPTION)}</description>
    <language>{PODCAST_LANGUAGE}</language>
    <itunes:author>IA Hoje (gerado automaticamente)</itunes:author>
    <itunes:explicit>false</itunes:explicit>
    {''.join(items)}
  </channel>
</rss>
"""
    (DOCS_DIR / "feed.xml").write_text(feed, encoding="utf-8")
    print(f"[publish] feed.xml atualizado ({len(episodes)} episódios)")


def write_index_page(episodes: list[dict]) -> None:
    rows = []
    for ep in episodes:
        sources = "".join(
            f"<li><a href=\"{escape(n['url'])}\">{escape(n['title'])}</a>"
            f" <small>({escape(n['source'])})</small></li>"
            for n in ep["news"]
        )
        rows.append(f"""
    <article>
      <h2>{escape(ep['title'])}</h2>
      <audio controls preload="none" src="episodes/{escape(ep['file'])}"></audio>
      <p><small>{_fmt_duration(ep['duration'])} · {ep['size'] // 1024} KB ·
        <a href="episodes/{escape(ep['file'])}" download>baixar MP3</a></small></p>
      <details><summary>Fontes deste episódio</summary><ul>{sources}</ul></details>
    </article>""")

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(PODCAST_TITLE)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 720px; margin: 2rem auto;
           padding: 0 1rem; line-height: 1.5; color: #222; }}
    h1 {{ font-size: 1.5rem; }}
    article {{ border-bottom: 1px solid #ddd; padding: 1rem 0; }}
    audio {{ width: 100%; }}
    .feed {{ background: #f4f1ea; padding: .75rem 1rem; border-radius: 8px; }}
    code {{ background: #eee; padding: 0 .3rem; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>🎙️ {escape(PODCAST_TITLE)}</h1>
  <p>{escape(PODCAST_DESCRIPTION)}</p>
  <p class="feed">📡 Assine no seu app de podcast com este feed:<br>
    <code>{escape(SITE_BASE_URL)}/feed.xml</code></p>
  {''.join(rows) if rows else '<p>Nenhum episódio ainda — o primeiro sai amanhã de manhã!</p>'}
</body>
</html>
"""
    (DOCS_DIR / "index.html").write_text(html, encoding="utf-8")
    print("[publish] index.html atualizado")
