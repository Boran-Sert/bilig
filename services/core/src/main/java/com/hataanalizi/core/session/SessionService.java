package com.hataanalizi.core.session;

import com.hataanalizi.core.auth.AuthUser;
import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.common.AppConstants;
import com.hataanalizi.core.common.ErrorCode;
import com.hataanalizi.core.exam.Exam;
import com.hataanalizi.core.exam.ExamRepository;
import com.hataanalizi.core.job.JobQueue;
import com.hataanalizi.core.job.JobType;
import com.hataanalizi.core.question.Question;
import com.hataanalizi.core.question.QuestionRepository;
import com.hataanalizi.core.session.dto.AnswerRequest;
import com.hataanalizi.core.session.dto.AnswerResponse;
import com.hataanalizi.core.session.dto.QuestionContent;
import com.hataanalizi.core.session.dto.SessionCompletionResponse;
import com.hataanalizi.core.session.dto.SessionQuestionResponse;
import com.hataanalizi.core.session.dto.SessionResponse;
import com.hataanalizi.core.session.dto.SessionReviewResponse;
import java.math.BigDecimal;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.ObjectMapper;

/** Öğrenci test oturumunu başlatır, sürdürür veya tamamlar. */
@Service
public class SessionService {

    private final ExamRepository examRepository;
    private final StudySessionRepository studySessionRepository;
    private final QuestionRepository questionRepository;
    private final StudentAnswerRepository studentAnswerRepository;
    private final ObjectMapper objectMapper;
    private final ScoringPolicy scoringPolicy;
    private final JobQueue jobQueue;

    /** Oturum ve test veritabanı bağımlılıklarını saklar. */
    public SessionService(
            ExamRepository examRepository,
            StudySessionRepository studySessionRepository,
            QuestionRepository questionRepository,
            StudentAnswerRepository studentAnswerRepository,
            ObjectMapper objectMapper,
            ScoringPolicy scoringPolicy,
            JobQueue jobQueue) {
        this.examRepository = examRepository;
        this.studySessionRepository = studySessionRepository;
        this.questionRepository = questionRepository;
        this.studentAnswerRepository = studentAnswerRepository;
        this.objectMapper = objectMapper;
        this.scoringPolicy = scoringPolicy;
        this.jobQueue = jobQueue;
    }

    /** Yayındaki test için öğrencinin açık oturumunu döndürür veya yenisini açar. */
    @Transactional
    public SessionResponse startOrResume(Long examId, AuthUser authUser) {
        Exam exam = requirePublishedExam(examId);
        StudySession session = findOrCreateSession(exam.getId(), authUser.id());
        List<ExamRepository.ExamQuestionPosition> positions =
                examRepository.findQuestionPositions(exam.getId(), AppConstants.QUESTION_STATUS_PUBLISHED);
        Map<Long, Question> questionsById = findQuestions(positions);
        Map<Long, String> selections = studySessionRepository.findAnswerSelectionsBySessionId(session.getId()).stream()
                .collect(Collectors.toMap(
                        StudySessionRepository.AnswerSelection::getQuestionId,
                        StudySessionRepository.AnswerSelection::getSelectedOption));
        List<SessionQuestionResponse> questions = positions.stream()
                .map(position -> toQuestionResponse(position, questionsById, selections))
                .toList();
        return new SessionResponse(session.getId(), session.getCurrentPosition(), questions);
    }

    /** Cevabı kaydeder, oturum ilerlemesini günceller ve kazanımları döndürür. */
    @Transactional
    public AnswerResponse submitAnswer(Long sessionId, Long questionId, AuthUser authUser, AnswerRequest request) {
        requireOwnedInProgressSession(sessionId, authUser.id());
        StudentAnswerRepository.QuestionContext question = studentAnswerRepository
                .findPublishedQuestionInSession(sessionId, questionId, AppConstants.QUESTION_STATUS_PUBLISHED)
                .orElseThrow(() -> new ApiException(ErrorCode.NOT_FOUND));
        String correctOption = question.getCorrectOption().trim();
        boolean correct = request.selectedOption().equals(correctOption);
        saveAnswer(sessionId, questionId, request, correct);
        studentAnswerRepository.moveToFirstUnansweredPosition(sessionId, AppConstants.QUESTION_STATUS_PUBLISHED);
        List<AnswerResponse.Outcome> outcomes =
                studentAnswerRepository.findLearningOutcomesByQuestionId(questionId).stream()
                        .map(outcome -> new AnswerResponse.Outcome(outcome.getCode(), outcome.getTitle()))
                        .toList();
        return new AnswerResponse(correct, correctOption, outcomes);
    }

