"""Baixa, divide por artigo, gera embeddings e grava no PostgreSQL. Uma transação por lei."""

import hashlib
from importlib import resources

import psycopg

from lei import embeddings
from lei.config import MODELO_EMBEDDING, PASTA_DADOS
from lei.fontes import LEIS, Lei, baixar
from lei.parser import dividir, extrair_artigos


def criar_schema(con: psycopg.Connection) -> None:
    con.execute(resources.files("lei").joinpath("schema.sql").read_text(encoding="utf-8"))


def ingerir_lei(con: psycopg.Connection, lei: Lei, html: bytes, modelo: str = MODELO_EMBEDDING) -> int | None:
    """Substitui a lei inteira. Devolve o número de trechos, ou None se nada mudou (mesmo HTML e modelo)."""
    hash_html = hashlib.sha256(html).hexdigest()
    atual = con.execute("SELECT hash_html, modelo FROM lei WHERE sigla = %s", (lei.sigla,)).fetchone()
    if atual == (hash_html, modelo):
        return None

    trechos = [t for a in extrair_artigos(lei.sigla, html) for t in dividir(a, lei.nome)]
    if not trechos:
        raise ValueError(f"Nenhum artigo encontrado em {lei.sigla}: o formato da página mudou?")
    vetores = embeddings.documentos([t.texto_busca for t in trechos], modelo)

    with con.transaction():
        con.execute("DELETE FROM lei WHERE sigla = %s", (lei.sigla,))
        con.execute(
            "INSERT INTO lei (sigla, nome, numero, url, hash_html, modelo) VALUES (%s, %s, %s, %s, %s, %s)",
            (lei.sigla, lei.nome, lei.numero, lei.url, hash_html, modelo),
        )
        with con.cursor() as cur:
            cur.executemany(
                "INSERT INTO trecho (lei, artigo, parte, contexto, texto, embedding) VALUES (%s, %s, %s, %s, %s, %s)",
                [
                    (t.lei, t.artigo, t.parte, t.contexto, t.texto, v.tolist())
                    for t, v in zip(trechos, vetores, strict=True)
                ],
            )
    return len(trechos)


def ingerir_tudo(con: psycopg.Connection, forcar_download: bool = False) -> dict[str, int | None]:
    criar_schema(con)
    return {
        sigla: ingerir_lei(con, lei, baixar(lei, PASTA_DADOS / "brutos", forcar_download).read_bytes())
        for sigla, lei in LEIS.items()
    }
