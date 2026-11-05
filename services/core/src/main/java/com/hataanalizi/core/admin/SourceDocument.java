package com.hataanalizi.core.admin;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

/** Yüklenmiş bir PDF dosyasını source_document satırıyla eşler. */
@Entity
@Table(name = "source_document")
@Getter
@Setter
@NoArgsConstructor
public class SourceDocument {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, columnDefinition = "text")
    private SourceKind kind = SourceKind.UNKNOWN;

    @Column(nullable = false, columnDefinition = "text")
    private String title;

    @Column(nullable = false, length = 64, columnDefinition = "char(64)")
    @JdbcTypeCode(SqlTypes.CHAR)
    private String sha256;

    @Column(name = "file_path", nullable = false, columnDefinition = "text")
    private String filePath;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, columnDefinition = "text")
    private SourceStatus status = SourceStatus.UPLOADED;

    @Column(name = "uploaded_by", nullable = false)
    private Long uploadedBy;

    @Column(name = "answer_key_source_id")
    private Long answerKeySourceId;
}