    /** Oturumu tamamlar ve test puanıyla kazanım bazlı yanlışları döndürür. */
    @Transactional
    public SessionCompletionResponse completeSession(Long sessionId, AuthUser authUser) {
        requireOwnedInProgressSession(sessionId, authUser.id());
        SessionCompletionResponse result = summarize(sessionId);
        if (studySessionRepository.completeSession(
                        sessionId,
                        result.net(),
                        AppConstants.SESSION_STATUS_COMPLETED,
                        AppConstants.SESSION_STATUS_IN_PROGRESS)
                != 1) {
            throw new IllegalStateException("In-progress study session was not completed.");
        }
        return result;
    }

    /** Öğrencinin tamamlanmış oturumunun puanını ve kazanım özetini döndürür. */
    @Transactional(readOnly = true)
    public SessionCompletionResponse getResult(Long sessionId, AuthUser authUser) {
        StudySession session = studySessionRepository
                .findById(sessionId)
                .filter(candidate -> candidate.getUserId().equals(authUser.id()))
                .orElseThrow(() -> new ApiException(ErrorCode.SESSION_NOT_FOUND));
        if (!AppConstants.SESSION_STATUS_COMPLETED.equals(session.getStatus())) {
            throw new ApiException(ErrorCode.SESSION_NOT_COMPLETED);
        }
        return summarize(sessionId);
    }

    /** Tamamlanmış oturumdaki soruları doğru şık, öğrenci cevabı ve kazanımlarıyla tek seferde döndürür. */
    @Transactional(readOnly = true)
    public SessionReviewResponse getReview(Long sessionId, AuthUser authUser) {
        StudySession session = studySessionRepository
                .findById(sessionId)
                .filter(candidate -> candidate.getUserId().equals(authUser.id()))
                .orElseThrow(() -> new ApiException(ErrorCode.SESSION_NOT_FOUND));
        if (!AppConstants.SESSION_STATUS_COMPLETED.equals(session.getStatus())) {
            throw new ApiException(ErrorCode.SESSION_NOT_COMPLETED);
        }
        List<ExamRepository.ExamQuestionPosition> positions =
                examRepository.findQuestionPositions(session.getExamId(), AppConstants.QUESTION_STATUS_PUBLISHED);
        Map<Long, Question> questionsById = findQuestions(positions);
        Map<Long, StudentAnswerRepository.ReviewAnswer> answers =
                studentAnswerRepository
                        .findReviewAnswersBySessionId(sessionId, AppConstants.QUESTION_STATUS_PUBLISHED)
                        .stream()
                        .collect(Collectors.toMap(
                                StudentAnswerRepository.ReviewAnswer::getQuestionId, Function.identity()));
        Map<Long, List<AnswerResponse.Outcome>> outcomes =
                studentAnswerRepository
                        .findReviewOutcomesBySessionId(sessionId, AppConstants.QUESTION_STATUS_PUBLISHED)
                        .stream()
                        .collect(Collectors.groupingBy(
                                StudentAnswerRepository.ReviewOutcome::getQuestionId,
                                Collectors.mapping(
                                        outcome -> new AnswerResponse.Outcome(outcome.getCode(), outcome.getTitle()),
                                        Collectors.toList())));
        List<SessionReviewResponse.ReviewQuestion> questions = positions.stream()
                .map(position -> toReviewQuestion(position, questionsById, answers, outcomes))
                .toList();
        return new SessionReviewResponse(questions);
    }

    /** Sıralı soruyu doğru şık, öğrenci cevabı ve kazanımlarıyla inceleme nesnesine dönüştürür. */
    private SessionReviewResponse.ReviewQuestion toReviewQuestion(
            ExamRepository.ExamQuestionPosition position,
            Map<Long, Question> questionsById,
            Map<Long, StudentAnswerRepository.ReviewAnswer> answers,
            Map<Long, List<AnswerResponse.Outcome>> outcomes) {
        Question question = questionsById.get(position.getQuestionId());
        StudentAnswerRepository.ReviewAnswer answer = answers.get(position.getQuestionId());
        if (question == null || answer == null) {
            throw new IllegalStateException("Exam question is missing from the question table.");
        }
        return new SessionReviewResponse.ReviewQuestion(
                question.getId(),
                position.getPosition(),
                objectMapper.convertValue(question.getContent(), QuestionContent.class),
                answer.getSelectedOption(),
                answer.getCorrectOption().trim(),
                answer.getCorrect(),
                outcomes.getOrDefault(question.getId(), List.of()));
    }

    /** Oturumun cevap sayılarını, AYT netini ve kazanım bazlı yanlışlarını hesaplar. */
    private SessionCompletionResponse summarize(Long sessionId) {
        StudentAnswerRepository.SessionAnswerCounts counts =
                studentAnswerRepository.findSessionAnswerCounts(sessionId, AppConstants.QUESTION_STATUS_PUBLISHED);
        BigDecimal net = scoringPolicy.calculateNet(counts.getCorrectCount(), counts.getWrongCount());
        List<SessionCompletionResponse.SessionCompletionOutcome> outcomes =
                studentAnswerRepository
                        .findOutcomeWrongCountsBySessionId(sessionId, AppConstants.QUESTION_STATUS_PUBLISHED)
                        .stream()
                        .map(this::toOutcomeResponse)
                        .toList();
        return new SessionCompletionResponse(
                counts.getCorrectCount(), counts.getWrongCount(), counts.getBlankCount(), net, outcomes);
    }

