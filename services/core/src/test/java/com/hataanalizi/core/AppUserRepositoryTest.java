package com.hataanalizi.core;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.hataanalizi.core.auth.AppUser;
import com.hataanalizi.core.auth.AppUserRepository;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.annotation.Import;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

/** Kullanıcı migration'ını ve repository davranışını doğrular. */
@ActiveProfiles("test")
@SpringBootTest
@Import(TestcontainersConfiguration.class)
@Transactional
class AppUserRepositoryTest {

    private final AppUserRepository appUserRepository;
    private final JdbcTemplate jdbcTemplate;

    /** Test bağımlılıklarını hazırlar. */
    @Autowired
    AppUserRepositoryTest(AppUserRepository appUserRepository, JdbcTemplate jdbcTemplate) {
        this.appUserRepository = appUserRepository;
        this.jdbcTemplate = jdbcTemplate;
    }

    /** Varsayılan kurum kaydının oluşturulduğunu doğrular. */
    @Test
    void createsDefaultTenant() {
        Integer tenantCount =
                jdbcTemplate.queryForObject("SELECT count(*) FROM tenant WHERE name = ?", Integer.class, "Bilig");

        assertEquals(1, tenantCount);
    }

    /** Aynı e-posta adresiyle ikinci kullanıcı kaydedilmesini engeller. */
    @Test
    void rejectsDuplicateEmailAndFindsUserByEmail() {
        String email = UUID.randomUUID() + "@example.test";
        AppUser firstUser = createUser(email);
        AppUser savedUser = appUserRepository.saveAndFlush(firstUser);

        assertTrue(appUserRepository.findByEmail(email).isPresent());
        assertThrows(DataIntegrityViolationException.class, () -> appUserRepository.saveAndFlush(createUser(email)));
        assertNotNull(savedUser.getId());
    }

    /** Zorunlu alanları doldurulmuş kullanıcı oluşturur. */
    private AppUser createUser(String email) {
        Long tenantId = jdbcTemplate.queryForObject("SELECT id FROM tenant LIMIT 1", Long.class);
        AppUser user = new AppUser();
        user.setTenantId(tenantId);
        user.setEmail(email);
        user.setDisplayName("Test user");
        user.setRole("STUDENT");
        user.setExplainStyle("SIMPLE");
        return user;
    }
}
