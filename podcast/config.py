"""Configurações centrais do podcast diário de IA."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
HISTORY_FILE = DATA_DIR / "history.json"
DOCS_DIR = REPO_ROOT / "docs"
EPISODES_DIR = DOCS_DIR / "episodes"
EPISODES_INDEX = DOCS_DIR / "episodes.json"

# Fontes confiáveis de notícias de IA (RSS)
NEWS_SOURCES = [
    {"name": "OpenAI", "url": "https://openai.com/news/rss.xml"},
    {"name": "Google AI", "url": "https://blog.google/technology/ai/rss/"},
    {"name": "Google DeepMind", "url": "https://deepmind.google/blog/rss.xml"},
    {"name": "Hugging Face", "url": "https://huggingface.co/blog/feed.xml"},
    {"name": "TechCrunch", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"},
    {"name": "VentureBeat", "url": "https://venturebeat.com/category/ai/feed/"},
    {"name": "MIT Technology Review", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed"},
    {"name": "Ars Technica", "url": "https://arstechnica.com/ai/feed/"},
    {"name": "Wired", "url": "https://www.wired.com/feed/tag/ai/latest/rss"},
]

# Janela de tempo: só considera notícias publicadas nas últimas N horas
NEWS_WINDOW_HOURS = 36
# Máximo de notícias candidatas enviadas ao roteirista
MAX_CANDIDATES = 14
# Quantos dias de histórico manter para deduplicação
HISTORY_RETENTION_DAYS = 30
# Quantos episódios manter publicados no feed
MAX_EPISODES_KEPT = 14

# Personagens e vozes (Microsoft Edge TTS, neurais, pt-BR)
SPEAKERS = {
    "MARCOS": "pt-BR-AntonioNeural",    # o especialista
    "ANA": "pt-BR-FranciscaNeural",     # a entusiasta
}

# URL pública do site (GitHub Pages). Ajuste se o nome do repositório mudar.
SITE_BASE_URL = "https://brurotger.github.io/claude"

PODCAST_TITLE = "IA Hoje — seu resumo diário de inteligência artificial"
PODCAST_DESCRIPTION = (
    "Um bate-papo diário entre Marcos, especialista em IA, e Ana, uma entusiasta "
    "curiosa, sobre as principais novidades do mundo da inteligência artificial. "
    "Gerado automaticamente todos os dias pela manhã."
)
PODCAST_LANGUAGE = "pt-BR"
