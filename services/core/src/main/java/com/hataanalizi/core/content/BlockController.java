package com.hataanalizi.core.content;

import com.hataanalizi.core.content.dto.BlockResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

/** Öğrenciye kaynak paragrafı uç noktasını sunar. */
@RestController
public class BlockController {

    private final ContentService contentService;

    /** İçerik okuma işlemlerini yöneten servisi saklar. */
    public BlockController(ContentService contentService) {
        this.contentService = contentService;
    }

    /** Yayındaki paragrafı kaynak bilgileriyle döndürür. */
    @GetMapping("/api/blocks/{id}")
    public BlockResponse getBlock(@PathVariable Long id) {
        return contentService.getBlock(id);
    }
}
