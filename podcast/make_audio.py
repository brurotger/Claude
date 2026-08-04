"""Agente 3: converte o roteiro em áudio (MP3) com vozes neurais em pt-BR.

Cada fala é sintetizada com a voz do personagem correspondente via edge-tts
(gratuito), com uma pequena variação aleatória de ritmo/entonação por fala e
pausas de duração levemente variável entre falas — sem isso, a leitura fica
com uma cadência perfeitamente uniforme e soa mais robótica. Os trechos são
então unidos com ffmpeg.
"""

import asyncio
import random
import re
import subprocess
import tempfile
from pathlib import Path

import edge_tts

from config import SPEAKERS

LINE_RE = re.compile(r"^([A-ZÀ-Ü]+)\s*:\s*(.+)$")

# Parâmetros de áudio do edge-tts (24 kHz mono)
SAMPLE_RATE = 24000

# Pausa entre falas: intervalo (segundos) sorteado a cada troca de personagem,
# em vez de um valor fixo — cadência uniforme é um dos motivos do efeito robótico.
PAUSE_RANGE = (0.35, 0.70)
_PAUSE_STEP = 0.05  # granularidade dos clipes de silêncio pré-gerados

# Variação aleatória de ritmo/tom aplicada em cima da linha de base de cada
# personagem (definida em config.SPEAKERS), fala a fala.
RATE_JITTER = 4   # pontos percentuais (ex.: base 0 -> entre -4% e +4%)
PITCH_JITTER = 3  # Hz


def parse_script(script: str) -> list[tuple[str, str]]:
    """Extrai (personagem, texto) de cada fala do roteiro."""
    lines: list[tuple[str, str]] = []
    for raw in script.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        m = LINE_RE.match(raw)
        if m and m.group(1) in SPEAKERS:
            lines.append((m.group(1), m.group(2).strip()))
        elif lines:
            # continuação de fala quebrada em várias linhas
            speaker, text = lines[-1]
            lines[-1] = (speaker, text + " " + raw)
    if not lines:
        raise ValueError("Nenhuma fala reconhecida no roteiro.")
    return lines


def _jittered_params(speaker: str) -> tuple[str, str]:
    """Ritmo e tom de voz para esta fala: base do personagem + variação aleatória."""
    base = SPEAKERS[speaker]
    rate = base["rate"] + random.uniform(-RATE_JITTER, RATE_JITTER)
    pitch = base["pitch"] + random.uniform(-PITCH_JITTER, PITCH_JITTER)
    return f"{rate:+.0f}%", f"{pitch:+.0f}Hz"


# Se a voz configurada em SPEAKERS não existir no servidor (nome mudou, região
# não suporta etc.), cai para uma voz clássica e estável em vez de quebrar o
# episódio inteiro por causa de uma fala.
FALLBACK_VOICE = "pt-BR-FranciscaNeural"


async def _synthesize_line(text: str, speaker: str, out_path: Path) -> None:
    rate, pitch = _jittered_params(speaker)
    voice = SPEAKERS[speaker]["voice"]
    try:
        await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(
            str(out_path)
        )
    except Exception as exc:
        if voice == FALLBACK_VOICE:
            raise
        print(f"[audio] aviso: voz '{voice}' falhou ({exc}); usando fallback")
        await edge_tts.Communicate(
            text, FALLBACK_VOICE, rate=rate, pitch=pitch
        ).save(str(out_path))


def _make_silence(path: Path, duration: float) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"anullsrc=r={SAMPLE_RATE}:cl=mono",
            "-t", f"{duration:.2f}", "-c:a", "libmp3lame", "-b:a", "48k",
            str(path),
        ],
        check=True,
    )


def make_audio(script: str, output_mp3: Path) -> float:
    """Gera o MP3 do episódio. Retorna a duração em segundos."""
    lines = parse_script(script)
    print(f"[audio] sintetizando {len(lines)} falas...")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        # pré-gera um pequeno conjunto de clipes de silêncio de durações
        # diferentes, para sortear entre eles (mais barato que gerar um por gap)
        lo, hi = PAUSE_RANGE
        steps = max(1, round((hi - lo) / _PAUSE_STEP))
        silence_durations = [lo + i * (hi - lo) / steps for i in range(steps + 1)]
        silence_files = []
        for i, dur in enumerate(silence_durations):
            path = tmp_dir / f"silence_{i:02d}.mp3"
            _make_silence(path, dur)
            silence_files.append(path.name)

        async def synth_all():
            # síntese sequencial: evita bloqueio por excesso de conexões
            for i, (speaker, text) in enumerate(lines):
                await _synthesize_line(text, speaker, tmp_dir / f"line_{i:04d}.mp3")

        asyncio.run(synth_all())

        concat_list = tmp_dir / "list.txt"
        entries = []
        for i in range(len(lines)):
            entries.append(f"file 'line_{i:04d}.mp3'")
            if i < len(lines) - 1:
                entries.append(f"file '{random.choice(silence_files)}'")
        concat_list.write_text("\n".join(entries), encoding="utf-8")

        output_mp3.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "concat", "-safe", "0", "-i", str(concat_list),
                "-c:a", "libmp3lame", "-b:a", "48k", "-ar", str(SAMPLE_RATE),
                "-ac", "1", str(output_mp3),
            ],
            check=True,
        )

    duration = float(
        subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(output_mp3),
            ],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    print(f"[audio] episódio gerado: {output_mp3.name} ({duration/60:.1f} min)")
    return duration
