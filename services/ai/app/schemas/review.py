"""Kaynak düzeyindeki inceleme kaydının ayrıntısı (review_item.detail, #269).

Her sorun bir kod ve varsa sayfası, testi ve soru numarasıdır. Soru kontrollerinin kodları
validators.ValidationProblem'dakilerle aynıdır; öbürleri kaynağın okumasından gelir: cevap
anahtarı bulunamayan soru, ünitesi bulunamayan test, hiç içerik çıkmayan kaynak, metin katmanı
bozuk kalan ya da harfi çözülemeyen sayfa ve kökünde soru olmadığı için atılan şık kümesi. JSON'da
alanlar camelCase yazılır; core inceleme ucunda olduğu gibi döner.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

ProblemCode = Literal[
    "NO_ANSWER_KEY",
    "OPTION_COUNT",
    "OPTION_LABELS",
    "EMPTY_OPTION",
    "EMPTY_STEM",
    "ANSWER_NOT_OPTION",
    "NUMBER_SEQUENCE",
    "UNIT_NOT_FOUND",
    "NO_CONTENT",
    "LOW_TEXT_LAYER",
    "UNDECODED_GLYPHS",
    "NOT_MULTIPLE_CHOICE",
]


class SourceProblem(BaseModel):
    """Kaynaktaki bir sorun: kodu ve varsa sayfası, sayfanın kaydı, testi ve soru numarası."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    code: ProblemCode
    page_no: int | None = None
    page_id: int | None = None
    test: int | None = None
    number: int | None = None
