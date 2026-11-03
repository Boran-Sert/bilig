"""Kaynak profilinin modelleri: stil anahtarı, profil dosyası, eşleşme ve sınıflanmış satırlar.

Profil bir kitap ya da serinin görünüm kurallarıdır: hangi stil hangi blok türüdür. Stil
anahtarı font, boyut, kalınlık, italik ve metnin içinde durduğu kutunun rengidir. Boyut 0,5
adımına yuvarlanır, böylece dosyaya yazılan boyut ile PDF'ten ölçülen boyut aynı anahtara düşer.
Profil dosyasının biçimi profiles/README.md'dedir.
"""

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.schemas.textbook import BlockType
from app.text.turkish import tr_lower

PROFILE_SIZE_STEP = 0.5


class StyleKey(BaseModel):
    """Bir metnin görünümü: font, boyut, kalın, italik ve kutu rengi (kutuda değilse boş)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    font: str
    size: float
    bold: bool = False
    italic: bool = False
    box_color: str | None = None

    @field_validator("size")
    @classmethod
    def round_size(cls, size: float) -> float:
        """Boyutu 0,5 adımına yuvarlar."""
        return round(size / PROFILE_SIZE_STEP) * PROFILE_SIZE_STEP

    @field_validator("box_color")
    @classmethod
    def lower_color(cls, color: str | None) -> str | None:
        """Rengi küçük harfli #rrggbb yazımına çevirir."""
        return tr_lower(color) if color else color

    def sort_key(self) -> tuple[str, float, bool, bool, str]:
        """Sayımları her çalışmada aynı sıraya koyan anahtar."""
        return (self.font, self.size, self.bold, self.italic, self.box_color or "")


class StyleRule(BaseModel):
    """Profildeki bir satır: bu stil bu blok türüdür."""

    model_config = ConfigDict(extra="forbid")

    style: StyleKey
    block_type: BlockType


class Profile(BaseModel):
    """Kayıtlı profil: ad (dosya adı) ve stil kuralları; stillerin tümü stil izini oluşturur."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str = ""
    styles: list[StyleRule]

    @model_validator(mode="after")
    def check_styles(self) -> "Profile":
        """Profil boş olamaz ve aynı stil iki kez yazılamaz."""
        keys = [rule.style for rule in self.styles]
        if not keys:
            raise ValueError("Profile has no styles")
        if len(set(keys)) != len(keys):
            raise ValueError(f"Profile {self.name!r} repeats a style")
        return self

    def block_type_of(self, style: StyleKey) -> BlockType | None:
        """Stilin blok türünü verir; profilde yoksa boş döner."""
        for rule in self.styles:
            if rule.style == style:
                return rule.block_type
        return None


class StyleCount(BaseModel):
    """Bir stille yazılmış harf sayısı."""

    style: StyleKey
    chars: int


class StyledLine(BaseModel):
    """Okunmuş satır: sayfası, metni, baskın stili ve stillerin harf sayıları."""

    page_no: int
    text: str
    style: StyleKey
    counts: list[StyleCount]


class ProfileMatch(BaseModel):
    """Eşleşme sonucu: bulunan profilin adı (yoksa boş) ve belge harflerinin kapsanan payı."""

    profile_name: str | None
    share: float


class ClassifiedLine(BaseModel):
    """Profil uygulanmış satır: sayfası, metni, stili ve blok türü (profilde yoksa boş)."""

    page_no: int
    text: str
    style: StyleKey
    block_type: BlockType | None
