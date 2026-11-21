# Pergunte à Lei

Responde dúvidas sobre a **Lei do Estágio**, a **LGPD** e o **Código de Defesa do Consumidor** sempre
**citando o artigo**, e **se recusa** a responder quando a pergunta não está nessas leis. A qualidade da
busca é **medida** com um conjunto de perguntas escritas à mão.

> **Status:** v0.1. Busca, respostas, API e página funcionando; avaliação reproduzível no CI.
> Ainda não está publicado online. **Não é aconselhamento jurídico.**

## Por que existe

Perguntas como "estagiário tem direito a férias?" ou "em quanto tempo posso desistir de uma compra online?"
têm resposta exata na lei, mas o texto é longo e usa outras palavras ("recesso", "direito de
arrependimento"). Um chatbot genérico responde com confiança, às vezes inventando o artigo. Aqui, a resposta
só pode usar artigos que a busca encontrou, e cada citação é conferida pelo código.

## Como funciona

```
planalto.gov.br (HTML oficial, versionado em dados/brutos)
      │ parser.py      divide por ARTIGO; remove texto riscado (revogado), vetos e notas do Planalto
      ▼
 PostgreSQL            trecho (texto + embedding) e índice full-text em português sem acento
      │
      │ busca.py       busca híbrida: palavras (ts_rank) + significado (embeddings) → RRF
      ▼
 resposta.py           com chave da API: Claude escreve a resposta em JSON validado e só pode citar
      │                artigos que estavam no contexto (citação inventada é descartada)
      │                sem chave: modo extrativo (mostra os artigos)
      │                abaixo do limiar de similaridade: recusa, sem gastar chamada
      ▼
 api.py + pagina.html  POST /perguntar, GET /artigo/{lei}/{n}, página simples
```

## Avaliação

`avaliacao/perguntas.jsonl` tem 48 perguntas em linguagem leiga, cada uma com o(s) artigo(s) que a
respondem, conferidos no texto da lei: 42 respondidas pelas três leis e 6 fora do escopo (homicídio,
divórcio, férias de CLT...), que devem ser recusadas.

- **acerto@k:** um artigo esperado está entre os k primeiros resultados;
- **MRR:** média de 1/posição do primeiro artigo certo;
- **decisão responder/recusar:** quantas das 48 perguntas ficam do lado certo do limiar de similaridade.

O workflow [Avaliação](.github/workflows/avaliacao.yml) monta o índice e mede três modelos de embedding em
cada mudança da busca. O resultado completo fica em [avaliacao/resultados.md](avaliacao/resultados.md).

## Decisões

- **Dividir por artigo, não por número de caracteres.** O artigo é o que se cita e o que dá para conferir.
  Artigos longos (o art. 5º da LGPD tem 19 definições) viram vários trechos, cada um repetindo o caput.
- **Busca híbrida.** Palavras acertam termos exatos; embeddings entendem paráfrases. O Reciprocal Rank Fusion
  soma as posições das duas listas sem precisar calibrar escalas diferentes.
- **Sem pgvector, de propósito.** São cerca de 270 trechos: a busca vetorial exata é uma multiplicação de
  matrizes em memória (menos de 1 ms) e não tem a perda de precisão de um índice aproximado. O vetor fica no
  PostgreSQL (`real[]`); pgvector passa a valer a pena com dezenas de milhares de trechos.
- **Modelo de embedding local** (ONNX, sem GPU): custo zero por pergunta e nenhum texto enviado a terceiros
  para indexar.
- **Citação conferida pelo código.** O Claude responde em JSON validado (structured outputs); qualquer
  citação de artigo que não estava no contexto é descartada. Se nenhuma sobra, a resposta cai para o modo
  extrativo.
- **Recusar é melhor que inventar.** Abaixo do limiar de similaridade, o sistema diz que as leis não tratam do
  assunto, sem chamar o modelo.
- **Texto da lei versionado.** A avaliação roda sempre sobre a mesma redação; `lei ingerir --baixar-de-novo`
  atualiza.

### Problemas que o HTML do Planalto revelou

Cada um virou teste em `tests/test_parser.py`:

1. **Redação revogada continua na página, riscada** (`<strike>` ou `text-decoration: line-through`). Sem
   tratar, o sistema citaria lei antiga.
2. **O título do capítulo "engolia" o primeiro artigo**: o nome do capítulo às vezes vem na linha seguinte,
   e o parser tomava o artigo como nome. Sumiam os arts. 10 da Lei do Estágio e 1º da LGPD, entre outros.
3. **Número partido no HTML**: o art. 57 da LGPD aparece como "Art. 5 7" e virava uma duplicata do art. 5º.
4. **Ordinais em `<sup>`** ("§ 1 o do art. 2 o") e codificação Windows-1252.

## Como rodar

### Com Docker

```bash
docker compose up --build
```

Página em http://localhost:8000. Na primeira subida, monta o índice (o modelo de embedding tem ~220 MB).
Para as respostas escritas pelo Claude, defina `ANTHROPIC_API_KEY` no `.env`; sem ela, modo extrativo.

### Sem Docker

Requer Python 3.12+ e PostgreSQL com a extensão `unaccent` (vem no pacote contrib).

```bash
python -m venv .venv && .venv\Scripts\activate      # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env                                  # ajuste DATABASE_URL
lei ingerir
lei perguntar "estagiário tem direito a férias?"
lei avaliar --erros
uvicorn lei.api:app
```

## Testes

```bash
pytest           # precisa de TEST_DATABASE_URL para os testes de banco
ruff check .
```

Os testes trocam o modelo de embedding por um falso e determinístico (rápido, sem download); a qualidade
do modelo real é medida à parte, na avaliação. O cliente da API do Claude também é falso nos testes: eles
conferem que citação inventada é descartada, que recusa do modelo cai no modo extrativo e que perguntas
abaixo do limiar não geram chamada.

## Limitações

- Três leis apenas, e só o texto da lei: sem decretos, regulamentos da ANPD ou jurisprudência.
- Vocabulário popular que a lei não usa ("venda casada", "nome sujo") depende do modelo de embedding.
- O limiar de recusa foi calibrado em 48 perguntas; é pouco para garantir o comportamento em produção.
- O modo com o Claude ainda não foi avaliado com chamadas reais (só com cliente falso nos testes).

## Próximos passos

- [ ] Avaliar a resposta gerada (fidelidade ao artigo citado), não só a busca.
- [ ] Glossário de termos populares para expandir a pergunta ("venda casada" → art. 39, I do CDC).
- [ ] Publicar a página com o modo extrativo.
- [ ] Mais leis (CLT, Marco Civil da Internet).

## Fonte e licença

Textos legais: [planalto.gov.br](https://www.planalto.gov.br/), domínio público. Código: MIT.

## Como foi construído

Desenvolvido com auxílio de um assistente de IA (Claude) para acelerar a implementação. As decisões e os
problemas encontrados estão no histórico de commits.
