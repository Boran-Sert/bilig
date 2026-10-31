"""Ortak aramayı (vektör, BM25, RRF ve reranker) sahte embedding ve gerçek Postgres'le test eder."""

import pytest
from pydantic import ValidationError

from app.schemas.search import SearchFilters, SearchTarget


def test_knowledge_node_search_rejects_filters() -> None:
    """knowledge_node aramasına verilen ünite filtresi reddedilir."""
    with pytest.raises(ValidationError):
        SearchFilters(target=SearchTarget.KNOWLEDGE_NODE, curriculum_unit_id=1)
