from types import SimpleNamespace

from lei.avaliacao import Pergunta, avaliar, melhor_limiar
from lei.busca import Indice, Resultado
from lei.resposta import AVISO, Citacao, RespostaModelo, responder


def _resultado(lei, artigo, sim=0.8):
    return Resultado(lei, artigo, f"Art. {artigo}. texto", "", 0.1, sim, [1])


class ClienteFalso:
    """Imita client.beta.messages.parse e guarda os argumentos recebidos."""

    def __init__(self, saida=None, stop_reason="end_turn"):
        self.chamadas = []
        self.saida, self.stop_reason = saida, stop_reason
        self.beta = SimpleNamespace(messages=SimpleNamespace(parse=self._parse))

    def _parse(self, **kwargs):
        self.chamadas.append(kwargs)
        return SimpleNamespace(stop_reason=self.stop_reason, parsed_output=self.saida)


RESULTADOS = [_resultado("estagio", "13"), _resultado("estagio", "12", 0.6)]


def test_llm_responde_so_com_artigos_do_contexto():
    saida = RespostaModelo(
        responde=True,
        resposta="Sim, há recesso de 30 dias.",
        citacoes=[Citacao(lei="estagio", artigo="13"), Citacao(lei="cdc", artigo="49")],
    )
    cliente = ClienteFalso(saida)
    r = responder("estagiário tem férias?", RESULTADOS, 0.3, cliente)
    assert r.modo == "llm" and r.respondida
    assert [c.chave for c in r.citacoes] == [("estagio", "13")]
    assert r.citacoes_descartadas == ["cdc art. 49"]  # inventado: não estava no contexto
    assert r.aviso == AVISO

    pedido = cliente.chamadas[0]
    assert pedido["output_format"] is RespostaModelo
    assert '<artigo lei="estagio" numero="13"' in pedido["messages"][0]["content"]
    assert pedido["fallbacks"] == "default"


def test_llm_diz_que_nao_responde():
    cliente = ClienteFalso(RespostaModelo(responde=False, resposta="Não trata.", citacoes=[]))
    r = responder("pena de homicídio?", RESULTADOS, 0.3, cliente)
    assert not r.respondida and r.citacoes == []


def test_abaixo_do_limiar_recusa_sem_chamar_o_modelo():
    cliente = ClienteFalso()
    r = responder("idade para votar?", [_resultado("cdc", "1", 0.1)], 0.3, cliente)
    assert not r.respondida
    assert cliente.chamadas == []  # não gasta chamada de API


def test_recusa_do_modelo_ou_citacoes_invalidas_caem_no_modo_extrativo():
    r = responder("x", RESULTADOS, 0.3, ClienteFalso(None, stop_reason="refusal"))
    assert r.modo == "extrativo" and r.respondida
    so_inventadas = RespostaModelo(responde=True, resposta="...", citacoes=[Citacao(lei="lgpd", artigo="99")])
    r = responder("x", RESULTADOS, 0.3, ClienteFalso(so_inventadas))
    assert r.modo == "extrativo"


def test_extrativo_sem_chave(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = responder("estagiário tem férias?", RESULTADOS, 0.7)
    assert r.modo == "extrativo"
    assert [c.chave for c in r.citacoes] == [("estagio", "13")]  # o de 0,6 fica abaixo do limiar


def test_melhor_limiar_separa_dentro_e_fora():
    assert melhor_limiar([0.6, 0.7, 0.5], [0.2, 0.3]) == (0.5, 5, 5)
    limiar, certas, total = melhor_limiar([0.6, 0.25], [0.3])
    assert (certas, total) == (2, 3)


def test_avaliar_mede_acerto_e_mrr(con_carregado):
    perguntas = [
        Pergunta(1, "desistir da compra pela internet", {("estagio", "10-A")}),
        Pergunta(2, "multa para a empresa que descumprir", {("estagio", "10")}),
        Pergunta(3, "idade mínima para votar", set()),
    ]
    m = avaliar(Indice(con_carregado), perguntas, "hibrida")
    assert m.acerto_5 == 1.0 and 0 < m.mrr <= 1
    assert len(m.sim_dentro) == 2 and len(m.sim_fora) == 1
