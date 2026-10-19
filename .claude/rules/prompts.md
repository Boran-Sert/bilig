---
paths:
  - "services/ai/prompts/**"
  - "services/ai/llm_tasks.yaml"
---
# Prompt ve görev kuralları
- Prompt dosyası prompts/tde/<görev>.j2 (Jinja2). İlk satır sürüm: {# version: N #}.
- Prompt değişince sürüm bir artar; sürüm her çağrıyla llm_call_log'a yazılır.
- Model adı sadece llm_tasks.yaml'da yazılır. Görev ayarları da orada: model, prompt, max_tokens, alıntı, tool'lar, batch.
- Alıntı gereken görevde kaynaklar search_result bloğu; alıntı ve JSON çıktı aynı görevde olmaz.
- JSON dönen görevin çıktısı bir Pydantic modeliyle tanımlanır.
- Sistem prompt'unda "emin değilsen bunu açıkça söyle" kuralı bulunur.
- Öğrencinin adı, e-postası ve okulu prompt'a girmez; sadece sayısal kullanıcı numarası.
- Prompt ya da görev ayarı değişen PR'da değerlendirme çalıştırılır ve doğruluk PR'a yazılır:
  uv run python -m app.eval.run --task <GÖREV>
