package com.hataanalizi.core.session;

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
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.annotations.UpdateTimestamp;
import org.hibernate.type.SqlTypes;

/** Öğrenci cevabını student_answer tablosuyla eşler. */
@Entity
@Table(name = "student_answer")
@Getter
@Setter
@NoArgsConstructor
public class StudentAnswer {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "study_session_id", nullable = false)
    private Long studySessionId;

    @Column(name = "question_id", nullable = false)
    private Long questionId;

    @JdbcTypeCode(SqlTypes.CHAR)
    @Column(name = "selected_option", nullable = false, columnDefinition = "char(1)")
    private String selectedOption;

    @Column(name = "is_correct", nullable = false)
    private boolean correct;

    @Column(name = "duration_ms")
    private Integer durationMs;

    @Column(name = "hint_used", nullable = false)
    private boolean hintUsed;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private OffsetDateTime updatedAt;
}
