# Plan

Hata Analizi Asistanı'nın genel çerçevesi. Ayrıntılar [ekip planında](<Hata Analizi Asistanı.md>),
işler [GitHub Issues](https://github.com/Boran-Sert/bilig/issues)'ta, kurallar [AGENTS.md](AGENTS.md)'de.

## Hedef
Öğrenci AYT Edebiyat sorusu çözer. Yanlış yaptığında sistem soruyu ders kitabından alıntıyla
anlatır ve aynı kazanımdan yeni bir soru verir.

## İlk sürümün kapsamı
- 12. sınıf AYT Türk Dili ve Edebiyatı, web.
- Öğrenci akışı: test çözme, yanlışın kazanımını kaydetme, kaynaklı anlatım, benzer soru.
- İçerik ekibi için yükleme, iş durumu ve inceleme ekranları.
- İlk sürümde yok: görselli sorular, öğretmen paneli, mobil uygulama, ödeme, Maarif Modeli sınıfları.
- Gerçek öğrencilerle canlıya çıkmadan önce KVKK, MEB ve telif izinleri gerekir (Bölüm 16).

## Sistem
- `apps/web` (React): öğrenci ve içerik ekibi ekranları.
- `services/core` (Java, Spring Boot): kurallar, giriş, test, cevap, tablolar.
- `services/ai` (Python, FastAPI): Claude çağrıları, arama, PDF hazırlık hattı, iş kuyruğu.
- PostgreSQL: pgvector ve pg_textsearch ile tek veritabanı.

Hepsi `docker compose up` ile tek komutla çalışır.

## Takvim
Teslim: 12 Kasım 2026 Perşembe. Her haftanın sonunda çalışan bir şey gösterilir.

| Hafta | Tarih | Hedef |
| --- | --- | --- |
| [H1](https://github.com/Boran-Sert/bilig/milestone/1) | 19-25 Ekim | Proje tek komutla çalışıyor, program katmanı kuruldu |
| [H2](https://github.com/Boran-Sert/bilig/milestone/2) | 26 Ekim-1 Kasım | Bir ders kitabı ve bir test seti yüklenip soru çözülebiliyor |
| [H3](https://github.com/Boran-Sert/bilig/milestone/3) | 2-8 Kasım | Yanlış cevap akışı alıntılarla baştan sona çalışıyor |
| [H4](https://github.com/Boran-Sert/bilig/milestone/4) | 9-12 Kasım | 10 Kasım kod dondurma, 11 Kasım prova, 12 Kasım demo |

29 Ekim resmi tatil; ikinci hafta dört iş günü.

## Ekip
| Kişi | Alan |
| --- | --- |
| Boran | Ürün sahibi, Team Lead. Mimari, repo ve kurallar, yapay zeka katmanı, PR onayları |
| Eren | Java: tablolar, giriş ve roller, test ve cevap API'leri, öğrenci paneli |
| Selman | Java: iş kuyruğu, yükleme ve inceleme API'leri, Python bağlantısı |
| Fatih | İçerik hattı: program katmanı, PDF ayrıştırma, kaynak profilleri, kontroller |
| Özcan | Arayüz: öğrenci ve içerik ekibi ekranları |
| Sinan | İş geliştirme, UX: rakip analizi, MEB izni, kullanıcı testleri, demo senaryosu |
