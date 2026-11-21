"""Compara modelos de embedding e modos de busca no conjunto de perguntas. Gera avaliacao/resultados.md.

Uso: python avaliacao/comparar_modelos.py   (precisa do índice montado com `lei ingerir`)
"""

import time
from pathlib import Path

import psycopg

from lei.avaliacao import avaliar, carregar, melhor_limiar
from lei.busca import Indice
from lei.config import database_url

MODELOS = [
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    "intfloat/multilingual-e5-large",
]
PASTA = Path(__file__).parent


def main() -> None:
    perguntas = carregar(PASTA / "perguntas.jsonl")
    dentro = sum(not p.fora_do_escopo for p in perguntas)
    linhas = [
        "# Resultados da avaliação da busca",
        "",
        f"{len(perguntas)} perguntas escritas à mão: {dentro} respondidas pelas leis e "
        f"{len(perguntas) - dentro} fora do escopo (devem ser recusadas).",
        "",
        "| modelo | modo | acerto@1 | acerto@3 | acerto@5 | MRR | decisão responder/recusar | tempo/pergunta |",
        "|---|---|---|---|---|---|---|---|",
    ]
    erros = {}
    with psycopg.connect(database_url(), autocommit=True) as con:
        for modelo in MODELOS:
            indice = Indice(con, modelo)
            nome = modelo.split("/")[-1]
            for modo in ("palavras", "vetorial", "hibrida"):
                if modo == "palavras" and modelo != MODELOS[0]:
                    continue  # a busca por palavras não depende do modelo
                inicio = time.perf_counter()
                m = avaliar(indice, perguntas, modo)
                ms = (time.perf_counter() - inicio) / len(perguntas) * 1000
                limiar, certas, total = melhor_limiar(m.sim_dentro, m.sim_fora)
                rotulo = "—" if modo == "palavras" else nome
                linhas.append(
                    f"| {rotulo} | {modo} | {m.acerto_1:.2f} | {m.acerto_3:.2f} | {m.acerto_5:.2f} | {m.mrr:.2f} "
                    f"| {certas}/{total} (limiar {limiar:.2f}) | {ms:.0f} ms |"
                )
                if modo == "hibrida":
                    erros[nome] = m.erros
            print(linhas[-1], flush=True)

    linhas += ["", "## Onde a busca híbrida errou o 1º lugar", ""]
    for nome, lista in erros.items():
        linhas.append(f"**{nome}** ({len(lista)} perguntas)")
        linhas.append("")
        linhas += [f"- {i}. {p} → veio {top}" for i, p, top in lista]
        linhas.append("")
    (PASTA / "resultados.md").write_text("\n".join(linhas), encoding="utf-8")
    print("ok", flush=True)


if __name__ == "__main__":
    main()
