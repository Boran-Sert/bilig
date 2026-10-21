# core (Java)
Spring Boot 4.1, Java 25 (Temurin), Maven Wrapper. Kuralların sahibi bu servis.

## Yapı
- Tablo ve kolon adları `docs/veritabani.md`'dedir; ad uydurulmaz.
- Özelliğe göre paket: auth, exam, session, question, tutor, dashboard, content, admin,
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
