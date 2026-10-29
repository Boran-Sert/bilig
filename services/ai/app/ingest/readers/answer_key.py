"""Cevap anahtarı okuyucusu (hazırlık hattı A5).

Cevap üç yerde bulunur: sorunun altında kendi satırında ("Cevap: A", "Doğru cevap: B"), testin
sonundaki ya da ayrı dosyadaki anahtarda ("1-B 2-E", "1. C", "1) D") ve birden çok testin
anahtarını taşıyan dosyada "Test 3" başlıklarının altında (ÖDSGM). Anahtar düzenli ifadeyle okunur
ve soru numarasıyla eşlenir; ilk başlıktan önceki metin (kapak, başlık) bölümlere girmez. Aynı
numaraya iki farklı cevap yazılmışsa anahtar güvenilmezdir: okuma ValueError verir ve kaynak
incelemeye düşer. Anahtarla eşlerken cevabı bulunamayan, anahtarla sorunun altındaki cevabı
çelişen ve anahtarda olup hiçbir soruya denk gelmeyen numaralar ayrıca döner; bunlar da
incelemeye düşer (NO_ANSWER_KEY, VALIDATION_FAILED).
"""

import re
from collections.abc import Sequence

from pydantic import BaseModel

from app.constants import ANSWER_KEY_MIN_ENTRIES
from app.schemas.question import OPTION_LABELS, OptionLabel, ParsedQuestion
from app.text.turkish import tr_lower

_KEY_ENTRY = re.compile(r"(?<![\w.])(\d{1,3})\s*[.)\-–:]\s*([A-E])(?!\w)")
_INLINE_ANSWER = re.compile(
    r"^[ \t]*(?:(?i:doğru)[ \t]+)?(?i:cevap|yanıt)[ \t]*:[ \t]*([A-E])[ \t]*\.?[ \t]*$",
    re.MULTILINE,
)
_TEST_HEADING = re.compile(r"^[ \t]*(?:Test|TEST)[ \t]+(\d{1,3})[ \t]*:?[ \t]*$", re.MULTILINE)
_KEY_HEADING = "cevap anahtarı"


class AttachedAnswers(BaseModel):
    """Cevapları yazılmış sorular ve incelemeye düşecek numaralar."""

    questions: list[ParsedQuestion]
    missing: list[int]
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
        inline, from_key = question.correct_option, key.get(question.number)
        if inline is not None and from_key is not None and inline != from_key:
            conflicting.append(question.number)
        correct = from_key or inline
        if correct is None:
            missing.append(question.number)
        answered.append(question.model_copy(update={"correct_option": correct}))
    numbers = {question.number for question in questions}
    unused = sorted(number for number in key if number not in numbers)
    return AttachedAnswers(
        questions=answered, missing=missing, conflicting=conflicting, unused=unused
    )


def _as_label(letter: str) -> OptionLabel:
    """Düzenli ifadenin yakaladığı A-E harfini şık tipine çevirir."""
    return OPTION_LABELS[OPTION_LABELS.index(letter)]
