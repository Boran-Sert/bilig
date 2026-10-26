# Kontrol seti

Kazanım eşleştirmesinin (plan A8) doğruluğunu ölçmek için 100 soruluk set. Her sorunun ölçtüğü
bütün kazanımları insan işaretler (#99); eşleştirmenin kesinliği ve duyarlılığı bu işaretlere
göre hesaplanır. Dosyanın biçimini `services/ai/tests/test_control_set.py` denetler.

## sorular.jsonl

Satır başına bir soru, UTF-8, Unicode NFC.

| Alan | Tür | Açıklama |
| --- | --- | --- |
| `id` | metin | `ks-001` ile `ks-100` arası, sırayla. |
| `source` | metin | Test ve soru numarası: `ÖDSGM 12 Roman Kazanım Testi 3, Soru 5`. |
| `unit` | metin | Testin ÖDSGM'deki ünite adı (aşağıdaki tablo). |
| `stem` | metin | Soru kökü; okuma parçası, dizeler ve soru cümlesi. Satır sonu `\n`. |
| `options` | nesne | `A`-`E` şıkları, düz metin; dize olan şıklarda satır sonu `\n`. |
| `correct` | metin | ÖDSGM cevap anahtarındaki doğru şık. |
| `outcomes` | liste | Sorunun ölçtüğü kazanım kodları; #99'a kadar boş. Sıra ya da ağırlık yok. |

## Kaynak

ÖDSGM, **12. Sınıf Türk Dili ve Edebiyatı Kazanım Kavrama Testleri (2022-2023)**,
[ÖDSGM sayfası][kaynak]. 40 test ve cevap anahtarı (`tde_ca_mayis.pdf`), 2026-10-26'da
indirildi. Testler 2018 öğretim programına göredir. PDF'ler repoya konmaz.

[kaynak]: https://odsgm.meb.gov.tr/www/12-sinif-turk-dili-ve-edebiyati-kazanim-testleri-2022-2023/icerik/900

### Kullanım

Soruların ve içlerindeki şiir ve metin parçalarının hakları MEB'e ve eser sahiplerine aittir.
Bu dosya açık lisanslı değildir. Sadece eşleştirmenin ölçülmesinde kullanılır: öğrenciye
gösterilmez, soru havuzuna girmez. Kullanım izni MEB izin başvurusuyla (#109) birlikte netleşir.

## Sorular nasıl seçildi

1. 40 testteki 387 soru PDF'in metin katmanından okundu. Her testte okunan soru sayısı cevap
   anahtarıyla aynı, her soruda beş şık var.
2. Düz metne çevrilince anlamı bozulan sorular çıkarıldı:
   - Altı çizili söze dayanan sorular.
   - Numaraları sözcüklerin altına basılmış sorular.
   - Tablo ile başlayan sorular.
3. Kalan sorular ünite, test ve soru sırasıyla dizildi. Her üniteden kotası kadar soru eşit
   aralıkla seçildi; böylece ünitenin bütün testlerinden ve testlerin başından sonuna soru geldi.

| Ünite | Test | Uygun soru | Seçilen |
| --- | ---: | ---: | ---: |
| Giriş | 2 | 15 | 5 |
| Hikâye | 8 | 63 | 20 |
| Şiir | 12 | 112 | 31 |
| Roman | 10 | 90 | 25 |
| Tiyatro | 4 | 28 | 8 |
| Deneme - Söylev (Nutuk) | 4 | 42 | 11 |
| **Toplam** | **40** | **350** | **100** |

Kotalar ünitelerin soru sayısına göre yaklaşık orantılı belirlendi; Giriş en az 5 soru alacak
şekilde yukarı yuvarlandı.

## Metin düzeni

- Satır sonunda bölünen kelimeler birleştirildi.
- Dize, diyalog ve numaralı madde satırları ayrı satırda bırakıldı.
- Yumuşak tire (U+00AD) silindi.
- İki yerde satır sonu tiresi iki ayrı kelimeyi birleştirmişti; boşlukla ayrıldı
  ("toplumsal gerçekçiliği", "yazarlardan hangisi").
- Kaynaktaki yazım hataları düzeltilmedi; örnek: `ks-008` "Gelenekselli-modernizm",
  `ks-090` "hagisidir". Şiir 1. testin 1. sorusunda D şıkkı kaynakta "C)" diye basılmıştır;
  şıklar sırasıyla A-E alındı.
