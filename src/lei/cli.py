"""Linha de comando: lei ingerir | lei perguntar "..." | lei avaliar"""

import argparse
import sys
from pathlib import Path

import psycopg

from lei.config import database_url


def _conectar() -> psycopg.Connection:
    return psycopg.connect(database_url(), autocommit=True)


def ingerir(args: argparse.Namespace) -> None:
    from lei.ingestao import ingerir_tudo

    with _conectar() as con:
        for sigla, n in ingerir_tudo(con, args.baixar_de_novo).items():
            print(f"{sigla}: {'sem mudanças' if n is None else f'{n} trechos'}")


def perguntar(args: argparse.Namespace) -> None:
    from lei.api import LIMIAR
    from lei.busca import Indice
    from lei.config import limiar_do_modelo
    from lei.resposta import responder, rotulo

    with _conectar() as con:
        indice = Indice(con)
        limiar = LIMIAR if LIMIAR is not None else limiar_do_modelo(indice.modelo)
        r = responder(args.pergunta, indice.buscar(args.pergunta), limiar)
    print(r.texto)
    for c in r.citacoes:
        print(f"\n[{rotulo(c)}]\n{c.texto}")
    print(f"\n{r.aviso}")


def avaliar(args: argparse.Namespace) -> None:
    from lei.avaliacao import avaliar as medir
    from lei.avaliacao import carregar, melhor_limiar
    from lei.busca import Indice

    perguntas = carregar(Path(args.arquivo))
    with _conectar() as con:
        indice = Indice(con, args.modelo)
        print(f"{len(perguntas)} perguntas | modelo {indice.modelo}\n")
        print("| modo | acerto@1 | acerto@3 | acerto@5 | MRR | recusa certa |")
        print("|---|---|---|---|---|---|")
        for modo in ("palavras", "vetorial", "hibrida"):
            m = medir(indice, perguntas, modo)
            limiar, certas, total = melhor_limiar(m.sim_dentro, m.sim_fora)
            print(
                f"| {modo} | {m.acerto_1:.2f} | {m.acerto_3:.2f} | {m.acerto_5:.2f} | {m.mrr:.2f} "
                f"| {certas}/{total} (limiar {limiar:.2f}) |"
            )
        if args.erros:
            print("\nPerguntas em que o artigo certo não ficou em 1º (busca híbrida):")
            for id_, pergunta, top in m.erros:
                print(f"  {id_:>2}. {pergunta} -> {top}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="lei", description=__doc__)
    sub = p.add_subparsers(required=True)

    s = sub.add_parser("ingerir", help="baixa as leis e monta o índice")
    s.add_argument("--baixar-de-novo", action="store_true")
    s.set_defaults(func=ingerir)

    s = sub.add_parser("perguntar", help="faz uma pergunta")
    s.add_argument("pergunta")
    s.set_defaults(func=perguntar)

    s = sub.add_parser("avaliar", help="mede a busca com o conjunto de perguntas")
    s.add_argument("--arquivo", default="avaliacao/perguntas.jsonl")
    s.add_argument("--modelo", help="outro modelo de embedding, calculado em memória")
    s.add_argument("--erros", action="store_true")
    s.set_defaults(func=avaliar)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
