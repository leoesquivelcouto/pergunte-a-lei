"""As leis do corpus e o download dos textos oficiais (planalto.gov.br, domínio público)."""

import ssl
from dataclasses import dataclass
from pathlib import Path

import httpx
import truststore


@dataclass(frozen=True)
class Lei:
    sigla: str
    nome: str
    numero: str
    url: str


LEIS = {
    lei.sigla: lei
    for lei in [
        Lei(
            "estagio",
            "Lei do Estágio",
            "Lei nº 11.788/2008",
            "https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2008/lei/l11788.htm",
        ),
        Lei(
            "lgpd",
            "Lei Geral de Proteção de Dados (LGPD)",
            "Lei nº 13.709/2018",
            "https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm",
        ),
        Lei(
            "cdc",
            "Código de Defesa do Consumidor",
            "Lei nº 8.078/1990",
            "https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm",
        ),
    ]
}


def baixar(lei: Lei, pasta: Path, forcar: bool = False) -> Path:
    """Baixa o HTML oficial. A verificação TLS usa os certificados do sistema operacional."""
    destino = pasta / f"{lei.sigla}.htm"
    if destino.exists() and not forcar:
        return destino
    pasta.mkdir(parents=True, exist_ok=True)
    contexto = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    resposta = httpx.get(
        lei.url,
        verify=contexto,
        timeout=60,
        follow_redirects=True,
        headers={"User-Agent": "pergunte-a-lei (projeto de estudo)"},
    )
    resposta.raise_for_status()
    destino.write_bytes(resposta.content)
    return destino
