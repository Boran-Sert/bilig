"""Cevap anahtarı okuyucusu (hazırlık hattı A5).

Cevap üç yerde bulunur: sorunun altında kendi satırında ("Cevap: A", "Doğru cevap: B"), testin
sonundaki ya da ayrı dosyadaki anahtarda ("1-B 2-E", "1. C", "1) D") ve birden çok testin
anahtarını taşıyan dosyada "Test 3" başlıklarının altında (ÖDSGM). Anahtar düzenli ifadeyle okunur
ve soru numarasıyla eşlenir; ilk başlıktan önceki metin (kapak, başlık) bölümlere girmez. ÖDSGM
anahtarında cevaplar başlıkla aynı satırda başlar ("Test 14 1. E 2. A"). Aynı numaraya iki
farklı cevap yazılmışsa anahtar güvenilmezdir: okuma ValueError verir ve kaynak incelemeye
düşer. Anahtarla eşlerken cevabı bulunamayan, anahtarla sorunun altındaki cevabı çelişen ve
anahtarda olup hiçbir soruya denk gelmeyen numaralar ayrıca döner. Testin anahtardaki numarası
ilk sayfanın altındaki ünite satırından sonra yazılır ("Şiir - 4" ve altında "14"); dosya adı
bu numarayı vermez. Ayrı yüklenen anahtar dosyası (ANSWER_KEY) EXTRACT'te okunur ve hiç cevap
çıkmazsa VALIDATION_FAILED (NO_CONTENT) ile incelemeye düşer; cevaplar saklanmaz, anahtar bağlı
test işlenirken dosyadan yeniden okunur (readers/test.py).
"""

import asyncio
import re
from collections.abc import Sequence
from typing import TYPE_CHECKING

import structlog
from pydantic import BaseModel

from app.constants import ANSWER_KEY_MIN_ENTRIES
from app.db.queries.review import close_source_review, open_source_review
from app.ingest import pdf
from app.schemas.question import OPTION_LABELS, OptionLabel, ParsedQuestion
from app.schemas.review import SourceProblem
from app.storage import source_key
from app.text.turkish import tr_lower

if TYPE_CHECKING:
    from app.ingest.pipeline import IngestContext

_KEY_ENTRY = re.compile(r"(?<![\w.])(\d{1,3})\s*[.)\-–:]\s*([A-E])(?!\w)")
_INLINE_ANSWER = re.compile(
    r"^[ \t]*(?:(?i:doğru)[ \t]+)?(?i:cevap|yanıt)[ \t]*:[ \t]*([A-E])[ \t]*\.?[ \t]*$",
    re.MULTILINE,
)
_TEST_HEADING = re.compile(r"^[ \t]*(?:Test|TEST)[ \t]+(\d{1,3})\b[ \t]*:?", re.MULTILINE)
_TEST_NUMBER = re.compile(r"-[ \t]*\d{1,2}[ \t\r]*\n[ \t]*(\d{1,3})[ \t\r]*$", re.MULTILINE)
_KEY_HEADING = "cevap anahtarı"


class AttachedAnswers(BaseModel):
    """Cevapları yazılmış sorular ve incelemeye düşecek numaralar."""

    questions: list[ParsedQuestion]
    missing: list[int | None]
    conflicting: list[int]
    unused: list[int]


def parse_answer_key(text: str) -> dict[int, OptionLabel]:
    """Tek testin anahtarını soru numarası → şık olarak okur."""
    key: dict[int, OptionLabel] = {}
    for match in _KEY_ENTRY.finditer(text):
        number, label = int(match.group(1)), _as_label(match.group(2))
        if key.get(number, label) != label:
            raise ValueError(f"Answer key has two answers for question {number}")
        key[number] = label
    return key


def is_answer_key(text: str) -> bool:
    """Metin anahtar başlığı ya da 1'den başlayan yeterince cevap taşıyorsa doğru döner."""
    if _KEY_HEADING in tr_lower(text):
        return True
    numbers = {int(match.group(1)) for match in _KEY_ENTRY.finditer(text)}
    return set(range(1, ANSWER_KEY_MIN_ENTRIES + 1)) <= numbers


def find_test_number(page_text: str) -> int | None:
    """İlk sayfanın altındaki "Şiir - 4" satırının ardından gelen test numarasını bulur."""
    numbers = _TEST_NUMBER.findall(page_text)
    return int(numbers[-1]) if numbers else None


def key_for_test(key_text: str, test_number: int | None) -> dict[int, OptionLabel]:
    """Anahtar dosyasından testin cevaplarını okur; "Test N" bölümü yoksa bütün metin anahtardır."""
    sections = split_by_test(key_text)
    if not sections:
        return parse_answer_key(key_text)
    section = sections.get(test_number) if test_number is not None else None
    return parse_answer_key(section) if section is not None else {}


def split_by_test(text: str) -> dict[int, str]:
    """Çok testli anahtarı "Test N" başlıklarına göre test numarası → metin olarak böler."""
    headings = list(_TEST_HEADING.finditer(text))
    sections: dict[int, str] = {}
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        number = int(heading.group(1))
        if number in sections:
            raise ValueError(f"Answer key has two sections for test {number}")
        sections[number] = text[heading.end() : end]
    return sections


def find_inline_answer(text: str) -> OptionLabel | None:
    """Kendi satırındaki "Cevap: A" ya da "Doğru cevap: A" satırından şıkkı bulur."""
    match = _INLINE_ANSWER.search(text)
    return _as_label(match.group(1)) if match else None


def attach_answers(
    questions: Sequence[ParsedQuestion], key: dict[int, OptionLabel]
) -> AttachedAnswers:
    """Anahtardaki cevapları sorulara yazar; eksik, çelişen ve kullanılmayan numaraları ayırır."""
    answered, missing, conflicting = [], [], []
    for question in questions:
        inline = question.correct_option
        from_key = key.get(question.number) if question.number is not None else None
        if inline is not None and from_key is not None and inline != from_key:
            conflicting.append(question.number)
        correct = from_key or inline
        if correct is None:
            missing.append(question.number)
        answered.append(question.model_copy(update={"correct_option": correct}))
    numbers = {question.number for question in questions if question.number is not None}
    unused = sorted(number for number in key if number not in numbers)
    return AttachedAnswers(
        questions=answered, missing=missing, conflicting=conflicting, unused=unused
    )


async def check_answer_key(source_id: int, context: "IngestContext") -> None:
    """Anahtar dosyasını okur; cevap çıkmazsa incelemeye düşer, çıkarsa eski kayıt kapanır."""
    content = await asyncio.to_thread(context.storage.read, source_key(source_id))
    text = await asyncio.to_thread(pdf.read_text, content)
    try:
        sections = split_by_test(text) or {0: text}
        entries = sum(len(parse_answer_key(section)) for section in sections.values())
    except ValueError as error:
        structlog.get_logger().warning(
            "answer key unreadable", source_id=source_id, error=str(error)
        )
        entries = 0
    async with context.connect() as connection:
        if entries:
            await close_source_review(connection, source_id, "VALIDATION_FAILED")
        else:
            problems = [SourceProblem(code="NO_CONTENT")]
            await open_source_review(connection, source_id, "VALIDATION_FAILED", problems)


def _as_label(letter: str) -> OptionLabel:
    """Düzenli ifadenin yakaladığı A-E harfini şık tipine çevirir."""
    return OPTION_LABELS[OPTION_LABELS.index(letter)]
