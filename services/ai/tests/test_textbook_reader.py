"""Ders kitabı okuyucusunun blok ve başlık yolu kurallarını test eder (hazırlık hattı A5).

Satırlar elle kurulur: kitap sayfası sol sütunda (40-280), yazı boyutu 10, satır aralığı 14.
"""

from app.ingest.readers.textbook import TextbookBlock, read_textbook
from app.schemas.profile import BlockType, BoundingBox, ProfiledLine, TextStyle
from tests.profiled_lines import PAGE_WIDTH

SOURCE = "TDE 12 Ders Kitabı"
INFO_BOX: BoundingBox = (35, 300, 285, 400)


def line(
    text: str,
    top: float,
    block_type: BlockType = "METIN",
    right: float = 280,
    left: float = 40,
    page_no: int = 1,
    size: float = 10,
    box: BoundingBox | None = None,
) -> ProfiledLine:
    """Verilen yerde, türde ve kutuda tek satır kurar."""
    style = TextStyle(font="Serif", size=size, bold=False, italic=False, color="#000000", box=None)
    return ProfiledLine(
        page_no=page_no,
        block_type=block_type,
        markdown=text,
        style=style,
        box_bbox=box,
        bbox=(left, top, right, top + size + 2),
    )


def read(lines: list[ProfiledLine]) -> list[TextbookBlock]:
    """Satırlardan kitabın bloklarını okur."""
    return read_textbook(lines, PAGE_WIDTH, SOURCE)


def kinds(blocks: list[TextbookBlock]) -> list[tuple[str, str]]:
    """Blokları tür ve markdown olarak döner."""
    return [(block.block_type, block.markdown) for block in blocks]


def test_paragraph_lines_join_into_one_block() -> None:
    """Paragrafın satırları birleşir: tireyle bölünen kelime birleşir, italik korunur."""
    lines = [
        line("Halk şiiri *Kara Toprak* gibi şiirlerle geli-", 100),
        line("şerek günümüze kadar uzanan bir gelenektir.", 114, right=230),
    ]

    assert kinds(read(lines)) == [
        (
            "METIN",
            "Halk şiiri *Kara Toprak* gibi şiirlerle gelişerek günümüze kadar uzanan "
            "bir gelenektir.",
        )
    ]


def test_type_box_gap_and_list_start_open_new_blocks() -> None:
    """Tür ya da kutu değişince, boşluk büyüyünce ve madde başlayınca yeni blok başlar."""
    lines = [
        line("Birinci paragraf.", 100, right=150),
        line("Kutudaki bilgi.", 114, "BILGI", right=150, box=INFO_BOX),
        line("Başka kutu.", 128, "BILGI", right=150, box=(35, 120, 285, 140)),
        line("Kıta bir.", 142, right=150),
        line("Kıta iki.", 172, right=150),
        line("1. Birinci soru.", 186, right=150),
        line("2. İkinci soru.", 200, right=150),
    ]

    assert [block.markdown for block in read(lines)] == [
        "Birinci paragraf.",
        "Kutudaki bilgi.",
        "Başka kutu.",
        "Kıta bir.",
        "Kıta iki.",
        "1. Birinci soru.",
        "2. İkinci soru.",
    ]


def test_headings_build_title_path_by_size() -> None:
    """Başlıklar boyutuna göre düzey alır; başlık yolu işaretsiz başlıklardan kurulur."""
    lines = [
        line("**ŞİİR**", 60, "BASLIK", size=14, right=120),
        line("**Halk Şiiri**", 90, "BASLIK", size=12, right=120),
        line("Gövde bir.", 110, right=150),
        line("**ROMAN**", 140, "BASLIK", size=14, right=120),
        line("Gövde iki.", 160, right=150),
    ]

    paths = [block.title_path for block in read(lines)]

    assert paths == [
        "TDE 12 Ders Kitabı › ŞİİR",
        "TDE 12 Ders Kitabı › ŞİİR › Halk Şiiri",
        "TDE 12 Ders Kitabı › ŞİİR › Halk Şiiri",
        "TDE 12 Ders Kitabı › ROMAN",
        "TDE 12 Ders Kitabı › ROMAN",
    ]


def test_search_text_is_title_path_and_markdown() -> None:
    """Arama metni başlık yolu ve markdown'dır."""
    lines = [line("**ŞİİR**", 60, "BASLIK", size=14, right=120), line("Gövde.", 90, right=150)]

    assert read(lines)[1].search_text == "TDE 12 Ders Kitabı › ŞİİR\nGövde."


def test_shadow_duplicates_are_read_once() -> None:
    """Gölge için aynı yere iki kez basılmış satır bir kez okunur."""
    heading = line("**BİLİNMEYEN KELİMELER**", 60, "BASLIK", size=13, right=200)

    assert kinds(read([heading, heading])) == [("BASLIK", "**BİLİNMEYEN KELİMELER**")]


def test_narrow_paragraph_beside_image_joins_by_its_own_width() -> None:
    """Resim yanında daralan paragrafın satırları, sütunun değil kendi genişliğine göre birleşir."""
    lines = [
        line("Sayfanın tam genişliğindeki satır.", 60),
        line("Romanlar ve şiirler birer iç ya-", 100, right=170),
        line("şayıştan doğmuştur.", 114, right=140),
    ]

    blocks = read(lines)

    assert blocks[-1].markdown == "Romanlar ve şiirler birer iç yaşayıştan doğmuştur."


def test_sibling_headings_do_not_nest_when_a_level_is_skipped() -> None:
    """Ara düzeyi olmayan bölümde aynı boyuttaki kardeş başlıklar birbirinin altına girmez."""
    lines = [
        line("**A**", 60, "BASLIK", size=14, right=100),
        line("**B**", 90, "BASLIK", size=12, right=100),
        line("**C**", 120, "BASLIK", size=12, right=100),
        line("**Z**", 150, "BASLIK", size=13, right=100),
    ]

    assert [block.title_path.removeprefix(SOURCE) for block in read(lines)] == [
        " › A",
        " › A › B",
        " › A › C",
        " › A › Z",
    ]


def test_heading_size_change_starts_a_new_heading() -> None:
    """Hemen alt alta duran farklı boyutlu iki başlık ayrı başlık bloklarıdır."""
    lines = [
        line("**ŞİİR**", 60, "BASLIK", size=14, right=100),
        line("**Halk Şiiri**", 76, "BASLIK", size=12, right=120),
    ]

    assert [block.title_path for block in read(lines)] == [
        "TDE 12 Ders Kitabı › ŞİİR",
        "TDE 12 Ders Kitabı › ŞİİR › Halk Şiiri",
    ]


def test_position_counts_blocks_on_their_first_page() -> None:
    """Her bloğun sırası ilk sayfasında 0'dan sayılır."""
    lines = [
        line("Bir.", 60, right=100),
        line("İki.", 90, right=100),
        line("Üç.", 60, right=100, page_no=2),
    ]

    assert [(block.page_no, block.position) for block in read(lines)] == [(1, 0), (1, 1), (2, 0)]


def test_list_number_continuing_a_sentence_is_not_a_new_item() -> None:
    """Dolu ve noktasız satırdan sonra gelen "19. yüzyıl" madde sayılmaz, cümle sürer."""
    lines = [
        line("Bu akım Avrupa'da ilk kez", 100),
        line("19. yüzyılda görülmüştür.", 114, right=200),
        line("1. Birinci soru.", 128, right=200),
    ]

    assert [block.markdown for block in read(lines)] == [
        "Bu akım Avrupa'da ilk kez 19. yüzyılda görülmüştür.",
        "1. Birinci soru.",
    ]
