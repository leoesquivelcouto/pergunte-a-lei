"""Transforma o HTML do Planalto em artigos e depois em trechos para a busca.

A unidade é o artigo, não um número fixo de caracteres: é o que a pessoa cita ("art. 10 da Lei do
Estágio") e o que dá para conferir. Artigos longos (como o art. 5º da LGPD, com 19 definições) viram
vários trechos, cada um repetindo o caput para não perder o contexto.
"""

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Tag

# "Art. 1o", "Art. 7º-A", "Art. 10." (de 10 em diante a lei usa ponto em vez de ordinal)
RE_ARTIGO = re.compile(r"^Art\.\s*(\d+)\s*(?:[º°o]|\.)?\s*(?:-\s*([A-Z]))?\.?\s*(.*)$", re.S)
RE_TITULO = re.compile(r"^(TÍTULO|CAPÍTULO|SEÇÃO|SUBSEÇÃO)\s+([IVXLC]+|ÚNIC[AO])\b\s*[-–]?\s*(.*)$", re.I)
# Notas do Planalto sobre a origem do texto: "(Redação dada pela Lei nº ...)", "(Incluído pela ...)".
RE_NOTA = re.compile(
    r"\((?:Redação dada|Incluíd[oa]|Acrescid[oa]|Renumerad[oa]|Vide|Vigência|Produção de efeitos|"
    r"Regulamento|Promulgação)[^()]*(?:\([^()]*\)[^()]*)*\)",
    re.I,
)
RE_FIM = re.compile(r"^Brasília,\s*\d")
TAMANHO_MAXIMO = 1400


@dataclass
class Artigo:
    lei: str
    numero: str  # "5", "7-A"
    texto: str  # sem as notas do Planalto
    contexto: str  # capítulo e seção, ex.: "Capítulo II - Do tratamento de dados pessoais"
    paragrafos: list[str] = field(default_factory=list)

    @property
    def rotulo(self) -> str:
        return f"Art. {self.numero}"


@dataclass
class Trecho:
    lei: str
    artigo: str
    parte: int
    contexto: str
    texto: str  # o que aparece para a pessoa e vai para a busca por palavras
    texto_busca: str  # com o contexto do capítulo, usado para gerar o embedding


def _riscado(tag: Tag) -> bool:
    estilo = (tag.get("style") or "").replace(" ", "").lower()
    return tag.name in ("strike", "s", "del") or "line-through" in estilo


def _limpar(texto: str) -> str:
    texto = texto.replace("\xa0", " ")
    return re.sub(r"\s+", " ", texto).strip()


def paragrafos_do_html(html: bytes) -> list[str]:
    """Texto de cada parágrafo, sem o que está riscado (redação revogada)."""
    try:
        texto_html = html.decode("utf-8")
    except UnicodeDecodeError:
        texto_html = html.decode("cp1252", errors="replace")  # o Planalto publica em Windows-1252
    sopa = BeautifulSoup(texto_html, "html.parser")
    for riscado in [t for t in sopa.find_all(True) if _riscado(t)]:
        riscado.decompose()
    linhas = []
    for p in sopa.find_all("p"):
        texto = _limpar(p.get_text(" "))
        # "Art. 1 o" (ordinal em <sup>) e "§ 1 o" voltam a ficar juntos
        texto = re.sub(r"^(Art\.|§)\s*(\d+)\s+([oº°])\b", r"\1 \2\3", texto)
        # O HTML às vezes parte o número em pedaços: "Art. 5 7." é o art. 57
        while m := re.match(r"^(Art\.\s*\d+)\s+(\d)", texto):
            texto = m.group(1) + texto[m.end(1) :].lstrip()
        if texto:
            linhas.append(texto)
    return linhas


def _frase(texto: str) -> str:
    """'DO TRATAMENTO DE DADOS' vira 'Do tratamento de dados' (só quando vem tudo em maiúsculas)."""
    return texto[0] + texto[1:].lower() if texto.isupper() else texto


def sem_notas(texto: str) -> str:
    texto = RE_NOTA.sub("", texto)
    # "§ 1 o do art. 2 o" (ordinal em <sup>) vira "§ 1º do art. 2º"
    texto = re.sub(r"(?<!\w)(§|art\.|arts\.)\s*(\d+)\s*[oº°](?=\W|$)", r"\1 \2º", texto, flags=re.I)
    return _limpar(texto)


