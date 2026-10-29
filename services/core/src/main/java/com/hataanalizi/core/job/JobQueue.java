package com.hataanalizi.core.job;

import com.fasterxml.jackson.databind.JsonNode;

/** İş kodunun kuyruk altyapısından bağımsız kullanacağı sözleşmeyi tanımlar. */
public interface JobQueue {

    /** Yeni işi çalışanların alması için kuyruğa ekler ve iş numarasını döndürür. */
    long enqueue(JobType type, JsonNode payload);
}
