package com.hataanalizi.core.job;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;
import tools.jackson.databind.JsonNode;

/** İşleri PostgreSQL background_job tablosuna kaydeder. */
@Component
@ConditionalOnProperty(name = "app.job-queue", havingValue = "postgres")
public class PostgresJobQueue implements JobQueue {

    private final BackgroundJobRepository backgroundJobRepository;

    /** İş kuyruğu kayıt deposunu saklar. */
    public PostgresJobQueue(BackgroundJobRepository backgroundJobRepository) {
        this.backgroundJobRepository = backgroundJobRepository;
    }

    /** İşi çağıranın transaction'ına katılarak kuyruğa ekler. */
    @Override
    public long enqueue(JobType type, JsonNode payload) {
        BackgroundJob backgroundJob = new BackgroundJob();
        backgroundJob.setJobType(type);
        backgroundJob.setPayload(payload);
        return backgroundJobRepository.save(backgroundJob).getId();
    }
}
