FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY avaliacao ./avaliacao
COPY dados/brutos ./dados/brutos
RUN pip install --no-cache-dir .

RUN useradd --create-home lei
USER lei
# Usa o texto das leis versionado no repositório; o modelo de embedding é baixado na primeira subida.
ENV FASTEMBED_CACHE_PATH=/home/lei/modelos LEI_DADOS=/app/dados

EXPOSE 8000
# Na primeira vez, baixa as leis e o modelo de embedding e monta o índice; depois só confere se mudou.
CMD ["sh", "-c", "lei ingerir && uvicorn lei.api:app --host 0.0.0.0 --port 8000"]
