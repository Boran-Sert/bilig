# data

Servislerin kullandığı küçük, açık lisanslı veri dosyaları. PDF, sayfa görüntüsü ya da kitap
metni bu klasöre konmaz.

## turkce_kelimeler.txt

Metin katmanı kontrolünün (`services/ai/app/ingest/text_layer.py`, plan A3) kullandığı Türkçe
kök listesi. Her satırda bir kök biçimi; küçük harf, Unicode NFC, sadece Türk alfabesi
(`a-z` içinden q, w, x hariç; ç, ğ, ı, ö, ş, ü ve â, î, û).
Dosya imaja girmez: compose bu klasörü `ai-worker`'a `/app/data` olarak salt okunur bağlar,
yolu `WORD_LIST_PATH` ayarı verir.

### Kaynak ve lisans
- Kaynak: [Zemberek-NLP](https://github.com/ahmetaa/zemberek-nlp), commit
  `037202c7e18b977c95181a76db05cb1e95846554`, `morphology/src/main/resources/tr/` altındaki
  `master-dictionary.dict`, `non-tdk.dict`, `proper.dict`, `person-names.dict`,
  `proper-from-corpus.dict` (yazar ve yer adları; derlemden toplanmış, hatalı ad içerebilir) ve
  `abbreviations.dict` (vb, bkz gibi kısaltmalar).
- Lisans: Apache License 2.0. Copyright 2018 Ahmet A. Akın, Mehmet D. Akın.
  Lisans metni: [LICENSE-zemberek.txt](LICENSE-zemberek.txt).
- Bu dosya Zemberek sözlüklerinden aşağıdaki kurallarla türetilmiştir; orijinal dosyalar değildir.

### Nasıl türetildi
1. Her satırda `[` işaretinden önceki kelime alınır; `##` ile başlayan yorumlar ve `P:Punc`
   etiketli satırlar atlanır. Birden çok kelimeli girişler kelimelerine bölünür,
   kelimenin başındaki ve sonundaki `'`, `-`, `.` işaretleri atılır.
2. Kelime NFC'ye ve Türkçe küçük harfe çevrilir (İ → i, I → ı). Türk alfabesi dışında harf
   içeren ya da iki harften kısa olanlar atılır.
3. Eklemeli yapı için kök biçimleri de eklenir:
   - Fiillerin `-mek` / `-mak` eki atılmış kökü (`gitmek` → `git`).
   - Sonu p, ç, t, k ile biten ve `NoVoicing` etiketi olmayan kökün yumuşamış biçimi
     (`kitap` → `kitab`, `renk` → `reng`, `git` → `gid`).
   - `LastVowelDrop` etiketli kökün son ünlüsü düşmüş biçimi (`ağız` → `ağz`).
   - `Doubling` etiketli kökün son ünsüzü ikilenmiş biçimi (`hak` → `hakk`).
   - `demek` ve `yemek` fiillerinin daralmış kökleri (`diy`, `yiy`: diyor, yiyor).
4. Sonuç tekrarsız ve Unicode kod noktası sırasıyla yazılır (75.664 satır).

Kontrol bir kelimenin kendisini değil, bu listedeki bir kökle başlayıp başlamadığını arar
(`romanlarından` → `roman`); bu yüzden çekimli biçimler listeye eklenmez.
