package com.hataanalizi.core.session;

import com.hataanalizi.core.common.AppConstants;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/** Öğrencinin test oturumunu study_session tablosuyla eşler. */
@Entity
@Table(name = "study_session")
@Getter
@Setter
@NoArgsConstructor
public class StudySession {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "exam_id")
    private Long examId;

    @Column(nullable = false, columnDefinition = "text")
    private String status = AppConstants.SESSION_STATUS_IN_PROGRESS;

    @Column(name = "current_position", nullable = false)
    private short currentPosition = 1;

    @Column(name = "started_at", nullable = false, insertable = false, updatable = false)
    private OffsetDateTime startedAt;

    @Column(name = "completed_at")
    private OffsetDateTime completedAt;
}
