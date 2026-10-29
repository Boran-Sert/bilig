package com.hataanalizi.core.storage;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.common.ErrorCode;
import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.nio.file.Path;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import org.springframework.core.env.MapPropertySource;

/** Yerel dosya saklamanın sözleşmesini ve etkinleşme ayarını sınar. */
class FileStorageContractTest {

    /** Kaydedilen PDF ve sayfa baytlarının aynı yollarla açılabildiğini doğrular. */
    @Test
    void savesAndOpensSourceAndPageFiles(@TempDir Path storageDirectory) throws Exception {
        LocalFileStorage storage = new LocalFileStorage(storageDirectory.toString());
        byte[] sourceContent = new byte[] {1, 2, 3, 4};
        byte[] pageContent = new byte[] {5, 6, 7, 8};

        storage.save("sources/42.pdf", new ByteArrayInputStream(sourceContent));
        storage.save("pages/42/0001.png", new ByteArrayInputStream(pageContent));

        try (InputStream source = storage.open("sources/42.pdf");
                InputStream page = storage.open("pages/42/0001.png")) {
            assertThat(source.readAllBytes()).containsExactly(sourceContent);
            assertThat(page.readAllBytes()).containsExactly(pageContent);
        }
    }

    /** exists kayıttan önce ve sonra dosyanın durumunu bildirir. */
    @Test
    void reportsWhetherFileExists(@TempDir Path storageDirectory) {
        LocalFileStorage storage = new LocalFileStorage(storageDirectory.toString());
        String path = "sources/42.pdf";

        assertThat(storage.exists(path)).isFalse();
        storage.save(path, new ByteArrayInputStream(new byte[] {1}));
        assertThat(storage.exists(path)).isTrue();
    }

    /** Kök dışına çıkan yolları reddeder. */
    @Test
    void rejectsPathsOutsideStorageDirectory(@TempDir Path storageDirectory) {
        LocalFileStorage storage = new LocalFileStorage(storageDirectory.toString());

        assertThatThrownBy(() -> storage.save("../outside.pdf", new ByteArrayInputStream(new byte[] {1})))
                .isInstanceOfSatisfying(
                        ApiException.class,
                        exception -> assertThat(exception.getErrorCode()).isEqualTo(ErrorCode.VALIDATION_FAILED));
        assertThatThrownBy(() -> storage.open(
                        storageDirectory.resolveSibling("outside.pdf").toString()))
                .isInstanceOfSatisfying(
                        ApiException.class,
                        exception -> assertThat(exception.getErrorCode()).isEqualTo(ErrorCode.VALIDATION_FAILED));
    }

    /** Yerel depolamanın yalnızca STORAGE_TYPE=local iken etkinleştiğini doğrular. */
    @Test
    void enablesLocalStorageOnlyForLocalType(@TempDir Path storageDirectory) {
        try (AnnotationConfigApplicationContext localContext = contextFor("local", storageDirectory)) {
            assertThat(localContext.getBean(FileStorage.class)).isInstanceOf(LocalFileStorage.class);
        }
        try (AnnotationConfigApplicationContext otherContext = contextFor("s3", storageDirectory)) {
            assertThat(otherContext.getBeansOfType(FileStorage.class)).isEmpty();
        }
    }

    /** Verilen depolama türüyle Spring bağlamı kurar. */
    private AnnotationConfigApplicationContext contextFor(String storageType, Path storageDirectory) {
        AnnotationConfigApplicationContext context = new AnnotationConfigApplicationContext();
        context.getEnvironment()
                .getPropertySources()
                .addFirst(new MapPropertySource(
                        "storageTest",
                        Map.of("STORAGE_TYPE", storageType, "STORAGE_DIR", storageDirectory.toString())));
        context.register(LocalFileStorage.class);
        context.refresh();
        return context;
    }
}
