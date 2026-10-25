package com.hataanalizi.core.auth;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

/** Kullanıcı kayıtlarına veritabanı üzerinden erişir. */
public interface AppUserRepository extends JpaRepository<AppUser, Long> {

    /** E-posta adresine göre kullanıcıyı bulur. */
    Optional<AppUser> findByEmail(String email);
}
