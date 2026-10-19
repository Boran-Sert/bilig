# Hata Analizi Asistanı

12. sınıf AYT Türk Dili ve Edebiyatı için öğrencinin yanlışlarını kazanım bazında analiz eden,
ders kitabından alıntıyla anlatan ve benzer soru üreten sistem.
Bu dosya ekipteki herkesin ve bütün yapay zeka araçlarının uyduğu ortak kurallardır.
Bölüm numaraları ekip planındakilerle aynıdır (`Hata Analizi Asistanı.md`); gerekirse sadece ilgili bölümü oku.

## Servisler
- `apps/web`: React 19, Vite, TypeScript. Sadece gösterir; iş kuralı yazılmaz.
- `services/core`: Java 25, Spring Boot 4.1. Kuralların sahibi: giriş, test, cevap, ilerleme,
  kazanım başarısı, limit, yetki. Tabloları sadece bu servis oluşturur (Flyway).
- `services/ai`: Python 3.13, FastAPI. Claude çağrıları, embedding, arama, PDF hazırlık hattı.
  `ai-worker` aynı imajla iş kuyruğunu çalıştırır.
- `postgres`: PostgreSQL 18, pgvector, pg_textsearch (`infra/postgres`).
- Servise özel kurallar her servisin klasöründeki kural dosyasındadır (14.10).

## Çalışma şekli
- Önce ilgili dosyaları oku, sonra plan çıkar. Plan onaylanmadan birden çok dosyayı değiştirme.
- Sadece istenen işi yap. İşle ilgisiz dosyayı yeniden adlandırma, taşıma, biçimlendirme.
- Emin olmadığın kütüphane API'sini, alanı ya da endpoint'i uydurma: dosyayı oku ya da sor.
- Yeni kod yazmadan önce var olanı ara; aynı işi yapan ikinci fonksiyonu yazma.
- İşi küçük adımlara böl: her adım derlenir ve test edilir.
- Her adımdan sonra o servisin format, lint ve test komutunu çalıştır. Kırmızıysa iş bitmemiştir.
- Aynı hatayı iki denemede çözemezsen dur ve durumu anlat.

## Kesin yasaklar
- `.env` okuma, değiştirme, commit etme. Yeni değişkeni `.env.example`'a ekle.
- Plandaki kütüphane listesinin (13.2) dışında bağımlılık ekleme; gerekiyorsa sor.
- Uygulanmış migration'ı değiştirme; yeni dosya ekle.
- Üretilen dosyaları elle düzenleme: `schema.d.ts`, `components/ui/`, kilit dosyaları.
- Testi geçirmek için testi silme, atlama ya da beklenen değeri değiştirme.
- Kontrolleri susturma (`@Disabled`, skip, `eslint-disable`, `noqa`, `@SuppressWarnings`,
  `@ts-ignore`); zorunluysa yanına issue numarası yaz.
- Hatayı yutma: boş `catch`, `except: pass`.
- Model adını, prompt metnini, kullanıcıya görünen metni ve sabit sayıları koda gömme.
- Öğrencinin adını, e-postasını, okulunu Claude'a ya da log'a gönderme.
- Telifli PDF'i, sayfa görüntüsünü ya da kitap metnini repoya, test verisine ya da örnek dosyaya koyma.
- İş kuralını arayüze yazma.
- Türkçe metinde düz `lower()` / `toLowerCase()` kullanma; `TurkishText` / `tr_lower` kullan.
- Soru için tek kazanım varsayma; kazanımlara sıra ya da ağırlık verme.
- İkinci kullanım çıkmadan interface, soyut sınıf ya da genel yardımcı yazma (istisnalar 13.12).

## Kod kuralları
- Kod adları ve log mesajları İngilizce; docstring, yorum ve kullanıcı metni Türkçe.
- İsimler açıklayıcı; kısaltma yok (`sess` değil `session`).
- Java ve TypeScript camelCase, Python ve SQL snake_case, sabitler `UPPER_SNAKE_CASE`, tablolar tekil.
- Her dosyanın başında ne işe yaradığını anlatan açıklama; her fonksiyonda tek cümlelik docstring.
- Docstring fonksiyonun ne yaptığını söyler, parametre saymaz. Python'da `def` satırının altında,
  Java ve TypeScript'te fonksiyonun üstünde (`/** ... */`).
- Kod içi yorum en fazla 3 kelime. Yapılacak notu: `TODO(#issue)` ve en fazla 3 kelime.
- Kullanıcı metni i18n dosyasında, değişmeyen değer constants dosyasında,
  ortama göre değişen değer ayar dosyasında (13.8).
