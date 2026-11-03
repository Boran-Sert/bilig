package com.hataanalizi.core.content;

import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.common.AppConstants;
import com.hataanalizi.core.common.ErrorCode;
import com.hataanalizi.core.content.dto.BlockResponse;
import com.hataanalizi.core.storage.FileStorage;
import java.io.IOException;
import java.io.InputStream;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Yayın durumunu denetleyip paragraf ve sayfa görüntülerini okur. */
@Service
public class ContentService {

    private final ContentBlockRepository contentBlockRepository;
    private final SourcePageRepository sourcePageRepository;
    private final FileStorage fileStorage;

    /** İçerik depolarını ve dosya deposunu saklar. */
    public ContentService(
            ContentBlockRepository contentBlockRepository,
            SourcePageRepository sourcePageRepository,
            FileStorage fileStorage) {
        this.contentBlockRepository = contentBlockRepository;
        this.sourcePageRepository = sourcePageRepository;
        this.fileStorage = fileStorage;
    }

    /** Yayındaki paragrafı kaynak başlığı ve sayfa bilgileriyle döndürür. */
    @Transactional(readOnly = true)
    public BlockResponse getBlock(Long id) {
        ContentBlockRepository.BlockDetails block =
                contentBlockRepository.findDetailsById(id).orElseThrow(() -> new ApiException(ErrorCode.NOT_FOUND));
        if (!AppConstants.CONTENT_BLOCK_STATUS_PUBLISHED.equals(block.getStatus())) {
            throw new ApiException(ErrorCode.NOT_FOUND);
        }
        return BlockResponse.from(block);
    }

    /** Depolama arayüzünden sayfa görüntüsünün baytlarını okur. */
    @Transactional(readOnly = true)
    public byte[] getPageImage(Long id) {
        String path = sourcePageRepository
                .findById(id)
                .map(SourcePage::getImagePath)
                .filter(imagePath -> !imagePath.isBlank())
                .orElseThrow(() -> new ApiException(ErrorCode.NOT_FOUND));
        try (InputStream image = fileStorage.open(path)) {
            return image.readAllBytes();
        } catch (IOException exception) {
            throw new ApiException(ErrorCode.INTERNAL_ERROR, exception);
        }
    }
}