    /** Oturumun varlığını ve sahibini doğrular, tamamlanmış oturumu reddeder. */
    private void requireOwnedInProgressSession(Long sessionId, Long userId) {
        StudentAnswerRepository.SessionContext session = studentAnswerRepository
                .lockSessionById(sessionId)
                .orElseThrow(() -> new ApiException(ErrorCode.SESSION_NOT_FOUND));
        if (!userId.equals(session.getUserId())) {
            throw new ApiException(ErrorCode.SESSION_NOT_FOUND);
        }
        if (AppConstants.SESSION_STATUS_COMPLETED.equals(session.getStatus())) {
            throw new ApiException(ErrorCode.SESSION_ALREADY_COMPLETED);
        }
    }

    /** Kazanım yanlış sayısını yanıt başarısızlık alanına dönüştürür. */
    private SessionCompletionResponse.SessionCompletionOutcome toOutcomeResponse(
            StudentAnswerRepository.OutcomeWrongCount outcome) {
        long wrong = outcome.getWrongCount();
        return new SessionCompletionResponse.SessionCompletionOutcome(
                outcome.getCode(), outcome.getTitle(), wrong, wrong > AppConstants.MAX_WRONG_PER_TEST);
    }

    /** Soruya ilk cevabı ekler, aynı soruya ikinci cevabı reddeder. */
    private void saveAnswer(Long sessionId, Long questionId, AnswerRequest request, boolean correct) {
        if (studentAnswerRepository.existsByStudySessionIdAndQuestionId(sessionId, questionId)) {
            throw new ApiException(ErrorCode.ANSWER_ALREADY_SUBMITTED);
        }
        StudentAnswer answer = new StudentAnswer();
        answer.setStudySessionId(sessionId);
        answer.setQuestionId(questionId);
        answer.setSelectedOption(request.selectedOption());
        answer.setCorrect(correct);
        answer.setDurationMs(request.durationMs());
        answer.setHintUsed(Boolean.TRUE.equals(request.hintUsed()));
        StudentAnswer savedAnswer = studentAnswerRepository.save(answer);
        if (!correct) {
            jobQueue.enqueue(
                    JobType.ANALYZE_ANSWER,
                    objectMapper.createObjectNode().put("studentAnswerId", savedAnswer.getId()));
        }
    }

    /** Yalnız yayındaki testi bulur. */
    private Exam requirePublishedExam(Long examId) {
        return examRepository
                .findByIdAndStatus(examId, AppConstants.EXAM_STATUS_PUBLISHED)
                .orElseThrow(() -> new ApiException(ErrorCode.EXAM_NOT_FOUND));
    }

    /** Açık oturumu bulur veya öğrenci için yeni oturum oluşturur. */
    private StudySession findOrCreateSession(Long examId, Long userId) {
        return studySessionRepository
                .findByUserIdAndExamIdAndStatus(userId, examId, AppConstants.SESSION_STATUS_IN_PROGRESS)
                .orElseGet(() -> createOrReadInProgressSession(examId, userId));
    }

    /** Oturumu atomik olarak oluşturur ve eşzamanlı isteğin oluşturduğu oturumu okur. */
    private StudySession createOrReadInProgressSession(Long examId, Long userId) {
        studySessionRepository.createInProgressSessionIfAbsent(userId, examId);
        return studySessionRepository
                .findByUserIdAndExamIdAndStatus(userId, examId, AppConstants.SESSION_STATUS_IN_PROGRESS)
                .orElseThrow(() -> new IllegalStateException("Active study session was not created."));
    }

    /** İstenen soru kimliklerinin veritabanı kayıtlarını bulur. */
    private Map<Long, Question> findQuestions(List<ExamRepository.ExamQuestionPosition> positions) {
        Collection<Long> questionIds = positions.stream()
                .map(ExamRepository.ExamQuestionPosition::getQuestionId)
                .toList();
        if (questionIds.isEmpty()) {
            return Map.of();
        }
        return questionRepository.findAllByQuestionIds(questionIds).stream()
                .collect(Collectors.toMap(Question::getId, Function.identity()));
    }

    /** Sıralı test sorusunu seçimiyle birlikte yanıt nesnesine dönüştürür. */
    private SessionQuestionResponse toQuestionResponse(
            ExamRepository.ExamQuestionPosition position,
            Map<Long, Question> questionsById,
            Map<Long, String> selections) {
        Question question = questionsById.get(position.getQuestionId());
        if (question == null) {
            throw new IllegalStateException("Exam question is missing from the question table.");
        }
        return new SessionQuestionResponse(
                question.getId(),
                position.getPosition(),
                objectMapper.convertValue(question.getContent(), QuestionContent.class),
                selections.get(question.getId()));
    }
}
