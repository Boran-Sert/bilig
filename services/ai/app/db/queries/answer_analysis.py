"""Yanlış öğrenci cevaplarının hata türü analizini okur ve kaydeder."""

from psycopg import AsyncConnection
from pydantic import BaseModel

from app.schemas.answer_analysis import ErrorTypeAnalysis
from app.schemas.question import OptionLabel, QuestionContent

FETCH_ANSWER_FOR_ANALYSIS = """
SELECT question.content, student_answer.selected_option, question.correct_option,
    study_session.user_id
FROM student_answer
JOIN question ON question.id = student_answer.question_id
JOIN study_session ON study_session.id = student_answer.study_session_id
WHERE student_answer.id = %(student_answer_id)s
    AND student_answer.is_correct = false
    AND NOT EXISTS (
        SELECT 1 FROM answer_analysis
        WHERE answer_analysis.student_answer_id = student_answer.id
    )
"""

UPDATE_STUDENT_ANSWER = """
UPDATE student_answer
SET error_type = %(error_type)s, updated_at = now()
WHERE id = %(student_answer_id)s AND is_correct = false
"""

UPSERT_ANSWER_ANALYSIS = """
INSERT INTO answer_analysis (student_answer_id, error_type, needs_review)
VALUES (%(student_answer_id)s, %(error_type)s, %(needs_review)s)
ON CONFLICT (student_answer_id) DO UPDATE
SET error_type = EXCLUDED.error_type, needs_review = EXCLUDED.needs_review
"""


class AnswerForAnalysis(BaseModel):
    """Sınıflandırma için gereken, kişisel veri içermeyen soru ve yanıtı taşır."""

    content: QuestionContent
    selected_option: OptionLabel
    correct_option: OptionLabel
    user_id: int


async def fetch_answer_for_analysis(
    connection: AsyncConnection, student_answer_id: int
) -> AnswerForAnalysis | None:
    """Analizi tamamlanmamış yanlış cevabın soru bağlamını döner."""
    cursor = await connection.execute(
        FETCH_ANSWER_FOR_ANALYSIS, {"student_answer_id": student_answer_id}
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return AnswerForAnalysis(
        content=QuestionContent.model_validate(row[0]),
        selected_option=row[1],
        correct_option=row[2].strip(),
        user_id=row[3],
    )


async def save_answer_analysis(
    connection: AsyncConnection, student_answer_id: int, analysis: ErrorTypeAnalysis
) -> None:
    """Analizi answer_analysis tablosuna yazar ve dashboard alanını eşzamanlı günceller."""
    values = {
        "student_answer_id": student_answer_id,
        "error_type": analysis.error_type.value,
        "needs_review": analysis.needs_review,
    }
    cursor = await connection.execute(UPDATE_STUDENT_ANSWER, values)
    if cursor.rowcount != 1:
        raise LookupError(f"Wrong student answer {student_answer_id} was not found")
    await connection.execute(UPSERT_ANSWER_ANALYSIS, values)