def extrair_artigos(sigla: str, html: bytes) -> list[Artigo]:
    artigos: list[Artigo] = []
    atual: Artigo | None = None
    titulos: dict[str, str] = {}
    pendente: str | None = None  # "CAPÍTULO II" aguardando o nome na linha seguinte

    for linha in paragrafos_do_html(html):
        if RE_FIM.match(linha):
            break
        if pendente:
            nome = sem_notas(linha)
            pendente_nivel, pendente = pendente, None
            # O nome do capítulo pode vir na linha seguinte; nunca consumir um artigo como se fosse o nome.
            if nome and not RE_ARTIGO.match(linha) and not RE_TITULO.match(linha):
                titulos[pendente_nivel] = f"{titulos[pendente_nivel]} - {_frase(nome)}"
                continue
        if m := RE_TITULO.match(linha):
            nivel = m.group(1).upper()
            if nivel == "TÍTULO":
                titulos.clear()
            elif nivel == "CAPÍTULO":
                titulos.pop("SEÇÃO", None)
                titulos.pop("SUBSEÇÃO", None)
            elif nivel == "SEÇÃO":
                titulos.pop("SUBSEÇÃO", None)
            rotulo = f"{nivel.capitalize()} {m.group(2).upper()}"
            nome = sem_notas(m.group(3))
            titulos[nivel] = f"{rotulo} - {_frase(nome)}" if nome else rotulo
            pendente = None if nome else nivel
            continue
        if m := RE_ARTIGO.match(linha):
            numero = m.group(1) + (f"-{m.group(2)}" if m.group(2) else "")
            corpo = sem_notas(m.group(3))
            if not corpo or corpo.startswith("(VETADO)") or re.fullmatch(r"\(?Revogad[oa].*", corpo, re.I):
                atual = None  # artigo vetado ou revogado: não entra no corpus
                continue
            # Forma canônica da lei: "Art. 1º" até o 9º, depois "Art. 10." ("Art. 1o", "Art. 1 0." no HTML)
            sufixo = "º" if int(m.group(1)) < 10 and not m.group(2) else "."
            cabeca = f"Art. {numero}{sufixo}"
            atual = Artigo(sigla, numero, "", " | ".join(titulos.values()), [f"{cabeca} {corpo}"])
            artigos.append(atual)
            continue
        if atual is not None:
            texto = sem_notas(linha)
            # "Parágrafo único. (Vetado).", "III - (revogado);": dispositivo sem texto em vigor
            if texto and not re.fullmatch(r"(.{0,20}\s)?\(?(VETADO|Revogad[oa])\)?[\s.;]*", texto, re.I):
                atual.paragrafos.append(texto)

    for a in artigos:
        a.texto = "\n".join(a.paragrafos)
    return artigos


def texto_para_embedding(nome_lei: str, contexto: str, artigo: str, texto: str) -> str:
    """O embedding vê também a lei e o capítulo: "Do estagiário" ajuda a achar perguntas sobre estagiários."""
    capitulo = f"{contexto}. " if contexto else ""
    return f"{nome_lei}. {capitulo}{nome_lei}, Art. {artigo}. {texto}"


def dividir(artigo: Artigo, nome_lei: str) -> list[Trecho]:
    """Um trecho por artigo; artigos longos são divididos nos parágrafos, repetindo o caput."""

    def trecho(parte: int, texto: str) -> Trecho:
        busca = texto_para_embedding(nome_lei, artigo.contexto, artigo.numero, texto)
        return Trecho(artigo.lei, artigo.numero, parte, artigo.contexto, texto, busca)

    if len(artigo.texto) <= TAMANHO_MAXIMO:
        return [trecho(1, artigo.texto)]

    caput, *resto = artigo.paragrafos
    trechos: list[Trecho] = []
    bloco: list[str] = []
    for paragrafo in resto:
        if bloco and len(caput) + sum(map(len, bloco)) + len(paragrafo) > TAMANHO_MAXIMO:
            trechos.append(trecho(len(trechos) + 1, "\n".join([caput, *bloco])))
            bloco = []
        bloco.append(paragrafo)
    trechos.append(trecho(len(trechos) + 1, "\n".join([caput, *bloco])))
    return trechos
