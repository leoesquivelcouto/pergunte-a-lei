"""Embeddings multilíngues rodando localmente (ONNX, sem GPU e sem custo por chamada)."""

from functools import lru_cache

import numpy as np

from lei.config import MODELO_EMBEDDING


@lru_cache(maxsize=2)
def _modelo(nome: str):
    import truststore
    from fastembed import TextEmbedding  # importação tardia: carregar o modelo leva alguns segundos

    # O download do modelo (Hugging Face) passa a usar os certificados do sistema operacional, como
    # um navegador. A verificação TLS continua ligada.
    truststore.inject_into_ssl()
    return TextEmbedding(nome)


def _prefixos(nome: str) -> tuple[str, str]:
    # Os modelos E5 foram treinados com prefixos diferentes para pergunta e documento.
    return ("query: ", "passage: ") if "e5" in nome.lower() else ("", "")


def normalizar(m: np.ndarray) -> np.ndarray:
    normas = np.linalg.norm(m, axis=-1, keepdims=True)
    return m / np.where(normas == 0, 1, normas)


def documentos(textos: list[str], modelo: str = MODELO_EMBEDDING) -> np.ndarray:
    prefixo = _prefixos(modelo)[1]
    # Lotes pequenos: com o lote padrão (256 textos longos), o modelo grande (e5-large) estourou a memória.
    vetores = np.array(list(_modelo(modelo).embed([prefixo + t for t in textos], batch_size=16)), dtype=np.float32)
    return normalizar(vetores)


def pergunta(texto: str, modelo: str = MODELO_EMBEDDING) -> np.ndarray:
    prefixo = _prefixos(modelo)[0]
    return normalizar(np.array(next(iter(_modelo(modelo).embed([prefixo + texto]))), dtype=np.float32))
