package com.hataanalizi.core.tutor;

import jakarta.persistence.CollectionTable;
import jakarta.persistence.Column;
import jakarta.persistence.ElementCollection;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;
import java.util.LinkedHashSet;
import java.util.Set;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

/** Öğrenci ve asistan mesajlarını tutor_message tablosuyla eşler. */
@Entity
@Table(name = "tutor_message")
@Getter
@Setter
@NoArgsConstructor
public class TutorMessage {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "tutor_conversation_id", nullable = false)
    private Long tutorConversationId;

    @Column(nullable = false, columnDefinition = "text")
    private String role;

    @Column(nullable = false, columnDefinition = "text")
    private String content;

    @Column(name = "created_at", nullable = false, insertable = false, updatable = false)
    private OffsetDateTime createdAt;

    @ElementCollection(fetch = FetchType.LAZY)
    @CollectionTable(name = "tutor_message_citation", joinColumns = @JoinColumn(name = "tutor_message_id"))
    @Column(name = "content_block_id", nullable = false)
    private Set<Long> citationBlockIds = new LinkedHashSet<>();
}
