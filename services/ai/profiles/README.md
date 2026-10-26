# Kaynak profilleri

Bir kitabın ya da serinin görünüm kuralları (plan A4). Profil, sayfadaki her satırın stiline göre
hangi blok türü olduğunu söyler. Hazırlık hattı profili sayfalara kodla uygular, model çalışmaz.
Kodu `app/ingest/profile.py` ve `app/ingest/styles.py`, modeli `app/schemas/profile.py`.

## Dosya

Her profil bu klasörde bir YAML dosyasıdır. `name` dosya adıyla aynıdır (`tde12_meb.yaml` →
`name: tde12_meb`) ve kaynağın `source_document.profile_name` kolonuna yazılır.

```yaml
name: tde12_meb
description: TDE 12 MEB ders kitabı.
rules:
  - match: {size: 8, color: "#808080"}
    block_type: IGNORE
  - match: {size: 14, bold: true}
    block_type: BASLIK
  - match: {box: "#d9ebff"}
    block_type: BILGI
  - match: {size: 10, boxed: false}
    block_type: METIN
```

| Alan | Açıklama |
| --- | --- |
| `name` | Profilin adı; dosya adıyla aynı. |
| `description` | Profilin hangi kaynak için yazıldığı. |
| `rules` | Sırayla denenen kurallar; satıra ilk uyan kural kazanır. |
| `rules[].match` | Aranan stil alanları. Boş ya da yazılmayan alan her değerle eşleşir; en az bir alan dolu olmalı. |
| `rules[].block_type` | `BASLIK`, `BILGI`, `ALINTI`, `ETKINLIK`, `METIN` ya da satırı atan `IGNORE`. |

`match` alanları PyMuPDF'in metin parçası için verdiği bilgilerdir. Değerleri elle tahmin etmek
yerine stil sayımından (`count_styles`) kopyalayın.

| Alan | Örnek | Not |
| --- | --- | --- |
| `font` | `CharisSIL-Bold` | Fontun tam adı. |
| `size` | `10.5` | Yarım puanın katı; sayımda boyut yarım puana yuvarlanır. |
| `bold`, `italic` | `true` | |
| `color` | `"#808080"` | Yazı rengi, küçük harf. Tırnak şart: YAML'da `#` yorum başlatır. |
| `box` | `"#d9ebff"` | Metnin içinde durduğu dolgulu kutunun rengi. |
| `boxed` | `false` | Metin bir kutunun içinde mi. |

Kutu sayılan çizim görünür dolgulu dikdörtgen ya da köşesi yuvarlak kutudur. Sayfanın %90'ını
kaplayan zemin, görünmez dolgu ve daire gibi şekiller kutu sayılmaz. İç içe kutularda en küçüğü
alınır.

## Nasıl uygulanır

- Satırın türünü, satırda en çok harf tutan stile uyan ilk kural belirler. Hiçbir kurala uymayan
  satır `METIN` olur.
- İtalik parça `*...*`, kalın parça `**...**` olarak korunur. Edebiyat'ta italik eser adıdır.
  Satırın tamamı kalın olan başlık gibi durumlarda, kural `bold: true` istiyorsa kalın işareti
  konmaz; `italic: true` için de aynısı geçerli.
- Yeni bir dosyanın stilleri sayılır. Kurallarına uyan stiller harflerin en az %90'ını tutan
  profiller arasından kapsamı en yüksek olan seçilir. Hiçbiri yetmezse profil önerisi istenir
  (#128).
