"""Kitap sayfasında yan yana duran iki alt sütunun okunuşunu test eder (hazırlık hattı A5)."""

from app.schemas.profile import ProfiledLine
from tests.test_textbook_reader import INFO_BOX, kinds, line, read

LEFT_VERSES = [
    "Korkma, sönmez bu şafaklarda yüzen al sancak;",
    "Sönmeden yurdumun üstünde tüten en son ocak.",
    "O benim milletimin yıldızıdır, parlayacak;",
]
RIGHT_VERSES = [
    "Bastığın yerleri toprak diyerek geçme, tanı:",
    "Düşün altındaki binlerce kefensiz yatanı.",
    "Sen şehit oğlusun, incitme, yazıktır, atanı:",
]


def poem_lines(left_rights: list[float]) -> list[ProfiledLine]:
    """Sol dizeleri verilen sağ kenarlarda, sağ dizeleri 265'ten başlayarak yan yana kurar."""
    lines = [line("Gövde satırı sütunun sağ kenarına kadar uzanır.", 60, right=560)]
    rows = zip(LEFT_VERSES, RIGHT_VERSES, left_rights, strict=True)
    for index, (left, right, left_end) in enumerate(rows):
        top = 100 + 14 * index
        lines += [line(left, top, right=left_end), line(right, top, left=265, right=480)]
    return lines


def test_two_column_poem_is_read_left_column_first() -> None:
    """Yan yana iki sütunlu şiirde önce sol sütunun dizeleri, sonra sağınkiler okunur."""
    markdown = [block.markdown for block in read(poem_lines([245, 220, 245]))]

    assert markdown[1:] == ["\n".join(LEFT_VERSES), "\n".join(RIGHT_VERSES)]


def test_split_region_reaches_back_to_aligned_rows() -> None:
    """Boşluğu dar olan ilk satır da sağ sütunun hizasında başlıyorsa bölgeye katılır."""
    markdown = [block.markdown for block in read(poem_lines([258, 220, 245]))]

    assert markdown[1:] == ["\n".join(LEFT_VERSES), "\n".join(RIGHT_VERSES)]


def test_line_after_poem_is_not_pulled_into_the_region() -> None:
    """Şiirden sonra gelen ve sağ sütunda parçası olmayan satır iki sütunun arasına girmez."""
    lines = poem_lines([245, 220, 245]) + [line("Şiirden sonra kısa paragraf.", 160, right=200)]

    markdown = [block.markdown for block in read(lines)]

    assert markdown[1:] == [
        "\n".join(LEFT_VERSES),
        "\n".join(RIGHT_VERSES),
        "Şiirden sonra kısa paragraf.",
    ]


def test_table_cells_stay_in_their_rows() -> None:
    """Kısa hücreli iki sütunlu tablo alt sütun sayılmaz; her hücre kendi satırıyla okunur."""
    cells = [("Eserler", "Yazarlar"), ("Kiralık Konak", "Yakup Kadri"), ("Eylül", "Mehmet Rauf")]
    lines = []
    for index, (work, author) in enumerate(cells):
        top = 100 + 14 * index
        lines += [line(work, top, right=150), line(author, top, left=200, right=270)]

    markdown = " ".join(" ".join(block.markdown.split()) for block in read(lines))

    assert markdown == "Eserler Yazarlar Kiralık Konak Yakup Kadri Eylül Mehmet Rauf"


def test_term_and_definition_on_one_row_stay_together() -> None:
    """Kelime ve açıklaması arasındaki dar boşluk alt sütun sayılmaz."""
    lines = [
        line("**bel**", 100, "BILGI", left=69, right=87, box=INFO_BOX),
        line(": Toprağı aktarmaya yarayan kürek.", 100, "BILGI", left=103, right=230, box=INFO_BOX),
        line("**dem**", 114, "BILGI", left=69, right=93, box=INFO_BOX),
        line(
            ": Zaman, çağ; devir ve dönem anlamında.",
            114,
            "BILGI",
            left=103,
            right=280,
            box=INFO_BOX,
        ),
    ]

    assert kinds(read(lines)) == [
        (
            "BILGI",
            "**bel** : Toprağı aktarmaya yarayan kürek.\n"
            "**dem** : Zaman, çağ; devir ve dönem anlamında.",
        )
    ]


def test_two_side_by_side_rows_are_not_enough_for_subcolumns() -> None:
    """Yan yana iki uzun satır alt sütun sayılmaz; en az üç iki yanlı satır gerekir."""
    lines = poem_lines([245, 220, 245])[:5]

    assert [block.markdown for block in read(lines)][1:] == [
        f"{LEFT_VERSES[0]} {RIGHT_VERSES[0]}\n{LEFT_VERSES[1]} {RIGHT_VERSES[1]}"
    ]


def test_narrow_gap_between_long_pieces_is_not_a_gutter() -> None:
    """Uzun parçalar arasındaki dar boşluk alt sütun boşluğu sayılmaz."""
    lines = [line("Gövde satırı sütunun sağ kenarına kadar uzanır.", 60, right=560)]
    for index in range(3):
        top = 100 + 14 * index
        lines += [
            line(f"Uzun bir terim adı burada {index}", top, right=200),
            line(f": açıklaması da burada {index}.", top, left=216, right=400),
        ]

    assert [block.markdown for block in read(lines)][1].startswith(
        "Uzun bir terim adı burada 0 : açıklaması da burada 0."
    )
