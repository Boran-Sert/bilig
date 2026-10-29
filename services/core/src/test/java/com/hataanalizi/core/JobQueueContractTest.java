package com.hataanalizi.core;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.node.JsonNodeFactory;
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

/** İş kuyruğu sözleşmesini PostgreSQL uygulamasına karşı sınar. */
@ActiveProfiles("test")
@SpringBootTest
@Import(TestcontainersConfiguration.class)
@TestPropertySource(properties = "app.job-queue=postgres")
class JobQueueContractTest {

    private final JdbcTemplate jdbcTemplate;
    private final JobQueue jobQueue;
    private final TransactionTemplate transactionTemplate;

    /** Kuyruk, veritabanı ve transaction test bağımlılıklarını hazırlar. */
    @Autowired
    JobQueueContractTest(JdbcTemplate jdbcTemplate, JobQueue jobQueue, PlatformTransactionManager transactionManager) {
        this.jdbcTemplate = jdbcTemplate;
        this.jobQueue = jobQueue;
        this.transactionTemplate = new TransactionTemplate(transactionManager);
    }

    /** Kuyruğa alınan işin kimliğini, durumunu ve deneme sayısını doğrular. */
    @Test
    @Transactional
    void enqueueReturnsIdAndPersistsQueuedJob() {
        long jobId = jobQueue.enqueue(
                JobType.INGEST_SOURCE, JsonNodeFactory.instance.objectNode().put("sourceId", 12));
        String status =
                jdbcTemplate.queryForObject("SELECT status FROM background_job WHERE id = ?", String.class, jobId);
        Short attempts =
                jdbcTemplate.queryForObject("SELECT attempts FROM background_job WHERE id = ?", Short.class, jobId);

        assertTrue(jobId > 0);
        assertEquals(JobStatus.QUEUED.name(), status);
        assertEquals((short) 0, attempts);
    }

    /** Çağıranın transaction'ı geri alındığında iş satırının kalmadığını doğrular. */
    @Test
    void enqueueIsRolledBackWithCallerTransaction() {
        Long jobId = transactionTemplate.execute(status -> {
            long enqueuedJobId = jobQueue.enqueue(
                    JobType.INGEST_SOURCE, JsonNodeFactory.instance.objectNode().put("sourceId", 12));
            status.setRollbackOnly();
            return enqueuedJobId;
        });

        assertNotNull(jobId);
        Long remainingJobs =
                jdbcTemplate.queryForObject("SELECT count(*) FROM background_job WHERE id = ?", Long.class, jobId);
        assertEquals(0L, remainingJobs);
    }
}
