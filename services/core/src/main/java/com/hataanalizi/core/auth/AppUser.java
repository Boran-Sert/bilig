package com.hataanalizi.core.auth;

import com.hataanalizi.core.common.AppConstants;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.time.OffsetDateTime;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.UpdateTimestamp;

/** Kullanıcı tablosundaki öğrenci ve içerik yöneticisi kayıtlarını temsil eder. */
@Entity
@Table(
        name = "app_user",
        uniqueConstraints =
                @UniqueConstraint(
                        name = "uq_app_user_tenant_id_external_user_id",
                        columnNames = {"tenant_id", "external_user_id"}))
@Getter
@Setter
@NoArgsConstructor
public class AppUser {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "tenant_id", nullable = false)
    private Long tenantId;

    @Column(columnDefinition = "text", unique = true)
    private String email;

    @Column(name = "password_hash", columnDefinition = "text")
    private String passwordHash;

    @Column(name = "display_name", nullable = false, columnDefinition = "text")
    private String displayName;

    @Column(nullable = false, columnDefinition = "text")
    private String role;

    private Short grade;

    @Column(name = "explain_style", nullable = false, columnDefinition = "text")
    private String explainStyle = AppConstants.DEFAULT_EXPLAIN_STYLE;

    @Column(name = "external_user_id", columnDefinition = "text")
    private String externalUserId;

    @Column(name = "created_at", nullable = false, insertable = false, updatable = false)
    private OffsetDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private OffsetDateTime updatedAt;
}
