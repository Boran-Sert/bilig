"""Testlerin kullandığı, repodaki Türkçe kök listesi."""

from pathlib import Path

from app.ingest.text_layer import load_word_list

REPOSITORY_WORD_LIST = Path(__file__).resolve().parents[3] / "data" / "turkce_kelimeler.txt"
KNOWN_WORDS = load_word_list(REPOSITORY_WORD_LIST)
