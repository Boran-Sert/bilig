package com.hataanalizi.core.session;

import com.hataanalizi.core.auth.AuthUser;
import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.common.AppConstants;
import com.hataanalizi.core.common.ErrorCode;
import com.hataanalizi.core.exam.Exam;
import com.hataanalizi.core.exam.ExamRepository;
import com.hataanalizi.core.question.Question;
import com.hataanalizi.core.question.QuestionRepository;
import com.hataanalizi.core.session.dto.QuestionContent;
import com.hataanalizi.core.session.dto.SessionQuestionResponse;
import com.hataanalizi.core.session.dto.SessionResponse;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.ObjectMapper;

/** Öğrenci test oturumunu başlatır ya da kaldığı yerden sürdürür. */
@Service
public class SessionService {

    private final ExamRepository examRepository;
    private final StudySessionRepository studySessionRepository;
    private final QuestionRepository questionRepository;
    private final ObjectMapper objectMapper;

    /** Oturum ve test veritabanı bağımlılıklarını saklar. */
    public SessionService(
            ExamRepository examRepository,
            StudySessionRepository studySessionRepository,
            QuestionRepository questionRepository,
            ObjectMapper objectMapper) {
        this.examRepository = examRepository;
        this.studySessionRepository = studySessionRepository;
        this.questionRepository = questionRepository;
        this.objectMapper = objectMapper;
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
