"""Configuração lida de variáveis de ambiente (e de um arquivo .env, se existir)."""

import os
from pathlib import Path


def _carregar_env(caminho: Path = Path(".env")) -> None:
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            chave, valor = linha.split("=", 1)
            os.environ.setdefault(chave.strip(), valor.strip().strip("\"'"))


_carregar_env()

PASTA_DADOS = Path(os.environ.get("LEI_DADOS", "dados"))
MODELO_EMBEDDING = os.environ.get("MODELO_EMBEDDING", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
MODELO_LLM = os.environ.get("MODELO_LLM", "claude-opus-5-5")


# Limiar de similaridade para recusar, calibrado por modelo na avaliação (avaliacao/resultados.md):
# cada modelo tem uma escala de cosseno diferente, então o mesmo número não serve para todos.
LIMIARES = {
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": 0.32,
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2": 0.47,
    "intfloat/multilingual-e5-large": 0.82,
}


def limiar_do_modelo(modelo: str) -> float:
    return LIMIARES.get(modelo, 0.5)


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("Defina DATABASE_URL (veja .env.example).")
    return url


def chave_anthropic() -> str | None:
    return os.environ.get("ANTHROPIC_API_KEY") or None
