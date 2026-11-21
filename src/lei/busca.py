"""Busca híbrida: palavras (PostgreSQL full-text) + significado (embeddings), combinadas por RRF.

Por que as duas: a busca por palavras acerta termos exatos ("venda casada", "recesso"), mas falha quando a
pessoa usa outras palavras ("férias do estagiário"). A busca vetorial entende a paráfrase, mas às vezes
traz um artigo "parecido" em vez do certo. Reciprocal Rank Fusion soma as posições nas duas listas sem
precisar calibrar escalas de pontuação diferentes.
"""

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
import psycopg

from lei import embeddings
from lei.parser import texto_para_embedding

K_RRF = 60  # constante usual do RRF: suaviza a diferença entre 1º e 2º lugar
CANDIDATOS = 30
Modo = Literal["palavras", "vetorial", "hibrida"]


@dataclass
class Resultado:
    lei: str
    artigo: str
    texto: str
    contexto: str
    pontuacao: float
    similaridade: float  # cosseno do melhor trecho do artigo com a pergunta (usado para recusar)
    partes: list[int] = field(default_factory=list)

    @property
    def chave(self) -> tuple[str, str]:
        return (self.lei, self.artigo)


class Indice:
    """Carrega os trechos e a matriz de embeddings uma vez; cada busca vetorial é um produto de matrizes."""

    def __init__(self, con: psycopg.Connection, modelo: str | None = None):
        """Com `modelo` diferente do indexado, gera os embeddings em memória (usado para comparar modelos)."""
        self.con = con
        linhas = con.execute(
            "SELECT t.id, t.lei, t.artigo, t.parte, t.contexto, t.texto, t.embedding, l.modelo, l.nome"
            " FROM trecho t JOIN lei l ON l.sigla = t.lei ORDER BY t.id"
        ).fetchall()
        if not linhas:
            raise RuntimeError("Índice vazio: rode `lei ingerir` primeiro.")
        modelos = {linha[7] for linha in linhas}
        if len(modelos) != 1:
            raise RuntimeError(f"Leis indexadas com modelos diferentes: {modelos}. Rode `lei ingerir`.")
        indexado = modelos.pop()
        self.modelo = modelo or indexado
        self.ids = [linha[0] for linha in linhas]
        self.trechos = {linha[0]: linha[1:6] for linha in linhas}
        if self.modelo == indexado:
            self.matriz = embeddings.normalizar(np.array([linha[6] for linha in linhas], dtype=np.float32))
        else:
            textos = [texto_para_embedding(ln[8], ln[4], ln[2], ln[5]) for ln in linhas]
            self.matriz = embeddings.documentos(textos, self.modelo)

    def _palavras(self, pergunta: str) -> list[int]:
        # plainto_tsquery liga as palavras com E (&); trocamos por OU (|) e deixamos o ts_rank_cd ordenar.
        linhas = self.con.execute(
            """
            WITH q AS (SELECT replace(plainto_tsquery('pt', %(p)s)::text, '&', '|') AS consulta)
            SELECT id FROM trecho, q
            WHERE consulta <> '' AND busca @@ consulta::tsquery
            ORDER BY ts_rank_cd(busca, consulta::tsquery, 32) DESC, id
            LIMIT %(n)s
            """,
            {"p": pergunta, "n": CANDIDATOS},
        ).fetchall()
        return [linha[0] for linha in linhas]

    def _vetorial(self, vetor: np.ndarray) -> list[int]:
        similaridades = self.matriz @ vetor
        melhores = np.argsort(-similaridades)[:CANDIDATOS]
        return [self.ids[i] for i in melhores]

    def buscar(self, pergunta: str, k: int = 5, modo: Modo = "hibrida") -> list[Resultado]:
        vetor = embeddings.pergunta(pergunta, self.modelo)
        similaridade = dict(zip(self.ids, (self.matriz @ vetor).tolist(), strict=True))

        listas = []
        if modo in ("palavras", "hibrida"):
            listas.append(self._palavras(pergunta))
        if modo in ("vetorial", "hibrida"):
            listas.append(self._vetorial(vetor))

        pontos: dict[int, float] = {}
        for lista in listas:
            for posicao, trecho_id in enumerate(lista, start=1):
                pontos[trecho_id] = pontos.get(trecho_id, 0.0) + 1 / (K_RRF + posicao)

        # Vários trechos do mesmo artigo viram um resultado só (a citação é por artigo).
        por_artigo: dict[tuple[str, str], Resultado] = {}
        for trecho_id, ponto in sorted(pontos.items(), key=lambda x: -x[1]):
            lei, artigo, parte, contexto, texto = self.trechos[trecho_id]
            atual = por_artigo.get((lei, artigo))
            if atual is None:
                por_artigo[(lei, artigo)] = Resultado(
                    lei, artigo, texto, contexto, ponto, similaridade[trecho_id], [parte]
                )
            else:
                atual.partes.append(parte)
                atual.similaridade = max(atual.similaridade, similaridade[trecho_id])
        return list(por_artigo.values())[:k]
