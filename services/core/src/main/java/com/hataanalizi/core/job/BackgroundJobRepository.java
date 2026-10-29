package com.hataanalizi.core.job;

import org.springframework.data.jpa.repository.JpaRepository;

/** Kuyruktaki iş kayıtlarına veritabanı üzerinden erişir. */
public interface BackgroundJobRepository extends JpaRepository<BackgroundJob, Long> {}
