package com.hataanalizi.core.storage;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.Objects;
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

    /** İçeriği belirtilen güvenli yola yazar. */
    @Override
    public void save(String path, InputStream content) {
        Path target = resolvePath(path);
        Objects.requireNonNull(content, "content");
        try {
            Files.createDirectories(target.getParent());
            Files.copy(content, target, StandardCopyOption.REPLACE_EXISTING);
        } catch (IOException exception) {
            throw new UncheckedIOException("Could not save stored file", exception);
        }
    }

    /** Belirtilen güvenli yoldaki dosyayı açar. */
    @Override
    public InputStream open(String path) {
        try {
            return Files.newInputStream(resolvePath(path));
        } catch (IOException exception) {
            throw new UncheckedIOException("Could not open stored file", exception);
        }
    }

    /** Belirtilen güvenli yolda dosya olup olmadığını bildirir. */
    @Override
    public boolean exists(String path) {
        return Files.exists(resolvePath(path));
    }

    /** Yolu köke sabitler ve depolama dizininin dışına çıkmasını engeller. */
    private Path resolvePath(String path) {
        Objects.requireNonNull(path, "path");
        Path relativePath = Path.of(path);
        if (path.contains("..") || relativePath.isAbsolute()) {
            throw new IllegalArgumentException("Storage path must remain inside the storage directory");
        }
        Path target = storageDirectory.resolve(relativePath).normalize();
        if (!target.startsWith(storageDirectory) || target.equals(storageDirectory)) {
            throw new IllegalArgumentException("Storage path must remain inside the storage directory");
        }
        return target;
    }
}
