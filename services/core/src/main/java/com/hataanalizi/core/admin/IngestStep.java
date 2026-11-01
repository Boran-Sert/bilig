package com.hataanalizi.core.admin;

/** Hazırlık hattının adımlarını Python servisiyle aynı sırada tanımlar. */
public enum IngestStep {
    REGISTERED,
    EXTRACT,
    VALIDATE,
    ENTITIES,
    OUTCOMES,
    INDEX
}
