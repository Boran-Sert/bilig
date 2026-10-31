package com.hataanalizi.core.storage;

import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.common.ErrorCode;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

/** Dosyaları STORAGE_DIR altındaki yerel dosya sisteminde saklar. */
@Component
@ConditionalOnProperty(name = "STORAGE_TYPE", havingValue = "local")
public class LocalFileStorage implements FileStorage {

    private final Path storageDirectory;

    /** Depolama kökünü ayarlayıp mutlak yola dönüştürür. */
    public LocalFileStorage(@Value("${STORAGE_DIR:/data}") String storageDirectory) {
        this.storageDirectory = Path.of(storageDirectory).toAbsolutePath().normalize();
    }

    /** İçeriği geçici dosyaya yazıp tamamlandığında hedefe taşır. */
    @Override
    public void save(String path, InputStream content) {
        Path target = resolvePath(path);
        if (content == null) {
            throw new ApiException(ErrorCode.VALIDATION_FAILED);
        }

        Path tempFile = null;
        try {
            Files.createDirectories(target.getParent());
            tempFile = Files.createTempFile(
                    target.getParent(), target.getFileName().toString(), ".tmp");
            Files.copy(content, tempFile, StandardCopyOption.REPLACE_EXISTING);

            try {
                Files.move(tempFile, target, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            } catch (AtomicMoveNotSupportedException exception) {
                Files.move(tempFile, target, StandardCopyOption.REPLACE_EXISTING);
            }
        } catch (IOException exception) {
            if (tempFile != null) {
                try {
                    Files.deleteIfExists(tempFile);
                } catch (IOException cleanupException) {
                    exception.addSuppressed(cleanupException);
                }
            }
            throw new ApiException(ErrorCode.INTERNAL_ERROR, exception);
        }
    }

    /** Belirtilen güvenli yoldaki dosyayı açar. */
    @Override
    public InputStream open(String path) {
        try {
            return Files.newInputStream(resolvePath(path));
        } catch (IOException exception) {
            throw new ApiException(ErrorCode.INTERNAL_ERROR, exception);
        }
    }

    /** Belirtilen güvenli yolda dosya olup olmadığını bildirir. */
    @Override
    public boolean exists(String path) {
        return Files.exists(resolvePath(path));
    }

    /** Yolu köke sabitler ve depolama dizininin dışına çıkmasını engeller. */
    private Path resolvePath(String path) {
        if (path == null || path.contains("..")) {
            throw new ApiException(ErrorCode.VALIDATION_FAILED);
        }
        try {
            Path relativePath = Path.of(path);
            Path target = storageDirectory.resolve(relativePath).normalize();
            if (relativePath.isAbsolute() || !target.startsWith(storageDirectory) || target.equals(storageDirectory)) {
                throw new ApiException(ErrorCode.VALIDATION_FAILED);
            }
            return target;
        } catch (InvalidPathException exception) {
            throw new ApiException(ErrorCode.VALIDATION_FAILED, exception);
        }
    }

    /** Belirtilen güvenli yoldaki dosyayı siler. */
    @Override
    public void delete(String path) {
        try {
            Files.deleteIfExists(resolvePath(path));
        } catch (IOException exception) {
            throw new ApiException(ErrorCode.INTERNAL_ERROR, exception);
        }
    }
}
