"""Agente 3: converte o roteiro em áudio (MP3) com vozes neurais em pt-BR.

Cada fala é sintetizada com a voz do personagem correspondente via edge-tts
(gratuito) e os trechos são unidos com ffmpeg, com uma pequena pausa entre falas.
"""

import asyncio
import re
import subprocess
import tempfile
from pathlib import Path

import edge_tts

from config import SPEAKERS

LINE_RE = re.compile(r"^([A-ZÀ-Ü]+)\s*:\s*(.+)$")

# Parâmetros de áudio do edge-tts (24 kHz mono); a pausa usa os mesmos
SAMPLE_RATE = 24000
PAUSE_SECONDS = 0.45


def parse_script(script: str) -> list[tuple[str, str]]:
    """Extrai (voz, texto) de cada fala do roteiro."""
    lines: list[tuple[str, str]] = []
    for raw in script.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        m = LINE_RE.match(raw)
        if m and m.group(1) in SPEAKERS:
            lines.append((SPEAKERS[m.group(1)], m.group(2).strip()))
        elif lines:
            # continuação de fala quebrada em várias linhas
            voice, text = lines[-1]
            lines[-1] = (voice, text + " " + raw)
    if not lines:
        raise ValueError("Nenhuma fala reconhecida no roteiro.")
    return lines


async def _synthesize_line(text: str, voice: str, out_path: Path) -> None:
    communicate = edge_tts.Communicate(text, voice, rate="+4%")
    await communicate.save(str(out_path))


def _make_silence(path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"anullsrc=r={SAMPLE_RATE}:cl=mono",
            "-t", str(PAUSE_SECONDS), "-c:a", "libmp3lame", "-b:a", "48k",
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
        silence = tmp_dir / "silence.mp3"
        _make_silence(silence)

        async def synth_all():
            # síntese sequencial: evita bloqueio por excesso de conexões
            for i, (voice, text) in enumerate(lines):
                await _synthesize_line(text, voice, tmp_dir / f"line_{i:04d}.mp3")

        asyncio.run(synth_all())

        concat_list = tmp_dir / "list.txt"
        entries = []
        for i in range(len(lines)):
            entries.append(f"file 'line_{i:04d}.mp3'")
            if i < len(lines) - 1:
                entries.append("file 'silence.mp3'")
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
