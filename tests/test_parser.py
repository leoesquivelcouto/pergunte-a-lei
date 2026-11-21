from pathlib import Path

from lei.parser import TAMANHO_MAXIMO, Artigo, dividir, extrair_artigos

HTML = (Path(__file__).parent / "dados" / "lei_exemplo.htm").read_bytes()


def artigos() -> dict[str, Artigo]:
    return {a.numero: a for a in extrair_artigos("exemplo", HTML)}


def test_artigos_em_vigor_sem_vetados_e_sem_o_que_vem_depois_da_assinatura():
    assert list(artigos()) == ["1", "2", "10", "10-A"]


def test_texto_riscado_e_revogado_nao_entra():
    texto = artigos()["2"].texto
    assert "30 (trinta) dias" in texto
    assert "15 (quinze)" not in texto  # <strike>
    assert "Texto antigo" not in texto  # text-decoration: line-through
    assert "Redação dada" not in texto  # nota do Planalto


def test_paragrafo_vetado_e_inciso_revogado_saem():
    assert artigos()["1"].texto == "Art. 1º Esta Lei trata do recesso remunerado de estudantes estagiários."
    assert "revogado" not in artigos()["10-A"].texto
    assert "II - a devolução é integral." in artigos()["10-A"].texto


def test_numeros_partidos_e_ordinais_em_sup():
    a = artigos()
    assert a["10"].texto.startswith("Art. 10.")  # "Art. 1 0." no HTML
    assert "§ 1º O recesso" in a["2"].texto
    assert "§ 2º do art. 1º" in a["2"].texto


def test_contexto_do_capitulo_com_nome_na_linha_seguinte_ou_na_mesma():
    a = artigos()
    assert a["1"].contexto == "Capítulo I - Das disposições gerais"
    assert a["10"].contexto == "Capítulo II - Da fiscalização"


def test_artigo_curto_vira_um_trecho_com_contexto_para_o_embedding():
    (trecho,) = dividir(artigos()["2"], "Lei de Exemplo")
    assert trecho.parte == 1
    assert trecho.texto_busca.startswith("Lei de Exemplo. Capítulo I - Das disposições gerais. Lei de Exemplo, Art. 2.")


def test_artigo_longo_e_dividido_repetindo_o_caput():
    caput = "Art. 5º Para os fins desta Lei, considera-se:"
    incisos = [f"{i} - definição número {i} " + "x" * 200 for i in range(1, 16)]
    longo = Artigo("exemplo", "5", "\n".join([caput, *incisos]), "", [caput, *incisos])
    trechos = dividir(longo, "Lei")
    assert len(trechos) > 1
    assert all(t.texto.startswith(caput) for t in trechos)
    assert all(len(t.texto) <= TAMANHO_MAXIMO + 250 for t in trechos)
    # nenhum inciso se perde nem se repete
    juntos = [linha for t in trechos for linha in t.texto.split("\n")[1:]]
    assert juntos == incisos
