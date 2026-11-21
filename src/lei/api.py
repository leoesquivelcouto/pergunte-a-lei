"""API e página web. Rodar com: uvicorn lei.api:app"""

import os
from contextlib import asynccontextmanager
from importlib import resources

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from lei import __version__
from lei.busca import Indice
from lei.config import database_url
from lei.fontes import LEIS
from lei.resposta import responder, rotulo

# Calibrado em avaliacao/ (ver README): abaixo disso, nenhum artigo trata do assunto.
LIMIAR = float(os.environ.get("LIMIAR_SIMILARIDADE", "0.32"))

estado: dict[str, Indice] = {}


@asynccontextmanager
async def ciclo(_: FastAPI):
    con = psycopg.connect(database_url(), autocommit=True)
    estado["indice"] = Indice(con)
    yield
    con.close()


app = FastAPI(title="Pergunte à Lei", version=__version__, lifespan=ciclo)


class PerguntaEntrada(BaseModel):
    pergunta: str = Field(min_length=5, max_length=300)


class CitacaoSaida(BaseModel):
    lei: str
    artigo: str
    rotulo: str
    texto: str
    link: str


class RespostaSaida(BaseModel):
    respondida: bool
    resposta: str
    citacoes: list[CitacaoSaida]
    modo: str
    aviso: str


@app.post("/perguntar", response_model=RespostaSaida)
def perguntar(dados: PerguntaEntrada) -> RespostaSaida:
    resultados = estado["indice"].buscar(dados.pergunta, k=5)
    r = responder(dados.pergunta, resultados, LIMIAR)
    return RespostaSaida(
        respondida=r.respondida,
        resposta=r.texto,
        citacoes=[
            CitacaoSaida(lei=c.lei, artigo=c.artigo, rotulo=rotulo(c), texto=c.texto, link=LEIS[c.lei].url)
            for c in r.citacoes
        ],
        modo=r.modo,
        aviso=r.aviso,
    )


@app.get("/artigo/{lei}/{artigo}")
def artigo(lei: str, artigo: str) -> dict[str, str]:
    linhas = (
        estado["indice"]
        .con.execute("SELECT texto FROM trecho WHERE lei = %s AND artigo = %s ORDER BY parte", (lei, artigo))
        .fetchall()
    )
    if not linhas or lei not in LEIS:
        raise HTTPException(404, "Artigo não encontrado.")
    texto = "\n".join(dict.fromkeys(par for (t,) in linhas for par in t.split("\n")))  # caput repetido 1x
    return {"lei": LEIS[lei].nome, "artigo": artigo, "texto": texto, "link": LEIS[lei].url}


@app.get("/", response_class=HTMLResponse)
def pagina() -> str:
    return resources.files("lei").joinpath("pagina.html").read_text(encoding="utf-8")


@app.get("/saude")
def saude() -> dict[str, str]:
    return {"status": "ok", "modelo_embedding": estado["indice"].modelo}
