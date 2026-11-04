SoftITo Yapay Zeka Yazılımcılığı · Ekip planı · Sürüm 3

# Hata Analizi Asistanı

Öğrenci AYT Edebiyat sorusu çözer. Yanlış yaptığında sistem soruyu ders kitabından alıntıyla anlatır ve aynı kazanımdan yeni bir soru verir.

*A**B**C**D**E* İlk sürüm: 12. sınıf AYT Türk Dili ve Edebiyatı, web 16 Ekim 2026 Hazırlayan: Boran, Team Lead

İçindekiler

1. [01Ne yapıyoruz](#s1)
2. [02Ürün yönü](#s2)
3. [03Ekip](#s3)
4. [04Sistem](#s4)
5. [05Bilgi tabanı](#s5)
6. [06Hazırlık hattı](#s6)
7. [07Yükleme ekranı](#s7)
8. [08Öğrenci akışı](#s8)
9. [09Arka plan akışı](#s9)
10. [10Yapay zeka](#s10)
11. [11Veritabanı](#s11)
12. [12Git ve PR](#s12)
13. [13Teknoloji ve kurallar](#s13)
14. [14Yapay zekayla geliştirme](#s14)
15. [15Yol haritası](#s15)
16. [16Sonraya kalanlar](#s16)
17. [··Terimler](#terimler)

01

## Ne yapıyoruz

İlk sürüm, 12. sınıf öğrencileri için AYT Türk Dili ve Edebiyatı. Öğrencinin bir sorudaki yanlışı dört adımda öğrenmeye dönüşür.

1. 1**Test çözer**Ünite testleri ve AYT denemeleri. Yarıda bırakırsa kaldığı yerden devam eder.
2. 2**Yanlış yapar**Sistem sorunun hangi kazanıma ait olduğunu bilir ve kaydeder.
3. 3**Kaynaklı anlatım**Yapay zeka anlatır, altında ders kitabındaki ilgili paragraf ve sayfası durur.
4. 4**Benzer soru**Aynı kazanımdan yeni soru çözer. Takılırsa ipucu açar.

### Neden 12. sınıf AYT Edebiyat?

- 2026-27'de 9, 10 ve 11. sınıflar Maarif Modeli'ne geçti; 12. sınıf hâlâ eski öğretim programıyla okuyor. Elimizdeki ders kitapları, ÖDSGM kazanım testleri ve OGM materyallerinin hepsi bu programa göre.
- AYT Edebiyat 9-12'nin tamamını kapsar. Program katmanını dört sınıf için tek PDF'ten birden kurarız; içeriği önce 12. sınıftan başlayarak doldururuz.
- Edebiyat'ta kaynak bol: ders kitabı, kazanım testi, soru bankası, konu anlatımı.

İlk sürümde yok: görselli sorular, öğretmen paneli, mobil uygulama, ödeme, Maarif Modeli sınıfları. Tam liste [Bölüm 16](#s16)'da.

02

## Ürün yönü

Demo öğrenci ekranıyla yapılır. Altyapı ise baştan kurumlara ve başka platformlara açılacak şekilde kurulur.

- **Öğrenci ve veli (B2C):** İlk sürümün yüzü.
- **Okul ve kurs merkezi (B2B):** Öğretmen paneli ve sınıf raporları sonra gelir. Gereken veri ilk günden kaydedilir.
- **Platform entegrasyonu (B2B2C):** Bütün özellikler belgelenmiş API üzerinden çalışır. MEBİ öğrenciye ücretsiz olduğu için en güçlü satış hikâyesi bu olabilir.

| Fark yaratacak madde | İlk sürümde | Şimdi sadece altyapı | Sonra |
| --- | --- | --- | --- |
| Kişiselleştirme | Kazanım bazlı başarı. Hata türü tahmini: bilgi eksikliği, kavram yanılgısı, dikkat, okuma | Her cevapta süre, ipucu kullanımı, anlatımın açılıp açılmadığı. Boş `difficulty` kolonu | Zorluğa göre soru seçimi, konu sırası |
| Yapay zeka öğretmen | İpucu, kaynaklı anlatım, "Başka örnekle anlat", sohbet, benzer soru, anlatım tarzı seçimi | MEB açıklamaları kazanım kuralı olarak saklanır | Çözüm adımlarını inceleme (sayısal derslerde) |
| Entegrasyon | – | OpenAPI, `tenant_id`, `external_user_id`, renkler token'larda, tool'lar sade fonksiyon | Kurum girişi (SSO), API anahtarı, MCP sunucusu, kurum logosu |
| Kurum raporu | – | Her cevap kazanım ve hata türüyle kayıtlı; rapor bir SQL sorgusu | Öğretmen paneli, sınıflar, ön test / son test |
| Güvenilirlik | Ders kitabından alıntı kartı, "Hatalı içerik bildir", üretilen soruya etiket, "emin değilsen söyle" kuralı | Her içerikte kaynak, sayfa, model ve prompt sürümü | Veli ve kurum kontrolleri |

Hata türü tek bir cevaptan güvenilir şekilde anlaşılamaz. Öğrenciye karar gibi gösterilmez; birçok cevapta tekrar eden örüntü raporlanır.

03

## Ekip ve görev dağılımı

Altı rolün her birinin bir sahibi var. Dağılım proje ilerledikçe değişebilir; değişiklik bu tabloya yazılır.

| Kişi | Rol | Bu projede yaptığı iş |
| --- | --- | --- |
| Boran | Ürün sahibi, Team Lead, Yapay zeka | Planlama, hoca ve kurum görüşmeleri, sunum. Mimari kararlar, repo ve kurallar. Bütün PR'ların incelenmesi ve onayı. Anlam katmanı: bilgi katmanı (yazar, eser, akım), kazanım eşleştirme, alıntılı anlatım, sohbet tool'ları, soru üretme ve doğrulama. |
| Eren | Backend | Java servisi: tablolar, giriş ve roller, testler, oturum ve cevap kaydı, öğrenci paneli. |
| Selman | Backend | Java servisi: `job` tablosu, yükleme ve inceleme API'leri, iş durumu, Python'a bağlantı ve akış aktarımı. |
| Fatih | Veri, yapay zeka | İçerik hattı: program katmanı, metin katmanı kontrolü, kaynak profilleri, kodla ve görüntüden ayrıştırma, cevap anahtarları, kontroller. |
| Özcan | Frontend | Öğrenci ekranları ve içerik ekibi ekranı: yükleme, iş durumu, inceleme listesi. Bölüm 7 ve 8'deki taslaklar. |
| Sinan | İş geliştirme, UX | Rakip analizi, fiyatlandırma, MEB izin süreci, öğrenci ve öğretmenlerle kullanıcı testleri, anlatım tarzı metinleri, demo senaryosu. |

- **Fatih ve Boran** 100 soruluk kontrol setini birlikte hazırlar: her sorunun ölçtüğü bütün kazanımları insan işaretler. Eşleştirmenin doğruluğu bu setle ölçülür.
- **Takılınca:** Bir işte yarım günden fazla takılan ekip kanalına yazar.

04

## Sistem nasıl çalışıyor

Sistem dört parçadan oluşur ve `docker compose up` ile tek komutla çalışır. Öğrenci ve içerik ekibi sadece web arayüzünü görür.

Kesik çizgili kutu dış servis. Python servisi hem anlık istekleri (anlatım, sohbet) hem de arka plandaki hazırlık işlerini çalıştırır.

- Tarayıcı sadece web arayüzüyle konuşur; arayüz her isteği Java servisine iletir.
- Java kuralların sahibidir: kim giriş yaptı, cevap doğru mu, ilerleme yüzde kaç, hangi dosya yüklendi. Yapay zeka gerektiğinde Python'u çağırır.
- Claude ile konuşan, embedding modelini ve hazırlık işlerini çalıştıran tek yer Python servisidir.
- İki servis aynı veritabanını kullanır. Tabloları her zaman Java tarafı oluşturur (Flyway).
- Hazırlık işleri ayrı bir kuyruk sistemi yerine PostgreSQL'deki `job` tablosundan alınır.

### Kullanılan hazır araçlar

| Parça | Araçlar |
| --- | --- |
| Web arayüzü | React, Vite, TypeScript, shadcn/ui, TanStack Query, Recharts, react-markdown, react-dropzone |
| Java servisi | Spring Boot (Web, Security, Data JPA, Validation), Flyway, springdoc-openapi |
| Python servisi | FastAPI, anthropic SDK, pypdfium2 ve Tesseract (PDF ve OCR), sentence-transformers (bge-m3 embedding, bge-reranker-v2-m3), psycopg, pgvector, Pydantic, Jinja2, rapidfuzz |
| Veritabanı | PostgreSQL, pgvector (vektör araması), pg_textsearch (Türkçe BM25 kelime araması) |

Sürümler ve her iş için seçilen kütüphanelerin tam listesi [Bölüm 13](#s13)'te.

### Repo yapısı

```
bilig/
├── apps/web/            React: öğrenci ve içerik ekibi ekranları
├── services/core/       Java servisi, Flyway migration'ları
├── services/ai/         Python servisi: API, iş kuyruğu çalışanı, prompt'lar, profiller
├── data/                Kontrol seti, Türkçe kelime listesi (PDF'ler konmaz)
├── docs/
├── infra/postgres/      Postgres imajı: pgvector + pg_textsearch
├── .claude/             Claude Code ayarları, hook'lar, kurallar (Bölüm 14)
├── .github/             CI iş akışları ve CODEOWNERS
├── AGENTS.md, CLAUDE.md, PLAN.md
├── .editorconfig, .gitattributes
├── docker-compose.yml
└── .env.example
```

Her servisin iç yapısı [Bölüm 13.3](#s13)'te.

### İleride eklenecekler için hazırlık

Kural: değişen şey veriyse tabloya, davranışsa interface'e.

| Değişebilecek şey | Nasıl eklenir |
| --- | --- |
| Yeni kaynak türü | Yeni bir profil dosyası. Bilinmeyen bir yapıysa Python'da yeni bir `SourceReader` sınıfı. |
| Yeni ders veya sınıf | O dersin öğretim programı PDF'i hatta verilir, `prompts/<ders>/` klasörü açılır. |
| Maarif Modeli | `curriculum` tablosuna yeni satır, eski ve yeni kazanımlar için eşleme tablosu. |
| Yeni sınav türü | `exam_type` kolonu ve `ScoringPolicy` interface'i (AYT: net = doğru − yanlış ÷ 4). |
| Yeni soru tipi | `question.type` ve blok yapılı `content`. Tablo değişmez. |
| Model değişimi | `llm_tasks.yaml` dosyasında tek satır. |
| Kurumlar | `tenant` tablosu hazır; paketler ve limitler satışa çıkarken tabloya eklenir. |
| Altyapı büyümesi | İş kuyruğu, dosya saklama, hız sınırı, önbellek, embedding ve reranker birer arayüzün arkasında. RabbitMQ, Redis ya da S3'e geçiş yeni bir uygulama ve ayar değişikliğidir ([Bölüm 13.12](#s13)). |

05

## Bilgi tabanı

Bütün içerik dört katmanlı tek bir bilgi tabanında durur. Her ders ve sınıf aynı şablonu kullanır; alt katmandaki her kayıt üst katmana bağlanır ve kaynağını taşır.

Örnek bağlar ders kitabının "Roman Türleri ve Özellikleri" kutusundan. Mavi kutular programdaki kazanımlar; her şey sonunda bunlara bağlanır.

| Katman | Ne içerir | Nereden gelir |
| --- | --- | --- |
| Program | Ders › alan › tür › kazanım ve MEB açıklaması. Sınıf › ünite › dönem, metin listesi, dil bilgisi konusu. | Öğretim programı PDF'i, bir kez |
| Bilgi | Yazar, eser, dönem, akım, tür, kavram notları ve aralarındaki bağlar. Her bağın dayandığı blok kayıtlı. | Ders kitapları ve konu anlatımları |
| İçerik | Paragraf paragraf konu anlatımı, alıntılar, metin örnekleri, sorular. Her biri sayfa ve kaynak bilgisiyle. | Ders kitabı, ÖDSGM, OGM, soru bankası, üretim |
| Öğrenci | Cevaplar, süre, ipucu kullanımı, hata türü, sohbetler. | Uygulama |

### Yapay zeka bilgi tabanını nasıl kullanır

- Bilgi tabanı Obsidian gibi çalışır: her düğüm bir not, notlar birbirine bağlı. Fark şu ki notlar dosyada değil, PostgreSQL'de durur; böylece aynı anda yüzlerce öğrenciye cevap verir ve SQL ile vektör aramasını birlikte kullanır.
- Model bilgi tabanını üç okuma tool'uyla gezer: `search_notes`, `open_note`, `get_outcome`. Bir cevapta en fazla 3 tool çağrısı yapılır.
- `search_notes` ortak arama fonksiyonunu kullanır: vektör ve BM25 sonuçları birleştirilir, reranker en iyi 5 notu seçer (13.11).
- Bilgi tabanı model için sadece okunur. Yeni bilgi yalnızca hazırlık hattından ve insan onayıyla girer; sohbetteki bir hata herkese yayılamaz.
- Ekip isterse bilgi katmanı Obsidian kasası olarak dışa aktarılıp gezilebilir. Obsidian insanlar için bir görüntüleyici, sistemin parçası değil.
- Ayrı bir graf veritabanı ya da GraphRAG kurulmaz. İskelet programda hazır; iki tablo (`kg_node`, `kg_edge`) yeter.

06

## Hazırlık hattı: içerik sisteme nasıl girer

Her kaynak bir kez işlenir ve aynı ortak formata dönüşür. Kaynaklar birbirinden çok farklı ama her biri kendi içinde tutarlı; bu yüzden pahalı işler kaynak başına bir kez yapılır, sayfalar ucuz yoldan işlenir.

Öğretim programı bu hattın özel bir kaynağıdır; kazanım ağacını kurar (A1). Diğer bütün kaynaklar aynı yoldan geçer.

Hattın adımları sırayla REGISTERED (A2), EXTRACT (A3, A5, A6), OUTCOMES (A8) ve INDEX (A9). Kontroller (A6) EXTRACT'ın içinde çalışır. Bilgi katmanı (A7) henüz hatta adım değil (#139). Her adım bitince işe kaydedilir; hata alan iş kaldığı adımdan sürer. Son adımdan sonra kaynak yayına girer ya da incelemede bekler (Yayına alma).

### A1Program katmanını kurma

Girdi

Öğretim programı PDF'i. Word'den üretilmiş, metin katmanı sağlam.

Nasıl

- PDF dış yüzü (`app.ingest.pdf.read_lines`) metni satır satır çıkarır. Kazanımlar düzenli ifadeyle yakalanır: `A.2. 5. Metnin olay örgüsünü belirler.`
- Kazanımın altındaki a, b, c maddeleri o kazanımın MEB açıklaması olarak kaydedilir. Bu açıklamalar yapay zekanın kurallarıdır, örneğin "aruz kalıplarını buldurmaya yönelik çalışmalara yer verilmez".
- Ünite tabloları üç sütunlu olduğu için her tablo sayfası bir kez Sonnet'e metin ve görüntüyle verilir. Çıktı JSON: sınıf, ünite, süre, dönemler, metin sayıları, dil bilgisi konuları.
- Üniteler kazanım gruplarına kuralla bağlanır: Hikâye, Roman, Masal → A.2; Şiir → A.1; Tiyatro → A.3; Makale, Deneme → A.4.

Kontrol

Kazanım sayıları programın kendi tablosuyla tutmalı: Şiir 13, Öyküleyici 16, Tiyatro 14, Bilgilendirici 15, Yazma 12, Konuşma 17, Dinleme 8.

Kim

Fatih çıktıyı tablo hâlinde kontrol eder. Ders başına bir kez.

### A2Kaynak kaydı

Nasıl

Dosyanın parmak izi (sha256) alınır; aynı dosya ikinci kez işlenmez. Türü dosyayı yükleyen seçer: ders kitabı, test ya da soru bankası. Program ve cevap anahtarı komutla yüklenir. İzin durumu ve yayıncı kaydedilir. REGISTERED adımı her sayfayı 150 dpi PNG olarak saklar; "Sayfayı aç" ve görüntü yolu bu görüntüyü kullanır.

Sonuç

Bir `source` kaydı, sayfa kayıtları ve kuyrukta bir iş.

### A3Metin katmanı kontrolü

Nasıl

Ayrı bir adım değildir; PDF okuması (A5) sırasında çalışır. PDF motoru her sayfanın harflerini okur, gizli metni atar ve bozuk eşlemeli harfleri ("Ġ", "Ģ") OCR oylarıyla onarır; onarılmış sayfa metninde kelimelerin ne kadarının Türkçe kelime listesinde bulunduğuna bakılır. %90 üstü metin yolu. Altındaysa önce bozuk font eşlemesi kodla düzeltilmeye çalışılır; düzeltilen metin %90'ı geçerse düzeltme harflere uygulanır, geçmezse sayfa Tesseract'la da okunur ve oranı yüksek okuma kalır. Metin katmanı olmayan sayfa ve metinli sayfadaki yazılı resimler Tesseract'la (Türkçe) okunur.

Örnek

Masal sayfasında "Masal; genellikle" metni "0DVDO JHQHOOLNOH" diye çıkıyor: her harf 29 kod noktası kaymış, fontun karakter eşlemesi bozuk. Kayma sabitse kodla geri çevrilir ve sayfa metin yoluna döner; Türkçe harflerde (ş, ğ, ı) aynı kaymanın olup olmadığı henüz denenmedi. Soru bankası çıktısında hiç metin yok: sayfa Tesseract'la okunur. Testlerde görüntü yolu henüz yok; metin yine zayıf kalırsa sayfa incelemeye düşer. Program, ÖDSGM testi ve MEB kitapları metin yolundan gider.

### A4Kaynak profili (kaldırıldı)

Yayınevine ya da seriye özel profil yoktur. Ölçüler (gövde boyutu, paragraf aralığı, başlık stili, soru numarası ve şık biçimi) her belgeden yeniden öğrenilir; yeni bir kitap için dosya yazılmaz, onay beklenmez.

### A5Ortak formata ayrıştırma

Kitap

Kitap motoru (`app.ingest.pdf.read_textbook`) kodla çalışır, LLM yok. Kenarda tekrarlayan satırlar, sayfa numarası ve logolar atılır; okuma sırası XY-cut ile bulunur, kutular bölünmez; paragraf eşiği belgeden öğrenilir. Başlıklar stil ve hizalamadan bulunur, düzey alır ve başlık yolu kurulur. Kutudaki metin BILGI, diğer paragraflar METIN olur; ALINTI ve ETKINLIK üretilmez. Anlatım ve sohbet kitaptan alıntıyı bu blokların metniyle aynen yapar. İtalik `*...*` olarak korunur. Sütun ya da sayfa sonunda yarım kalan paragraf sonraki sütunda sürer.

Görüntü

Metin katmanı A3'ten sonra da zayıf kalan kitap sayfası (LOW_TEXT_LAYER) REGISTERED'da saklanan PNG'den okunur. Haiku (PAGE_EXTRACT) sayfayı JSON şemasıyla BASLIK, BILGI ve METIN bloklarına ayırır. Hiç metin dönmezse ya da model emin olmadığını söylerse aynı sayfa Sonnet'e (PAGE_EXTRACT_FALLBACK) gider. Okuma geçerse sayfanın motor blokları görüntüden okunanlarla değişir ve sayfa incelemeye düşmez. İkisi de geçemezse motorun okuması kalır, sayfa incelemeye düşer. Görüntüden okunan metin metin katmanıyla karşılaştırılmaz; bu sayfalarda katman zaten bozuk. Şimdilik sadece kitap sayfaları bu yoldan geçer (#142).

Testler

Her zaman metin ve görüntü birlikte gider. Altı çizili "değildir", kelime altındaki I–V numaraları ve tablolar ancak görüntüde görünür. Çıktı: soru kökü blokları, 5 şık, cevap.

Cevap

Sorunun altındaysa ("Cevap: A") ayrıştırmada alınır. Ayrı sayfa ya da dosyaysa ("1-B 2-E") düzenli ifadeyle okunup numarayla eşlenir. Yoksa Sonnet çözer, soru incelemeye düşer.

Kayıt

Her blok: tür, markdown metin, sayfa, konum, kaynak, güven. Sayfa görüntüsü saklanır; "Sayfayı aç" bunu gösterir.

```
{"source": "TDE 12 Ders Kitabı", "page": 174, "blocks": [
  {"type": "BASLIK", "markdown": "Roman Türleri ve Özellikleri"},
  {"type": "BILGI", "title_path": "TDE 12 Ders Kitabı › Roman › Roman Türleri ve Özellikleri",
   "markdown": "**Tarihî Roman:** Konusunu tarihten alan romanlardır... *Devlet Ana* (Kemal Tahir)"},
  {"type": "METIN", "title_path": "TDE 12 Ders Kitabı › Roman › Üslûp",
   "markdown": "En kısa tanımıyla üslûp...", "pages": [174, 175]}
]}
```

### A6Kontroller

Sorular

Şık sayısı 5 mi, şık harfleri sıralı mı, şıklar ve kök dolu mu, cevap şıklardan biri mi, numaralar sıralı mı. Cevabı bulunamayan soru da ayrılır.

Sayfa

Metin katmanı A3'ten sonra da zayıf mı (LOW_TEXT_LAYER), çözülemeyen harf kaldı mı (UNDECODED_GLYPHS). Kitapta zayıf sayfa önce görüntü yolundan okunur; okunursa sorun sayılmaz.

Kaynak

Hiç içerik çıktı mı (NO_CONTENT), testin ünitesi bulundu mu (UNIT_NOT_FOUND), kökünde soru olmayan şık kümesi var mı (NOT_MULTIPLE_CHOICE).

Sonuç

Kontrolü geçemeyen soru yazılmaz. Kaynağın bütün sorunları tek inceleme kaydında toplanır: cevap anahtarı eksikleri NO_ANSWER_KEY, diğerleri VALIDATION_FAILED. Her sorun kodu, sayfası, testi ve soru numarasıyla kayıtlıdır (`review_item.detail`). Sorunu olan kaynak REVIEW durumunda kalır. Hiçbir içerik kontrolsüz yayına girmez.

### A7Bilgi katmanı

Kural

`*Eser* (Yazar)` ve `*Eser* [Yazar (okunuş)]` kalıpları eser ve yazar notu ile aralarında bağ üretir. Bilgi Köşesi tablosunun her satırı bir zincire dönüşür: kavram (Tarihî Roman) → örnek eser → yazar.

Haiku

Kalan düz metinden yazar, eser, dönem, akım ve kavramları bağlarıyla çıkarır. Her bağ hangi bloğa dayandığını göstermek zorunda; dayanağı olmayan atılır.

Birleştirme

Aynı kişinin farklı yazımları birleştirilir (Viktor Hügo = Victor Hugo): Türkçe küçük harf, aksan temizliği, benzerlik puanı. Emin olunamayanlar incelemeye düşer.

### A8Kazanım eşleştirme

MEB soruları sık sık birden çok kazanımı aynı anda ölçer. Bu yüzden bir soru birden çok kazanıma bağlanabilir. Kazanımlar arasında sıra, ağırlık ya da "ana kazanım" yok; MEB'deki gibi soru bir kazanımı ya ölçer ya ölçmez.

1. **Ünite:** Kaynakta yazıyorsa ("Hikâye - 5", kitabın ünite başlığı) oradan alınır. Ünite bulunamazsa ya da ünitenin bağlı kazanımı yoksa (Giriş, Söylev) adaylar bütün kazanımlardan aranır.
2. **Adaylar:** O ünitenin kazanımları vektör ve BM25 aramasıyla sıralanır; iki sonuç RRF ile birleştirilir. Sorularda ilk 16, paragraflarda ilk 5 aday alınır. Kelime araması soru köküyle birlikte şıklarda da yapılır; "mekân", "bakış açısı" gibi boyutlar çoğu zaman şıklarda geçer. Kazanım vektörü yoluyla birlikte hesaplanır: "12. sınıf › Roman › Metnin olay örgüsünü belirler".
3. **Seçim:** Haiku her seferinde temiz bağlamla adaylar arasından sorunun ölçtüğü bütün kazanımları seçer, her biri için bir güven verir.
4. **Kontrol (kod):** En az bir kazanım var ve kodlar aday listesinde. Herhangi bir kazanımın güveni orta ya da düşükse soru incelemeye düşer (LOW_CONFIDENCE) ve taslak kalır; düşmeyen içerik hemen yayına girer. Güven sadece bu karar için; kayıtta kazanım ya vardır ya yoktur.
5. **Kaynakta kazanım yazıyorsa** (bazı test ve soru bankaları kazanım kodunu basar) o kazanımlar doğrudan bağlanır, model çalışmaz.
6. **Paragraflar** da birden çok kazanıma bağlanabilir. Etkinlik blokları eşlenmez ve kaynak olarak gösterilmez.

```
// OUTCOME_MATCH çıktısı (Pydantic şeması)
OutcomeMatch {
  outcomes: { code: string,
              confidence: "HIGH" | "MEDIUM" | "LOW" }[]   // en az bir kazanım
}
```

### Örnek: bir soru, dört kazanım

Soru bankası çıktısındaki Soru 2. Tabloda tema, kahraman sayısı, mekân, zaman ve bakış açısı verilmiş, doğru cevap E. Yanlış şıklar farklı boyutlarda tutmuyor; bu yüzden soru dört kazanımı birden ölçüyor ve dördüne de bağlanıyor.

| Şık | Neden tutmuyor | İlgili kazanım |
| --- | --- | --- |
| A | Saat on biri bir saat geçmiş, sabah değil; üç kişi var | A.2.7 Zaman ve mekân, A.2.6 Şahıs kadrosu |
| B | Anlatıcı kahraman değil, üçüncü kişi; mekân park değil | A.2.8 Anlatıcı ve bakış açısı, A.2.7 Zaman ve mekân |
| C | Mekân hastane | A.2.7 Zaman ve mekân |
| D | Tema dostluk değil, mekân park değil | A.2.3 Tema ve konu, A.2.7 Zaman ve mekân |
| E | Doğru cevap | – |

Kayıtta sadece "bu soru A.2.3, A.2.6, A.2.7 ve A.2.8'i ölçer" yazar. Şık bazında kayıt tutulmaz; öğrencinin hangi boyutu kaçırdığını "Neden yanlış?" anlatımı söyler, çünkü model öğrencinin şıkkını görür.

| Nerede | Nasıl davranır |
| --- | --- |
| Öğrenci paneli | Yanlış cevap, sorunun bütün kazanımlarına birer yanlış olarak yazılır. Başarısızlık kuralı [Bölüm 9](#s9)'da. Toplam soru ve doğruluk sayılırken soru bir kez sayılır. |
| Cevap ekranı | Kazanımlar cevaptan sonra gösterilir; önce gösterilirse ipucu olur. |
| Neden yanlış? | Sorunun bütün kazanımları ve MEB açıklamaları prompt'a girer; kaynak arama bu kazanımların bloklarında yapılır. |
| Benzer soru | Bu sorunun kazanımlarından en az birini içeren sorular; ortak kazanımı en çok olan, eşitse vektörü en yakın olan seçilir. |
| Pratik yap | Seçilen kazanımı içeren bütün sorular. |
| Soru üretimi | Hedef 1-3 kazanım verilir; MEB gibi birleşik soru da üretilebilir. Üretilen soru eşleştirmeden geçer; bulunan kazanımlar hedefle aynı değilse atılır. |
| İnceleme | Kazanım eklenir ya da çıkarılır. |
| Kontrol seti | İnsan her sorunun ölçtüğü bütün kazanımları işaretler. Ölçüm: kesinlik (seçilenlerin kaçı doğru) ve duyarlılık (doğruların kaçı seçildi). |

### A9İndeksleme

Her paragraf, soru, kazanım ve not iki şekilde indekslenir:

- **Vektör:** bge-m3 metni 1024 sayılık vektöre çevirir; pgvector'da HNSW index'iyle tutulur. Paragrafın başına başlık yolu eklenir: "TDE 12 Ders Kitabı › Roman › Roman Türleri". Tek başına anlamı eksik kalan bir paragraf da böylece doğru konuyla eşleşir.
- **Kelime (BM25):** pg_textsearch aynı metni Türkçe kök bulmayla indeksler. Yazar adı, eser adı ve "bilinç akışı" gibi terimleri vektör aramasının kaçırdığı yerde yakalar.
- **Adım:** INDEX, vektörü boş ve reddedilmemiş BILGI, ALINTI ve METIN bloklarıyla soruların vektörünü yazar; başlık blokları indekslenmez. Kazanım vektörü OUTCOMES'ta, aramadan önce yazılır. Not vektörü bilgi katmanıyla gelir (#139). BM25 index'ini veritabanı kendisi günceller.

### Yayına alma

- Hat bitince en az bir yayındaki sorusu olan test yayına girer.
- Kaynağın kendisinde, sorularında ya da bloklarında açık inceleme kaydı varsa kaynak REVIEW, yoksa PUBLISHED olur.
- Onaylanan soru taslaktaki testini de yayına alır. Son açık kayıt kapanınca REVIEW'deki kaynak PUBLISHED olur.
- Kaynak kaydı reddedilirse kaynağın taslak soru ve blokları atılır (REJECTED), kaynak FAILED olur.

### A10Soru havuzu

- Sorusu 15'ten az olan kazanımlar için üretim gece Batch API ile çalışır. Modele verilenler: hedef 1-3 kazanım ve MEB açıklamaları, ünite kapsamı, aynı kazanımlardan 3-5 gerçek ÖDSGM sorusu, bilgi katmanından aynı dönemin yazarları (çeldirici), dayandığı bloklar.
- Ayrı bir çağrı soruyu cevabı görmeden çözer; tutmazsa soru atılır. Üretilen soru kazanım eşleştirmeden de geçer; bulunan kazanımlar hedefle aynı değilse atılır. Mevcut soruya çok benzeyen de atılır.
- Geçen sorular "yapay zeka üretti" etiketiyle yayına girer; %10'u insan kontrolünden geçer.

### İş kuyruğu ve maliyet

- İşler PostgreSQL'deki `job` tablosundan `FOR UPDATE SKIP LOCKED` ile alınır. Her işin adımı kaydedilir; yarıda kalan iş kaldığı adımdan devam eder, 3 denemeden sonra hata durumuna düşer.
- Görüntü işleme sadece hazırlıkta, sayfa başına bir kez yapılır. Öğrenci çalışırken modele hiç görsel gitmez.
- Kabaca: dört TDE ders kitabı en fazla 76 forma, yaklaşık 1.200 sayfa. Hepsini Sonnet'e Batch ile okutmak yaklaşık 10 dolar; Haiku ile yaklaşık 20 kat ucuz. Metin yolundan giden sayfalar bedava.

07

## İçerik ekibinin ekranı

Geliştirici ve içerik ekibi dosyayı bırakır ve türünü seçer; geri kalan her şey arka planda çalışır. Sistem yalnızca emin olamadığında sorar.

Ekran A · İçerik yükle · Çalışan prototip: dosya bırakabilirsin, adımlar simüle edilir ve dosya hiçbir yere gönderilmez

**İçerik yükle**TDE · eski programİnceleme listesi · 5

Okuma kazanımları: **58**, en az 15 sorusu olan: **41** Yayındaki soru: **1.284** Paragraf: **3.916** Bu ayki model maliyeti: **$14,20**

**PDF'leri buraya bırak** Ders kitabı, kazanım testi, soru bankası, cevap anahtarı ya da öğretim programı. Birden çok dosya olabilir. Dosya seç

DosyaDurumSonuç

- kazanim-testi-7-hikaye-5.pdf

  Test · 11. sınıf · metin + görüntü

  Kazanım eşleştirme · 7/8

  9 soru ayrıldı, cevap anahtarı bekleniyor
- tde12-ders-kitabi.pdf

  Ders kitabı · 12. sınıf · metin yolu

  İnceleme bekliyor · 3 sayfa okunamadı

  İnceleme listesinde
- ogm-sorular.pdf

  Soru bankası · 9. sınıf · görüntü yolu

  Tamamlandı

  Yayında · 2 soru
- tde-ogretim-programi.pdf

  Öğretim programı · 9-12 · metin yolu

  Tamamlandı

  Yayında · 95 kazanım

Ekran B · İnceleme listesi

**İnceleme listesi**5 kayıt

- Düşük güvenli eşleşmeSoru bankası · Soru 2
- Kontrol geçmeditde12-ders-kitabi.pdf · 3 sayfa
- Cevap anahtarı yokKazanım Testi 7 · 9 soru
- Yeni bağViktor Hügo = Victor Hugo
- Öğrenci bildirimiÜretilen soru #4812

Sayfa 1 · kaynak görüntüsü

**Soru 2.** Tablo: tema dostluk, kahraman sayısı iki, mekân park, zaman sabah, bakış açısı kahraman anlatıcı. Aşağıdaki parçalardan hangisi bu bilgilerin tamamıyla örtüşmektedir?

A.2.3 Tema ve konuseçildi · yüksek

A.2.6 Şahıs kadrosuseçildi · orta

A.2.7 Zaman ve mekânseçildi · yüksek

A.2.8 Anlatıcı ve bakış açısıseçildi · yüksek

A.2.9 Anlatım biçimleri ve teknikleriaday

Soru dört kazanımı ölçüyor. A.2.6 (şahıs kadrosu) için güven orta: kişi sayısı sadece A şıkkında ayırt ediyor.

OnaylaKazanım ekle ya da çıkarAt

### Sistem neyi otomatik yapar, neyi sorar

| Konu | Otomatik | İnsana sorulur |
| --- | --- | --- |
| Tür | – | Yüklerken her dosya için |
| Ayrıştırma | Kontrolleri geçen her şey | Kontrolü geçmeyen soru ya da sayfa, hiç içerik çıkmayan kaynak; hepsi kaynak başına tek kayıtta |
| Cevap anahtarı | Sorunun altında ya da ayrı sayfadaysa | Hiç bulunamazsa (model çözümü onaya gelir) |
| Kazanım | Bütün kazanımların güveni yüksekse | Herhangi birinin güveni orta ya da düşükse |
| Yazar ve eser bağları | Kuralla bulunanlar | Modelin bulduğu yeni bağlar ve isim birleştirmeleri |
| Öğrenci bildirimleri | – | Her biri |

### Bu ekranın API'leri

| İstek | Ne yapar |
| --- | --- |
| `POST /api/admin/sources` | Dosyaları alır (çok parçalı yükleme), kaynak kaydı açar, işi kuyruğa koyar. |
| `GET /api/admin/sources` | Dosyaların durumunu ve adımlarını döner. Arayüz 3 saniyede bir sorar. |
| `GET /api/admin/review` | İnceleme listesi: düşük güvenli soru ve paragraflar (LOW_CONFIDENCE) ile kaynak kayıtları (NO_ANSWER_KEY, VALIDATION_FAILED). Kaynak kaydı `targetType: SOURCE` ve sorun listesiyle (`problems`: kod, sayfa, test, soru numarası) gelir; sorunun sayfası varsa görüntüsü açılır. |
| `POST /api/admin/review/{id}` | Soru ve paragrafta: onayla (yayına alır), düzelt (kazanımları değiştirip yayına alır) ya da at. Kaynak kaydında: onayla kaydı kapatır, at kaynağın taslak içeriğini atar ve kaynağı FAILED yapar, düzelt 400 döner. Son açık kayıt kapanınca kaynak PUBLISHED olur. |

Bu ekran sadece `CONTENT_ADMIN` rolüne açıktır. Sürükle-bırak için react-dropzone kullanılır.

08

## Öğrenci akışı

Öğrenci sadece soru çözer, anlatım okur ve soru sorar. Her adımın arka planı [Bölüm 9](#s9)'da.

1. Kaydolur, 12. sınıfı ve anlatım tarzını seçer: Sade, Örnekli, Adım adım.
2. Panelde devam eden testlerini, başarısız kazanımlarını ve son deneme netini görür.
3. Bir ünite testi seçer (Hikâye, Şiir, Roman...) ya da karışık AYT denemesi başlatır.
4. Soruları çözer. Her cevap anında kaydedilir; sayfayı kapatsa da aynı sorudan devam eder.
5. Takılırsa cevaplamadan önce ipucu açar.
6. Yanlış yaparsa doğru şık ve sorunun kazanımları gösterilir. "Neden yanlış?" ile anlatım yazıldıkça gelir; altında ders kitabından alıntı kartı ve "Sayfayı aç" durur.
7. Anlamazsa "Başka örnekle anlat" der ya da soru yazar; cevaplar da kaynak gösterir.
8. "Benzer soru çöz" ile aynı kazanımdan yeni soru çözer.
9. Test bitince AYT kuralıyla netini ve kazanım bazlı sonucunu görür. Bu testte bir kazanımdan 2'den fazla yanlışı varsa o kazanım başarısız işaretlenir ve pratik önerilir.
10. Bir soruda ya da anlatımda hata görürse "Hatalı içerik bildir" der.

Ekran 1 · Test çözme

← Testler**Roman · Kazanım Testi 3**Soru 7 / 20

%35 tamamlandı · kaldığın yerden devam ediyorsun

**7.** Aşağıdakilerden hangisi konusuna göre tarihî roman türünün örneklerindendir?

1. AEylül*Senin cevabın*
2. BKüçük Ağa*Doğru cevap*
3. CAylak Adam
4. DBereketli Topraklar Üzerinde
5. ETutunamayanlar

Bu sorunun kazanımları: **A.2.15** Türün yazar ve eserleri · **A.2.3** Tema ve konu

İpucu Neden yanlış? Benzer soru çöz Sonraki →

Hatalı içerik bildir

Ekran 2 · Kaynaklı anlatım ve sohbet

**Neden yanlış?**Tarz: Adım adım ▾

Eylül bir psikolojik (tahlil) romanıdır; kişilerin ruhsal çözümlemesine odaklanır. Tarihî roman ise konusunu tarihten alır. Küçük Ağa bu yüzden doğru cevap.

DERS KİTABINDA · BİLGİ KÖŞESİ: ROMAN TÜRLERİ "Konusunu tarihten alan romanlardır. Bu romanlarda tarihsel birtakım kişi ve olaylar kurmaca bir çerçevede yansıtılır." Sayfayı aç

Devlet Ana da tarihî roman mı?

Evet. Ders kitabı Kemal Tahir'in Devlet Ana'sını da tarihî roman örneği olarak veriyor. Ders kitabı · Roman Türleri

Anlamadığın yeri yaz…Başka örnekle anlatGönder

Bugün 12 / 30 mesaj

Ekran 3 · Öğrenci paneli

**Merhaba Elif**12. sınıf · AYT Türk Dili ve Edebiyatı

312çözülen soru

%64doğruluk

15,25son deneme neti · 24 soruda

Devam eden testler

Roman · Kazanım Testi 3Devam et

Şiir · Kazanım Testi 1Devam et

Başarısız kazanımlar

A.2.15 Türün yazar ve eserleri · Roman Testi 3'te 3 yanlışPratik yap

A.1.5 Edebî sanatlar · toplam 7 yanlışPratik yap

A.2.12 Akımların yansımaları · toplam 6 yanlışPratik yap

Tür bazlı başarı

Makale%81

Hikâye%78

Tiyatro%71

Şiir%58

Roman%52

Yanlışlarında öne çıkan

Bilgi eksikliği %46Kavram yanılgısı %21Dikkat %18Okuma %15

Ekranlardaki veriler örnektir. Soru ve alıntı, ders kitabının "Roman Türleri ve Özellikleri" kutusundaki bilgilerle kuruldu.

09

## Arka planda her adımda ne olur

Öğrencinin her tıklaması Java'ya bir istek olarak gider. Doğru/yanlış ve ilerleme gibi kurallar Java'da, yapay zeka gerektiren işler Python'da çalışır.

| Öğrenci | İstek | Kod ne yapar |
| --- | --- | --- |
| Test listesi | `GET /api/tests` | Java testleri ve öğrencinin ilerlemesini tek SQL'le getirir. |
| Başla / devam | `POST /api/tests/{id}/sessions` | Yarım oturum varsa onu, yoksa yenisini döner. Sorular cevapsız gönderilir. |
| Cevap | `PUT /api/sessions/{id}/answers/{qId}` | Java cevabı veritabanındaki doğruyla karşılaştırır, kaydeder (aynı soruya ikinci cevap 409 döner), ilerleme sayacını cevaplanmamış ilk soruya taşır, süreyi ve ipucu bilgisini kaydeder. Yanıtta sorunun kazanımları döner. Yanlışsa Python'a hata türü işi düşer (Haiku, arka planda). |
| İpucu | `GET /api/questions/{id}/hint` | Kayıtlıysa döner; yoksa Haiku üretir ve soruya kaydedilir. |
| Neden yanlış? | `POST /api/tutor/explanations` | Aşağıda adım adım. |
| Sohbet | `POST /api/tutor/conversations/{id}/messages` | Aynı akış, artı üç okuma tool'u. |
| Benzer soru | `GET /api/questions/{id}/similar` | Tek SQL: bu sorunun kazanımlarından en az birini içeren, yayında, öğrencinin çözmediği sorular; ortak kazanımı en çok olan, eşitse vektörü en yakın olan seçilir. Yoksa üretim işi kuyruğa girer. |
| Test bitir | `POST /api/sessions/{id}/complete` | AYT kuralıyla net (doğru − yanlış ÷ 4) ve kazanım bazlı özet: her kazanımın bu testteki yanlış sayısı; 2'yi geçen kazanım başarısız. |
| Panel | `GET /api/me/dashboard` | Başarısız kazanımlar (kural aşağıda), tür bazlı doğruluk, hata türü dağılımı, devam eden testler. |
| Bildir | `POST /api/reports` | Bildirim inceleme listesine düşer. |

### Kazanım ne zaman başarısız sayılır

İki eşik var; biri aşılırsa kazanım başarısız sayılır:

- **Bir testte:** o kazanımdan yapılan yanlış sayısı `> 2`
- **Genel toplamda:** o kazanımdan yapılan bütün yanlışlar `> 5` (testler, pratik ve benzer sorular dahil)

Boş bırakılan soru yanlış sayılmaz. Birden çok kazanımı olan sorudaki yanlış, o kazanımların her birine bir yanlış olarak yazılır. Eşikler `AppConstants.MAX_WRONG_PER_TEST = 2` ve `MAX_WRONG_TOTAL = 5`. Sayım `DashboardService`'te SQL ile yapılır; ayrı tablo tutulmaz.

### "Neden yanlış?" adım adım

1. Java oturumun öğrenciye ait olduğunu ve günlük kotanın dolmadığını kontrol eder, Python'u çağırır.
2. Python bağlamı toplar: soru, öğrencinin şıkkı, doğru şık, sorunun bütün kazanımları ve MEB açıklamaları, öğrencinin başarısız kazanımları, anlatım tarzı.
3. Kaynak arama: sorunun kazanımlarına bağlı bilgi, alıntı ve metin bloklarında (BILGI, ALINTI, METIN) vektör ve BM25 aramaları ayrı yapılır, sonuçlar RRF ile birleştirilir (ilk 20). Reranker bu blokları soru ve doğru şıkka göre yeniden sıralar; en iyi 4 tanesi alınır. Etkinlikler hariç.
4. Bloklar Sonnet'e alıntılanabilir kaynak olarak gider; her paragraf ayrı bir parça, başlığı "TDE 12 Ders Kitabı · s. 174" gibi. Sistem prompt'u önbellekte.
5. Sonnet'in yazdığı metin Python → Java → tarayıcıya akar. Claude bir paragrafa dayandığında alıntı bilgisi de gelir; Python bunu kendi blok numaramıza çevirir.
6. Tarayıcı alıntı kartını veritabanındaki orijinal paragrafla çizer; model alıntı metni uyduramaz. "Sayfayı aç" kayıtlı sayfa görüntüsünü getirir.
7. Sohbet kaydedilir; modelin adı, token sayısı ve maliyeti log'a yazılır.

Doğrulamada cevaplar tutmazsa soru atılır ve bir kez daha üretilir. İkinci deneme de tutmazsa öğrenciye "Şu an bu konuda yeni soru yok" denir.

10

## Yapay zeka katmanı

Her yapay zeka işi bir görev adıyla çağrılır; model ve prompt tek bir ayar dosyasından seçilir. Çok tekrarlanan basit işler Haiku'da, kalitenin ürünün kendisi olduğu işler Sonnet'te.

```
# services/ai/llm_tasks.yaml
DOC_CLASSIFY:      { model: claude-haiku-5-5,  prompt: doc_classify.j2 }
UNIT_DETECT:       { model: claude-haiku-5-5,  prompt: unit_detect.j2 }
PAGE_EXTRACT:      { model: claude-haiku-5-5,  prompt: page_extract.j2 }
PAGE_EXTRACT_FALLBACK: { model: claude-sonnet-5-5, prompt: page_extract.j2 }
ENTITY_EXTRACT:    { model: claude-haiku-5-5,  prompt: entity_extract.j2 }
OUTCOME_MATCH:     { model: claude-haiku-5-5,  prompt: outcome_match.j2 }
ANSWER_SOLVE:      { model: claude-sonnet-5-5, prompt: answer_solve.j2 }
HINT:              { model: claude-haiku-5-5,  prompt: hint.j2 }
ERROR_TYPE:        { model: claude-haiku-5-5,  prompt: error_type.j2 }
TOPIC_EXPLAIN:     { model: claude-sonnet-5-5, prompt: topic_explain.j2, citations: true }
CHAT:              { model: claude-sonnet-5-5, prompt: chat.j2, citations: true,
                     tools: [search_notes, open_note, get_outcome], max_tool_calls: 3 }
QUESTION_GENERATE: { model: claude-sonnet-5-5, prompt: question_generate.j2, batch: true }
QUESTION_VERIFY:   { model: claude-sonnet-5-5, prompt: question_verify.j2 }
```

- **Alıntı ve JSON birlikte çalışmaz.** Anlatım ve sohbet alıntılı serbest metindir; diğer bütün görevler Pydantic şemasıyla JSON döner.
- **Alıntı paragraf düzeyinde.** Claude bir bloğu bütün olarak alıntılar; bu yüzden içerik paragraf paragraf saklanır.
- **Arama modelleri:** embedding için bge-m3 (1024 boyut, MIT), yeniden sıralama için bge-reranker-v2-m3 (Apache 2.0). İkisi de Python servisinin içinde çalışır; ekran kartı varsa onu, yoksa CPU'yu kullanır. Ayrı sunucu gerekmez.
- **Prompt'lar** `prompts/tde/` klasöründe, sürümlü. Her çağrıda prompt sürümü kaydedilir.
- Eşleştirme çağrıları birbirinden bağımsızdır; her çağrıda bağlam sıfırdan başlar.
- Claude'a öğrencinin adı veya okulu gönderilmez.
- Sistem prompt'una "emin değilsen bunu açıkça söyle" kuralı eklenir.

11

## Veritabanı

Tek PostgreSQL veritabanı, bilgi tabanının dört katmanı ve işletim tabloları. Tabloları Java tarafı Flyway ile oluşturur.

| Tablo | Ne tutar |
| --- | --- |
| Program |  |
| `subject`, `curriculum` | Ders ve program sürümü (eski program, Maarif Modeli). |
| `curriculum_node` | Alan, tür grubu, kazanım, sınıf, ünite. Kod, başlık, MEB açıklaması, anahtar kelimeler, vektör, `parent_id`. |
| `unit_outcome` | Hangi ünitede hangi kazanımlar işlenir. |
| Kaynak ve içerik |  |
| `source` | Dosya: tür, sınıf, yayıncı, yıl, izin durumu, sha256, metin katmanı sağlam mı, profil. |
| `source_profile` | Kaynak profili kuralları (stil → blok türü). |
| `source_page` | Sayfa numarası ve sayfa görüntüsünün yolu. |
| `content_block` | Bilgi, alıntı, etkinlik, metin blokları: markdown, konum, alıntı kaynağı, güven, durum, başlık yolu (`title_path`), arama metni (`search_text`: başlık yolu + metin), vektör. |
| `block_outcome` | Blok ve kazanım bağı (çoka-çok): bağı kimin kurduğu. |
| `question` | Soru: blok yapılı içerik, cevap, ipucu, şık sayısı, kaynak sayfa, köken (kaynak / üretildi), durum, `difficulty`, `content_hash`, vektör. Kazanım kolonu yok. |
| `question_outcome` | Soru ve kazanım bağı (çoka-çok): `question_id`, `outcome_id` ve bağı kimin kurduğu (`MODEL` / `HUMAN` / `SOURCE`). Sıra ya da ağırlık yok. |
| `test`, `test_question` | Test, ünite, sınav türü; sorular sıralı (`position`). |
| Bilgi |  |
| `kg_node` | Yazar, eser, dönem, akım, tür, kavram notu: ad, diğer yazımlar, not metni, vektör, durum. |
| `kg_edge` | Bağ: kimden, kime, ilişki (yazarı, türü, dönemi...), dayandığı blok, durum. |
| Öğrenci |  |
| `tenant`, `app_user` | Kurum (şimdilik tek kayıt), kullanıcı, rol, sınıf, `external_user_id`, anlatım tarzı. |
| `test_session` | Durum, kalınan soru, cevaplanan sayısı, net. Pratik ve benzer soru cevapları da bir oturuma yazılır; bu oturumların `test_id`'si boştur. |
| `answer`, `answer_analysis` | Seçilen şık, doğru mu, süre, ipucu açıldı mı, anlatım açıldı mı. Hata türü tahmini. |
| `chat_session`, `chat_message`, `message_citation` | Sohbet, mesajlar ve her mesajın dayandığı bloklar. |
| İşletim |  |
| `job` | Hazırlık işleri: tür, durum, adım, deneme sayısı, hata. |
| `review_item` | İnceleme listesi: neden, hedef kayıt, durum, karar veren, ayrıntı (`detail`: kaynak kaydının sorun listesi). |
| `content_report` | Öğrenci bildirimleri. |
| `llm_call_log` | Görev, model, prompt sürümü, token, maliyet, süre. |

### Önemli kurallar

- Bir öğrencinin aynı testte tek yarım oturumu olur: `UNIQUE (user_id, test_id) WHERE status = 'IN_PROGRESS'`.
- Bir oturumda her soruya tek cevap satırı olur; ilk cevaptan sonra cevap değiştirilemez (doğru şık hemen gösterildiği için).
- Aynı dosya (`source.sha256`) ve aynı soru (`question.content_hash`) iki kez eklenmez.
- Öğrenciye sadece `status = 'PUBLISHED'` olan içerik gösterilir.
- Vektör kolonlarına HNSW index'i, arama metinlerine BM25 index'i (`pg_textsearch`, `text_config='turkish'`) eklenir.
- Yayına alınan her sorunun en az bir kazanımı olur; yayına alma kontrolünde doğrulanır.

12

## Git ve PR düzeni

Altı kişi aynı repoda (`bilig`) çalışıyor. Herkes doğrudan ana dala yazarsa biri diğerinin kodunu ezer ve bozuk kod demoya gider. Bu yüzden master'a kimse doğrudan yazmaz; her değişiklik PR ile gelir.

Her iş kendi kısa ömürlü branch'inde yapılır, PR ile incelenir ve tek commit olarak master'a girer. Demo öncesi master'a sürüm etiketi atılır.

### Kurallar

- **master korumalıdır:** doğrudan push, force push ve dal silme kapalı. Birleşmek için Boran'ın onayı ve yeşil CI şart. Onaydan sonra yeni commit gelirse onay düşer, yeniden onay gerekir.
- **Merge yetkisi:** Diğer ekip üyeleri PR'ı ancak Boran onayladıktan sonra birleştirebilir. Boran, repo yöneticisi olarak onaysız birleştirebilir.
- **Her iş bir GitHub Issue ile başlar,** branch issue numarasıyla açılır.
- **Branch kısa ömürlüdür:** 1-3 gün.
- **Commit'ler küçük ve tek amaçlıdır.** Bir commit tek bir mantıklı değişikliği içerir: bir migration, bir servis metodu ve testi, bir bileşen. Hedef 150 satırın altı. 800 satırlık tek bir commit okunamaz ve kabul edilmez.
- **Her commit derlenir.** Yarım kalmış, çalışmayan kod commit edilmez.
- **PR en fazla 400 satır değişiklik içerir.** Üretilen dosyalar (API tipleri, kilit dosyaları) sayılmaz. Geçecekse iş bölünür; inceleyen 400'ü geçen PR'ı geri çevirebilir.
- **Büyük iş sırayla ayrı PR'lara bölünür:** önce migration, sonra servis ve testleri, sonra API, en son arayüz.
- **PR açıklaması** ne yapıldığını, nedenini, nasıl test edildiğini ve değişen satır sayısını yazar.
- **Birleştirme "Squash and merge"** ile yapılır, ardından branch silinir. İnceleme sırasında commit commit okunur; master'a tek commit olarak girer.
- **Migration:** uygulanmış Flyway dosyası asla değiştirilmez; yeni dosya eklenir.
- **Gizli bilgi:** `.env` commit edilmez, `.env.example` güncellenir. Yanlışlıkla commit edilen API anahtarı hemen iptal edilir.
- **PDF'ler ve sayfa görüntüleri repoya konmaz.** Telifli içerik ortak sürücüde durur.
- **Profil dosyaları ve prompt'lar repoda** durur; değişiklikleri de PR ile gelir.
- **İnceleme 24 saat içinde yapılır.**

### İsimlendirme

| Ne | Biçim | Örnek |
| --- | --- | --- |
| Branch | `tür/issue-kisa-aciklama`, küçük harf, Türkçe karakter yok | `feat/12-test-oturumu` |
| Commit | `tür(alan): ne yapıldı` | `feat(ai): kaynak profili önerisi eklendi` |
| Tür | `feat` · `fix` · `refactor` · `test` · `docs` · `chore` |  |
| Alan | `web` · `core` · `ai` · `ingest` · `db` · `infra` · `docs` |  |

### Günlük çalışma

```
# 1. Güncel master'dan yeni branch aç
git switch master
git pull
git switch -c feat/12-test-oturumu

# 2. Çalış, küçük commit'ler at
git add -p
git commit -m "feat(core): test oturumu başlatma eklendi"

# 3. PR açmadan önce master'daki değişiklikleri al
git fetch origin
git rebase origin/master
git push -u origin feat/12-test-oturumu

# 4. GitHub'da PR aç. Rebase sonrası tekrar push gerekirse:
git push --force-with-lease
```

### PR açmadan önce

- Açıklamada issue bağlandı (`Closes #12`).
- Kendi kodumu baştan sona okudum; yapay zekanın yazdığı her satırı anlıyorum.
- Lokal olarak çalıştırdım, testler geçiyor.
- Prompt ya da profil değiştiyse kontrol seti yeniden çalıştırıldı, sonuç PR'a yazıldı.
- Ekran değiştiyse ekran görüntüsü eklendi.
- PR 400 satırın altında, commit'ler küçük ve tek amaçlı.

### Kim inceler

```
# .github/CODEOWNERS
*    @Boran-Sert
```

Onay yetkisi yalnızca Boran'dadır; bu yüzden CODEOWNERS'ta tek sahip vardır. Alan sahipleri PR'a isteğe bağlı inceleyici olarak eklenir; yorumları değerlidir ama birleştirmeyi açmaz.

| Alan | İsteğe bağlı inceleyici |
| --- | --- |
| `services/core/` | Eren, Selman |
| `services/ai/app/ingest/`, `services/ai/profiles/` | Fatih |
| `services/ai/app/tutor/`, `services/ai/app/generation/`, `services/ai/prompts/`, `services/ai/llm_tasks.yaml` | Fatih |
| `apps/web/` | Özcan |
| `docs/` | Sinan |

CI her PR'da değişen alanın derlemesini, testlerini ve format kontrolünü çalıştırır.

13

## Teknoloji ve kod standartları

Bu bölüm AGENTS.md ve CLAUDE.md dosyalarının kaynağıdır. Kodu yapay zeka desteğiyle yazacağımız için herkesin aynı aracı, aynı yapıyı ve aynı adlandırmayı kullanması gerekir. Burada yazmayan bir kütüphane, klasör ya da kural eklenmeden önce ekipte konuşulur ve bu bölüm güncellenir. Yapay zekayla nasıl çalışılacağı [Bölüm 14](#s14)'te.

### 13.1Sürümler

Ana sürümler burada sabittir. Yama sürümleri ilk kurulum PR'ında kilit dosyalarına yazılır (`pom.xml`, `uv.lock`, `package-lock.json`) ve herkes o dosyalardan kurar.

| Araç | Sürüm | Not |
| --- | --- | --- |
| Java | 25 (LTS) | Eclipse Temurin JDK. IDE değil, Java'nın kendisi; Docker imajı da `eclipse-temurin:25` |
| IDE | IntelliJ IDEA 2025.3+ | Java için. JDK olarak Temurin 25 seçilir. Python ve React tarafında editör serbest; biçimi Spotless, ruff, Prettier ve `.editorconfig` belirler |
| Spring Boot | 4.1.x | Maven ve Maven Wrapper (`mvnw`) |
| Python | 3.13 | Paket yöneticisi uv. PyTorch Linux'ta PyPI'dan, Windows'ta cu132 deposundan kurulur; ekran kartı yoksa CPU'da çalışır |
| Node.js | 24 (LTS) | Paket yöneticisi npm |
| TypeScript | 6.0 | `strict: true` |
| React | 19 | Vite 8 ile |
| PostgreSQL | 18 | Kendi imajımız (`infra/postgres`): `pgvector/pgvector:pg18` üstüne pg_textsearch. pgvector 0.8.x |
| Docker | Compose v2 | `docker compose` (tire yok) |
| Claude modelleri | `claude-haiku-5-5`, `claude-sonnet-5-5` | Sadece `llm_tasks.yaml` içinde yazılır |
| Embedding | `BAAI/bge-m3` | 1024 boyut, MIT |
| Reranker | `BAAI/bge-reranker-v2-m3` | Apache 2.0 |
| BM25 | `pg_textsearch` 1.x | PostgreSQL lisansı, Türkçe metin ayarıyla |

### 13.2Her iş için tek seçim

Aynı işi yapan ikinci bir kütüphane eklenmez. "Kullanma" sütunu, yapay zekanın sık önerdiği ama bizim seçmediğimiz araçları listeler.

| İş | Kullan | Kullanma |
| --- | --- | --- |
| Java servisi (core) |  |  |
| REST API | `spring-boot-starter-web` (Spring MVC) | WebFlux ile controller |
| Python'a istek | `RestClient`; akış için sadece `WebClient` (spring-webflux, istemci olarak) | Feign, OkHttp |
| Akışı tarayıcıya iletme | `SseEmitter` | WebSocket |
| Güvenlik | `spring-boot-starter-security`, oturum çerezi | JWT, Keycloak |
| Veritabanı erişimi | Spring Data JPA (Hibernate) | MyBatis, jOOQ |
| Migration | Flyway | Liquibase, `ddl-auto=update` |
| Doğrulama | `spring-boot-starter-validation` (jakarta.validation) | Elle if blokları |
| API belgesi | springdoc-openapi (Boot 4 uyumlu sürüm) | Elle yazılmış OpenAPI |
| DTO | Java `record` | MapStruct, ModelMapper |
| Boilerplate | Lombok, sadece entity'lerde `@Getter @Setter @NoArgsConstructor` | `@Data`, `@Builder`, `@AllArgsConstructor` |
| Log | Spring Boot yapılandırılmış log (`logging.structured.format.console=ecs`) | Log4j, ek JSON kütüphanesi |
| Önbellek | Spring Cache soyutlaması (`@Cacheable`), şimdilik bellek içi | Elle `Map` ile önbellek |
| Test | JUnit 5, AssertJ, Mockito, Testcontainers (PostgreSQL) | H2 veritabanı |
| Format ve Javadoc | Spotless + palantir-java-format; Checkstyle sadece Javadoc kuralları için | Elle düzen |
| Python servisi (ai) |  |  |
| Web çatısı | FastAPI, uvicorn | Flask, Django |
| Veri modelleri | Pydantic v2, ayarlar için pydantic-settings | dataclass ile elle doğrulama |
| Claude | Resmi `anthropic` SDK (`AsyncAnthropic`) | LangChain, LlamaIndex, OpenAI SDK |
| Veritabanı | `psycopg[binary,pool]` 3 (async), `pgvector`, elle yazılmış SQL | SQLAlchemy ORM, Django ORM |
| Embedding ve reranker | `sentence-transformers` (`SentenceTransformer`, `CrossEncoder`) | Ayrı embedding sunucusu, embedding API'si |
| Kelime araması | `pg_textsearch` (BM25) | ParadeDB pg_search (AGPL), Elasticsearch, Postgres `ts_rank` |
| Sonuç birleştirme | RRF, elle yazılmış kısa fonksiyon | LangChain retriever'ları |
| PDF | pypdfium2 (PDFium) ve Tesseract 5 (`tur`), `app.ingest.pdf` dış yüzüyle | PyMuPDF (AGPL), Docling, pdfplumber, PyPDF2 |
| Prompt şablonu | Jinja2 (`.j2` dosyaları) | Python f-string içinde prompt |
| Metin benzerliği | rapidfuzz | difflib |
| Log | structlog (JSON çıktı) | `print` |
| İş kuyruğu | PostgreSQL `job` tablosu, kendi çalışanımız | Celery, RabbitMQ, Redis |
| Test | pytest, pytest-asyncio, httpx2 (FastAPI TestClient için) | unittest |
| Lint, format, tip | ruff (lint, format ve `D` docstring kuralları), mypy | black, flake8, isort |
| Web arayüzü (web) |  |  |
| Derleme | Vite 8, React 19, TypeScript 6 | Next.js, CRA |
| Sayfa geçişleri | React Router 7 (kütüphane modu) | TanStack Router |
| Sunucu verisi | TanStack Query 5 | Redux, Zustand, elle `useEffect` + fetch |
| API istemcisi | openapi-typescript + openapi-fetch (tipler springdoc'tan üretilir) | axios, elle yazılmış tipler |
| Akış (SSE) | `@microsoft/fetch-event-source` | Tarayıcının `EventSource`'u (POST ve başlık desteklemez) |
| Arayüz bileşenleri | shadcn/ui, Tailwind CSS 4, lucide-react ikonları | MUI, Ant Design, styled-components |
| Formlar | react-hook-form + zod 4 + @hookform/resolvers | Formik |
| Metinler (i18n) | i18next + react-i18next | Bileşen içinde Türkçe metin |
| Grafik | Recharts | Chart.js, D3 |
| Markdown | react-markdown + remark-gfm + rehype-raw + rehype-sanitize | `dangerouslySetInnerHTML` |
| Dosya bırakma | react-dropzone | Elle sürükle-bırak |
| Test | Vitest, Testing Library | Jest, Enzyme |
| Lint, format | ESLint 10 (flat config) + eslint-plugin-jsdoc + eslint-plugin-i18next, Prettier 3 | TSLint |

### 13.3Klasör yapısı

Her servis kendi içinde özelliğe göre bölünür: bir özelliğin bütün dosyaları aynı klasörde durur.

```
# services/core (Java)
services/core/
├── pom.xml, mvnw, mvnw.cmd
└── src/
    ├── main/java/com/hataanalizi/core/
    │   ├── CoreApplication.java
    │   ├── common/      AppConstants, ErrorCode, ApiException, GlobalExceptionHandler,
    │   │                RequestIdFilter, PageResponse, TurkishText
    │   ├── config/      SecurityConfig, AiClientConfig, OpenApiConfig
    │   ├── auth/        AuthController, AuthService, AppUser, AppUserRepository, dto/
    │   ├── test/        Test, TestQuestion, TestController, TestService, TestRepository, dto/
    │   ├── session/     TestSession, Answer, SessionController, SessionService,
    │   │                ScoringPolicy, AytScoringPolicy, dto/
    │   ├── question/    Question, QuestionController (ipucu, benzer soru), QuestionService
    │   ├── tutor/       TutorController (SSE), AiClient
    │   ├── dashboard/   DashboardController, DashboardService (salt SQL sorguları)
    │   ├── content/     BlockController, PageImageController
    │   ├── admin/       SourceController, ReviewController
    │   ├── job/         Job, JobType, JobQueue (arayüz), PostgresJobQueue
    │   ├── storage/     FileStorage (arayüz), LocalFileStorage
    │   ├── ratelimit/   RateLimiter (arayüz), DatabaseRateLimiter
    │   └── report/      ReportController, ContentReport
    ├── main/resources/
    │   ├── application.yml
    │   ├── messages_tr.properties
    │   └── db/migration/   Flyway dosyaları
    └── test/java/...       aynı paket yapısı

# services/ai (Python)
services/ai/
├── pyproject.toml, uv.lock, Dockerfile
├── scripts/download_models.py modelleri sabit sürümle /models'e indirir
├── llm_tasks.yaml          görev → model, prompt, ayarlar
├── prompts/tde/*.j2        prompt dosyaları, ders başına klasör
├── app/
│   ├── main.py             FastAPI uygulaması (python -m uvicorn app.main:app)
│   ├── worker.py           iş kuyruğu çalışanı (python -m app.worker)
│   ├── config.py           pydantic-settings
│   ├── constants.py
│   ├── api/                /internal router'ları: explain.py, chat.py, hint.py, analysis.py
│   ├── llm/                runner.py (run_task), tasks.py (LlmTask), prompts.py, pricing.py
│   ├── search/             EmbeddingProvider ve Reranker (arayüz), BgeEmbedding, BgeReranker,
│   │                       vector.py, bm25.py, hybrid.py (hybrid_search, RRF)
│   ├── jobs/               JobQueue (arayüz), PostgresJobQueue, JobStore (iş durumu)
│   ├── storage.py          FileStorage (arayüz), LocalFileStorage
│   ├── db/                 pool.py, queries/ (modül başına SQL sabitleri)
│   ├── ingest/
│   │   ├── pipeline.py     adımları sırayla çalıştırır, job.step günceller
│   │   ├── pdf/            PDF dış yüzü (read_questions, read_textbook, read_lines, render_page);
│   │   │                   question_reader.py ve book_reader.py tek dosyalık iki motor
│   │   ├── readers/        program.py, program_units.py, answer_key.py (düz satırlardan)
│   │   ├── text_layer.py   metin katmanı kontrolü
│   │   ├── vision.py       sayfa görüntüsü → bloklar
│   │   ├── validators.py
│   │   ├── entities.py     bilgi katmanı
│   │   └── outcomes.py     kazanım eşleştirme
│   ├── tutor/              explain.py, chat.py, tools.py, citations.py
│   ├── generation/         generate.py, verify.py
│   ├── schemas/            Pydantic modelleri: blocks.py, question.py, entities.py ...
│   ├── text/turkish.py     tr_lower, tr_upper, normalize_nfc, ascii_fold
│   └── eval/               run.py, kontrol seti okuyucusu
└── tests/                  fixtures/ içinde kendi ürettiğimiz küçük PDF'ler

# apps/web (React)
apps/web/
├── package.json, vite.config.ts, tsconfig.json, eslint.config.js, .prettierrc, components.json
└── src/
    ├── main.tsx, routes.tsx
    ├── components/ui/      shadcn bileşenleri (CLI ile eklenir, elle düzenlenmez)
    ├── components/         ortak: Markdown, CitationCard, OptionBubble, PageImageDialog
    ├── features/
    │   └── auth/ tests/ solve/ tutor/ dashboard/ admin/
    │       ├── pages/      sayfa bileşenleri
    │       ├── components/
    │       ├── api.ts      TanStack Query hook'ları
    │       └── types.ts
    ├── lib/
    │   ├── api/schema.d.ts üretilir, elle düzenlenmez
    │   ├── api/client.ts
    │   ├── sse.ts, i18n.ts, constants.ts, utils.ts
    ├── locales/tr/         common.json, auth.json, test.json, tutor.json, dashboard.json, admin.json
    └── styles/index.css    Tailwind ve tema token'ları
```

### 13.4Adlandırma

| Ne | Java | Python | TypeScript | SQL |
| --- | --- | --- | --- | --- |
| Dosya | `SessionService.java` | `outcome_match.py` | Bileşen `SolvePage.tsx`, diğer `client.ts` | `V202610161430__create_session_tables.sql` |
| Sınıf, tip | `TestSession` | `QuestionBlock` | `QuestionContent` | – |
| Fonksiyon | `calculateProgress` | `match_outcome` | `formatNet`, hook `useTestSession` | – |
| Değişken | `answeredCount` | `answered_count` | `answeredCount` | `answered_count` |
| Sabit | `MAX_TOOL_CALLS` | `MAX_TOOL_CALLS` | `MAX_TOOL_CALLS` | – |
| Tablo, kolon | Entity sınıfı tekil (`Question`) ↔ tablo tekil (`question`) | `question_outcome`, `created_at` |  |  |
| DTO | `StartSessionRequest`, `SessionResponse` | `ExplainRequest` | Üretilen tipler | – |

- **Kod İngilizce, kullanıcı metni Türkçe.** Sınıf, fonksiyon, değişken adları ve log mesajları İngilizce. Kullanıcının gördüğü her metin Türkçe ve i18n dosyalarında. Docstring, yorum ve belgeler Türkçe yazılır.
- **İsimler açıklayıcı olur, uzunluk sorun değildir.** Kısaltma yok: `sess` değil `session`.
- **Java'da** constructor injection kullanılır; alana `@Autowired` yazılmaz. Controller, Service, Repository son ekleri zorunlu.
- **Python'da** her fonksiyonun tip ipuçları vardır. Servisler arası veri Pydantic modeliyle taşınır, `dict` ile değil.
- **TypeScript'te** `any` yasak. Bileşen başına bir dosya.

### 13.5API sözleşmesi

| Konu | Kural |
| --- | --- |
| Yol | Dışa açık: `/api/...` (Java). İç: `/internal/...` (Python), nginx üzerinden dışarı açılmaz. |
| JSON | Alan adları her yerde camelCase. Python'da Pydantic `alias_generator=to_camel` ve `populate_by_name=True`. |
| Tarih | ISO-8601, UTC, sonu `Z`: `2026-10-16T11:30:00Z`. Veritabanında `timestamptz`. |
| Kimlik | Sayısal `id` (`bigint`). Erişim yetkisi her istekte servis katmanında kontrol edilir. |
| Sayfalama | `?page=0&size=20` (en fazla 100). Cevap: `{ "items": [], "page": 0, "size": 20, "total": 134 }` |
| Hata | RFC 9457 Problem Details (Spring `ProblemDetail`). Ek alanlar: `code` (`SESSION_NOT_FOUND` gibi) ve `requestId`. `detail` metni `messages_tr.properties` dosyasından gelir. |
| Durum kodları | 200 okuma ve güncelleme, 201 oluşturma, 202 arka plana alınan iş, 204 içeriksiz, 400 doğrulama, 401 giriş yok, 403 yetki yok, 404 bulunamadı, 409 çakışma (aynı dosya), 413 dosya büyük, 429 günlük limit. |
| Akış (SSE) | Olaylar: `delta` `{"text"}`, `citation` `{"blockId","sourceTitle","page"}`, `done` `{"messageId"}`, `error` (Problem Details). |
| Kazanım bilgisi | Sorunun kazanımları cevaptan önce gönderilmez. Cevap kaydının yanıtı: `{"isCorrect": false, "correctOption": "E", "outcomes": [{"code": "A.2.7", "title": "..."}, {"code": "A.2.8", "title": "..."}]}` |
| İç kimlik | Java → Python isteklerinde `X-Internal-Token` ve `X-Request-Id` başlıkları zorunlu. |
| Tipler | OpenAPI belgesi `/v3/api-docs` adresinde. Arayüz tipleri `npm run gen:api` ile üretilir; elle tip yazılmaz. |

Tam istek listesi: kimlik için `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/me`. Diğerleri [Bölüm 7](#s7) ve [Bölüm 9](#s9)'daki tablolarda; ek olarak `GET /api/blocks/{id}` ve `GET /api/pages/{id}/image`.

### 13.6Ortak içerik formatı

Üç servis aynı şemayı kullanır. Python'da Pydantic modeli, Java'da record, arayüzde üretilen tip olarak bulunur.

```
// question.content (jsonb)
QuestionContent {
  passage?: Block[]                  // birden çok sorunun ortak parçası
  stem: Block[]                      // soru kökü
  options: { label: "A" | "B" | "C" | "D" | "E", blocks: Block[] }[]
}
Block { type: "paragraph" | "table" | "list" | "numbered_items", md: string }

// content_block.block_type
"BILGI" | "ALINTI" | "ETKINLIK" | "METIN" | "BASLIK"
```

- `md` alanında izin verilen işaretler: `*italik*`, `**kalın**`, `<u>altı çizili</u>`, GFM tablosu, liste. Başka HTML etiketi yok; arayüz rehype-sanitize ile sadece `u` etiketine izin verir.
- Edebiyat'ta italik eser adı demektir; ayrıştırmada kaybolmamalı.
- Doğru cevap tek harftir (`"B"`) ve `question.answer` kolonunda durur; `content` içinde yer almaz.

### 13.7Veritabanı kuralları

- **Şemayı sadece Flyway değiştirir.** `spring.jpa.hibernate.ddl-auto=validate`. Python tablo oluşturmaz.
- **Migration dosya adı** zaman damgalı: `V202610161430__create_session_tables.sql`. Böylece iki kişinin dosyası aynı numarayı almaz.
- **Tablo ve kolonlar** tekil ve snake_case. Birincil anahtar `id bigint generated always as identity`, yabancı anahtar `<tablo>_id`.
- **Her tabloda** `created_at timestamptz not null default now()`; güncellenen tablolarda `updated_at`.
- **Sabit değer kümeleri** PostgreSQL enum değil, `text` + `CHECK` ile tutulur; değerler büyük harf (`'IN_PROGRESS'`).
- **İsimler:** index `idx_<tablo>_<kolonlar>`, tekillik `uq_...`, yabancı anahtar `fk_...`.
- **Vektör:** `vector(1024)`, HNSW index, `vector_cosine_ops`; sorguda `<=>` (kosinüs uzaklığı).
- **Kelime araması (BM25):** eklentiyi ilk migration kurar: `CREATE EXTENSION IF NOT EXISTS pg_textsearch;` Index: `CREATE INDEX idx_content_block_bm25 ON content_block USING bm25 (search_text) WITH (text_config = 'turkish');` Sorgu: `ORDER BY search_text <@> :query LIMIT 30`. Skor negatiftir; küçük olan önce gelir. Aynı index `kg_node` ve `curriculum_node` için de kurulur.
- **Türkçe sıralama:** veritabanı ICU `tr-TR` yereliyle kurulur (`POSTGRES_INITDB_ARGS=--locale-provider=icu --icu-locale=tr-TR`).
- **Esnek içerik** `jsonb` kolonlarda; aranacak ya da filtrelenecek alan ayrı kolona çıkarılır.

### 13.8Metinler, i18n ve sabitler

Üç farklı şey üç farklı yerde durur: kullanıcıya görünen metin i18n dosyasında, değişmeyen değer sabitler dosyasında, ortama göre değişen değer ayar dosyasında.

| Ne | Java | Python | Arayüz |
| --- | --- | --- | --- |
| Kullanıcı metni | `messages_tr.properties` (MessageSource) | Yok; Türkçe metin sadece prompt dosyalarında | `src/locales/tr/*.json` (i18next) |
| Sabit | `common/AppConstants.java` | `app/constants.py` | `src/lib/constants.ts` |
| Ayar (limitler, adresler) | `application.yml` + ortam değişkeni | `app/config.py` + ortam değişkeni | `import.meta.env.VITE_*` |
| Hata kodu | `ErrorCode` enum | `ErrorCode` (StrEnum) | Problem Details `code` alanı |

```
# services/core/src/main/resources/messages_tr.properties
error.SESSION_NOT_FOUND=Oturum bulunamadı.
error.DAILY_LIMIT_REACHED=Bugünkü mesaj hakkın doldu. Yarın tekrar deneyebilirsin.
error.FILE_NOT_PDF=Sadece PDF dosyası yüklenebilir.

// apps/web/src/locales/tr/test.json
{
  "answer": { "correct": "Doğru cevap", "yours": "Senin cevabın" },
  "progress": "%{{percent}} tamamlandı",
  "actions": { "hint": "İpucu", "explain": "Neden yanlış?", "similar": "Benzer soru çöz" }
}
```

- i18n anahtarları İngilizce ve noktalı: `alan.öğe.amaç` → `test.answer.correct`. Dosya adı özelliğin adıdır.
- Bileşen içinde Türkçe metin yazılmaz; ESLint'te `eslint-plugin-i18next` ile kontrol edilir.
- Şimdilik sadece `tr` var; yeni dil yeni klasör demektir.

### 13.9Türkçe metin kuralları

- Her yerde UTF-8. Hazırlık hattına giren her metin Unicode NFC'ye çevrilir.
- Türkçe metinde düz `lower()` / `toLowerCase()` kullanılmaz. İ/i ve I/ı yanlış dönüşür. Java'da `common/TurkishText` (`Locale.forLanguageTag("tr")`), Python'da `app/text/turkish.py` (`tr_lower`, `tr_upper`) kullanılır.
- Dosya adı ve branch adı gibi teknik alanlarda ASCII'ye çevirme `ascii_fold` ile yapılır.
- Sıralama veritabanında ICU yereliyle yapılır, kodda değil.

### 13.10Yapay zeka kodu kuralları

- **Tek giriş noktası:** Claude'a her çağrı `app/llm/runner.py` içindeki `run_task(task, variables, *, output_model=None, documents=None, tools=None, stream=False)` üzerinden gider. SDK başka yerde içe aktarılmaz.
- **Görevler** `LlmTask` enum'unda, ayarları `llm_tasks.yaml`'da: model, prompt, `max_tokens`, alıntı, tool'lar, batch.
- **Prompt dosyaları** `prompts/tde/<görev>.j2`. İlk satır sürüm: `{# version: 3 #}`. Sürüm her çağrıyla kaydedilir.
- **JSON çıktı** `client.messages.parse(..., output_format=PydanticModel)` ile alınır. Model çıktısından düzenli ifadeyle bilgi ayıklanmaz.
- **Alıntı** gereken görevlerde kaynaklar `search_result` bloğu olarak verilir: `source` = `kb://block/{id}`, başlık = "TDE 12 Ders Kitabı · s. 174", her paragraf ayrı metin bloğu. Alıntı ile JSON çıktı aynı çağrıda kullanılmaz.
- **Önbellek:** sistem prompt'u ve sabit bağlam `cache_control` ile işaretlenir.
- **Tool'lar** `app/tutor/tools.py` içinde, sadece okuma yapar, sonuçları `search_result` bloğu olarak döner. Bir cevapta en fazla 3 çağrı.
- **Hata ve tekrar:** SDK'nın kendi tekrar mekanizması (`max_retries=3`) kullanılır; zaman aşımı görev ayarında.
- **Kayıt:** her çağrı `llm_call_log`'a yazılır: görev, model, prompt sürümü, giriş/çıkış/önbellek token'ı, maliyet, süre, `request_id`.
- **Kişisel veri** modele gitmez: öğrencinin adı, e-postası, okulu. Sadece sayısal kullanıcı numarası.

### 13.11Embedding ve arama kuralları

- Embedding ve reranker sadece `app/search/` içindeki arayüzlerle kullanılır: `EmbeddingProvider` (`encode(texts)`) ve `Reranker` (`rerank(query, docs, top_k)`). Modeller süreç başına bir kez yüklenir; başka yerde `SentenceTransformer` ya da `CrossEncoder` oluşturulmaz.
- **Embedding:** `BAAI/bge-m3`, 1024 boyut, `normalize_embeddings=True`, toplu işlemde 32'lik gruplar, en fazla 2048 token. Sorgu ve belge için ön ek (prompt) kullanılmaz.
- **Başlık yolu:** paragrafın vektörü ve BM25 metni başlık yoluyla birlikte hesaplanır: "TDE 12 Ders Kitabı › Roman › Roman Türleri" + paragraf. Kazanım da yoluyla: "12. sınıf › Roman › Metnin olay örgüsünü belirler".
- **Arama sırası her yerde aynı:** vektör (ilk 30) ve BM25 (ilk 30) ayrı çalışır, RRF ile birleşir (her sonuç için `1 / (60 + sıra)` toplanır, ilk 20), sonra reranker. Tek fonksiyon: `hybrid_search(query, filters, top_k, rerank)`.
- **Reranker:** `BAAI/bge-reranker-v2-m3`, `max_length=512`. "Neden yanlış?" ve sohbet aramasında açık; kazanım eşleştirmede ve benzer soruda kapalı, çünkü orada seçimi Haiku ya da SQL yapıyor.
- **Süre:** arama ve reranker birlikte 1 saniyenin altında kalmalı. Aşarsa reranker'a giden aday sayısı 20'den 10'a indirilir (`constants.py`).
- **Model dosyaları:** modeller `scripts/download_models.py` ile ayardaki sabit commit'ten (`EMBEDDING_REVISION`, `RERANKER_REVISION`) `/models`'e bir kez indirilir; servis `HF_HUB_OFFLINE=1` ile çalışır ve çalışırken hiçbir şey indirmez. Hugging Face'ten kendi kodunu çalıştıran (`trust_remote_code=True`) model seçilmez, çünkü o kod sabit commit'e bağlanamıyor.
- Embedding modeli değişirse bütün vektörler yeniden hesaplanır (`EMBED` işi); iki modelin vektörleri karıştırılmaz.

### 13.12İş kuyruğu, dosyalar ve büyüme noktaları

- **İş türleri** (`job.type`): `INGEST_SOURCE`, `BUILD_PROGRAM`, `EXTRACT_ENTITIES`, `MATCH_OUTCOMES`, `EMBED`, `GENERATE_QUESTIONS`, `ANALYZE_ANSWER`.
- **Çalışan** 2 saniyede bir `SELECT ... FOR UPDATE SKIP LOCKED` ile iş alır; `WORKER_CONCURRENCY` kadar işi aynı anda yürütür.
- **Her adım tekrar çalıştırılabilir olmalı:** adım çıktısını yazar, sonra `job.step`'i ilerletir. Yarıda kalan iş kaldığı adımdan başlar. 3 denemeden sonra `FAILED`.
- **Dosyalar** `/data` volume'ünde: `/data/sources/{source_id}.pdf`, `/data/pages/{source_id}/{page_no:04d}.png` (150 dpi). Repoya girmez, tarayıcıya sadece Java üzerinden yetki kontrolüyle verilir.
- **Yükleme:** en fazla 100 MB, sadece PDF; tür dosyanın ilk baytlarından (`%PDF`) kontrol edilir, uzantıya güvenilmez.
- **RabbitMQ ve Redis'e ne zaman geçilir:** saniyede yüzlerce iş, aynı olayı birden çok servisin dinlemesi ya da birden çok Java sunucusunda anlık hız sınırı gerektiğinde. Geçiş aşağıdaki arayüzler sayesinde yeni bir uygulama ve ayar değişikliğidir.

**Büyüme noktaları.** Sistem büyüdüğünde değişmesi muhtemel altyapı parçaları baştan bir arayüzün arkasına konur. Şimdi sadece en basit uygulaması yazılır; büyüyünce yeni uygulama eklenir ve ayar değiştirilir, iş kodu değişmez.

| Altyapı | Arayüz | Şimdi | Büyüyünce | Ayar |
| --- | --- | --- | --- | --- |
| İş kuyruğu | `JobQueue` (Java, Python) | `PostgresJobQueue`: job tablosu, `SKIP LOCKED` | `RabbitMqJobQueue` + outbox tablosu | `JOB_QUEUE=postgres` |
| Dosya saklama | `FileStorage` (Java, Python) | `LocalFileStorage`: `/data` volume'ü | S3 uyumlu nesne deposu (MinIO, bulut) | `STORAGE_TYPE=local` |
| Hız sınırı | `RateLimiter` (Java) | `DatabaseRateLimiter`: günlük sayım | `RedisRateLimiter` | `RATE_LIMIT_TYPE=database` |
| Önbellek | Spring Cache (`@Cacheable`) | Bellek içi | Redis | `SPRING_CACHE_TYPE=simple` |
| Embedding | `EmbeddingProvider`, `Reranker` (Python) | `BgeEmbedding`, `BgeReranker` | GPU sunucusu ya da API | `EMBEDDING_PROVIDER=local` |
| Dil modeli | `run_task` + `llm_tasks.yaml` | Claude API | Model ya da sağlayıcı değişimi | `llm_tasks.yaml` |

```
// Java · services/core/.../job/JobQueue.java
/** İşleri kuyruğa koyar; altyapıdan bağımsızdır. */
public interface JobQueue {

    /** Yeni işi kaydeder ve çalışanların alması için sıraya koyar. */
    long enqueue(JobType type, JsonNode payload);
}

# Python · services/ai/app/jobs/queue.py
class JobQueue(Protocol):
    """İş kuyruğu sözleşmesi; çalışan sadece bunu bilir."""

    async def enqueue(self, job_type: JobType, payload: BaseModel) -> int:
        """Yeni işi kaydeder ve sıraya koyar."""

    async def claim(self, limit: int) -> list[Job]:
        """Sıradaki işleri alır ve başkası almasın diye kilitler."""

    async def complete(self, job_id: int) -> None:
        """İşi başarıyla bitmiş olarak işaretler."""

    async def fail(self, job_id: int, error: str) -> None:
        """İşi hatalı işaretler; deneme hakkı varsa yeniden sıraya koyar."""
```

- **İş kodu sadece arayüzü bilir.** Hangi uygulamanın çalışacağını ayar seçer: Java'da `@ConditionalOnProperty`, Python'da `app/config.py` içindeki fabrika fonksiyonu.
- **İşin durumu her zaman `job` tablosunda kalır** (adım, deneme, hata). Kuyruk sadece iş numarasını taşır; RabbitMQ'ya geçince yükleme ekranı ve inceleme listesi değişmez.
- **RabbitMQ'ya geçişte iki yere yazma sorunu outbox ile çözülür:** Java işi ve bir outbox satırını aynı transaction'da yazar, ayrı bir yayıncı outbox'taki satırları RabbitMQ'ya gönderir.
- **Her arayüzün bir sözleşme testi vardır:** aynı test seti her uygulamaya karşı çalışır. Yeni uygulama bu testleri geçmeden açılmaz.
- **Şimdi sadece "Şimdi" sütunu yazılır.** RabbitMQ, Redis ya da S3 kodu ihtiyaç doğmadan yazılmaz.

### 13.13Güvenlik

- Oturum çerezi `HttpOnly`, `Secure`, `SameSite=Lax`. CSRF koruması açık; token çerezden okunup `X-XSRF-TOKEN` başlığıyla gönderilir.
- Şifreler Spring Security'nin varsayılan şifreleyicisiyle (BCrypt) saklanır.
- Roller: `STUDENT`, `CONTENT_ADMIN`, `ADMIN`. `/api/admin/**` sadece `CONTENT_ADMIN` ve `ADMIN`.
- Bir öğrenci sadece kendi oturumunu, cevabını ve sohbetini görebilir; kontrol servis katmanında yapılır.
- Doğru cevap, öğrenci cevaplamadan hiçbir yanıtta yer almaz.
- Gizli değerler sadece `.env`'de. CORS sadece geliştirmede açık.

### 13.14Log ve hata

- Seviyeler: INFO, WARN (Python'da WARNING), ERROR. DEBUG sadece yerelde.
- Java ve Python JSON log yazar. Ortak alanlar: `timestamp`, `level`, `service`, `requestId`, `userId`, `message`.
- `RequestIdFilter` her isteğe `X-Request-Id` atar; Python'a başlıkla geçer, hata cevabında `requestId` olarak döner.
- Log'a şifre, API anahtarı, öğrenci mesajının tamamı ya da kişisel veri yazılmaz.
- Yakalanan hata ya yeniden fırlatılır ya da log'a yazılıp anlamlı bir hata koduna çevrilir; boş `catch` yasak.

### 13.15Test kuralları

- **Java:** servis mantığı için birim testi (JUnit 5, Mockito, AssertJ); her controller için Testcontainers'lı en az bir entegrasyon testi. Testcontainers projenin kendi Postgres imajını kullanır (pgvector ve pg_textsearch içinde).
- **Python:** ayrıştırıcı, kontrol ve eşleştirme fonksiyonları için pytest. Testlerde Claude çağrıları sahte nesneyle değiştirilir; gerçek çağrı sadece değerlendirme komutunda yapılır.
- **Arayüz:** mantık içeren bileşen ve hook'lar için Vitest ve Testing Library.
- **Test PDF'leri** kendi ürettiğimiz küçük dosyalardır; telifli kitap sayfası repoya konmaz.
- **Prompt, profil ya da eşleştirme değişikliği** yapan PR'da değerlendirme çalıştırılır ve doğruluk PR açıklamasına yazılır.

### 13.16Format, docstring ve yorumlar

Açıklama koda iki yerde yazılır: dosyanın başında ve her fonksiyonda. Kod satırlarının arasına uzun yorum yazılmaz.

- **Dosya başı:** Elle yazılan her kod dosyası, ne işe yaradığını anlatan bir açıklamayla başlar. Birkaç cümle olabilir: dosyanın görevi, hangi akışın parçası olduğu, dikkat edilecek nokta.
- **Fonksiyon docstring'i:** Her fonksiyon ve metodun tek cümlelik, açıklayıcı bir docstring'i vardır. Cümle fonksiyonun ne yaptığını söyler; parametreleri tek tek saymaz.
- **Yeri:** Python'da `def` satırının hemen altında. Java ve TypeScript'te dilin kuralı gereği fonksiyonun hemen üstünde (`/** ... */`). Java'da dosya başı açıklaması sınıfın Javadoc'udur.
- **Kod içi yorum** (`#`, `//`, `/* */`) en fazla 3 kelimedir. Daha uzun açıklama gerekiyorsa o kısım ayrı bir fonksiyona alınır ve açıklama onun docstring'ine yazılır.
- **Yapılacak notu:** issue numarasıyla ve en fazla 3 kelime: `# TODO(#42): sayfa birleştirme`.
- **Dil:** Docstring ve yorumlar Türkçe, kod adları İngilizce.
- **Kapsam:** Elle yazılan bütün `.java`, `.py`, `.ts`, `.tsx` ve `.sql` dosyaları; React bileşenleri, hook'lar ve test fonksiyonları dahil. Hariç: üretilen dosyalar (`components/ui/`, `schema.d.ts`), Lombok'un ve record'un ürettiği metodlar, fonksiyon içindeki isimsiz lambda'lar.
- **Kontrol:** Python'da ruff `D` kuralları, TypeScript'te eslint-plugin-jsdoc (`require-jsdoc`), Java'da Checkstyle (`MissingJavadocType`, `MissingJavadocMethod`). Araçların yakalamadığı özel fonksiyonlar ve 3 kelime sınırı PR incelemesinde kontrol edilir.

```
# Python · services/ai/app/ingest/outcomes.py
"""Kazanım eşleştirme adımı.

Bir soru ya da paragraf için ünitenin kazanımlarından en yakın 5 adayı bulur,
son seçimi Haiku'ya yaptırır. Güveni düşük sonuçlar inceleme listesine düşer.
"""

def match_outcome(item: ContentItem, unit_id: int) -> OutcomeMatch:
    """Verilen içeriğin ölçtüğü kazanımları seçer."""
    candidates = find_candidates(item, unit_id)  # aday kazanımlar
    ...

// Java · services/core/.../session/SessionService.java
/**
 * Test oturumlarını yönetir: başlatma, kaldığı yerden devam ve cevap kaydı.
 * Doğru cevap kontrolü ve ilerleme sayacı bu sınıftadır.
 */
@Service
public class SessionService {

    /** Öğrencinin yarım oturumunu döner, yoksa yenisini başlatır. */
    public SessionResponse startOrResume(long userId, long testId) {
        // tek aktif oturum
        ...
    }
}

// TypeScript · apps/web/src/features/solve/api.ts
/**
 * Test çözme ekranının sunucu istekleri.
 * Cevap kaydı ve oturum bilgisi TanStack Query hook'larıyla alınır.
 */

/** Seçilen şıkkı kaydeder ve doğru/yanlış sonucunu döner. */
export function useSubmitAnswer(sessionId: number) { ... }

-- SQL · V202610161430__create_session_tables.sql
-- Test oturumu ve cevap tabloları.
-- Bir öğrencinin aynı testte tek yarım oturumu olmasını sağlayan kısıtı içerir.
CREATE TABLE test_session ( ... );
```

- `.editorconfig`: UTF-8, LF satır sonu, Java ve Python 4 boşluk, TypeScript, JSON ve YAML 2 boşluk, satır sonunda boşluk yok.
- `.gitattributes`: `* text=auto eol=lf`. Windows kullananlarda satır sonu farkı PR'ları kirletmez.
- Satır uzunluğu 100. Java Spotless, Python ruff, arayüz Prettier ile otomatik düzenlenir.
- Dosya 300 satırı, fonksiyon 40 satırı geçiyorsa bölünür.

### 13.17Ortam değişkenleri

```
# .env.example (gerçek değerler .env'de, .env repoya girmez)
POSTGRES_DB=hata_analizi
POSTGRES_USER=app
POSTGRES_PASSWORD=degistir
POSTGRES_INITDB_ARGS=--locale-provider=icu --icu-locale=tr-TR
INTERNAL_TOKEN=uzun-rastgele-bir-deger
STORAGE_DIR=/data
STORAGE_TYPE=local
JOB_QUEUE=postgres

# core (Java)
SPRING_DATASOURCE_URL=jdbc:postgresql://postgres:5432/hata_analizi
SPRING_DATASOURCE_USERNAME=app
SPRING_DATASOURCE_PASSWORD=degistir
AI_BASE_URL=http://ai-api:8000
DAILY_CHAT_LIMIT=30
MAX_MESSAGE_CHARS=1000
MAX_UPLOAD_MB=100
RATE_LIMIT_TYPE=database
SPRING_CACHE_TYPE=simple

# ai (Python)
DATABASE_URL=postgresql://app:degistir@postgres:5432/hata_analizi
ANTHROPIC_API_KEY=
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=BAAI/bge-m3
RERANKER_MODEL=BAAI/bge-reranker-v2-m3
HF_HOME=/models
HF_HUB_OFFLINE=1
WORKER_CONCURRENCY=4
LOG_LEVEL=INFO
WORD_LIST_PATH=/app/data/turkce_kelimeler.txt
TESSERACT_CMD=tesseract
OCR_CACHE_DIR=

# web
VITE_API_BASE_URL=/api
```

### 13.18Docker Compose servisleri

| Servis | İmaj | Port | Not |
| --- | --- | --- | --- |
| web | nginx + derlenmiş React | 8080 → 80 | `/api` isteklerini core'a iletir |
| core | Java 25 | 8081 | `/data` volume'ü bağlı |
| ai-api | Python 3.13 | 8000, sadece iç ağ | `/data` ve `/models` bağlı; `gpus: all`, NVIDIA ekran kartı ister |
| ai-worker | ai-api ile aynı imaj | yok | Komut: `python -m app.worker`; `gpus: all` |
| postgres | `infra/postgres`'tan derlenir | 5432 | `pgdata` volume'ü, ICU tr-TR, `shared_preload_libraries=pg_textsearch` |

### 13.19Komutlar

```
# Her şey birlikte
docker compose up --build

# Modeller, bir kez (/models volume'üne)
docker compose run --rm -e HF_HUB_OFFLINE=0 ai-api python -m scripts.download_models

# NVIDIA ekran kartı olmayan makinede (Mac) ai-api ve ai-worker açılmaz;
# Docker'da sadece postgres, core ve web açılır, ai servisleri aşağıdaki gibi yerelde çalışır

# Geliştirirken: sadece veritabanı Docker'da, servisler yerelde
docker compose up -d postgres
cd services/core && ./mvnw spring-boot:run          # Windows: mvnw.cmd
cd services/ai && uv sync && uv run uvicorn app.main:app --reload --port 8000
cd services/ai && uv run python -m app.worker
cd apps/web && npm ci && npm run dev
cd apps/web && npm run gen:api                       # Java çalışırken API tiplerini üretir

# PR açmadan önce
cd services/core && ./mvnw spotless:apply verify
cd services/ai && uv run ruff format . && uv run ruff check . && uv run mypy app && uv run pytest
cd apps/web && npm run lint && npm run typecheck && npm test

# Değerlendirme (gerçek Claude çağrısı yapar)
cd services/ai && uv run python -m app.eval.run --task OUTCOME_MATCH
```

`infra/postgres/Dockerfile`, `pgvector/pgvector:pg18` imajının üstüne pg_textsearch'ün GitHub sürüm sayfasındaki hazır Linux paketini sabit sürümle kurar.

CI (GitHub Actions) her serviste sadece o servisin klasörü değiştiğinde çalışır: `core.yml`, `ai.yml`, `web.yml`. Aynı komutları çalıştırır; biri kırmızıysa PR birleşmez.

### 13.20Bir iş ne zaman bitmiş sayılır

- Kod bu bölümdeki kurallara uyuyor; format, lint ve tip kontrolü temiz.
- Testler yazıldı ve geçiyor; CI yeşil.
- Yeni kullanıcı metni i18n dosyasında, yeni ortam değişkeni `.env.example`'da.
- API değiştiyse arayüz tipleri yeniden üretildi.
- Prompt ya da eşleştirme değiştiyse değerlendirme sonucu PR'da.
- Her dosyada başlık açıklaması, her fonksiyonda tek cümlelik docstring var; kod içi yorumlar en fazla 3 kelime.
- PR 400 satırın altında; commit'ler küçük, tek amaçlı ve her biri derleniyor.
- Yapay zekayla yazıldıysa 14.6'daki liste işaretlendi.
- Boran PR'ı inceledi ve onayladı.

14

## Yapay zekayla geliştirme

Kodun büyük kısmını Claude Code yazacak. Bu bölüm herkesin aynı şekilde çalışmasını ve yapay zekanın her bilgisayarda aynı kodu üretmesini sağlayan kuralları anlatır. AGENTS.md ve CLAUDE.md dosyaları bu bölümden ve Bölüm 13'ten üretilir; 14.9 ve 14.10'daki iskeletler doğrudan kopyalanabilir.

### 14.1Temel ilke

- **Kodu yapay zeka yazar, sorumluluk PR'ı açanındır.** PR'daki her satırı açıklayabilmelisin. İnceleyen "bu satır ne yapıyor?" diye sorduğunda "Claude yazdı" cevap değildir.
- **CLAUDE.md bir rehberdir, kilit değildir.** Claude kuralları çoğu zaman uygular ama bazen atlar. Asıl güvence otomatik kontrollerdir: CI, format ve lint, testler, Claude Code'un izin ayarları ve hook'lar (14.7).
- **Ölçü hız değil doğruluktur.** Hızlı yazılıp yanlış çalışan kod, yavaş yazılıp doğru çalışan koddan pahalıya gelir.

### 14.2Bir iş baştan sona nasıl yapılır

1. **Issue'yu oku.** Ne istendiği ve iş bitince neyin çalışacağı (kabul kriteri) yazmıyorsa önce issue'yu netleştir.
2. **Branch aç** (Bölüm 12) ve Claude Code'u repo kökünden başlat. Kök CLAUDE.md ve ortak ayarlar ancak kökten başlatınca yüklenir.
3. **Her issue için temiz oturum aç** (`/clear`). Önceki işin konuşmasını yeni işe taşıma; uzayan oturumda kurallar unutulmaya başlar.
4. **Önce plan.** Plan modunda Claude'dan ilgili dosyaları okumasını ve plan çıkarmasını iste. Plan şunları yazmalı: değişecek ve eklenecek dosyalar, yazılacak testler, işin kaç commit'e bölüneceği. Planı oku, yanlışsa düzelt, sonra uygulat.
5. **Küçük adımlarla uygula.** Her adım tek commit: önce migration, sonra servis ve testi, sonra API, en son arayüz. Bir adım bitmeden sonrakine geçme.
6. **Her adımdan sonra doğrula.** O servisin format, lint ve test komutları (13.19). Kırmızıysa adım bitmemiştir.
7. **Diff'i satır satır oku.** `git diff` ile neyin değiştiğine bak. İstenmeyen değişikliği geri al. Anlamadığın satırı commit etme; Claude'a açıklat ya da sil.
8. **Commit'i sen at.** `git add -p` ile parça parça ekle, mesajı Bölüm 12'ye göre yaz.
9. **PR aç.** Açıklamayı kısa tut ve kendi cümlelerinle yaz: ne yaptın, neden, nasıl test ettin. 14.6'daki listeyi işaretle.

### 14.3Claude'a iş nasıl verilir

- **Bir istekte tek iş.** "Oturum API'sini yaz ve arayüze de bağla" iki ayrı iştir.
- **Plandaki bölümü söyle.** "Bölüm 13.5'teki hata formatına göre" demek, kuralı yeniden anlatmaktan daha güvenilirdir.
- **Örnek dosya göster.** "`SessionService` gibi yaz" dediğinde Claude mevcut düzeni izler, yeni bir düzen icat etmez.
- **Bitiş koşulunu yaz.** Hangi test geçmeli, hangi istek hangi cevabı dönmeli.
- **Sınırı yaz.** "Sadece `session/` klasöründe çalış."
- **Hatayı olduğu gibi yapıştır.** Hata mesajını ve stack trace'i özetleme.
- **İki denemede çözülmezse dur.** Aynı hatayı üçüncü kez denettirme; sorunu kendin incele ya da ekipten birine sor. Döngüye giren oturum kodu bozar.
- **İsteğe koyma:** `.env` içeriği, API anahtarı, gerçek öğrenci verisi, telifli kitap sayfası.

```
# Kötü istek
oturum işini yap

# İyi istek
#12: Öğrenci yarım kalan testine devam edebilsin.
POST /api/tests/{id}/sessions yarım oturum varsa onu, yoksa yenisini dönsün (plan Bölüm 9).
Önce session/ klasörünü ve SessionService'i oku, plan çıkar; ben onaylamadan yazma.
Hata cevabı Bölüm 13.5'teki Problem Details formatında olsun.
Bitti sayılması için: SessionServiceTest'te "yarım oturum varsa onu döner" ve
"yoksa yenisini başlatır" testleri geçsin, ./mvnw spotless:apply verify temiz olsun.
Sadece session/ klasörüne ve yeni migration dosyasına dokun.
```

### 14.4Kesin yasaklar

Bu liste kök AGENTS.md'ye aynen girer. Yapay zeka için de insan için de geçerlidir.

1. `.env` dosyasını okuma, değiştirme, commit etme. Yeni değişken `.env.example`'a eklenir.
2. Bölüm 13.2'deki listenin dışında kütüphane ekleme. Gerekiyorsa önce ekipte konuş.
3. Uygulanmış migration dosyasını değiştirme; yeni dosya ekle.
4. Üretilen dosyaları elle düzenleme: `schema.d.ts`, `components/ui/`, kilit dosyaları.
5. Testi geçirmek için testi silme, atlama ya da beklenen değeri yanlış sonuca göre değiştirme.
6. Kontrolleri susturma: `@Disabled`, `pytest.mark.skip`, `eslint-disable`, `# noqa`, `@SuppressWarnings`, `@ts-ignore`. Zorunluysa yanına issue numarası yazılır.
7. master'a doğrudan ya da `--force` ile push, `--no-verify` ile commit, kör `git add .`.
8. Hatayı yutma: boş `catch`, `except: pass`.
9. Model adını, prompt metnini, kullanıcıya görünen metni ve sabit sayıları koda gömme (13.8, 13.10).
10. Öğrencinin adını, e-postasını ya da okulunu Claude'a veya log'a gönderme.
11. Telifli PDF'i, sayfa görüntüsünü ya da kitap metnini repoya, test verisine ya da örnek dosyaya koyma.
12. İş kuralını arayüze yazma. Doğru/yanlış, ilerleme, limit, yetki ve kazanım başarısı Java'da hesaplanır.
13. Türkçe metinde düz `lower()` ya da `toLowerCase()` kullanma.
14. Soru için tek kazanım varsayma; kazanımlara sıra ya da ağırlık verme.
15. İşle ilgisiz dosyaları yeniden adlandırma, taşıma ya da biçimlendirme.
16. İkinci kullanım çıkmadan arayüz, soyut sınıf ya da genel yardımcı fonksiyon yazma (istisnalar 13.12'de).

### 14.5Yapay zekanın sık yaptığı hatalar

PR incelemesinde özellikle bunlara bakılır.

| Hata | Örnek | Ne yapılır |
| --- | --- | --- |
| Eski sürüm kodu | Spring'de `javax.*` ya da `WebSecurityConfigurerAdapter`; Pydantic v1 (`class Config`, `@validator`); TanStack Query'de `useQuery(key, fn)` | Sürümler 13.1'de. Emin değilsen kütüphanenin resmi belgesine bak. |
| Uydurma API | Kütüphanede olmayan metod; projede olmayan alan ya da endpoint | Derle ve çalıştır; IDE'de tanıma git. |
| Var olanı yeniden yazma | `TurkishText` varken yeni bir küçük harf fonksiyonu; ikinci bir API istemcisi | Önce ara: `common/`, `lib/`, `app/text/`, `app/search/`. |
| Gereğinden büyük çözüm | Tek kullanım için fabrika, strateji deseni, genel `utils` dosyası | Sil, en basit hali bırak. |
| Sahte uygulama | `return true`, sabit veri döndüren metod, `TODO` ile bırakılmış dal | İş bitmemiştir. |
| Mock'u ölçen test | Her şeyi mock'layıp sadece mock'un çağrıldığını doğrulayan test | Davranışı doğrula; veritabanı için Testcontainers. |
| Sessiz yan değişiklik | İstenmeden değişen import sırası, yeniden adlandırılan değişken, silinen docstring | Diff'te geri al. |
| Kalıntı | `print`, `console.log`, `System.out`, yoruma alınmış kod | Sil; log için 13.14. |
| Kural dışı metin | Bileşende Türkçe metin, uzun kod içi yorum, eksik docstring | i18n dosyasına taşı; 13.16'ya uydur. |
| Güvenlik açığı | Başka öğrencinin oturumunu dönen sorgu, cevaptan önce doğru şıkkı gönderen yanıt, metin birleştirerek kurulan SQL | Yetki kontrolü servis katmanında; SQL her zaman parametreli. |

### 14.6PR kontrol listesi

- Plan modunda plan çıkarıldı ve okundu.
- Diff satır satır okundu; istenmeyen değişiklik yok.
- Yeni bağımlılık yok; varsa ekipte konuşuldu ve gerekçesi PR'da.
- 14.5'teki hataların hiçbiri yok.
- Testler davranışı ölçüyor; format, lint, tip kontrolü ve testler yerelde temiz.
- Ekran değiştiyse tarayıcıda denendi; API değiştiyse Swagger arayüzünden çağrıldı.
- PR açıklamasını kendim yazdım: ne, neden, nasıl test ettim.

### 14.7Claude Code ayarları

Bazı kuralları Claude Code'un kendisi uygular. Bu dosyalar repoya commit edilir ve herkeste aynı çalışır.

| Dosya | Ne yapar |
| --- | --- |
| `.claude/settings.json` | Ortak izinler ve hook'lar. `.env` okunamaz ve düzenlenemez; sık kullanılan kontrol komutları sormadan çalışır. |
| `.claude/hooks/protect.sh` | Korunan dosyalarda düzenlemeyi engeller: `.env`, uygulanmış migration'lar, üretilen dosyalar, kilit dosyaları. |
| `.claude/hooks/format.sh` | Claude bir dosyayı yazınca o dosyayı biçimlendirir: `.py` ruff, `.ts` ve `.tsx` Prettier. Java her düzenlemede Maven açmasın diye hook'ta yok; commit'ten önce `./mvnw spotless:apply`. |
| `.claude/rules/*.md` | Sadece belirli dosyalara dokunulunca yüklenen kurallar (14.8). |
| `.claude/settings.local.json`, `CLAUDE.local.md` | Kişisel ayar ve notlar. `.gitignore`'da; commit edilmez. |

```
// .claude/settings.json
{
  "permissions": {
    "deny": ["Read(./.env)", "Edit(./.env)"],
    "allow": [
      "Bash(git status)",
      "Bash(git diff *)",
      "Bash(uv run pytest *)",
      "Bash(uv run ruff *)",
      "Bash(npm run lint)",
      "Bash(npm run typecheck)",
      "Bash(npm test)"
    ]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "bash \"${CLAUDE_PROJECT_DIR}/.claude/hooks/protect.sh\"" }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "bash \"${CLAUDE_PROJECT_DIR}/.claude/hooks/format.sh\"" }
        ]
      }
    ]
  }
}

# .claude/hooks/protect.sh
#!/bin/bash
# Korunan dosyalarda düzenlemeyi engeller.
command -v jq >/dev/null || { echo "jq kurulu değil (Windows: winget install jqlang.jq)" >&2; exit 2; }
FILE=$(jq -r '.tool_input.file_path // empty')
FILE=${FILE//\\//}
deny() { echo "Korunan dosya: $FILE ($1)" >&2; exit 2; }
case "$FILE" in
  */.env.example) exit 0 ;;
  */.env|*/.env.*) deny "gizli değerler" ;;
  */schema.d.ts|*/components/ui/*) deny "üretilen dosya" ;;
  */uv.lock|*/package-lock.json) deny "kilit dosyası" ;;
esac
if [[ "$FILE" == */db/migration/* && -e "$FILE" ]]; then
  deny "uygulanmış migration; yeni dosya ekle"
fi
exit 0

# .claude/hooks/format.sh
#!/bin/bash
# Claude'un yazdığı dosyayı biçimlendirir.
FILE=$(jq -r '.tool_input.file_path // empty')
case "$FILE" in
  *.py) cd "$CLAUDE_PROJECT_DIR/services/ai" && uv run ruff format -q "$FILE" ;;
  *.ts|*.tsx) cd "$CLAUDE_PROJECT_DIR/apps/web" && npx prettier --write --log-level warn "$FILE" ;;
esac
exit 0
```

- Hook'lar `jq` ister. Windows'ta Claude Code komutları Git Bash ile çalıştırır; `jq` ayrıca kurulur (`winget install jqlang.jq`). `jq` yoksa `protect.sh` her düzenlemeyi durdurur.
- Hook'lar `bash "..."` ile çağrılır, `args` alanı kullanılmaz. `args` olunca komut kabuksuz çalışır ve Windows'ta `.sh` dosyası açılamaz.
- Windows'ta dosya yolu ters bölüyle gelir; `protect.sh` kalıplara bakmadan önce düz bölüye çevirir.
- `protect.sh` çıkış kodu 2 ile düzenlemeyi durdurur; Claude nedeni görür ve başka yol arar.
- Yeni migration dosyası oluşturmak serbesttir; sadece var olan migration dosyası değiştirilemez.

### 14.8AGENTS.md ve CLAUDE.md dosyaları

Ekipte herkes Claude Code kullanmıyor. Ortak kurallar bu yüzden `AGENTS.md`'de durur; Codex, Cursor ve Copilot gibi araçlar bu dosyayı okur. Kök `CLAUDE.md` sadece `@AGENTS.md` satırıyla onu içe aktarır, kurallar iki yerde yazılmaz. Servislerde de aynı düzen geçerlidir. Kökte `CLAUDE.md` olduğu için Claude Code alt klasördeki `AGENTS.md`'yi tek başına okumaz; bu yüzden her serviste onu içe aktaran bir `CLAUDE.md` de durur.

| Dosya | Ne zaman yüklenir | İçerik |
| --- | --- | --- |
| `AGENTS.md` (kök) | Her oturumun başında | Proje özeti, servisler, çalışma şekli, kesin yasaklar (14.4), ortak kod kuralları, API, git ve PR, komutlar. Metni 14.9'da. |
| `CLAUDE.md` (kök) | Her oturumun başında | Sadece `@AGENTS.md` satırı. Claude Code'a özel kural çıkarsa altına yazılır. |
| `services/core/AGENTS.md` ve `CLAUDE.md` | Claude bu klasörde bir dosyayı okuyunca ya da yazınca | Java kuralları: 13.2 Java satırları, 13.3 Java yapısı, 13.7, 13.12, 13.15 Java kısmı, kazanım başarısızlık kuralı, komutlar. |
| `services/ai/AGENTS.md` ve `CLAUDE.md` | Aynı şekilde | Python kuralları: 13.2 Python satırları, 13.3 Python yapısı, 13.6, 13.10, 13.11, hazırlık hattı (Bölüm 6), komutlar. |
| `apps/web/AGENTS.md` ve `CLAUDE.md` | Aynı şekilde | Arayüz kuralları: 13.2 arayüz satırları, 13.3 arayüz yapısı, 13.8 i18n, ekran taslakları (Bölüm 7 ve 8), komutlar. |
| `.claude/rules/migrations.md` | Sadece migration dosyalarına dokunulunca | 13.7 veritabanı kuralları. |
| `.claude/rules/prompts.md` | Sadece `prompts/` ve `llm_tasks.yaml` dosyalarına dokunulunca | 13.10 yapay zeka kodu kuralları, prompt sürümleme. |

- **Her dosya 200 satırın altında kalır.** Dosya uzadıkça Claude'un kurallara uyma oranı düşer. Bir kısmı ilgilendiren kural servis dosyasına ya da `.claude/rules/` altına gider.
- **Kurallar kısa, emir kipinde ve kontrol edilebilir yazılır.** "Kod içi yorum en fazla 3 kelime" iyi bir kural; "temiz kod yaz" değil.
- **Çelişen iki kural olmaz.** Çelişki varsa Claude birini rastgele seçer.
- **Plan dosyası içe aktarılmaz.** `@dosya` ile eklenen dosya da her oturumda yüklenir ve bağlamı doldurur. CLAUDE.md gereken kuralı kendisi yazar. Tek istisna `@AGENTS.md`; o dosya zaten yüklenmesi gereken kuralların kendisidir.
- **AGENTS.md ve CLAUDE.md değişikliği PR ile gelir;** sahibi Boran (CODEOWNERS).
- **Claude aynı hatayı iki kez yaparsa** ilgili dosyaya bir satır eklenir. İşe yaramayan ya da eskiyen kural silinir.

```
# .claude/rules/migrations.md
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
- Vektör vector(1024) + HNSW (vector_cosine_ops). Kelime araması BM25 (pg_textsearch, 'turkish').
- Dosyanın başında ne yaptığını anlatan -- açıklama.
```

### 14.9Kök AGENTS.md metni

Kökteki `AGENTS.md` bu metnin aynısıdır. Yeni bir kural eklenecekse önce bu bölüm güncellenir, sonra dosya.

```
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
```

### 14.10Servis AGENTS.md metinleri

Her servisteki `AGENTS.md` bu metnin aynısıdır; yanındaki `CLAUDE.md` onu `@AGENTS.md` ile içe aktarır.

```
# services/core/AGENTS.md
# core (Java)
Spring Boot 4.1, Java 25 (Temurin), Maven Wrapper. Kuralların sahibi bu servis.

## Yapı
- Özelliğe göre paket: auth, test, session, question, tutor, dashboard, content, admin,
  job, storage, ratelimit, report; ortaklar common ve config.
- Her özellikte: Entity, Repository, Service, Controller ve dto/ (record).

## Kurallar
- Constructor injection; alana @Autowired yazma.
- Lombok sadece entity'de: @Getter @Setter @NoArgsConstructor. @Data ve @Builder yok.
- DTO Java record. Mapper kütüphanesi yok; dönüşüm record içinde from(entity) metoduyla.
- Yetki kontrolü serviste: öğrenci sadece kendi oturumunu, cevabını, sohbetini görür.
- Hata: ApiException(ErrorCode); metin messages_tr.properties dosyasında.
- Şema sadece Flyway ile; ddl-auto=validate.
- Python'a istek sadece AiClient (RestClient) ile; X-Internal-Token ve X-Request-Id zorunlu.
- Kazanım başarısız: bir test oturumunda yanlış > MAX_WRONG_PER_TEST (2)
  ya da toplam yanlış > MAX_WRONG_TOTAL (5). Boş bırakılan soru yanlış sayılmaz.

## Test
- Servis mantığı: JUnit 5, Mockito, AssertJ.
- Her controller için Testcontainers'lı entegrasyon testi; projenin Postgres imajı kullanılır. H2 yok.

## Komut
- ./mvnw spotless:apply verify   (Windows: mvnw.cmd)

# services/ai/AGENTS.md
# ai (Python)
FastAPI, Python 3.13, uv. Claude çağrıları, embedding, arama ve PDF hazırlık hattı.

## Yapı
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
- Hazırlık adımları tekrar çalıştırılabilir: önce çıktıyı yaz, sonra job.step'i ilerlet.
- Türkçe metin için app/text/turkish.py (tr_lower, normalize_nfc).

## Test
- pytest ve pytest-asyncio. Testte Claude çağrıları sahte nesneyle; gerçek çağrı sadece app.eval.run'da.
- Test PDF'leri kendi ürettiğimiz küçük dosyalardır.

## Komut
- uv run ruff format . && uv run ruff check . && uv run mypy app && uv run pytest

# apps/web/AGENTS.md
# web (React)
React 19, Vite 8, TypeScript 6 (strict), shadcn/ui, Tailwind CSS 4.

## Yapı
- src/features/<özellik>/ altında pages/, components/, api.ts (TanStack Query hook'ları), types.ts.
- Ortak bileşenler src/components/; shadcn bileşenleri src/components/ui/ (CLI ile eklenir, elle düzenlenmez).

## Kurallar
- Sunucu verisi sadece TanStack Query ile; elle useEffect + fetch yok.
- API tipleri npm run gen:api ile üretilir; elle tip yazılmaz. any yok.
- Metinler src/locales/tr/<özellik>.json dosyasında; bileşende Türkçe metin yok.
- Formlar react-hook-form + zod. Markdown react-markdown + rehype-sanitize; dangerouslySetInnerHTML yok.
- Akış (SSE) sadece lib/sse.ts üzerinden (@microsoft/fetch-event-source).
- İş kuralı yok: doğru/yanlış, ilerleme ve başarı Java'dan gelir.
- Bileşen başına bir dosya.

## Test
- Mantık içeren bileşen ve hook için Vitest ve Testing Library.

## Komut
- npm run lint && npm run typecheck && npm test
```

15

## Yol haritası

Teslim tarihi 12 Kasım 2026 Perşembe. Plan dört hafta; son hafta dört gün. Her haftanın sonunda çalışan bir şey gösteriyoruz; mavi satır o haftanın hedefi.

| Kişi | Hafta 1 · 19-25 Ekim | Hafta 2 · 26 Ekim-1 Kasım | Hafta 3 · 2-8 Kasım | Hafta 4 · 9-12 Kasım |
| --- | --- | --- | --- | --- |
| Hedef | Proje tek komutla çalışıyor, program katmanı kuruldu | Bir ders kitabı ve bir test seti yüklenip soru çözülebiliyor | Yanlış cevap akışı alıntılarla baştan sona çalışıyor | 10 Kasım kod dondurma, 11 Kasım prova, 12 Kasım demo |
| Boran | Repo, CI, docker-compose, CLAUDE.md dosyaları ve Claude Code ayarları; embedding, BM25 ve reranker kurulumu (Fatih ile) | Kazanım eşleştirme, doğruluk ölçümü | Bilgi katmanı, alıntılı anlatım, sohbet tool'ları | Prompt iyileştirme, demo, sunum, son incelemeler. Yetişirse soru üretimi ve doğrulama. |
| Eren | Tablolar (Flyway), giriş ve roller | Test, oturum ve cevap API'leri | Panel API'si, cevap analizi kayıtları | Hata düzeltme, testler |
| Selman | `job` tablosu, Java'dan Python'u çağıran istemci | Yükleme API'si, iş durumu API'si | İnceleme API'leri, akış aktarımı | Hata düzeltme, uçtan uca test |
| Fatih | Program katmanı (A1), metin katmanı kontrolü ve bozuk font eşlemesi düzeltme denemesi; kontrol seti (Boran ile) | Kaynak profili, kitap ve test ayrıştırma, sayfa birleştirme, cevap anahtarı | Görüntü yolu, kontroller | Gerçek kaynaklarla doğrulama |
| Özcan | Arayüz iskeleti, giriş ekranı | Yükleme ekranı, test çözme | Anlatım ve alıntı kartı, sohbet, inceleme ekranı | Öğrenci paneli, telefon görünümü |
| Sinan | Rakip analizi: MEBİ, yayınevi platformları | MEB izin başvurusu, öğrenci ve öğretmen görüşmeleri | Fiyatlandırma, anlatım tarzı metinleri | Kullanıcı testi, demo senaryosu |

29 Ekim resmi tatil; ikinci hafta dört iş günü.

16

## Sonraya kalanlar

Aşağıdakiler bilinçli olarak ilk sürüme alınmadı; altyapısı hazır, ihtiyaç doğunca eklenir.

- Görselli sorular ve şekil üretimi
- Öğretmen paneli, sınıflar, ön test / son test
- Maarif Modeli sınıfları ve eski-yeni kazanım eşlemesi
- Kurum girişi (SSO), API anahtarı, MCP sunucusu, kurum logosu
- Zorluğa göre soru seçimi ve konu sırası
- Sayfa görüntüsünde alıntılanan paragrafın vurgulanması
- Mobil uygulama, ödeme

### Gerçek öğrencilerle canlıya çıkmadan önce zorunlu

- KVKK: veli açık rızası ve aydınlatma metni.
- MEB'den içerik kullanımı ve alıntı gösterimi için yazılı izin.
- Özel yayınevi kitapları için telif izni; izin yoksa sadece MEB kitapları kullanılır.
- Anthropic'in 18 yaş altı kullanıcılara hizmet eden uygulamalar için kurallarının kontrolü.

··

## Terimler

Kazanım

MEB programında öğrencinin kazanması beklenen beceri. Altındaki açıklama, öğretmenden beklenen sınırları yazar.

Metin katmanı

PDF'in içindeki seçilebilir metin. Bazı PDF'lerde bozuk ya da hiç yok.

Kaynak profili

Bir kitabın ya da serinin görünüm kuralları: hangi stil başlık, hangisi bilgi kutusu, italik ne demek.

Ortak format

Bütün kaynakların dönüştüğü blok yapısı: bilgi, alıntı, etkinlik, metin, soru.

Embedding, vektör

Metnin anlamını taşıyan sayı listesi. Anlamca yakın metinlerin vektörleri de yakındır.

Alıntı (citation)

Claude'un cevabında hangi paragrafa dayandığını göstermesi. Gösterilen metin bizim veritabanımızdan gelir.

BM25

Kelime araması puanı. Nadir geçen kelimeye (yazar ya da eser adı) daha çok ağırlık verir.

RRF

Vektör ve kelime aramasının sıralamalarını tek listede birleştirme yöntemi.

Reranker

Aramadan gelen adayları soruyla tek tek karşılaştırıp yeniden sıralayan küçük model.

Tool

Modelin çağırabildiği fonksiyon. Bizde sadece okuma yapanlar var.

Net

AYT puanlaması: doğru sayısından yanlış sayısının dörtte biri çıkarılır.

Akış (stream)

Cevabın yazıldıkça ekrana gelmesi.

Migration

Veritabanı tablolarını değiştiren numaralı SQL dosyası (Flyway).

PR

Pull request. Branch'teki değişikliğin incelenip master'a alınma isteği.

### Açık konular

- İlk yüklenecek ders kitapları: MEB yayını mı, özel yayınevi mi?
- Başarısız kazanım nasıl düzelir? Yanlış sayıları hiç azalmadığı için şu kurala göre bir kez başarısız olan kazanım hep öyle kalır.

Kaynaklar: [Claude alıntılı arama sonuçları](https://platform.claude.com/docs/en/build-with-claude/search-results) · [Claude yapısal çıktı](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) · [Claude Batch ve fiyatlar](https://platform.claude.com/docs/en/build-with-claude/batch-processing) · [bge-m3](https://huggingface.co/BAAI/bge-m3) · [bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) · [pg_textsearch](https://github.com/timescale/pg_textsearch) · [Claude Code CLAUDE.md](https://code.claude.com/docs/en/memory) · [Claude Code hook'ları](https://code.claude.com/docs/en/hooks) · [Maarif Modeli, ortaöğretim](https://tymm.meb.gov.tr/taslak-cerceve-planlari/ortaogretim)