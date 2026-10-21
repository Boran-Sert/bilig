# ai (Python)
FastAPI, Python 3.13, uv. Claude çağrıları, embedding, arama ve PDF hazırlık hattı.

## Yapı
- Tablo ve kolon adları `docs/veritabani.md`'dedir; ad uydurulmaz.
- app/api iç uç noktalar, app/llm Claude, app/search embedding + BM25 + reranker,
  app/ingest hazırlık hattı, app/tutor anlatım ve sohbet, app/jobs iş kuyruğu,
  app/schemas Pydantic modelleri, app/text Türkçe metin araçları.

## Kurallar
- Claude sadece run_task(...) ile çağrılır; anthropic SDK başka yerde import edilmez.
- Model ve prompt llm_tasks.yaml ve prompts/tde/*.j2 içinde. Prompt'un ilk satırı {# version: N #}.
- JSON çıktı messages.parse(output_format=...) ile; model çıktısı düzenli ifadeyle ayıklanmaz.
- Alıntı gereken görevde kaynaklar search_result bloğu; alıntı ve JSON çıktı aynı çağrıda olmaz.
- Arama sadece hybrid_search(...) ile: vektör + BM25, RRF ile birleşir, sonra reranker.
- Embedding EmbeddingProvider, reranker Reranker arayüzüyle; model başka yerde yüklenmez.
- Servisler arası veri Pydantic modeliyle taşınır, dict ile değil. Her fonksiyonda tip ipucu.
- SQL elle ve parametreli yazılır; Python tablo oluşturmaz.
- Hazırlık adımları tekrar çalıştırılabilir: önce çıktıyı yaz, sonra background_job.last_completed_step'i ilerlet.
- Türkçe metin için app/text/turkish.py (tr_lower, normalize_nfc).

## Test
- pytest ve pytest-asyncio. Testte Claude çağrıları sahte nesneyle; gerçek çağrı sadece app.eval.run'da.
- Test PDF'leri kendi ürettiğimiz küçük dosyalardır.

## Komut
- uv run ruff format . && uv run ruff check . && uv run mypy app && uv run pytest
