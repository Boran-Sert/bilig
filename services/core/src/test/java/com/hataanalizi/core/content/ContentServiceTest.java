package com.hataanalizi.core.content;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.content.dto.BlockResponse;
import com.hataanalizi.core.storage.FileStorage;
import java.io.ByteArrayInputStream;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/** İçerik okuma servisinin yayın ve görüntü yolu kurallarını doğrular. */
class ContentServiceTest {

    private ContentBlockRepository contentBlockRepository;
    private SourcePageRepository sourcePageRepository;
    private FileStorage fileStorage;
    private ContentService contentService;

    /** Servis bağımlılıklarını Mockito nesneleriyle oluşturur. */
    @BeforeEach
    void setUp() {
        contentBlockRepository = mock(ContentBlockRepository.class);
        sourcePageRepository = mock(SourcePageRepository.class);
        fileStorage = mock(FileStorage.class);
        contentService = new ContentService(contentBlockRepository, sourcePageRepository, fileStorage);
    }

    /** Yayındaki paragrafın bütün kaynak alanlarını cevaba taşır. */
    @Test
    void returnsPublishedBlockDetails() {
        ContentBlockRepository.BlockDetails block = blockDetails("PUBLISHED");
        when(contentBlockRepository.findDetailsById(101L)).thenReturn(Optional.of(block));

        assertThat(contentService.getBlock(101L))
                .isEqualTo(new BlockResponse(101L, "Özgün paragraf.", "TDE 12 Ders Kitabı", 174, 15L));
    }

    /** Yayında olmayan veya bulunmayan paragrafı 404 hatasına çevirir. */
    @Test
    void rejectsUnpublishedOrMissingBlock() {
        ContentBlockRepository.BlockDetails unpublishedBlock = blockDetails("DRAFT");
        when(contentBlockRepository.findDetailsById(102L)).thenReturn(Optional.of(unpublishedBlock));
        when(contentBlockRepository.findDetailsById(103L)).thenReturn(Optional.empty());

        assertNotFound(() -> contentService.getBlock(102L));
        assertNotFound(() -> contentService.getBlock(103L));
    }

    /** Sayfa görüntüsünü dosya deposundan baytlarıyla okur. */
    @Test
    void returnsPageImageBytes() {
        SourcePage page = sourcePage("pages/15.png");
        when(sourcePageRepository.findById(15L)).thenReturn(Optional.of(page));
        when(fileStorage.open("pages/15.png")).thenReturn(new ByteArrayInputStream(new byte[] {1, 2, 3}));

        assertThat(contentService.getPageImage(15L)).containsExactly(1, 2, 3);

        verify(fileStorage).open("pages/15.png");
    }

    /** Olmayan sayfa ya da boş görüntü yolu için 404 döndürür. */
    @Test
    void rejectsMissingPageOrImagePath() {
        when(sourcePageRepository.findById(16L)).thenReturn(Optional.empty());
        when(sourcePageRepository.findById(17L)).thenReturn(Optional.of(sourcePage("  ")));

        assertNotFound(() -> contentService.getPageImage(16L));
        assertNotFound(() -> contentService.getPageImage(17L));
    }

    /** Yayın durumu belirtilen sorgu sonucunu hazırlar. */
    private ContentBlockRepository.BlockDetails blockDetails(String status) {
        ContentBlockRepository.BlockDetails block = mock(ContentBlockRepository.BlockDetails.class);
        when(block.getId()).thenReturn(101L);
        when(block.getMarkdown()).thenReturn("Özgün paragraf.");
        when(block.getStatus()).thenReturn(status);
        when(block.getSourceTitle()).thenReturn("TDE 12 Ders Kitabı");
        when(block.getPageNo()).thenReturn(174);
        when(block.getPageId()).thenReturn(15L);
        return block;
    }

    /** Görüntü yolu verilen sayfa varlığını oluşturur. */
    private SourcePage sourcePage(String imagePath) {
        SourcePage page = new SourcePage();
        page.setId(15L);
        page.setImagePath(imagePath);
        return page;
    }

    /** İşlemin standart bulunamadı hatası verdiğini doğrular. */
    private void assertNotFound(Runnable action) {
        assertThatThrownBy(action::run)
                .isInstanceOf(ApiException.class)
                .extracting(
                        exception -> ((ApiException) exception).getErrorCode().name())
                .isEqualTo("NOT_FOUND");
    }
}
