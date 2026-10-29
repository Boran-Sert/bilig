package com.hataanalizi.core.auth;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

/** Kurum kayıtlarına veritabanı üzerinden erişir. */
public interface TenantRepository extends JpaRepository<Tenant, Long> {

    /** Adıyla kurum kaydını bulur. */
    Optional<Tenant> findByName(String name);
}
