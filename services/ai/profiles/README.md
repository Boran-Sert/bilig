# Kaynak profilleri

Profil, bir kitap ya da serinin görünüm kurallarıdır: hangi stil hangi blok türüdür.
Her profil bu klasörde bir `.yaml` dosyasıdır. Dosya adı (uzantısız) profilin adıdır ve
eşleşince `source_document.profile_name` alanına yazılır.

Profil telifli kitap metni içermez; sadece stil ölçüleri yazılır.

## Biçim

```yaml
description: İsteğe bağlı kısa açıklama
styles:
  - style: {font: Palatino-Bold, size: 18, bold: true}
    block_type: BASLIK
  - style: {font: Palatino, size: 10}
    block_type: METIN
  - style: {font: Palatino, size: 10, box_color: "#dcdcdc"}
    block_type: BILGI
  - style: {font: Palatino-Italic, size: 10, italic: true}
    block_type: ALINTI
```

Stil alanları:

| Alan | Anlam |
|---|---|
| `font` | PDF'teki font adı, alt küme öneki (`ABCDEF+`) olmadan |
| `size` | Punto; 0,5 adımına yuvarlanır |
| `bold`, `italic` | Kalın ve italik (varsayılan `false`) |
| `box_color` | Metni çevreleyen dolgulu kutunun rengi (`#rrggbb`); kutuda değilse yazılmaz |

`block_type`: `BASLIK`, `BILGI`, `ALINTI`, `ETKINLIK`, `METIN`.

## Kurallar

- Her stil bir kez yazılır; gövde stili de listede olmalıdır.
- Stiller aynı zamanda profilin stil izidir: belgedeki harflerin en az %85'i profildeki
  stillerle yazılmışsa profil eşleşir; birden çok profil eşleşirse payı en yüksek olan seçilir.
- Profilde olmayan stilli satırın türü boş kalır.
- Hiçbir profil eşleşmezse `profile_name` boş kalır ve profil önerisi istenir (#128).
- Font adları ve boyutlar belgeden ölçülür; `app.ingest.profile.count_styles` bir PDF'in
  stillerini harf sayısıyla verir.
