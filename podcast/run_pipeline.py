"""Orquestrador do pipeline: notícias -> roteiro -> áudio -> publicação.

Uso:
    python podcast/run_pipeline.py            # pipeline completo (precisa de ANTHROPIC_API_KEY)
    python podcast/run_pipeline.py --dry-run  # testa áudio/publicação com roteiro de exemplo
"""

import locale
import sys
from datetime import datetime, timezone, timedelta

from config import EPISODES_DIR, EPISODES_INDEX
from fetch_news import fetch_candidates, mark_as_reported
from make_audio import make_audio
from publish import register_episode
from write_script import write_script

# Horário de Brasília para a data do episódio
BRT = timezone(timedelta(hours=-3))

MONTHS_PT = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]

DRY_RUN_SCRIPT = """\
ANA: Bom dia! Hoje é um episódio de teste do IA Hoje.
MARCOS: Isso mesmo, Ana. Este áudio serve só para verificar que a síntese de voz e a montagem do episódio estão funcionando.
ANA: Perfeito! Então até amanhã com as notícias de verdade.
MARCOS: Até amanhã!
"""


def main(dry_run: bool = False) -> int:
    now = datetime.now(BRT)
    date_iso = now.strftime("%Y-%m-%d")
    date_pt = f"{now.day} de {MONTHS_PT[now.month - 1]} de {now.year}"

    if dry_run:
        candidates = []
        script = DRY_RUN_SCRIPT
        title = f"IA Hoje — teste ({date_pt})"
    else:
        candidates = fetch_candidates()
        if not candidates:
            print("[pipeline] nenhuma notícia nova hoje; episódio não será gerado.")
            return 0
        script = write_script(candidates, date_pt)
        title = f"IA Hoje — {date_pt}"

    filename = f"ia-hoje-{date_iso}.mp3"
    output = EPISODES_DIR / filename
    duration = make_audio(script, output)

    # guarda também o roteiro em texto, para consulta
    (EPISODES_DIR / f"ia-hoje-{date_iso}.txt").write_text(script, encoding="utf-8")

    register_episode(
        date_str=date_iso,
        title=title,
        filename=filename,
        duration_seconds=duration,
        size_bytes=output.stat().st_size,
        news=candidates,
    )

    if not dry_run:
        # só marca como reportadas depois que o episódio saiu com sucesso
        mark_as_reported(candidates)

    print(f"[pipeline] episódio de {date_iso} publicado com sucesso.")
    return 0


if __name__ == "__main__":
    sys.exit(main(dry_run="--dry-run" in sys.argv))