- Dosya 300, fonksiyon 40 satırı geçmez; geçerse böl.
- Satır uzunluğu 100. Biçimi araç verir: Java Spotless, Python ruff, arayüz Prettier.
- UTF-8 ve LF satır sonu. Java ve Python 4 boşluk; TypeScript, JSON ve YAML 2 boşluk.
- Altyapıya (iş kuyruğu, dosya, önbellek, hız sınırı, embedding, reranker) sadece arayüzle eriş.
- SQL her zaman parametreli; metin birleştirerek sorgu kurma.

## API
- Dışa açık: `/api/**` (Java). İç: `/internal/**` (Python), dışarı açılmaz.
- JSON camelCase, tarih ISO-8601 UTC, id `bigint`. Hata: RFC 9457 + `code` + `requestId`.
- Yetki kontrolü servis katmanında: öğrenci sadece kendi oturumunu, cevabını ve sohbetini görür.
- Doğru cevap ve sorunun kazanımları öğrenci cevaplamadan gönderilmez.
- Arayüz tipleri üretilir (`npm run gen:api`), elle yazılmaz.

## Git ve PR

### Branch
- Her iş bir GitHub Issue ile başlar; branch issue numarasıyla açılır ve 1-3 gün yaşar.
- Ad: `tür/issue-kisa-aciklama`, küçük harf, Türkçe karakter yok. Örnek: `feat/12-test-oturumu`.
- master'a doğrudan push yok; her değişiklik PR ile gelir.
- PR açmadan önce `git fetch origin` ve `git rebase origin/master`.
  Rebase sonrası kendi branch'ine sadece `git push --force-with-lease`.

### Commit
- Biçim: `tür(alan): ne yapıldı`. Örnek: `feat(ai): kaynak profili önerisi eklendi`.
- Tür: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`.
- Alan: `web`, `core`, `ai`, `ingest`, `db`, `infra`, `docs`.
- Commit küçük ve tek amaçlı: bir migration, bir servis metodu ve testi, bir bileşen.
  Hedef 150 satırın altı.
- Her commit derlenir; yarım ya da çalışmayan kod commit edilmez.
- Commit'i geliştirici atar: diff'i satır satır okur, `git add -p` ile parça parça ekler.
- `git add .`, `--no-verify` ve `--force` kullanma.

### PR
- En fazla 400 satır değişiklik; üretilen dosyalar (API tipleri, kilit dosyaları) sayılmaz.
  Geçecekse işi böl.
- Büyük iş sırayla ayrı PR'lara bölünür: migration, servis ve testleri, API, arayüz.
- Açıklama: ne yapıldı, neden, nasıl test edildi, değişen satır sayısı ve `Closes #<issue>`.
  Geliştirici açıklamayı kendi cümleleriyle yazar.
- Prompt, profil ya da eşleştirme değiştiyse değerlendirme çalıştırılır, doğruluk PR'a yazılır.
- Birleşmek için Boran'ın onayı ve yeşil CI şart. Onaydan sonra gelen commit onayı düşürür.
- Birleştirme "Squash and merge" ile yapılır, ardından branch silinir.
- İnceleme 24 saat içinde yapılır.
- Yanlışlıkla commit edilen API anahtarı hemen iptal edilir.

### PR açmadan önce
- Plan çıkarıldı ve okundu.
- Diff satır satır okundu; istenmeyen değişiklik yok, her satır açıklanabiliyor.
- Format, lint, tip kontrolü ve testler yerelde temiz; testler davranışı ölçüyor.
- Yeni bağımlılık yok; varsa ekipte konuşuldu ve gerekçesi PR'da.
- Ekran değiştiyse tarayıcıda denendi ve ekran görüntüsü eklendi.
- API değiştiyse Swagger arayüzünden çağrıldı.
- Yapay zekanın sık yaptığı hatalar (14.5) yok: eski sürüm kodu, uydurma API, sahte uygulama,
  kalıntı `print` / `console.log`, sessiz yan değişiklik.

## Komutlar
- Java: `cd services/core && ./mvnw spotless:apply verify` (Windows: `mvnw.cmd`)
- Python: `cd services/ai && uv run ruff format . && uv run ruff check . && uv run mypy app && uv run pytest`
- Web: `cd apps/web && npm run lint && npm run typecheck && npm test`
- Hepsi birlikte: `docker compose up --build`

## İş ne zaman bitmiş sayılır
- Format, lint, tip kontrolü ve testler temiz; CI yeşil.
- Yeni kullanıcı metni i18n dosyasında, yeni ortam değişkeni `.env.example`'da.
- API değiştiyse arayüz tipleri yeniden üretildi; prompt değiştiyse değerlendirme çalıştırıldı.
- Her dosyada başlık açıklaması, her fonksiyonda tek cümlelik docstring var.
- Boran PR'ı inceledi ve onayladı.
