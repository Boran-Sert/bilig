"""Bilgi katmanı adımının veritabanı kullanmayan parçalarını test eder.

Kural kalıpları, ad anahtarı, dayanak kontrolü, benzer ad eşiği ve prompt'un kodun verdiği
değişkenlerle dolması burada sınanır.
"""

import pytest

from app.constants import PROMPTS_DIR
from app.ingest.entities import check_evidence, name_key, rule_entities, similar_node
from app.llm.prompts import render_prompt
from app.schemas.entity_extract import (
    EntityBlock,
    EntityExtraction,
    ExtractedEdge,
    ExtractedNode,
    NodeType,
    Relation,
)


def wrote(author: str, work: str) -> ExtractedEdge:
    """Yazardan esere WROTE bağı kurar."""
    return ExtractedEdge(
        from_type=NodeType.AUTHOR,
        from_name=author,
        relation=Relation.WROTE,
        to_type=NodeType.WORK,
        to_name=work,
    )


def author(name: str) -> ExtractedNode:
    """Yazar notu kurar."""
    return ExtractedNode(node_type=NodeType.AUTHOR, name=name)


def work(name: str) -> ExtractedNode:
    """Eser notu kurar."""
    return ExtractedNode(node_type=NodeType.WORK, name=name)


@pytest.mark.parametrize(
    ("text", "key"),
    [
        ("Viktor Hügo", "viktor hugo"),
        ("  İNCE   Memed! ", "ince memed"),
        ("Küçük Ağa'da", "kucuk aga da"),
        ("Fatih-Harbiye", "fatih harbiye"),
    ],
)
def test_name_key_folds_case_marks_and_punctuation(text: str, key: str) -> None:
    """Ad anahtarı Türkçe küçük harfli, aksansız ve tek boşluklu olur."""
    assert name_key(text) == key


def test_rule_reads_work_author_with_and_without_reading() -> None:
    """Okunuşlu ve okunuşsuz kalıplardan eser, yazar ve WROTE bağı çıkar."""
    text = (
        "*Küçük Ağa* (Tarık Buğra) ve *Sefiller* [Victor Hugo (Viktor Hügo)] "
        "bu dönemin romanlarıdır."
    )

    result = rule_entities(text)

    assert result.nodes == [
        work("Küçük Ağa"),
        author("Tarık Buğra"),
        work("Sefiller"),
        author("Victor Hugo"),
    ]
    assert result.edges == [wrote("Tarık Buğra", "Küçük Ağa"), wrote("Victor Hugo", "Sefiller")]


def test_rule_reads_several_works_of_one_author() -> None:
    """Aynı yazarın birden çok eseri ayrı bağlar olarak çıkar."""
    result = rule_entities("*Yaban* (Yakup Kadri), *Ankara* (Yakup Kadri).")

    assert result.edges == [wrote("Yakup Kadri", "Yaban"), wrote("Yakup Kadri", "Ankara")]


@pytest.mark.parametrize(
    "text",
    ["**Roman** (tür) anlatılır.", "*Sefiller* (1862) yayımlandı.", "Roman (tür) anlatılır."],
)
def test_rule_skips_bold_years_and_plain_text(text: str) -> None:
    """Kalın yazı, yıl ve italik olmayan ad kalıba uymaz."""
    assert rule_entities(text) == EntityExtraction(nodes=[], edges=[])


@pytest.mark.parametrize(
    "text",
    [
        "*Kiralık Konak* (roman) okunur.",
        "*Çile* (şiir kitabı) okunur.",
        "*Yaban* (Tarihî roman) okunur.",
        "*Sefiller* [roman (romanı)] okunur.",
    ],
)
def test_rule_skips_lowercase_descriptions(text: str) -> None:
    """Parantezde küçük harfle başlayan kelime olan tür açıklaması yazar sayılmaz."""
    assert rule_entities(text) == EntityExtraction(nodes=[], edges=[])


def test_evidence_keeps_names_found_in_text() -> None:
    """Adı metinde Türkçe harf ve aksan farkıyla geçen notlar ve bağ kalır."""
    extraction = EntityExtraction(
        nodes=[author("TARIK BUĞRA"), work("Küçük Ağa")],
        edges=[wrote("TARIK BUĞRA", "Küçük Ağa")],
    )

    result = check_evidence(extraction, "Tarık Buğra'nın *Kucuk Aga* romanı")

    assert result == extraction


