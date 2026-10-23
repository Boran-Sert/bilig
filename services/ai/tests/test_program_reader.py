"""Öğretim programı okuyucusunu test eder.

Test PDF'i burada üretilir. Satırlar gerçek programın biçimini (kod yazımları, çok satırlı
başlık, harfli ve harfsiz açıklama, sayfa numarası, sayfa geçişi) taklit eder; metinler bu test
için yazılmıştır.
"""

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import pymupdf
import pytest

from app.config import get_settings
from app.constants import PROGRAM_CURRICULUM_NAME, PROGRAM_SUBJECT_CODE, PROGRAM_SUBJECT_NAME
from app.ingest.readers import program as program_reader
from app.ingest.readers.program import (
    heading_name,
    parse_outcome_groups,
    read_outcome_groups,
    read_program,
)
from app.schemas.program import (
    Curriculum,
    LearningOutcome,
    LearningOutcomeGroup,
    Program,
    Subject,
)

SUBJECT = Subject(code="TDE", name="Türk Dili ve Edebiyatı")
CURRICULUM = Curriculum(name="TDE Öğretim Programı 2018", model="LEGACY", year=2018)

PAGES = [
    [
        "12",
        "3.1. PROGRAMIN YAPISI",
        "Kazanımlar aşağıda okuma, yazma ve sözlü iletişim başlıklarıyla verilmiştir.",
        "A) OKUMA (METNİ ANLAMA)",
        "1. ŞİİR",
        "A.1. 1. Şiirin konusunu belirler.",
        "Öğrencinin şiirin konusunu kendi cümleleriyle",
        "söylemesi sağlanır.",
        "A.1. 2. Şiirdeki imgeleri belirleyerek anlama",
        "katkısını değerlendirir.",
        "a. İmge kavramı örneklerle açıklanır.",
        "b. Şiirdeki bütün imgelerin bulunması",
        "beklenmez.",
        "A.1.3. Metinden hareketle dil bilgisi çalışmaları yapar.",
    ],
    [
        "13",
        "2. ÖYKÜLEYİCİ (ANLATMAYA BAĞLI) METİNLER (Masal, Hikâye,",
        "Roman vb.)",
        "A.2. 1. Metnin olay örgüsünü belirler.",
        "a. Olayların sırası giriş-gelişme-",
        "sonuç düzeninde ele alınır.",
        "B) YAZMA",
        "B.1. Farklı türlerde metinler yazar.",
        "B.10. Yazdığı metni gözden geçirir.",
        "a. Yazım ve noktalama denetlenir.",
        "c. Metnin akışı bakımından gözden",
    ],
    [
        "14",
        "geçirilmesi sağlanır.",
        "C) SÖZLÜ İLETİŞİM",
        "1. KONUŞMA",
        "C.1. 1. Konuşmasını planlar.",
        "2. DİNLEME",
        "C.2. 1. Dinlediğini özetler.",
        "3.3. ÜNİTE, SÜRE VE İÇERİK TABLOLARI",
        "1. ÜNİTE: GİRİŞ",
        "A.1. 9. Bu satır bölüm bittikten sonra geldiği için okunmamalı.",
    ],
]


