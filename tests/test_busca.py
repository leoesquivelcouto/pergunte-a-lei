import pytest

from lei.busca import Indice
from lei.fontes import LEIS
from lei.ingestao import ingerir_lei
from tests.conftest import HTML


def test_ingestao_idempotente_e_refeita_quando_o_modelo_muda(con_carregado):
    con = con_carregado
    assert ingerir_lei(con, LEIS["estagio"], HTML, modelo="falso") is None  # nada mudou
    assert con.execute("SELECT count(*) FROM trecho").fetchone()[0] == 4
    assert ingerir_lei(con, LEIS["estagio"], HTML, modelo="outro") == 4  # modelo novo: reindexa
    assert con.execute("SELECT count(*) FROM trecho").fetchone()[0] == 4


def test_ingestao_falha_sem_artigos_e_nao_apaga_o_que_existia(con_carregado):
    with pytest.raises(ValueError, match="formato da página mudou"):
        ingerir_lei(con_carregado, LEIS["estagio"], b"<html><p>pagina nova sem artigos</p></html>")
    assert con_carregado.execute("SELECT count(*) FROM trecho").fetchone()[0] == 4


def test_busca_por_palavras_ignora_acento_e_flexao(con_carregado):
    indice = Indice(con_carregado)
    # "estagiario" sem acento e no singular encontra "estagiários"/"estagiário"
    chaves = [r.chave for r in indice.buscar("estagiario recesso", k=3, modo="palavras")]
    assert ("estagio", "2") in chaves


def test_hibrida_combina_e_agrupa_por_artigo(con_carregado):
    resultados = Indice(con_carregado).buscar("desistir da compra pela internet", k=5)
    assert resultados[0].chave == ("estagio", "10-A")
    assert len({r.chave for r in resultados}) == len(resultados)  # um resultado por artigo
    assert all(r.similaridade <= 1.0001 for r in resultados)


def test_pergunta_sem_palavra_util_nao_quebra(con_carregado):
    assert Indice(con_carregado).buscar("??? !!!", modo="palavras") == []


def test_indice_vazio_e_modelos_misturados(con, con_carregado):
    con.execute("UPDATE lei SET modelo = 'outro'")
    con.execute(
        "INSERT INTO lei (sigla, nome, numero, url, hash_html, modelo) VALUES ('x', 'X', '1', 'u', 'h', 'falso')"
    )
    con.execute(
        "INSERT INTO trecho (lei, artigo, parte, contexto, texto, embedding) VALUES ('x', '1', 1, '', 't', %s)",
        ([0.0] * 256,),
    )
    with pytest.raises(RuntimeError, match="modelos diferentes"):
        Indice(con)
    con.execute("DELETE FROM lei")
    with pytest.raises(RuntimeError, match="Índice vazio"):
        Indice(con)
