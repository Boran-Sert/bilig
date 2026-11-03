package com.hataanalizi.core.content;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.Immutable;

/** Kaynak sayfasının görüntü yolu kolonunu salt okunur eşler. */
@Entity
@Immutable
@Table(name = "source_page")
@Getter
@Setter
@NoArgsConstructor
public class SourcePage {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "image_path", columnDefinition = "text")
    private String imagePath;
}
