package com.hataanalizi.core.content;

import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

/** Öğrenciye kaynak sayfası görüntüsü uç noktasını sunar. */
@RestController
public class PageImageController {

    private final ContentService contentService;

    /** İçerik okuma işlemlerini yöneten servisi saklar. */
    public PageImageController(ContentService contentService) {
        this.contentService = contentService;
    }

    /** Sayfa görüntüsünü PNG baytları olarak döndürür. */
    @GetMapping("/api/pages/{id}/image")
    public ResponseEntity<byte[]> getImage(@PathVariable Long id) {
        return ResponseEntity.ok().contentType(MediaType.IMAGE_PNG).body(contentService.getPageImage(id));
    }
}
