-- Busca por palavras em português ignorando acentos ("estagio" encontra "estágio").
CREATE EXTENSION IF NOT EXISTS unaccent;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'pt') THEN
        CREATE TEXT SEARCH CONFIGURATION pt (COPY = portuguese);
        ALTER TEXT SEARCH CONFIGURATION pt
            ALTER MAPPING FOR hword, hword_part, word WITH unaccent, portuguese_stem;
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS lei (
    sigla        text PRIMARY KEY,
    nome         text NOT NULL,
    numero       text NOT NULL,
    url          text NOT NULL,
    hash_html    text NOT NULL,
    modelo       text NOT NULL,
    carregada_em timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS trecho (
    id          serial PRIMARY KEY,
    lei         text NOT NULL REFERENCES lei (sigla) ON DELETE CASCADE,
    artigo      text NOT NULL,
    parte       smallint NOT NULL CHECK (parte >= 1),
    contexto    text NOT NULL,
    texto       text NOT NULL,
    -- Com pgvector seria vector(384). Com ~300 trechos, a busca exata em memória basta (ver README).
    embedding   real[] NOT NULL,
    busca       tsvector GENERATED ALWAYS AS (to_tsvector('pt', contexto || ' ' || texto)) STORED,
    UNIQUE (lei, artigo, parte)
);

CREATE INDEX IF NOT EXISTS trecho_busca_idx ON trecho USING gin (busca);
