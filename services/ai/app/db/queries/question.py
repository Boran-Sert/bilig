"""Test sorularını question, exam ve exam_question tablolarına yazan sorgular (hazırlık hattı A5).

Soru content_hash ile tektir: aynı soru ikinci kez eklenmez, var olan satır kullanılır; böylece
adım tekrar çalışınca ve aynı soru başka testte geçince kopya oluşmaz. Test (exam) kaynak ve
başlıkla bulunur, yoksa açılır. Soru testteki sırasıyla (position) bağlanır. Doğru şık
correct_option kolonundadır, content'e girmez. Sorular DRAFT yazılır; yayın kazanım eşleştirmesinden
sonra olur. Hazırlık bitince kaynağın en az bir yayındaki sorusu olan taslak testleri yayına girer.
Tablolar core'un Flyway migration'larıyla kurulur.
"""

import hashlib

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb

from app.ingest.validators import normalize_for_comparison
from app.schemas.question import ParsedQuestion, QuestionContent

SELECT_EXAM = """
SELECT id FROM exam WHERE source_document_id = %(source_id)s AND title = %(title)s
"""

INSERT_EXAM = """
INSERT INTO exam (curriculum_unit_id, source_document_id, title)
VALUES (%(unit_id)s, %(source_id)s, %(title)s)
RETURNING id
"""

UPSERT_QUESTION = """
INSERT INTO question (source_page_id, curriculum_unit_id, origin, content, correct_option,
    content_hash)
VALUES (
    (SELECT id FROM source_page
     WHERE source_document_id = %(source_id)s AND page_no = %(page_no)s),
    %(unit_id)s, 'SOURCE', %(content)s, %(correct_option)s, %(content_hash)s
)
ON CONFLICT (content_hash) DO UPDATE SET content_hash = EXCLUDED.content_hash
RETURNING id
"""

LINK_EXAM_QUESTION = """
INSERT INTO exam_question (exam_id, question_id, position)
VALUES (%(exam_id)s, %(question_id)s, %(position)s)
ON CONFLICT DO NOTHING
"""

PUBLISH_SOURCE_EXAMS = """
UPDATE exam SET status = 'PUBLISHED'
WHERE source_document_id = %(source_id)s
    AND status = 'DRAFT'
    AND EXISTS (
        SELECT 1
        FROM exam_question
        JOIN question ON question.id = exam_question.question_id
        WHERE exam_question.exam_id = exam.id AND question.status = 'PUBLISHED'
    )
"""


def content_hash(content: QuestionContent) -> str:
    """Sorunun içeriğinden 64 karakterlik özet üretir; biçim farkları özeti değiştirmez."""
    text = normalize_for_comparison(content.to_text())
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def save_exam(
    connection: AsyncConnection,
    source_id: int,
    unit_id: int,
    title: str,
    questions: list[ParsedQuestion],
) -> int:
    """Testi ve cevabı bulunmuş sorularını yazar; yazılan sorunun sayısını verir."""
    exam_id = await _fetch_exam_id(connection, source_id, unit_id, title)
    for position, question in enumerate(questions, start=1):
        cursor = await connection.execute(
            UPSERT_QUESTION,
            {
                "source_id": source_id,
                "page_no": question.page_no,
                "unit_id": unit_id,
                "content": Jsonb(question.content.model_dump(mode="json")),
                "correct_option": question.correct_option,
                "content_hash": content_hash(question.content),
            },
        )
        row = await cursor.fetchone()
        assert row is not None
        await connection.execute(
            LINK_EXAM_QUESTION,
            {"exam_id": exam_id, "question_id": row[0], "position": position},
        )
    return len(questions)


async def publish_source_exams(connection: AsyncConnection, source_id: int) -> None:
    """Kaynağın en az bir yayındaki sorusu olan taslak testlerini yayına alır."""
    await connection.execute(PUBLISH_SOURCE_EXAMS, {"source_id": source_id})


async def _fetch_exam_id(
    connection: AsyncConnection, source_id: int, unit_id: int, title: str
) -> int:
    """Kaynağın aynı başlıklı testini bulur; yoksa açar."""
    params = {"source_id": source_id, "unit_id": unit_id, "title": title}
    row = await (await connection.execute(SELECT_EXAM, params)).fetchone()
    if row is None:
        row = await (await connection.execute(INSERT_EXAM, params)).fetchone()
    assert row is not None
    return int(row[0])
