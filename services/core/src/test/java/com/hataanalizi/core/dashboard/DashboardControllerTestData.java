package com.hataanalizi.core.dashboard;

import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;

/** Öğrenci paneli entegrasyon testleri için PostgreSQL verisi oluşturur. */
class DashboardControllerTestData {

    private static final OffsetDateTime BASE_TIMESTAMP = OffsetDateTime.parse("2026-01-01T00:00:00Z");

    private final JdbcTemplate jdbcTemplate;

    /** Test veritabanı bağlantısını saklar. */
    DashboardControllerTestData(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /** Eşik, sıralama ve sahiplik senaryolarının kayıtlarını hazırlar. */
    DashboardFixture createDashboardFixture() {
        Long userId = insertUser();
        Long romanUnitId = insertCurriculumUnit("Roman");
        Long poetryUnitId = insertCurriculumUnit("Şiir");
        Long latestExamId = insertExam("Roman · Kazanım Testi 3");
        List<Long> questionIds = insertQuestions(romanUnitId, latestExamId, 7);
        Long poetryQuestionId = insertQuestions(poetryUnitId, latestExamId, 1).getFirst();
        Map<String, Long> outcomeIds = insertOutcomes(romanUnitId);
        mapQuestionToOutcome(questionIds, outcomeIds);
        insertAcrossSessionWrongAnswers(userId, latestExamId, questionIds);

        Long latestSessionId =
                insertSession(userId, latestExamId, "COMPLETED", new BigDecimal("0.25"), BASE_TIMESTAMP.plusDays(2));
        insertLatestSessionAnswers(latestSessionId, questionIds, poetryQuestionId);
        Long earlierFailureExamId = insertExam("Roman · Kazanım Testi 2");
        Long laterIdEarlierSessionId =
                insertSession(userId, earlierFailureExamId, "COMPLETED", BigDecimal.ZERO, BASE_TIMESTAMP.plusDays(1));
        insertAnswers(laterIdEarlierSessionId, questionIds.subList(0, 3));
        markQuestionForReview(questionIds.getFirst());

        Long activeExamId = insertExam("Şiir · Kazanım Testi 1");
        insertQuestions(romanUnitId, activeExamId, 2);
        insertSession(userId, activeExamId, "IN_PROGRESS", null, BASE_TIMESTAMP.plusDays(3));
        return new DashboardFixture(userId, latestExamId, activeExamId, questionIds.getFirst());
    }

    /** İlk sorusu incelemede olan aktif testi ikinci soruda bekleyen oturumla hazırlar. */
    Long createActiveSessionWithReviewQuestion() {
        Long userId = insertUser();
        Long unitId = insertCurriculumUnit("Şiir");
        Long examId = insertExam("Şiir · Kazanım Testi 2");
        List<Long> questionIds = insertQuestions(unitId, examId, 3);
        markQuestionForReview(questionIds.getFirst());
        Long sessionId = insertSession(userId, examId, "IN_PROGRESS", null, BASE_TIMESTAMP);
        insertAnswer(sessionId, questionIds.get(1), true, null);
        jdbcTemplate.update("UPDATE study_session SET current_position = 3 WHERE id = ?", sessionId);
        return userId;
    }

    /** Yayındaki sorularla en son başarısız testi ve yalnızca toplam eşiğini aşan kazanımı hazırlar. */
    Long createFailedOutcomeOrderingFixture() {
        Long userId = insertUser();
        Long unitId = insertCurriculumUnit("Roman");
        Long latestExamId = insertExam("Roman · Kazanım Testi 3");
        Long earlierExamId = insertExam("Roman · Kazanım Testi 2");
        List<Long> questionIds = insertQuestions(unitId, latestExamId, 3);
        Map<String, Long> outcomeIds = insertOutcomes(unitId);
        questionIds.forEach(questionId -> insertOutcomeMapping(questionId, outcomeIds.get("A.2.7")));
        insertOutcomeMapping(questionIds.get(0), outcomeIds.get("A.2.8"));
        insertOutcomeMapping(questionIds.get(1), outcomeIds.get("A.2.8"));

        Long latestSessionId =
                insertSession(userId, latestExamId, "COMPLETED", BigDecimal.ZERO, BASE_TIMESTAMP.plusDays(2));
        insertAnswers(latestSessionId, questionIds);
        Long laterIdEarlierSessionId =
                insertSession(userId, earlierExamId, "COMPLETED", BigDecimal.ZERO, BASE_TIMESTAMP.plusDays(1));
        insertAnswers(laterIdEarlierSessionId, questionIds);
        Long oldestSessionId = insertSession(userId, earlierExamId, "COMPLETED", BigDecimal.ZERO, BASE_TIMESTAMP);
        insertAnswers(oldestSessionId, questionIds.subList(0, 2));
        return userId;
    }

    /** Başka öğrencinin cevabını ekleyerek panel sahipliği sınamasını hazırlar. */
    void insertOtherStudentAnswer(DashboardFixture fixture) {
        Long otherUserId = insertUser();
        Long otherSessionId =
                insertSession(otherUserId, fixture.examId(), "IN_PROGRESS", null, BASE_TIMESTAMP.plusDays(4));
        insertAnswer(otherSessionId, fixture.questionId(), true, null);
    }

    /** Soruları test başına birer yanlışla toplam eşiğine kadar doldurur. */
    private void insertAcrossSessionWrongAnswers(Long userId, Long examId, List<Long> questionIds) {
        for (int attempt = 0; attempt < 5; attempt++) {
            OffsetDateTime startedAt = BASE_TIMESTAMP.plusMinutes(attempt * 2L);
            Long sessionId = insertSession(userId, examId, "COMPLETED", BigDecimal.ZERO, startedAt);
            insertAnswer(sessionId, questionIds.get(0), false, null);
            insertAnswer(sessionId, questionIds.get(3), false, null);
        }
    }

    /** Ana oturumun cevaplarını ve iki sınır kazanımını kaydeder. */
    private void insertLatestSessionAnswers(Long sessionId, List<Long> questionIds, Long poetryQuestionId) {
        insertAnswer(sessionId, questionIds.get(0), false, "READING");
        insertAnswer(sessionId, questionIds.get(1), false, "KNOWLEDGE");
        insertAnswer(sessionId, questionIds.get(2), false, null);
        insertAnswer(sessionId, questionIds.get(3), true, null);
        insertAnswer(sessionId, questionIds.get(4), false, null);
        insertAnswer(sessionId, questionIds.get(5), false, null);
        insertAnswer(sessionId, questionIds.get(6), false, null);
        insertAnswer(sessionId, poetryQuestionId, true, null);
    }

    /** Test sorularını kazanımlara bağlar. */
    private void mapQuestionToOutcome(List<Long> questionIds, Map<String, Long> outcomeIds) {
        insertOutcomeMapping(questionIds.get(4), outcomeIds.get("A.2.4"));
        insertOutcomeMapping(questionIds.get(5), outcomeIds.get("A.2.4"));
        insertOutcomeMapping(questionIds.get(6), outcomeIds.get("A.2.4"));
        insertOutcomeMapping(questionIds.get(4), outcomeIds.get("A.2.5"));
        insertOutcomeMapping(questionIds.get(5), outcomeIds.get("A.2.5"));
        insertOutcomeMapping(questionIds.get(0), outcomeIds.get("A.2.7"));
        insertOutcomeMapping(questionIds.get(1), outcomeIds.get("A.2.7"));
        insertOutcomeMapping(questionIds.get(2), outcomeIds.get("A.2.7"));
        insertOutcomeMapping(questionIds.get(0), outcomeIds.get("A.2.8"));
        insertOutcomeMapping(questionIds.get(3), outcomeIds.get("A.2.9"));
    }

    /** Belirtilen ünite ve test için sıralı sorular oluşturur. */
    private List<Long> insertQuestions(Long unitId, Long examId, int count) {
        List<Long> questionIds = new ArrayList<>();
        Integer firstPosition = jdbcTemplate.queryForObject(
                "SELECT COALESCE(MAX(position), 0) + 1 FROM exam_question WHERE exam_id = ?", Integer.class, examId);
        for (int index = 0; index < count; index++) {
            String content = """
                    {"stem":[{"type":"paragraph","md":"Question"}],
                     "options":[{"label":"A","blocks":[{"type":"paragraph","md":"Option"}]}]}
                    """;
            String contentHash = UUID.randomUUID().toString().replace("-", "")
                    + UUID.randomUUID().toString().replace("-", "");
            Long questionId = jdbcTemplate.queryForObject("""
                    INSERT INTO question (
                        curriculum_unit_id, origin, content, correct_option, content_hash, status
                    ) VALUES (?, 'SOURCE', ?::jsonb, 'A', ?, 'PUBLISHED')
                    RETURNING id
                    """, Long.class, unitId, content, contentHash);
            questionIds.add(questionId);
            jdbcTemplate.update(
                    "INSERT INTO exam_question (exam_id, question_id, position) VALUES (?, ?, ?)",
                    examId,
                    questionId,
                    firstPosition + index);
        }
        return questionIds;
    }

    /** Panel senaryolarında kullanılacak kazanımları oluşturur. */
    private Map<String, Long> insertOutcomes(Long unitId) {
        String identifier = UUID.randomUUID().toString();
        Long groupId = jdbcTemplate.queryForObject("""
                INSERT INTO learning_outcome_group (curriculum_id, code, name)
                VALUES ((SELECT curriculum_id FROM curriculum_unit WHERE id = ?), ?, ?)
                RETURNING id
                """, Long.class, unitId, identifier, identifier);
        Map<String, Long> outcomeIds = new HashMap<>();
        for (String code : List.of("A.2.4", "A.2.5", "A.2.7", "A.2.8", "A.2.9")) {
            Long outcomeId =
                    jdbcTemplate.queryForObject("""
                    INSERT INTO learning_outcome (learning_outcome_group_id, code, title, search_text)
                    VALUES (?, ?, ?, ?)
                    RETURNING id
                    """, Long.class, groupId, code, "Outcome " + code, "Outcome " + code);
            outcomeIds.put(code, outcomeId);
        }
        return outcomeIds;
    }

    /** Soruyu belirtilen kazanıma bağlar. */
    private void insertOutcomeMapping(Long questionId, Long outcomeId) {
        jdbcTemplate.update("""
                INSERT INTO question_outcome (question_id, learning_outcome_id, mapped_by)
                VALUES (?, ?, 'SOURCE')
                """, questionId, outcomeId);
    }

    /** Tamamlanan test oturumuna verilen cevapları kaydeder. */
    private void insertAnswers(Long sessionId, List<Long> questionIds) {
        questionIds.forEach(questionId -> insertAnswer(sessionId, questionId, false, null));
    }

    /** Yeni bir öğrenci hesabı oluşturur. */
    Long insertUser() {
        String identifier = UUID.randomUUID().toString();
        return jdbcTemplate.queryForObject("""
                INSERT INTO app_user (tenant_id, email, display_name, role)
                SELECT id, ?, ?, 'STUDENT' FROM tenant WHERE name = 'Bilig'
                RETURNING id
                """, Long.class, identifier + "@example.test", identifier);
    }

    /** Testte kullanılacak ders programı ve ünitesini oluşturur. */
    private Long insertCurriculumUnit(String title) {
        String identifier = UUID.randomUUID().toString();
        Long subjectId = jdbcTemplate.queryForObject(
                "INSERT INTO subject (code, name) VALUES (?, ?) RETURNING id", Long.class, identifier, identifier);
        Long curriculumId = jdbcTemplate.queryForObject(
                "INSERT INTO curriculum (subject_id, name, model, year) VALUES (?, ?, ?, ?) RETURNING id",
                Long.class,
                subjectId,
                identifier,
                "LEGACY",
                2018);
        return jdbcTemplate.queryForObject("""
                INSERT INTO curriculum_unit (curriculum_id, grade, unit_no, title) VALUES (?, ?, ?, ?)
                RETURNING id
                """, Long.class, curriculumId, 12, 1, title);
    }

    /** Yayındaki test kaydını oluşturur. */
    private Long insertExam(String title) {
        return jdbcTemplate.queryForObject(
                "INSERT INTO exam (title, status) VALUES (?, 'PUBLISHED') RETURNING id", Long.class, title);
    }

    /** Oturumu zaman bilgileriyle oluşturur. */
    private Long insertSession(Long userId, Long examId, String status, BigDecimal net, OffsetDateTime startedAt) {
        OffsetDateTime completedAt = "COMPLETED".equals(status) ? startedAt.plusMinutes(5) : null;
        return jdbcTemplate.queryForObject("""
                INSERT INTO study_session (user_id, exam_id, status, net, started_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?::timestamptz)
                RETURNING id
                """, Long.class, userId, examId, status, net, startedAt, completedAt);
    }

    /** Öğrencinin doğru veya yanlış cevabını ve varsa hata türünü kaydeder. */
    private void insertAnswer(Long sessionId, Long questionId, boolean correct, String errorType) {
        jdbcTemplate.update("""
                INSERT INTO student_answer (study_session_id, question_id, selected_option, is_correct, error_type)
                VALUES (?, ?, 'A', ?, ?)
                """, sessionId, questionId, correct, errorType);
    }

    /** Yayındaki soruyu sonradan incelemeye alır. */
    private void markQuestionForReview(Long questionId) {
        jdbcTemplate.update("UPDATE question SET status = 'REVIEW' WHERE id = ?", questionId);
    }

    /** Panel testinin kullanıcı ve aktif test kimliklerini taşır. */
    record DashboardFixture(Long userId, Long examId, Long activeExamId, Long questionId) {}
}