def test_evidence_accepts_turkish_suffixes() -> None:
    """Ek almış ad metinde geçmiş sayılır; kelimenin ortasından başlayan ad sayılmaz."""
    genre = ExtractedNode(node_type=NodeType.GENRE, name="tarihî roman")
    has_genre = ExtractedEdge(
        from_type=NodeType.WORK,
        from_name="Zümrüt",
        relation=Relation.HAS_GENRE,
        to_type=NodeType.GENRE,
        to_name="tarihî roman",
    )
    extraction = EntityExtraction(
        nodes=[work("Zümrüt"), genre, author("Şan")],
        edges=[has_genre, wrote("Şan", "Zümrüt")],
    )

    result = check_evidence(extraction, "Zümrüt tarihî romanlardandır. Alişan geldi.")

    assert result.nodes == [work("Zümrüt"), genre]
    assert result.edges == [has_genre]


def test_evidence_drops_notes_without_links() -> None:
    """Adı metinde geçse de hiçbir bağın ucu olmayan not yazılmaz."""
    extraction = EntityExtraction(nodes=[author("Tarık Buğra"), work("Küçük Ağa")], edges=[])

    result = check_evidence(extraction, "Tarık Buğra ve Küçük Ağa.")

    assert result == EntityExtraction(nodes=[], edges=[])


def test_evidence_drops_edges_and_nodes_without_support() -> None:
    """Metinde geçmeyen not, ona giden bağ ve not listesinde ucu olmayan bağ atılır."""
    extraction = EntityExtraction(
        nodes=[author("Tarık Buğra"), work("Küçük Ağa"), work("İbiş'in Rüyası")],
        edges=[
            wrote("Tarık Buğra", "İbiş'in Rüyası"),
            wrote("Tarık Buğra", "Küçük Ağa"),
            wrote("Kemal Tahir", "Küçük Ağa"),
        ],
    )

    result = check_evidence(extraction, "Tarık Buğra, Kemal Tahir ve Küçük Ağa.")

    assert result.nodes == [author("Tarık Buğra"), work("Küçük Ağa")]
    assert result.edges == [wrote("Tarık Buğra", "Küçük Ağa")]


def test_evidence_merges_repeated_nodes_and_edges() -> None:
    """Aynı not ve aynı bağ bir kez kalır; notu olan yazım tutulur."""
    noted = ExtractedNode(node_type=NodeType.WORK, name="Küçük Ağa", note="Tarihî roman.")
    extraction = EntityExtraction(
        nodes=[work("Küçük Ağa"), noted, author("Tarık Buğra")],
        edges=[wrote("Tarık Buğra", "Küçük Ağa"), wrote("Tarık Buğra", "Küçük Ağa")],
    )

    result = check_evidence(extraction, "Tarık Buğra, Küçük Ağa")

    assert result.nodes == [noted, author("Tarık Buğra")]
    assert result.edges == [wrote("Tarık Buğra", "Küçük Ağa")]


ALIASES = [(1, "victor hugo"), (2, "orhan kemaloglu")]


@pytest.mark.parametrize(
    ("key", "expected"),
    [("viktor hugo", 1), ("orhan kemal", 2), ("orhan veli", None)],
)
def test_similar_node_returns_note_above_review_score(key: str, expected: int | None) -> None:
    """İnceleme eşiğini geçen en benzer yazımın notu döner; geçmeyen ad için sonuç boştur."""
    result = similar_node(key, ALIASES)

    assert (None if result is None else result[0]) == expected


def test_similar_node_without_aliases_is_none() -> None:
    """Hiç yazım yoksa benzer not yoktur."""
    assert similar_node("tarik bugra", []) is None


def test_entity_prompt_renders_page_paragraphs_with_ids() -> None:
    """Prompt sayfanın paragrafları, numaraları ve başlık yollarıyla dolar."""
    block = EntityBlock(id=41, title_path="TDE 12 › Roman", markdown="*Küçük Ağa* (Tarık Buğra)")
    variables = {"blocks": [block.model_dump()]}

    prompt = render_prompt(PROMPTS_DIR, "entity_extract.j2", variables)

    assert prompt.version >= 1
    assert "not sure" in prompt.system
    assert '<paragraph id="41" heading="TDE 12 › Roman">' in prompt.user
    assert "Küçük Ağa" in prompt.user
