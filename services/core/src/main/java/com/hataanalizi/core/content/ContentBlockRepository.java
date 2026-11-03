package com.hataanalizi.core.content;

import java.util.Optional;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.Repository;
import org.springframework.data.repository.query.Param;

/** Kaynak paragrafını ve sayfa/kaynak bilgilerini salt okunur sorgular. */
public interface ContentBlockRepository extends Repository<ContentBlock, Long> {

    /** Paragrafla ilişkili sayfa ve kaynak bilgilerini bulur. */
    @Query(value = """
            SELECT block.id AS id, block.markdown AS markdown, block.status AS status,
                   document.title AS "sourceTitle", page.page_no AS "pageNo", page.id AS "pageId"
            FROM content_block block
            JOIN source_page page ON page.id = block.source_page_id
            JOIN source_document document ON document.id = page.source_document_id
            WHERE block.id = :id
            """, nativeQuery = true)
    Optional<BlockDetails> findDetailsById(@Param("id") Long id);

    /** Sorgu sonucundaki paragraf ve kaynak alanlarını taşır. */
    interface BlockDetails {

        /** Paragraf kimliğini döndürür. */
        Long getId();

        /** Paragrafın özgün markdown metnini döndürür. */
        String getMarkdown();

        /** Paragrafın yayın durumunu döndürür. */
        String getStatus();

        /** Kaynak belgenin başlığını döndürür. */
        String getSourceTitle();

        /** Kaynak sayfanın numarasını döndürür. */
        Integer getPageNo();

        /** Kaynak sayfanın kimliğini döndürür. */
        Long getPageId();
    }
}
