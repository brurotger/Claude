"""Regera só o áudio de um episódio já publicado, a partir do roteiro salvo em
texto — sem chamar o Claude de novo (zero custo extra). Útil depois de ajustes
no motor de voz, ritmo, pausas etc., quando o texto do episódio não muda.

Uso:
    python regenerate_audio.py                    # episódio de hoje (data de Brasília)
    python regenerate_audio.py --date 2026-08-04
"""

import argparse
import json
from datetime import datetime, timedelta, timezone

from config import EPISODES_DIR, EPISODES_INDEX
from make_audio import make_audio
from publish import load_episodes, write_feed, write_index_page

BRT = timezone(timedelta(hours=-3))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--date",
        help="Data do episódio no formato AAAA-MM-DD (padrão: hoje, horário de Brasília)",
    )
    args = parser.parse_args()

    date_str = args.date or datetime.now(BRT).strftime("%Y-%m-%d")
    script_path = EPISODES_DIR / f"ia-hoje-{date_str}.txt"
    if not script_path.exists():
        print(f"[regenerate] roteiro não encontrado: {script_path}")
        return 1

    episodes = load_episodes()
    match = next((e for e in episodes if e["date"] == date_str), None)
    if match is None:
        print(f"[regenerate] nenhum episódio publicado com data {date_str} em {EPISODES_INDEX}")
        return 1

    script = script_path.read_text(encoding="utf-8")
    output = EPISODES_DIR / match["file"]
    duration = make_audio(script, output)

    match["duration"] = round(duration)
    match["size"] = output.stat().st_size

    EPISODES_INDEX.write_text(
        json.dumps(episodes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_feed(episodes)
    write_index_page(episodes)
    print(f"[regenerate] áudio de {date_str} regenerado: {duration/60:.1f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
