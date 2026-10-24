"""Öğretim programı okuyucusu (hazırlık hattı A1).

Program PDF'i Word'den üretildiği için metin katmanı sağlamdır; PyMuPDF metni satır satır
verir. Kazanımlar "A.2. 5. Metnin olay örgüsünü belirler." ya da "B.3. ..." biçiminde yakalanır.
Kazanımın altındaki a, b, c maddeleri ya da maddesiz paragraf o kazanımın MEB açıklamasıdır ve
olduğu gibi saklanır. Grup adı, kazanımlardan önceki büyük harfli başlıktan ("1. ŞİİR",
"B) YAZMA") alınır. Okuma kazanımlardan sonraki ilk bölüm başlığında ("3.3. ÜNİTE, ...") durur.
Kazanım başlığı noktaya kadar sürer ve küçük harfle başlayan satırlarla devam eder; noktasız
biten ya da büyük harfli satıra taşan başlık, açıklamayı yutmamak için hatayla durdurulur.
"""

import re
from collections.abc import Iterable
from itertools import takewhile
from pathlib import Path

import pymupdf

from app.schemas.program import LearningOutcome, LearningOutcomeGroup
from app.text.turkish import normalize_nfc, tr_lower, tr_upper

_OUTCOME = re.compile(r"^([A-Z])\.\s*(\d+)\.(?:\s*(\d+)\.)?\s+(\S.*)$")
_LETTER_HEADING = re.compile(r"^[A-Z]\)\s+(\S.*)$")
_NUMBERED_HEADING = re.compile(r"^\d+\.\s+(\S.*)$")
_SECTION_HEADING = re.compile(r"^\d+\.\d+\.\s+[A-ZÇĞİÖŞÜ]{2,}")
_ITEM_MARKER = re.compile(r"^[a-zçğıöşü]\.\s")
_PAGE_NUMBER = re.compile(r"^\d+$")
_SPACES = re.compile(r"\s+")


def read_outcome_groups(path: Path) -> list[LearningOutcomeGroup]:
    """Program PDF'ini okuyup kazanım gruplarını ve kazanımları döner."""
    with pymupdf.open(path) as document:
        lines = [line for page in document for line in page.get_text().splitlines()]
    return parse_outcome_groups(lines)


def parse_outcome_groups(lines: Iterable[str]) -> list[LearningOutcomeGroup]:
    """Program metninin satırlarından kazanım gruplarını ve kazanımları çıkarır."""
    parser = _ProgramParser()
    for line in lines:
        if not parser.feed(_SPACES.sub(" ", normalize_nfc(line)).strip()):
            break
    return parser.finish()


def heading_name(text: str) -> str:
    """Büyük harfli başlığın baştaki büyük harfli kısmını Türkçe cümle düzenine çevirir."""
    parts = re.split(r"\s(?=\()", text.strip())
    name = " ".join(takewhile(lambda part: part == tr_upper(part), parts))
    return tr_upper(name[:1]) + tr_lower(name[1:])


def _is_group_heading(text: str) -> bool:
    """Metnin ilk parçası en az iki harfli ve tamamen büyük harfse doğru döner."""
    first = re.split(r"\s(?=\()", text)[0]
    return sum(char.isalpha() for char in first) >= 2 and first == tr_upper(first)


class _ProgramParser:
    """Program satırlarını sırayla okuyup kazanım ağacını kuran durum makinesi."""

    def __init__(self) -> None:
        """Boş ağaçla başlar."""
        self._heading: str | None = None
        self._groups: dict[str, LearningOutcomeGroup] = {}
        self._code: str | None = None
        self._title: list[str] = []
        self._explanation: list[str] = []
        self._paragraph_break = False

    def feed(self, line: str) -> bool:
        """Bir satırı işler; kazanımlar bittiyse yanlış döner."""
        if not line:
            self._paragraph_break = True
        elif _PAGE_NUMBER.match(line):
            return True
        elif self._groups and _SECTION_HEADING.match(line):
            return False
        elif match := _OUTCOME.match(line):
            self._start_outcome(match)
        elif heading := _LETTER_HEADING.match(line) or _NUMBERED_HEADING.match(line):
            if heading.re is _LETTER_HEADING or _is_group_heading(heading.group(1)):
                self._close_outcome()
                self._heading = heading.group(1)
            else:
                self._add_text(line)
        else:
            self._add_text(line)
        return True

    def finish(self) -> list[LearningOutcomeGroup]:
        """Son kazanımı kapatır ve grupları programdaki sırayla döner."""
        self._close_outcome()
        if not self._groups:
            raise ValueError("No learning outcomes found in program text")
        return list(self._groups.values())

    def _start_outcome(self, match: re.Match[str]) -> None:
        """Yeni bir kazanıma başlar; grubu yoksa son başlıkla açar."""
        self._close_outcome()
        letter, first, second, title = match.groups()
        group_code = f"{letter}.{first}" if second else letter
        if group_code not in self._groups:
            if self._heading is None:
                raise ValueError(f"Outcome {group_code} appears before any heading")
            self._groups[group_code] = LearningOutcomeGroup(
                code=group_code, name=heading_name(self._heading), outcomes=[]
            )
        self._code = f"{group_code}.{second or first}"
        self._title = [title]

    def _add_text(self, line: str) -> None:
        """Satırı açık kazanımın başlığına ya da açıklamasına ekler."""
        if self._code is None:
            return
        if not self._title[-1].endswith(".") and not _ITEM_MARKER.match(line):
            if line[0].isupper():
                raise ValueError(f"Title of {self._code} does not end with a period")
            self._title.append(line)
        elif _ITEM_MARKER.match(line) or self._paragraph_break or not self._explanation:
            self._explanation.append(line)
        else:
            self._explanation[-1] = _join_lines(self._explanation[-1], line)
        self._paragraph_break = False

    def _close_outcome(self) -> None:
        """Açık kazanımı grubuna ekler."""
        if self._code is None:
            return
        if not self._title[-1].endswith("."):
            raise ValueError(f"Title of {self._code} does not end with a period")
        group = self._groups[self._code.rsplit(".", 1)[0]]
        if any(outcome.code == self._code for outcome in group.outcomes):
            raise ValueError(f"Duplicate learning outcome code {self._code}")
        group.outcomes.append(
            LearningOutcome(
                code=self._code,
                title=" ".join(self._title),
                meb_explanation="\n".join(self._explanation) or None,
            )
        )
        self._code, self._title, self._explanation = None, [], []
        self._paragraph_break = False


def _join_lines(previous: str, line: str) -> str:
    """Bölünmüş satırı öncekine ekler; satır sonu tiresinde boşluk bırakmaz."""
    return f"{previous}{line}" if previous.endswith("-") else f"{previous} {line}"
