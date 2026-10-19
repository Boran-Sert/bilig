# Projenin PostgreSQL imajı.
# pgvector imajının üstüne pg_textsearch (BM25) eklentisini kurar ve veritabanını ICU tr-TR yereliyle başlatır.
# Eklentileri veritabanında ilk Flyway migration'ı açar (CREATE EXTENSION).
FROM pgvector/pgvector:0.8.7-pg18-trixie

ARG PG_TEXTSEARCH_VERSION=1.5.1
ARG TARGETARCH

ADD https://github.com/timescale/pg_textsearch/releases/download/v${PG_TEXTSEARCH_VERSION}/pg-textsearch-v${PG_TEXTSEARCH_VERSION}-pg18-${TARGETARCH}.zip /tmp/pg_textsearch.zip

RUN apt-get update \
    && apt-get install -y --no-install-recommends unzip \
    && unzip /tmp/pg_textsearch.zip -d /tmp/pg_textsearch \
    && apt-get install -y --no-install-recommends /tmp/pg_textsearch/*.deb \
    && apt-get purge -y --auto-remove unzip \
    && rm -rf /tmp/pg_textsearch /tmp/pg_textsearch.zip /var/lib/apt/lists/* \
    && echo "shared_preload_libraries = 'pg_textsearch'" >> /usr/share/postgresql/postgresql.conf.sample

ENV POSTGRES_INITDB_ARGS="--locale-provider=icu --icu-locale=tr-TR"
