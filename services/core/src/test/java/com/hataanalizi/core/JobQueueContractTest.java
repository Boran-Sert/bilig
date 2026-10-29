package com.hataanalizi.core;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.hataanalizi.core.job.JobQueue;
import com.hataanalizi.core.job.JobStatus;
import com.hataanalizi.core.job.JobType;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.TestPropertySource;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;

/** İş kuyruğu sözleşmesini PostgreSQL uygulamasına karşı sınar. */
@ActiveProfiles("test")
@SpringBootTest
@Import(TestcontainersConfiguration.class)
@TestPropertySource(properties = "app.job-queue=postgres")
class JobQueueContractTest {

    private final JdbcTemplate jdbcTemplate;
    private final JobQueue jobQueue;
    private final TransactionTemplate transactionTemplate;
    private final ObjectMapper objectMapper;

    /** Kuyruk, veritabanı ve transaction test bağımlılıklarını hazırlar. */
    @Autowired
    JobQueueContractTest(
            JdbcTemplate jdbcTemplate,
            JobQueue jobQueue,
            PlatformTransactionManager transactionManager,
            ObjectMapper objectMapper) {
        this.jdbcTemplate = jdbcTemplate;
        this.jobQueue = jobQueue;
        this.transactionTemplate = new TransactionTemplate(transactionManager);
        this.objectMapper = objectMapper;
    }

    /** Kuyruğa alınan işin kimliğini, durumunu ve deneme sayısını doğrular. */
    @Test
    @Transactional
    void enqueueReturnsIdAndPersistsQueuedJob() {
        JsonNode payload = objectMapper.createObjectNode().put("sourceId", 12);

        long jobId = jobQueue.enqueue(JobType.INGEST_SOURCE, payload);

        String status =
                jdbcTemplate.queryForObject("SELECT status FROM background_job WHERE id = ?", String.class, jobId);
        Short attempts =
                jdbcTemplate.queryForObject("SELECT attempts FROM background_job WHERE id = ?", Short.class, jobId);
        String sourceId = jdbcTemplate.queryForObject(
                "SELECT payload->>'sourceId' FROM background_job WHERE id = ?", String.class, jobId);
        String payloadType = jdbcTemplate.queryForObject(
                "SELECT pg_typeof(payload)::text FROM background_job WHERE id = ?", String.class, jobId);

        assertTrue(jobId > 0);
        assertEquals(JobStatus.QUEUED.name(), status);
        assertEquals((short) 0, attempts);
        assertEquals("12", sourceId);
        assertEquals("jsonb", payloadType);
    }

    /** Çağıranın transaction'ı geri alındığında iş satırının kalmadığını doğrular. */
    @Test
    void enqueueIsRolledBackWithCallerTransaction() {
        Long jobId = transactionTemplate.execute(status -> {
            JsonNode payload = objectMapper.createObjectNode().put("sourceId", 12);

            long enqueuedJobId = jobQueue.enqueue(JobType.INGEST_SOURCE, payload);
            status.setRollbackOnly();
            return enqueuedJobId;
        });

        assertNotNull(jobId);
        Long remainingJobs =
                jdbcTemplate.queryForObject("SELECT count(*) FROM background_job WHERE id = ?", Long.class, jobId);
        assertEquals(0L, remainingJobs);
    }
}
