"""İpucu, anlatım ve sohbetin okuduğu sorgular.

Öğrenciye sadece yayındaki (PUBLISHED) soru ve paragraf gösterilir. Sorunun kazanımları sırasız
gelir; kodla sıralama sadece çıktının sabit olması içindir. Sohbetin mesajları yazılış sırasıyla
okunur. Bu servis sohbet tablolarına yazmaz; mesajları Java kaydeder.
"""

from psycopg import AsyncConnection

from app.schemas.question import QuestionContent
from app.schemas.tutor import ChatTurn, ExplainStyle, OutcomeInfo, SourceBlock, TutorQuestion

SELECT_PUBLISHED_QUESTION = """
SELECT content, correct_option FROM question WHERE id = %(id)s AND status = 'PUBLISHED'
"""

SELECT_QUESTION_OUTCOMES = """
SELECT learning_outcome.id, learning_outcome.code, learning_outcome.title,
    learning_outcome.meb_explanation
FROM question_outcome
JOIN learning_outcome ON learning_outcome.id = question_outcome.learning_outcome_id
WHERE question_outcome.question_id = %(id)s
ORDER BY learning_outcome.code
"""

SELECT_OUTCOMES_BY_CODE = """
SELECT id, code, title, meb_explanation FROM learning_outcome WHERE code = %(code)s ORDER BY id
"""

SELECT_EXPLAIN_STYLE = """
SELECT explain_style FROM app_user WHERE id = %(id)s
"""

SELECT_CONVERSATION = """
SELECT question_id FROM tutor_conversation WHERE id = %(id)s AND user_id = %(user_id)s
"""

SELECT_MESSAGES = """
SELECT role, content FROM tutor_message WHERE tutor_conversation_id = %(id)s ORDER BY id
"""

SELECT_SOURCE_BLOCKS = """
SELECT content_block.id, source_document.title, source_page.page_no, content_block.title_path,
    content_block.markdown
FROM content_block
JOIN source_page ON source_page.id = content_block.source_page_id
JOIN source_document ON source_document.id = source_page.source_document_id
WHERE content_block.id = ANY(%(ids)s)
    AND content_block.status = 'PUBLISHED'
    AND content_block.block_type = ANY(%(block_types)s)
"""


async def fetch_question(connection: AsyncConnection, question_id: int) -> TutorQuestion | None:
    """Yayındaki soruyu doğru şıkkı ve kazanımlarıyla döner; yoksa boş döner."""
    cursor = await connection.execute(SELECT_PUBLISHED_QUESTION, {"id": question_id})
    row = await cursor.fetchone()
    if row is None:
        return None
    cursor = await connection.execute(SELECT_QUESTION_OUTCOMES, {"id": question_id})
    outcomes = [
        OutcomeInfo(id=item[0], code=item[1], title=item[2], meb_explanation=item[3])
        for item in await cursor.fetchall()
    ]
    return TutorQuestion(
        content=QuestionContent.model_validate(row[0]),
        correct_option=row[1].strip(),
        outcomes=outcomes,
    )


async def fetch_outcomes_by_code(connection: AsyncConnection, code: str) -> list[OutcomeInfo]:
    """Koduyla eşleşen kazanımları döner; kod birden çok programda geçebilir."""
    cursor = await connection.execute(SELECT_OUTCOMES_BY_CODE, {"code": code})
    return [
        OutcomeInfo(id=row[0], code=row[1], title=row[2], meb_explanation=row[3])
        for row in await cursor.fetchall()
    ]


async def fetch_explain_style(connection: AsyncConnection, user_id: int) -> ExplainStyle | None:
    """Öğrencinin anlatım tarzını döner; öğrenci yoksa boş döner."""
    cursor = await connection.execute(SELECT_EXPLAIN_STYLE, {"id": user_id})
    row = await cursor.fetchone()
    return None if row is None else ExplainStyle(row[0])


async def fetch_conversation(
    connection: AsyncConnection, conversation_id: int, user_id: int
) -> tuple[int | None, list[ChatTurn]] | None:
    """Öğrencinin sohbetinin sorusunu ve mesajlarını döner; sohbet onun değilse boş döner."""
    values = {"id": conversation_id, "user_id": user_id}
    cursor = await connection.execute(SELECT_CONVERSATION, values)
    row = await cursor.fetchone()
    if row is None:
        return None
    cursor = await connection.execute(SELECT_MESSAGES, {"id": conversation_id})
    turns = [ChatTurn(role=item[0], content=item[1]) for item in await cursor.fetchall()]
    return row[0], turns


async def fetch_source_blocks(
    connection: AsyncConnection, block_ids: list[int], block_types: tuple[str, ...]
) -> list[SourceBlock]:
    """Yayındaki ve türü uyan paragrafları verilen kimlik sırasıyla döner."""
    values = {"ids": block_ids, "block_types": list(block_types)}
    cursor = await connection.execute(SELECT_SOURCE_BLOCKS, values)
    found = {
        row[0]: SourceBlock(
            block_id=row[0],
            source_title=row[1],
            page_no=row[2],
            title_path=row[3],
            markdown=row[4],
        )
        for row in await cursor.fetchall()
    }
    return [found[block_id] for block_id in block_ids if block_id in found]
