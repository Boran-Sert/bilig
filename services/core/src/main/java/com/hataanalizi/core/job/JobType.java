package com.hataanalizi.core.job;

/** background_job.job_type kolonunun kabul ettiği iş türlerini tanımlar. */
public enum JobType {
    INGEST_SOURCE,
    BUILD_PROGRAM,
    EXTRACT_ENTITIES,
    MATCH_OUTCOMES,
    EMBED,
    GENERATE_QUESTIONS,
    ANALYZE_ANSWER
}
