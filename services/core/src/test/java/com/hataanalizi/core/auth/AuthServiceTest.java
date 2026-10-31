package com.hataanalizi.core.auth;

import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.hataanalizi.core.auth.dto.RegisterRequest;
import com.hataanalizi.core.common.AppConstants;
import java.util.Optional;
import org.hibernate.exception.ConstraintViolationException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.crypto.password.PasswordEncoder;

/** Kayıt işleminin yalnız e-posta benzersizlik hatasını eşlediğini doğrular. */
class AuthServiceTest {

    private AppUserRepository appUserRepository;
    private TenantRepository tenantRepository;
    private AuthService authService;

    /** Kayıt servisinin mock bağımlılıklarını hazırlar. */
    @BeforeEach
    void setUp() throws Exception {
        appUserRepository = mock(AppUserRepository.class);
        tenantRepository = mock(TenantRepository.class);
        AuthenticationConfiguration authenticationConfiguration = mock(AuthenticationConfiguration.class);
        PasswordEncoder passwordEncoder = mock(PasswordEncoder.class);
        Tenant tenant = mockTenant();
        when(tenantRepository.findByName(AppConstants.DEFAULT_TENANT_NAME)).thenReturn(Optional.of(tenant));
        when(passwordEncoder.encode("Valid-password-123")).thenReturn("encoded-password");
        authService =
                new AuthService(appUserRepository, tenantRepository, authenticationConfiguration, passwordEncoder);
    }

    /** E-posta dışındaki benzersizlik kısıtı hatasını aynen yeniden fırlatır. */
    @Test
    void rethrowsNonEmailConstraintViolation() {
        ConstraintViolationException constraintViolation =
                new ConstraintViolationException("constraint violation", null, "app_user_role_check");
        DataIntegrityViolationException databaseException =
                new DataIntegrityViolationException("constraint violation", constraintViolation);
        doThrow(databaseException).when(appUserRepository).saveAndFlush(any(AppUser.class));

        assertThatThrownBy(() -> authService.register(validRequest())).isSameAs(databaseException);
    }

    /** Tenant repository için test kurum kaydı oluşturur. */
    private Tenant mockTenant() {
        Tenant tenant = mock(Tenant.class);
        when(tenant.getId()).thenReturn(1L);
        return tenant;
    }

    /** Kayıt servisine geçerli profil değerleri sağlar. */
    private RegisterRequest validRequest() {
        return new RegisterRequest("student@example.test", "Valid-password-123", "Test student", (short) 12, "SIMPLE");
    }
}
