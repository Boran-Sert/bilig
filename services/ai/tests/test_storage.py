"""Dosya saklama sözleşmesini ve yerel uygulamayı test eder (plan 13.12).

Sözleşme testleri storage fikstürünün verdiği her uygulamaya karşı çalışır; yeni uygulama
(S3 uyumlu depo gibi) fikstüre eklenir ve bu testleri geçmeden açılmaz.
"""

import os
from pathlib import Path

import pytest

from app.storage import FileStorage, LocalFileStorage, page_image_key, source_key


@pytest.fixture(params=["local"])
def storage(request: pytest.FixtureRequest, tmp_path: Path) -> FileStorage:
    """Sözleşme testlerinin çalışacağı saklama uygulaması."""
    implementations = {"local": LocalFileStorage(tmp_path / "data")}
    return implementations[request.param]


def test_written_file_is_read_back(storage: FileStorage) -> None:
    """Yazılan dosya aynı baytlarla okunur ve var sayılır; klasör dosya sayılmaz."""
    storage.write("pages/12/0001.png", b"\x89PNG\r\n")

    assert storage.read("pages/12/0001.png") == b"\x89PNG\r\n"
    assert storage.exists("pages/12/0001.png")
    assert not storage.exists("pages/12")


def test_writing_again_replaces_the_file(storage: FileStorage) -> None:
    """Adım tekrar çalışınca dosyanın üstüne yazılır."""
    storage.write("sources/12.pdf", b"eski")
    storage.write("sources/12.pdf", b"yeni")

    assert storage.read("sources/12.pdf") == b"yeni"


def test_missing_file(storage: FileStorage) -> None:
    """Olmayan dosya yok sayılır, okunursa FileNotFoundError verir."""
    assert not storage.exists("sources/99.pdf")
    with pytest.raises(FileNotFoundError):
        storage.read("sources/99.pdf")


@pytest.mark.parametrize(
    "key",
    [
        "../disari.pdf",
        "/etc/passwd",
        "pages/../../x",
        "pages/..",
        "",
        ".",
        "pages//1.png",
        "pages/./1.png",
        "pages/12/",
        "pages/../1.png",
    ],
)
def test_bad_keys_are_rejected_everywhere(storage: FileStorage, key: str) -> None:
    """Kök dışına çıkan, boş ya da düzgün yazılmamış anahtar her çağrıda reddedilir."""
    with pytest.raises(ValueError, match="Invalid storage key"):
        storage.write(key, b"x")
    with pytest.raises(ValueError, match="Invalid storage key"):
        storage.read(key)
    with pytest.raises(ValueError, match="Invalid storage key"):
        storage.exists(key)


def test_keys_follow_java_paths() -> None:
    """Kaynak ve sayfa görüntüsü anahtarları Java'daki yollarla aynıdır."""
    assert source_key(12) == "sources/12.pdf"
    assert page_image_key(12, 7) == "pages/12/0007.png"
    assert page_image_key(12, 1234) == "pages/12/1234.png"


def test_local_storage_writes_under_root(tmp_path: Path) -> None:
    """Yerel uygulama dosyayı kök altına okunabilir izinle yazar, geçici dosya bırakmaz."""
    storage = LocalFileStorage(tmp_path)

    storage.write(page_image_key(12, 3), b"png")

    path = tmp_path / "pages" / "12" / "0003.png"
    assert path.read_bytes() == b"png"
    assert path.stat().st_mode & 0o777 == 0o644
    assert os.listdir(tmp_path / "pages" / "12") == ["0003.png"]


def test_failed_write_keeps_old_file_and_leaves_no_temporary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Yazma yarıda kesilirse eski dosya bozulmaz ve geçici dosya silinir."""
    storage = LocalFileStorage(tmp_path)
    storage.write("sources/12.pdf", b"eski")

    def fail_replace(source: str, target: Path) -> None:
        """Taşıma anında kesilmeyi taklit eder."""
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(OSError, match="disk full"):
        storage.write("sources/12.pdf", b"yeni")

    assert storage.read("sources/12.pdf") == b"eski"
    assert os.listdir(tmp_path / "sources") == ["12.pdf"]


def test_local_storage_rejects_link_pointing_outside_root(tmp_path: Path) -> None:
    """Kök içindeki bağlantı kökün dışını gösteriyorsa anahtar reddedilir."""
    root, outside = tmp_path / "data", tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "pages").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="Invalid storage key"):
        LocalFileStorage(root).write("pages/12/0001.png", b"png")
    assert list(outside.iterdir()) == []
