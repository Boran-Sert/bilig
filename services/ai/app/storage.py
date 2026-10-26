"""Dosya saklama: kaynak PDF'leri ve sayfa görüntüleri (plan 13.12).

İş kodu sadece FileStorage sözleşmesini bilir; şimdiki uygulama LocalFileStorage, /data
volume'üne yazar (STORAGE_DIR). Yollar Java'dakiyle aynıdır: kaynak sources/{id}.pdf, sayfa
görüntüsü pages/{id}/{sayfa:04d}.png. Yazma önce geçici dosyaya yapılır, diske işlenir (fsync),
sonra yerine taşınır; yarıda kesilen yazma yarım dosya bırakmaz ve adım tekrar çalışınca dosyanın
üstüne yazılır. Dosyalar STORAGE_FILE_MODE izniyle yazılır; volume'ü paylaşan core da okur.
Anahtar köke göre göreli ve düzgün yazılmış olmalıdır ("a//b", "a/./b", sondaki / reddedilir;
S3'te bunlar ayrı anahtarlardır); kökün dışına çıkan anahtar (.., mutlak yol, kök dışını gösteren
bağlantı) reddedilir.
"""

import os
import tempfile
from pathlib import Path, PurePosixPath
from typing import Protocol

from app.constants import STORAGE_FILE_MODE


class FileStorage(Protocol):
    """Dosya saklama sözleşmesi; anahtar köke göre göreli, / ile ayrılmış yoldur.

    Çağrılar eşzamanlıdır; iş kuyruğu çalışanından asyncio.to_thread ile çağrılır. Geçersiz
    anahtar her çağrıda ValueError verir.
    """

    def write(self, key: str, content: bytes) -> None:
        """Dosyayı yazar; varsa üstüne yazar."""

    def read(self, key: str) -> bytes:
        """Dosyayı okur; yoksa FileNotFoundError verir."""

    def exists(self, key: str) -> bool:
        """Dosya varsa doğru döner."""


def source_key(source_id: int) -> str:
    """Kaynak PDF'inin anahtarını verir."""
    return f"sources/{source_id}.pdf"


def page_image_key(source_id: int, page_no: int) -> str:
    """Sayfa görüntüsünün anahtarını verir."""
    return f"pages/{source_id}/{page_no:04d}.png"


class LocalFileStorage:
    """Dosyaları yerel bir klasörde (Docker'da /data volume'ü) saklar."""

    def __init__(self, root: Path) -> None:
        """Kök klasörü saklar."""
        self.root = root.resolve()

    def write(self, key: str, content: bytes) -> None:
        """Dosyayı diske işlenmiş geçici dosyaya yazıp okunabilir izinle yerine taşır."""
        path = self._path_of(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as file:
            temporary = Path(file.name)
            try:
                file.write(content)
                file.flush()
                os.fsync(file.fileno())
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise
        try:
            os.chmod(temporary, STORAGE_FILE_MODE)
            os.replace(temporary, path)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise

    def read(self, key: str) -> bytes:
        """Dosyayı okur."""
        return self._path_of(key).read_bytes()

    def exists(self, key: str) -> bool:
        """Dosya varsa doğru döner."""
        return self._path_of(key).is_file()

    def _path_of(self, key: str) -> Path:
        """Anahtarın kök altındaki yolunu verir; bozuk ya da kök dışı anahtarı reddeder."""
        relative = PurePosixPath(key)
        path = (self.root / relative).resolve()
        canonical = str(relative) == key and ".." not in relative.parts
        if not canonical or path == self.root or not path.is_relative_to(self.root):
            raise ValueError(f"Invalid storage key {key!r}")
        return path
