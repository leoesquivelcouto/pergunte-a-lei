import os

import pytest
from fastapi.testclient import TestClient

from lei import api


@pytest.fixture
def cliente(con_carregado, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", os.environ["TEST_DATABASE_URL"])
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(api, "LIMIAR", 0.2)
    with TestClient(api.app) as c:
        yield c


def test_pergunta_com_citacao_e_link_oficial(cliente):
    r = cliente.post("/perguntar", json={"pergunta": "posso desistir da compra feita pela internet?"})
    assert r.status_code == 200
    d = r.json()
    assert d["respondida"] and d["modo"] == "extrativo"
    primeira = d["citacoes"][0]
    assert (primeira["lei"], primeira["artigo"]) == ("estagio", "10-A")
    assert primeira["rotulo"] == "Lei do Estágio, art. 10-A"
    assert primeira["link"].startswith("https://www.planalto.gov.br/")
    assert "aconselhamento jurídico" in d["aviso"]


def test_fora_do_escopo_e_validacao(cliente):
    d = cliente.post("/perguntar", json={"pergunta": "qual a idade mínima para votar?"}).json()
    assert not d["respondida"] and d["citacoes"] == []
    assert cliente.post("/perguntar", json={"pergunta": "oi"}).status_code == 422


def test_artigo_e_pagina(cliente):
    a = cliente.get("/artigo/estagio/2").json()
    assert a["texto"].startswith("Art. 2º") and a["lei"] == "Lei do Estágio"
    assert cliente.get("/artigo/estagio/999").status_code == 404
    assert "Pergunte à Lei" in cliente.get("/").text
    assert cliente.get("/saude").json()["modelo_embedding"] == "falso"
