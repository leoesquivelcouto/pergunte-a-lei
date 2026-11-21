"""Testes de banco rodam contra um PostgreSQL de verdade (TEST_DATABASE_URL).

O modelo de embedding é trocado por um falso, determinístico: os testes não baixam 220 MB nem dependem
da qualidade do modelo. A qualidade é medida à parte, em `lei avaliar`.
"""

import hashlib
import os
import re
import unicodedata
from pathlib import Path

import numpy as np
import psycopg
import pytest

from lei import embeddings
from lei.fontes import LEIS
from lei.ingestao import criar_schema, ingerir_lei

HTML = (Path(__file__).parent / "dados" / "lei_exemplo.htm").read_bytes()
DIM = 256


def _vetor_falso(texto: str) -> np.ndarray:
    """Saco de palavras com hash: textos com palavras em comum ficam próximos."""
    sem_acento = unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()
    v = np.zeros(DIM, dtype=np.float32)
    for palavra in re.findall(r"[a-z]{4,}", sem_acento):
        v[int(hashlib.md5(palavra[:6].encode()).hexdigest(), 16) % DIM] += 1
    return v


@pytest.fixture(autouse=True)
def embedding_falso(monkeypatch):
    monkeypatch.setattr(
        embeddings,
        "documentos",
        lambda textos, modelo=None: embeddings.normalizar(np.array([_vetor_falso(t) for t in textos])),
    )
    monkeypatch.setattr(embeddings, "pergunta", lambda texto, modelo=None: embeddings.normalizar(_vetor_falso(texto)))


@pytest.fixture
def con():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Defina TEST_DATABASE_URL para os testes de banco.")
    with psycopg.connect(url, autocommit=True) as c:
        c.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public")
        criar_schema(c)
        yield c


@pytest.fixture
def con_carregado(con):
    """A lei de exemplo entra no lugar da Lei do Estágio (para ter nome e link reais)."""
    assert ingerir_lei(con, LEIS["estagio"], HTML, modelo="falso") == 4
    return con
