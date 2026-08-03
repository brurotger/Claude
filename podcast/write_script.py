"""Agente 2: transforma as notícias em um roteiro de diálogo em português.

Escreve uma conversa natural entre Marcos (especialista) e Ana (entusiasta),
em linguagem acessível, sempre citando a fonte de cada notícia.

Dois modos de autenticação, escolhidos automaticamente:
- ANTHROPIC_API_KEY definida      -> API da Anthropic (Claude Opus 5)
- CLAUDE_CODE_OAUTH_TOKEN definida -> Claude Code CLI usando a assinatura
                                      Pro/Max do claude.ai (custo zero extra)
"""

import os
import subprocess

import anthropic

SYSTEM_PROMPT = """\
Você é roteirista de um podcast diário brasileiro chamado "IA Hoje", que resume \
as novidades do mundo da inteligência artificial em linguagem simples.

O episódio é um diálogo entre duas pessoas:
- MARCOS: especialista em IA. Explica os conceitos com clareza, dá contexto e \
opinião técnica, mas sem jargão — quando um termo técnico é inevitável, ele \
explica em uma frase o que significa.
- ANA: entusiasta curiosa. Faz as perguntas que uma pessoa leiga faria, reage \
com naturalidade, pede exemplos do dia a dia e puxa a conversa adiante.

Regras do roteiro:
1. Escreva SOMENTE falas, uma por linha, no formato "MARCOS: texto" ou "ANA: texto". \
Nada de marcações de cena, efeitos sonoros, markdown, emojis ou títulos.
2. O texto será convertido em áudio por um sintetizador de voz: escreva por extenso \
tudo que precisa ser falado (por exemplo, "GPT" vira "G P T", "US$ 5 bilhões" vira \
"cinco bilhões de dólares", siglas pouco conhecidas são soletradas ou explicadas).
3. Abra com Ana dando bom dia, dizendo a data do episódio e chamando o Marcos.
4. Cubra as notícias mais relevantes da lista (todas, se possível; se houver muitas, \
priorize as de maior impacto e agrupe as menores num bloco rápido de "outras notícias").
5. SEMPRE cite a fonte de cada notícia de forma natural na conversa \
("segundo o TechCrunch...", "a própria OpenAI anunciou no blog dela...").
6. Linguagem: português do Brasil, coloquial, fácil de entender, frases curtas. \
Tom leve e bem-humorado, mas informativo.
7. Duração alvo: entre cinco e nove minutos de fala (roughly 900 a 1500 palavras).
8. Feche com um resumo de uma frase por notícia principal e uma despedida simpática \
lembrando que amanhã tem mais.
9. Responda APENAS com as falas do roteiro: nenhum texto antes ("Aqui está o \
roteiro...") nem depois delas.
"""


def build_user_prompt(candidates: list[dict], date_str: str) -> str:
    lines = [
        f"Data do episódio: {date_str}.",
        "",
        "Notícias de hoje (título, fonte, resumo e link):",
        "",
    ]
    for i, c in enumerate(candidates, 1):
        lines.append(f"{i}. [{c['source']}] {c['title']}")
        if c["summary"]:
            lines.append(f"   Resumo: {c['summary']}")
        lines.append(f"   Link: {c['url']}")
        lines.append("")
    lines.append("Escreva o roteiro completo do episódio de hoje.")
    return "\n".join(lines)


def write_script(candidates: list[dict], date_str: str) -> str:
    user_prompt = build_user_prompt(candidates, date_str)

    if os.environ.get("ANTHROPIC_API_KEY"):
        script = _generate_via_api(user_prompt)
    elif os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        script = _generate_via_claude_code(user_prompt)
    else:
        raise RuntimeError(
            "Defina ANTHROPIC_API_KEY (API) ou CLAUDE_CODE_OAUTH_TOKEN "
            "(assinatura Pro/Max via Claude Code) no ambiente."
        )

    n_lines = len([l for l in script.splitlines() if l.strip()])
    print(f"[script] roteiro gerado: {n_lines} falas, {len(script.split())} palavras")
    return script


def _generate_via_api(user_prompt: str) -> str:
    client = anthropic.Anthropic()  # usa ANTHROPIC_API_KEY do ambiente

    with client.beta.messages.stream(
        model="claude-opus-5",
        max_tokens=32000,
        # Fallback automático: se o classificador de segurança recusar a
        # requisição (raro para notícias), o Opus 4.8 responde na mesma chamada.
        betas=["server-side-fallback-2026-06-01"],
        fallbacks=[{"model": "claude-opus-4-8"}],
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        response = stream.get_final_message()

    if response.stop_reason == "refusal":
        raise RuntimeError("A API recusou a requisição (stop_reason=refusal).")
    if response.stop_reason == "max_tokens":
        print("[script] aviso: roteiro pode ter sido truncado (max_tokens)")

    return "".join(b.text for b in response.content if b.type == "text").strip()


def _generate_via_claude_code(user_prompt: str) -> str:
    """Gera o roteiro pelo Claude Code CLI, autenticado com a assinatura Pro/Max.

    O token vem de `claude setup-token` e é lido da variável de ambiente
    CLAUDE_CODE_OAUTH_TOKEN pelo próprio CLI.
    """
    full_prompt = SYSTEM_PROMPT + "\n\n" + user_prompt
    result = subprocess.run(
        ["claude", "-p", "--output-format", "text"],
        input=full_prompt,
        capture_output=True,
        text=True,
        timeout=1200,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Claude Code CLI falhou (token expirado? rode `claude setup-token` "
            f"de novo e atualize o secret). Erro: {result.stderr[-2000:]}"
        )
    script = result.stdout.strip()
    if not script:
        raise RuntimeError("Claude Code CLI retornou resposta vazia.")
    return script
