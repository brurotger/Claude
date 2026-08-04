# 🎙️ IA Hoje — seu podcast diário de inteligência artificial

Um podcast pessoal, gerado automaticamente todos os dias pela manhã, com as
principais notícias de IA do mundo — contadas como um bate-papo entre **Marcos**
(especialista) e **Ana** (entusiasta), em linguagem fácil de entender.

## Como funciona (os 3 "agentes")

```
06:00 (Brasília), todos os dias — GitHub Actions
        │
        ▼
1. fetch_news.py   → lê feeds RSS de 10 fontes confiáveis (OpenAI, Google AI,
   (o repórter)      DeepMind, TechCrunch, The Verge, MIT Tech Review, Wired...),
                     pega só notícias das últimas 36h e descarta qualquer uma
                     que já tenha aparecido em episódios anteriores (data/history.json)
        │
        ▼
2. write_script.py → o Claude (Opus 5) escreve o roteiro: um diálogo natural
   (o roteirista)    em português entre Marcos e Ana, citando a fonte de cada
                     notícia ("segundo o TechCrunch...")
        │
        ▼
3. make_audio.py   → cada fala vira áudio com vozes neurais em pt-BR
   (o locutor)       (edge-tts, gratuito) e o ffmpeg monta o MP3 final
        │
        ▼
4. publish.py      → atualiza o feed RSS do podcast + página web e o GitHub
                     faz commit de tudo; o episódio aparece no seu app de podcast
```

## O que você precisa fazer (uma vez só)

1. **Dar acesso ao Claude — escolha UMA das opções**

   **Opção A — chave de API (paga por uso, mais estável):**
   - Gere uma chave em <https://platform.claude.com/> (Console → API Keys) e
     adicione crédito (US$ 5 duram meses).
   - No GitHub, vá em **Settings → Secrets and variables → Actions → New repository secret**
     e crie um secret chamado `ANTHROPIC_API_KEY` com a chave.

   **Opção B — assinatura Pro/Max do claude.ai (custo zero extra):**
   - Num terminal (funciona no GitHub Codespaces, inclusive pelo celular):
     ```bash
     npm install -g @anthropic-ai/claude-code
     claude setup-token
     ```
     Siga o link que aparecer, faça login com a sua conta do claude.ai e copie
     o token gerado (começa com `sk-ant-oat...`).
   - Crie o secret `CLAUDE_CODE_OAUTH_TOKEN` com esse token (mesmo caminho acima).
   - Observações: o consumo sai da cota da assinatura; se o token expirar,
     o workflow falha com uma mensagem clara — basta rodar `claude setup-token`
     de novo e atualizar o secret.

2. **Ativar o GitHub Pages** (é o que hospeda o feed e os áudios)
   - **Settings → Pages → Build and deployment**: em *Source* escolha
     **Deploy from a branch**, branch `main`, pasta `/docs`. Salve.
   - O site ficará em `https://brurotger.github.io/claude/`.
   - ⚠️ Se o repositório for **privado**, o Pages exige plano pago do GitHub.
     Alternativas gratuitas: tornar o repositório público, ou baixar o MP3
     direto do repositório/artifact da execução (cada execução do workflow
     anexa o MP3 como *artifact* por 14 dias).

3. **Levar este código para a branch `main`**
   - O agendamento (`schedule`) do GitHub Actions só funciona na branch padrão.
     Faça o merge desta branch em `main`.

4. **Testar**
   - Aba **Actions → Podcast diário de IA → Run workflow**.
     Marque *dry run* para um teste rápido sem gastar API, ou rode sem marcar
     para gerar um episódio de verdade na hora.

5. **Assinar o podcast no celular**
   - Em qualquer app que aceite feed RSS (AntennaPod, Pocket Casts,
     Podcast Addict, Apple Podcasts via "Seguir programa por URL"), adicione:
     `https://brurotger.github.io/claude/feed.xml`
   - Pronto: todo dia às ~6h da manhã o episódio novo aparece sozinho no app.

## Custos

| Item | Custo |
|---|---|
| GitHub Actions | grátis (repositório público) ou dentro da cota grátis mensal |
| edge-tts (vozes) | grátis |
| GitHub Pages | grátis (repositório público) |
| Roteiro (Claude) | opção A: ~US$ 0,05–0,15/episódio · opção B: incluso na assinatura Pro/Max |

## Garantias de "não repetir notícia"

- `data/history.json` guarda a impressão digital (hash de link + título
  normalizado) de todas as notícias já usadas, por 30 dias.
- Antes de escrever o roteiro, tudo que já apareceu é descartado.
- A deduplicação também compara títulos normalizados, então a mesma notícia
  vinda de duas fontes diferentes não entra duas vezes.

## Personalização rápida (`podcast/config.py`)

- **Fontes**: edite a lista `NEWS_SOURCES` (qualquer feed RSS funciona).
- **Vozes**: `SPEAKERS` — cada personagem tem `voice` (veja outras opções com
  `edge-tts --list-voices | grep pt-BR`), `rate` (ritmo, em %) e `pitch` (tom,
  em Hz) como linha de base; `make_audio.py` soma uma variação aleatória
  pequena em cima disso a cada fala pra tirar o efeito de cadência robótica.
- **Horário**: mude o `cron` em `.github/workflows/podcast.yml`
  (está em UTC: `0 9 * * *` = 6h de Brasília).
- **Duração/tom do episódio**: ajuste o `SYSTEM_PROMPT` em `podcast/write_script.py`.
- **Retenção**: `MAX_EPISODES_KEPT` (episódios no feed) e
  `HISTORY_RETENTION_DAYS` (memória de deduplicação).

## Rodando localmente

```bash
pip install -r podcast/requirements.txt
# precisa do ffmpeg instalado e da variável ANTHROPIC_API_KEY exportada
cd podcast
python run_pipeline.py --dry-run   # teste sem API
python run_pipeline.py             # episódio completo
```

## Se algo der errado

- **Workflow falhou**: veja o log na aba Actions. As falhas mais comuns são
  secret ausente/com nome errado, token da assinatura expirado (rode
  `claude setup-token` de novo e atualize o secret `CLAUDE_CODE_OAUTH_TOKEN`)
  ou uma fonte RSS fora do ar (fontes fora do ar são apenas ignoradas —
  só quebra se *nenhuma* responder).
- **"Nenhuma notícia nova hoje"**: normal em dias muito parados; o episódio
  daquele dia simplesmente não é gerado.
- **Feed não atualiza no app**: confira se o Pages está ativo e se o commit
  do episódio apareceu na branch `main`.
