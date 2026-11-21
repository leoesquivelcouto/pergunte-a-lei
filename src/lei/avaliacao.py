"""Mede a busca com perguntas escritas à mão, cada uma com o(s) artigo(s) que a respondem.

Métricas:
- acerto@k: a pergunta tem ao menos um artigo esperado entre os k primeiros resultados;
- MRR: média de 1/posição do primeiro artigo certo (1,0 = sempre em 1º lugar);
- recusa: perguntas fora das três leis devem ficar abaixo do limiar de similaridade, e as de dentro, acima.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from lei.busca import Indice, Modo


@dataclass
class Pergunta:
    id: int
    pergunta: str
    esperado: set[tuple[str, str]]

    @property
    def fora_do_escopo(self) -> bool:
        return not self.esperado


@dataclass
class Metricas:
    modo: str
    modelo: str
    acerto_1: float
    acerto_3: float
    acerto_5: float
    mrr: float
    erros: list[tuple[int, str, list[tuple[str, str]]]]
    sim_dentro: list[float]
    sim_fora: list[float]


def carregar(caminho: Path) -> list[Pergunta]:
    perguntas = []
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        if linha.strip():
            d = json.loads(linha)
            perguntas.append(Pergunta(d["id"], d["pergunta"], {tuple(e) for e in d["esperado"]}))
    return perguntas


def avaliar(indice: Indice, perguntas: list[Pergunta], modo: Modo) -> Metricas:
    posicoes: list[int | None] = []
    erros = []
    sim_dentro, sim_fora = [], []
    for p in perguntas:
        resultados = indice.buscar(p.pergunta, k=5, modo=modo)
        maior = max((r.similaridade for r in resultados), default=0.0)
        if p.fora_do_escopo:
            sim_fora.append(maior)
            continue
        sim_dentro.append(maior)
        chaves = [r.chave for r in resultados]
        posicao = next((i for i, c in enumerate(chaves, start=1) if c in p.esperado), None)
        posicoes.append(posicao)
        if posicao != 1:
            erros.append((p.id, p.pergunta, chaves[:3]))

    n = len(posicoes)
    return Metricas(
        modo=modo,
        modelo=indice.modelo.split("/")[-1],
        acerto_1=sum(1 for x in posicoes if x == 1) / n,
        acerto_3=sum(1 for x in posicoes if x and x <= 3) / n,
        acerto_5=sum(1 for x in posicoes if x) / n,
        mrr=sum(1 / x for x in posicoes if x) / n,
        erros=erros,
        sim_dentro=sim_dentro,
        sim_fora=sim_fora,
    )


def melhor_limiar(dentro: list[float], fora: list[float]) -> tuple[float, int, int]:
    """Limiar de similaridade que mais acerta a decisão responder/recusar. Devolve (limiar, acertos, total)."""
    candidatos = sorted(set(dentro + fora))
    melhor = (0.0, 0)
    for limiar in candidatos:
        acertos = sum(s >= limiar for s in dentro) + sum(s < limiar for s in fora)
        if acertos > melhor[1]:
            melhor = (limiar, acertos)
    return melhor[0], melhor[1], len(dentro) + len(fora)
