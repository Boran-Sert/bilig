"""İpucu, anlatım ve sohbet uçlarının modelleri (plan Bölüm 9, 13.5).

İstek ve cevap gövdeleri Java'yla camelCase konuşur. Akışın olayları tarayıcıya giden olaylarla
aynı adı taşır: delta, citation, done, error. done boştur; mesajı Java kaydeder ve numarasını
kendisi ekler. CitationSource Claude'a search_result olarak giden paragraftır; StreamText ve
StreamCitation stream_task'in parçalarıdır, alıntı kaynağı sıra numarasıyla gelir.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.schemas.question import OptionLabel, QuestionContent


class CamelModel(BaseModel):
    """Java'yla camelCase alan adlarıyla konuşan model."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class HintRequest(CamelModel):
    """İpucu istenen soru."""

    question_id: int


class HintResponse(CamelModel):
    """Sorunun ipucu."""

    hint: str


class ExplanationRequest(CamelModel):
    """Neden yanlış anlatımı istenen soru ve öğrencinin şıkkı."""

    user_id: int
    question_id: int
    selected_option: OptionLabel


class ChatRequest(CamelModel):
    """Son mesajı öğrenciden gelmiş sohbet."""

    conversation_id: int
    user_id: int


class ExplainStyle(StrEnum):
    """Öğrencinin seçtiği anlatım tarzı (app_user.explain_style)."""

    SIMPLE = "SIMPLE"
    EXAMPLES = "EXAMPLES"
    STEP_BY_STEP = "STEP_BY_STEP"


class OutcomeInfo(BaseModel):
    """Sorunun ölçtüğü kazanım."""

    id: int
    code: str
    title: str
    meb_explanation: str | None


class TutorQuestion(BaseModel):
    """Anlatımda kullanılan yayındaki soru."""

    content: QuestionContent
    correct_option: OptionLabel
    outcomes: list[OutcomeInfo]


class ChatTurn(BaseModel):
    """Sohbetteki tek mesaj."""

    role: str
    content: str


class SourceBlock(BaseModel):
    """Alıntılanabilir paragraf ve kaynağı."""

    block_id: int
    source_title: str
    page_no: int
    title_path: str
    markdown: str


class CitationSource(BaseModel):
    """Claude'a search_result olarak giden paragraf."""

    source: str
    title: str
    text: str


class StreamText(BaseModel):
    """Akışta gelen metin parçası."""

    text: str


class StreamCitation(BaseModel):
    """Akışta gelen alıntı: kaynağın gönderilen listedeki sırası."""

    source_index: int


class DeltaEvent(CamelModel):
    """Tarayıcıya giden metin parçası."""

    text: str


class CitationEvent(CamelModel):
    """Tarayıcıya giden alıntı: paragrafın numarası, kaynağı ve sayfası."""

    block_id: int
    source_title: str
    page: int


class ProblemEvent(CamelModel):
    """Akış hatası; Problem Details biçiminde."""

    title: str
    status: int
