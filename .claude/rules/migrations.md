---
paths:
  - "services/core/src/main/resources/db/migration/**"
---
# Migration kuralları
- Dosya adı zaman damgalı: V202610161430__create_session_tables.sql
- Uygulanmış dosya değiştirilmez; düzeltme yeni dosyayla yapılır.
- Tablo ve kolon tekil, snake_case. id bigint generated always as identity.
- Her tabloda created_at timestamptz not null default now().
- Sabit değer kümeleri text + CHECK, değerler büyük harf.
- Vektör vector(768) + HNSW (vector_cosine_ops). Kelime araması BM25 (pg_textsearch, 'turkish').
- Dosyanın başında ne yaptığını anlatan -- açıklama.
