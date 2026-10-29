"""Sorunun ortak içerik formatı (plan 13.6) ve ayrıştırılan sorunun modeli.

QuestionContent question.content (jsonb) kolonuna olduğu gibi yazılır; doğru şık content'e
girmez, question.correct_option kolonundadır. ParsedQuestion okuyucunun (#130) çıktısıdır:
içerik, testteki soru numarası, sayfa ve bulunduysa cevap anahtarındaki şık.
"""

from typing import Literal, get_args

from pydantic import BaseModel

OptionLabel = Literal["A", "B", "C", "D", "E"]
OPTION_LABELS: tuple[OptionLabel, ...] = get_args(OptionLabel)


class Block(BaseModel):
    """Markdown metin parçası; md'de *italik*, **kalın**, <u>altı çizili</u>, tablo ve liste."""

    type: Literal["paragraph", "table", "list", "numbered_items"]
    md: str


class QuestionOption(BaseModel):
    """Bir şık: harfi ve metin blokları."""

    label: OptionLabel
    blocks: list[Block]


class QuestionContent(BaseModel):
    """Soru kökü, şıklar ve birden çok sorunun ortak parçası."""

    passage: list[Block] | None = None
    stem: list[Block]
    options: list[QuestionOption]


class ParsedQuestion(BaseModel):
    """Kaynaktan okunan soru; cevap anahtarı bulunamadıysa correct_option boştur."""

    number: int
    page_no: int
    content: QuestionContent
    correct_option: OptionLabel | None
