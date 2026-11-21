"""Monta a resposta a partir dos artigos encontrados.

Duas formas:
- com ANTHROPIC_API_KEY: o Claude escreve a resposta usando só os artigos recuperados, em JSON validado
  (structured outputs). Toda citação é conferida: se o modelo citar um artigo que não estava no contexto,
  a citação é descartada e marcada;
- sem chave: modo extrativo, que devolve os artigos mais relevantes como estão na lei.

Nos dois casos, se nenhum artigo passar do limiar de similaridade, o sistema recusa em vez de adivinhar.
"""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

from lei.busca import Resultado
from lei.config import MODELO_LLM, chave_anthropic
from lei.fontes import LEIS

AVISO = "Informação baseada no texto da lei. Não é aconselhamento jurídico."

INSTRUCOES = """Você responde dúvidas de pessoas leigas sobre três leis brasileiras: Lei do Estágio, LGPD e \
Código de Defesa do Consumidor.

Use somente os artigos fornecidos na mensagem. Não use conhecimento próprio sobre outras leis, \
jurisprudência ou números que não estejam nos artigos.

- Se os artigos respondem à pergunta, responda em português claro, em até 5 frases, e cite os artigos \
usados no formato exato em que aparecem (lei e número).
- Se os artigos não respondem à pergunta, marque `responde` como falso e explique em uma frase que as \
leis consultadas não tratam do assunto. Não tente responder com outra fonte.
- Não dê conselho sobre o caso concreto da pessoa; explique o que a lei diz."""


class Citacao(BaseModel):
    lei: Literal["estagio", "lgpd", "cdc"]
    artigo: str = Field(description='Número do artigo como aparece no contexto, ex.: "10", "7-A"')


class RespostaModelo(BaseModel):
    responde: bool
    resposta: str
    citacoes: list[Citacao]


@dataclass
class Resposta:
    pergunta: str
    respondida: bool
    texto: str
    citacoes: list[Resultado]
    modo: Literal["llm", "extrativo"]
    citacoes_descartadas: list[str] = field(default_factory=list)
    aviso: str = AVISO


def rotulo(r: Resultado) -> str:
    return f"{LEIS[r.lei].nome}, art. {r.artigo}"


def _contexto(resultados: list[Resultado]) -> str:
    return "\n\n".join(
        f'<artigo lei="{r.lei}" numero="{r.artigo}" nome="{rotulo(r)}">\n{r.texto}\n</artigo>' for r in resultados
    )


def recusa(pergunta: str, modo: Literal["llm", "extrativo"]) -> Resposta:
    texto = (
        "Não encontrei esse assunto na Lei do Estágio, na LGPD nem no Código de Defesa do Consumidor, "
        "que são as leis que consigo consultar."
    )
    return Resposta(pergunta, False, texto, [], modo)


def extrativa(pergunta: str, resultados: list[Resultado], limiar: float) -> Resposta:
    relevantes = [r for r in resultados[:3] if r.similaridade >= limiar]
    if not relevantes:
        return recusa(pergunta, "extrativo")
    return Resposta(
        pergunta,
        True,
        "Estes são os artigos que tratam do assunto. Leia o texto completo antes de concluir algo.",
        relevantes,
        "extrativo",
    )


def com_llm(pergunta: str, resultados: list[Resultado], limiar: float, cliente=None) -> Resposta:
    if not resultados or max(r.similaridade for r in resultados) < limiar:
        return recusa(pergunta, "llm")

    import anthropic

    cliente = cliente or anthropic.Anthropic()
    resposta = cliente.beta.messages.parse(
        model=MODELO_LLM,
        max_tokens=2000,
        system=INSTRUCOES,
        messages=[{"role": "user", "content": f"{_contexto(resultados)}\n\nPergunta: {pergunta}"}],
        output_format=RespostaModelo,
        output_config={"effort": "low"},  # resposta curta sobre poucos artigos: não precisa de mais
        # Se o modelo principal recusar por política, a API tenta outro modelo na mesma chamada.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if resposta.stop_reason == "refusal" or resposta.parsed_output is None:
        return extrativa(pergunta, resultados, limiar)

    saida: RespostaModelo = resposta.parsed_output
    if not saida.responde:
        return recusa(pergunta, "llm")

    # Só vale citação de artigo que estava no contexto: o modelo não pode inventar artigo.
    por_chave = {r.chave: r for r in resultados}
    citados, descartados = [], []
    for c in saida.citacoes:
        r = por_chave.get((c.lei, c.artigo))
        if r is None:
            descartados.append(f"{c.lei} art. {c.artigo}")
        elif r not in citados:
            citados.append(r)
    if not citados:
        return extrativa(pergunta, resultados, limiar)
    return Resposta(pergunta, True, saida.resposta, citados, "llm", descartados)


def responder(pergunta: str, resultados: list[Resultado], limiar: float, cliente=None) -> Resposta:
    if cliente is not None or chave_anthropic():
        return com_llm(pergunta, resultados, limiar, cliente)
    return extrativa(pergunta, resultados, limiar)