@pytest.fixture(scope="module")
def program_pdf(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Test satırlarını her biri ayrı sayfada olacak biçimde PDF'e yazar."""
    document = pymupdf.open()
    for lines in PAGES:
        page = document.new_page(width=900)
        page.insert_htmlbox(pymupdf.Rect(30, 30, 870, 820), "<br>".join(lines))
    path = tmp_path_factory.mktemp("program") / "program.pdf"
    document.save(path)
    return path


@pytest.fixture(scope="module")
def groups(program_pdf: Path) -> list[LearningOutcomeGroup]:
    """Test PDF'inden okunan kazanım grupları."""
    return read_outcome_groups(program_pdf)


def outcome(groups: list[LearningOutcomeGroup], code: str) -> LearningOutcome:
    """Gruplar içinden koduyla kazanımı bulur."""
    return next(item for group in groups for item in group.outcomes if item.code == code)


def test_groups_are_read_in_order(groups: list[LearningOutcomeGroup]) -> None:
    """Gruplar programdaki sırayla, adları ve kazanım kodlarıyla okunur."""
    assert [(group.code, group.name) for group in groups] == [
        ("A.1", "Şiir"),
        ("A.2", "Öyküleyici (anlatmaya bağlı) metinler"),
        ("B", "Yazma"),
        ("C.1", "Konuşma"),
        ("C.2", "Dinleme"),
    ]
    assert [[item.code for item in group.outcomes] for group in groups] == [
        ["A.1.1", "A.1.2", "A.1.3"],
        ["A.2.1"],
        ["B.1", "B.10"],
        ["C.1.1"],
        ["C.2.1"],
    ]


@pytest.mark.parametrize(
    ("code", "title", "explanation"),
    [
        pytest.param(
            "A.1.1",
            "Şiirin konusunu belirler.",
            "Öğrencinin şiirin konusunu kendi cümleleriyle söylemesi sağlanır.",
            id="maddesiz-paragraf",
        ),
        pytest.param(
            "A.1.2",
            "Şiirdeki imgeleri belirleyerek anlama katkısını değerlendirir.",
            "a. İmge kavramı örneklerle açıklanır.\n"
            "b. Şiirdeki bütün imgelerin bulunması beklenmez.",
            id="cok-satirli-baslik-ve-harfli-maddeler",
        ),
        pytest.param(
            "A.1.3",
            "Metinden hareketle dil bilgisi çalışmaları yapar.",
            None,
            id="bosluksuz-kod-aciklamasiz",
        ),
        pytest.param(
            "A.2.1",
            "Metnin olay örgüsünü belirler.",
            "a. Olayların sırası giriş-gelişme-sonuç düzeninde ele alınır.",
            id="satir-sonu-tiresi",
        ),
        pytest.param(
            "B.10",
            "Yazdığı metni gözden geçirir.",
            "a. Yazım ve noktalama denetlenir.\n"
            "c. Metnin akışı bakımından gözden geçirilmesi sağlanır.",
            id="sayfa-gecisi-ve-sayfa-numarasi",
        ),
    ],
)
def test_outcome_title_and_explanation(
    groups: list[LearningOutcomeGroup], code: str, title: str, explanation: str | None
) -> None:
    """Başlık tek cümle; açıklama harfli maddeler satır satır, maddesiz metin paragraf olarak."""
    item = outcome(groups, code)

    assert item.title == title
    assert item.meb_explanation == explanation


def test_reading_stops_at_next_section(groups: list[LearningOutcomeGroup]) -> None:
    """Kazanımlardan önceki bölüm başlığında durulmaz, sonrakinde durulur."""
    codes = {item.code for group in groups for item in group.outcomes}

    assert "A.1.1" in codes
    assert "A.1.9" not in codes


def test_blank_line_starts_new_paragraph() -> None:
    """Boş satırla ayrılan iki maddesiz paragraf ayrı satırlarda kalır."""
    lines = ["1. ŞİİR", "A.1. 1. Şiiri yorumlar.", "Birinci paragraf.", "", "İkinci paragraf."]

    parsed = parse_outcome_groups(lines)

    assert outcome(parsed, "A.1.1").meb_explanation == "Birinci paragraf.\nİkinci paragraf."


def test_numbered_sentence_inside_explanation_is_not_heading() -> None:
    """Rakamla başlayan küçük harfli açıklama satırı başlık sayılmaz."""
    lines = ["1. ŞİİR", "A.1. 1. Şiiri yorumlar.", "a. Dönem ele alınır.", "2. Yüzyıl şiiri"]

    parsed = parse_outcome_groups(lines)

    assert outcome(parsed, "A.1.1").meb_explanation == "a. Dönem ele alınır. 2. Yüzyıl şiiri"


def test_spaces_are_collapsed_and_text_is_nfc() -> None:
    """Fazla boşluklar teke iner, ayrık şapka harfle birleşir."""
    lines = ["1. ŞİİR", "A.1. 1.  Şiirdeki  ahengi  belirler.", "Kâtip örneği."]

    item = outcome(parse_outcome_groups(lines), "A.1.1")

    assert item.title == "Şiirdeki ahengi belirler."
    assert item.meb_explanation == "Kâtip örneği."


def test_duplicate_outcome_code_fails() -> None:
    """Aynı kod iki kez geçerse okuma hatayla durur."""
    lines = ["1. ŞİİR", "A.1. 1. Şiiri yorumlar.", "A.1. 1. Şiiri yeniden yorumlar."]

    with pytest.raises(ValueError, match="Duplicate learning outcome code A.1.1"):
        parse_outcome_groups(lines)


@pytest.mark.parametrize(
    "after_title",
    [["Bu kazanımda şiir ele alınır."], ["a. Not."], ["A.1. 2. Temayı belirler."], []],
    ids=["paragraf", "madde", "sonraki-kazanim", "metin-sonu"],
)
def test_title_without_period_fails(after_title: list[str]) -> None:
    """Noktasız başlık altındaki metni yutmaz, sessizce de kabul edilmez; okuma hatayla durur."""
    with pytest.raises(ValueError, match="Title of A.1.1 does not end with a period"):
        parse_outcome_groups(["1. ŞİİR", "A.1. 1. Şiiri yorumlar", *after_title])


def test_outcome_before_heading_fails() -> None:
    """Başlıksız kazanımın grubu adlandırılamaz; okuma hatayla durur."""
    with pytest.raises(ValueError, match="before any heading"):
        parse_outcome_groups(["A.1. 1. Şiiri yorumlar."])


def test_text_without_outcomes_fails() -> None:
    """Kazanım bulunamazsa okuma hatayla durur."""
    with pytest.raises(ValueError, match="No learning outcomes"):
        parse_outcome_groups(["Kapak", "İçindekiler"])


@pytest.mark.parametrize(
    ("heading", "name"),
    [
        (
            "ÖYKÜLEYİCİ (ANLATMAYA BAĞLI) EDEBÎ METİNLER (Masal/Fabl, Destan,",
            ("Öyküleyici (anlatmaya bağlı) edebî metinler"),
        ),
        ("SÖZLÜ İLETİŞİM", "Sözlü iletişim"),
        ("IŞIK VE İZ", "Işık ve iz"),
    ],
)
def test_heading_name_uses_turkish_sentence_case(heading: str, name: str) -> None:
    """Başlığın büyük harfli kısmı Türkçe kurallarla cümle düzenine çevrilir."""
    assert heading_name(heading) == name


def test_read_program_adds_subject_and_curriculum(program_pdf: Path) -> None:
    """Program, sabitlerdeki ders ve program sürümüyle birlikte okunur."""
    program = read_program(program_pdf)

    assert program.subject == Subject(code=PROGRAM_SUBJECT_CODE, name=PROGRAM_SUBJECT_NAME)
    assert program.curriculum.name == PROGRAM_CURRICULUM_NAME
    assert program.curriculum.model == "LEGACY"
    assert [group.code for group in program.groups] == ["A.1", "A.2", "B", "C.1", "C.2"]


def test_dry_run_logs_counts_and_writes_nothing(
    program_pdf: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """--dry-run grup başına kazanım sayısını log'a yazar, veritabanına dokunmaz."""

    async def fail_save(program: Program) -> None:
        """Yazma çağrılırsa testi düşürür."""
        raise AssertionError("dry run must not write")

    monkeypatch.setattr(program_reader, "_save", fail_save)

    program_reader.main([str(program_pdf), "--dry-run"])

    record = json.loads(capsys.readouterr().out.splitlines()[-1])
    assert record["message"] == "program parsed"
    assert record["outcomes"] == {"A.1": 3, "A.2": 1, "B": 2, "C.1": 1, "C.2": 1}


def test_command_without_dry_run_saves_program(
    program_pdf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--dry-run verilmezse okunan program veritabanına yazılır."""
    saved: list[Program] = []

    async def record_save(program: Program) -> None:
        """Yazılacak programı kaydeder."""
        saved.append(program)

    monkeypatch.setattr(program_reader, "_save", record_save)

    program_reader.main([str(program_pdf)])

    assert len(saved) == 1
    assert saved[0].curriculum.name == PROGRAM_CURRICULUM_NAME


@pytest.mark.asyncio
async def test_save_closes_pool_even_when_writing_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Yazma hata verse de havuz kapanır ve hata yutulmaz."""
    events: list[str] = []

    class FakePool:
        """Bağlantı veren sahte havuz."""

        @asynccontextmanager
        async def connection(self) -> AsyncIterator[str]:
            """Sahte bağlantı verir."""
            yield "connection"

    async def fake_open(settings: object) -> FakePool:
        """Havuzun açıldığını kaydeder."""
        events.append("open")
        return FakePool()

    async def fake_close() -> None:
        """Havuzun kapandığını kaydeder."""
        events.append("close")

    async def failing_save(connection: str, program: Program) -> None:
        """Yazma hatasını taklit eder."""
        raise RuntimeError("write failed")

    monkeypatch.setenv("DATABASE_URL", "postgresql://app:secret@localhost:5432/hata_analizi")
    get_settings.cache_clear()
    monkeypatch.setattr(program_reader, "open_pool", fake_open)
    monkeypatch.setattr(program_reader, "close_pool", fake_close)
    monkeypatch.setattr(program_reader, "save_program", failing_save)

    with pytest.raises(RuntimeError, match="write failed"):
        await program_reader._save(Program(subject=SUBJECT, curriculum=CURRICULUM, groups=[]))

    assert events == ["open", "close"]
    get_settings.cache_clear()
