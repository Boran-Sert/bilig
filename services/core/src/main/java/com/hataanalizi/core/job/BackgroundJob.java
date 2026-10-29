package com.hataanalizi.core.job;

import com.fasterxml.jackson.databind.JsonNode;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
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

/** İş kuyruğundaki bir işi veritabanındaki background_job satırıyla eşler. */
@Entity
@Table(name = "background_job")
@Getter
@Setter
@NoArgsConstructor
public class BackgroundJob {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Enumerated(EnumType.STRING)
    @Column(name = "job_type", nullable = false, columnDefinition = "text")
    private JobType jobType;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, columnDefinition = "text")
    private JobStatus status = JobStatus.QUEUED;

    @Column(name = "last_completed_step", columnDefinition = "text")
    private String lastCompletedStep;

    @Column(nullable = false)
    private short attempts;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(nullable = false, columnDefinition = "jsonb")
    private JsonNode payload;

    @Column(name = "last_error", columnDefinition = "text")
    private String lastError;

    @Column(name = "run_after", nullable = false, insertable = false, updatable = false)
    private OffsetDateTime runAfter;

    @Column(name = "created_at", nullable = false, insertable = false, updatable = false)
    private OffsetDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private OffsetDateTime updatedAt;
}
