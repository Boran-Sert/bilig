package com.hataanalizi.core.content.dto;

import com.hataanalizi.core.content.ContentBlockRepository;

/** Alıntı kartında gösterilecek paragraf ve kaynak bilgisini taşır. */
public record BlockResponse(Long id, String markdown, String sourceTitle, Integer pageNo, Long pageId) {

    /** Sorgu sonucundan alıntı kartı cevabı oluşturur. */
    public static BlockResponse from(ContentBlockRepository.BlockDetails block) {
        return new BlockResponse(
                block.getId(), block.getMarkdown(), block.getSourceTitle(), block.getPageNo(), block.getPageId());
    }
}
