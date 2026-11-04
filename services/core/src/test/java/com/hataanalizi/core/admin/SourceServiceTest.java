package com.hataanalizi.core.admin;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

import com.hataanalizi.core.admin.dto.UploadResponse;
import com.hataanalizi.core.admin.dto.UploadedFile;
import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.common.ErrorCode;
import com.hataanalizi.core.job.JobQueue;
import com.hataanalizi.core.job.JobType;
import com.hataanalizi.core.storage.FileStorage;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.util.unit.DataSize;
import org.springframework.web.multipart.MultipartFile;
import tools.jackson.databind.ObjectMapper;

/** SourceService'ın doğrulama, tekilleştirme ve iş kuyruğu sözleşmesini sınar. */
@ExtendWith(MockitoExtension.class)
class SourceServiceTest {

    private static final DataSize MAXIMUM_FILE_SIZE = DataSize.ofMegabytes(100);
    private static final long UPLOADER_ID = 17L;

    @Mock
    private SourceDocumentRepository sourceDocumentRepository;

    @Mock
    private FileStorage fileStorage;

    @Mock
    private JobQueue jobQueue;

    private SourceService sourceService;

    /** Gerçek JSON üreticisiyle servisi ve en fazla dosya boyutunu hazırlar. */
    @BeforeEach
    void setUp() {
        sourceService = new SourceService(
                sourceDocumentRepository, fileStorage, jobQueue, new ObjectMapper(), MAXIMUM_FILE_SIZE);
    }

    /** Yeni dosyayı varsayılan metadata ile kaydeder ve hazırlık işini kuyruğa koyar. */
    @Test
    void uploadsNewPdfAndEnqueuesIngestJob() throws Exception {
        when(sourceDocumentRepository.findBySha256(anyString())).thenReturn(Optional.empty());
        when(sourceDocumentRepository.insertIfAbsent(
                        anyString(), anyString(), anyString(), anyString(), eq(UPLOADER_ID)))
                .thenReturn(Optional.of(42L));

        MockMultipartFile file = pdfFile("ders-kitabi.pdf", "tiny.pdf");

        UploadResponse response = sourceService.upload(List.of(file), SourceKind.TEXTBOOK, UPLOADER_ID);

        assertThat(response.files()).singleElement().satisfies(uploadedFile -> {
            assertThat(uploadedFile.sourceId()).isEqualTo(42L);
            assertThat(uploadedFile.fileName()).isEqualTo("ders-kitabi.pdf");
            assertThat(uploadedFile.duplicate()).isFalse();
        });
        verify(sourceDocumentRepository)
                .insertIfAbsent(
                        eq("ders-kitabi.pdf"), anyString(), eq("sources/pending.pdf"), eq("TEXTBOOK"), eq(UPLOADER_ID));
        verify(sourceDocumentRepository, never()).save(any(SourceDocument.class));
        verify(fileStorage).save(eq("sources/42.pdf"), any(InputStream.class));
        verify(jobQueue)
                .enqueue(
                        eq(JobType.INGEST_SOURCE),
                        org.mockito.ArgumentMatchers.argThat(
                                payload -> payload.get("sourceId").asLong() == 42L));
    }

    /** Dosyanın PDF olduğunu uzantıya değil imzasına göre tanır. */
    @Test
    void acceptsPdfContentWithNonPdfExtension() throws Exception {
        when(sourceDocumentRepository.findBySha256(anyString())).thenReturn(Optional.empty());
        when(sourceDocumentRepository.insertIfAbsent(
                        anyString(), anyString(), anyString(), anyString(), eq(UPLOADER_ID)))
                .thenReturn(Optional.of(42L));

        UploadResponse response =
                sourceService.upload(List.of(pdfFile("ders-kitabi.txt", "tiny.pdf")), SourceKind.TEXTBOOK, UPLOADER_ID);

        assertThat(response.files().get(0).fileName()).isEqualTo("ders-kitabi.txt");
        verify(fileStorage).save(eq("sources/42.pdf"), any(InputStream.class));
    }

    /** Veritabanında bulunan içeriği tekrar yazmadan eski kaynak numarasıyla döndürür. */
    @Test
    void returnsExistingSourceForDuplicateContent() throws Exception {
        SourceDocument existing = new SourceDocument();
        existing.setId(13L);
        when(sourceDocumentRepository.findBySha256(anyString())).thenReturn(Optional.of(existing));

        UploadResponse response =
                sourceService.upload(List.of(pdfFile("tekrar.pdf", "tiny.pdf")), SourceKind.TEXTBOOK, UPLOADER_ID);

        assertThat(response.files()).singleElement().satisfies(uploadedFile -> {
            assertThat(uploadedFile.sourceId()).isEqualTo(13L);
            assertThat(uploadedFile.duplicate()).isTrue();
        });
        verify(sourceDocumentRepository, never()).save(any(SourceDocument.class));
        verifyNoInteractions(fileStorage, jobQueue);
    }

    /** Atomik insert sırasında oluşan duplicate durumunu mevcut kaynakla çözer. */
    @Test
    void returnsExistingSourceWhenConcurrentInsertWins() throws Exception {
        SourceDocument existing = new SourceDocument();
        existing.setId(99L);

        when(sourceDocumentRepository.findBySha256(anyString())).thenReturn(Optional.empty(), Optional.of(existing));

        when(sourceDocumentRepository.insertIfAbsent(
                        anyString(), anyString(), anyString(), anyString(), eq(UPLOADER_ID)))
                .thenReturn(Optional.empty());

        UploadResponse response =
                sourceService.upload(List.of(pdfFile("tekrar.pdf", "tiny.pdf")), SourceKind.TEXTBOOK, UPLOADER_ID);

        assertThat(response.files()).singleElement().satisfies(uploadedFile -> {
            assertThat(uploadedFile.sourceId()).isEqualTo(99L);
            assertThat(uploadedFile.fileName()).isEqualTo("tekrar.pdf");
            assertThat(uploadedFile.duplicate()).isTrue();
        });

        verify(sourceDocumentRepository, times(2)).findBySha256(anyString());

        verify(sourceDocumentRepository)
                .insertIfAbsent(anyString(), anyString(), anyString(), anyString(), eq(UPLOADER_ID));

        verify(sourceDocumentRepository, never()).updateFilePath(anyLong(), anyString());

        verify(sourceDocumentRepository, never()).save(any(SourceDocument.class));

        verifyNoInteractions(fileStorage, jobQueue);
    }

    /** Aynı batch içindeki tekrar için tek kayıt ve iş oluşturur. */
    @Test
    void deduplicatesRepeatedFilesWithinBatch() throws Exception {
        when(sourceDocumentRepository.findBySha256(anyString())).thenReturn(Optional.empty());
        when(sourceDocumentRepository.insertIfAbsent(
                        anyString(), anyString(), anyString(), anyString(), eq(UPLOADER_ID)))
                .thenReturn(Optional.of(42L));
        List<MultipartFile> files = List.of(pdfFile("ilk.pdf", "tiny.pdf"), pdfFile("tekrar.pdf", "tiny.pdf"));

        UploadResponse response = sourceService.upload(files, SourceKind.TEXTBOOK, UPLOADER_ID);

        assertThat(response.files()).extracting(UploadedFile::duplicate).containsExactly(false, true);
        verify(sourceDocumentRepository, times(1))
                .insertIfAbsent(anyString(), anyString(), anyString(), anyString(), eq(UPLOADER_ID));
        verify(sourceDocumentRepository).updateFilePath(42L, "sources/42.pdf");
        verify(fileStorage).save(eq("sources/42.pdf"), any(InputStream.class));
        verify(jobQueue).enqueue(eq(JobType.INGEST_SOURCE), any());
    }

    /** Bir batch içindeki farklı PDF dosyalarını ayrı kaynaklar ve işler olarak ekler. */
    @Test
    void uploadsMultipleDistinctPdfs() throws Exception {
        when(sourceDocumentRepository.findBySha256(anyString())).thenReturn(Optional.empty());
        when(sourceDocumentRepository.insertIfAbsent(
                        anyString(), anyString(), anyString(), anyString(), eq(UPLOADER_ID)))
                .thenReturn(Optional.of(42L), Optional.of(43L));
        List<MultipartFile> files = List.of(
                pdfFile("ilk.pdf", "tiny.pdf"),
                new MockMultipartFile(
                        "files",
                        "ikinci.pdf",
                        "application/pdf",
                        "%PDF-1.4 ikinci test PDF".getBytes(StandardCharsets.US_ASCII)));

        UploadResponse response = sourceService.upload(files, SourceKind.TEXTBOOK, UPLOADER_ID);

        assertThat(response.files()).extracting(UploadedFile::duplicate).containsExactly(false, false);
        assertThat(response.files()).extracting(UploadedFile::sourceId).containsExactly(42L, 43L);
        verify(sourceDocumentRepository).updateFilePath(42L, "sources/42.pdf");
        verify(sourceDocumentRepository).updateFilePath(43L, "sources/43.pdf");
        verify(jobQueue, times(2)).enqueue(eq(JobType.INGEST_SOURCE), any());
    }

    /** Geçersiz PDF bulunan batch'te kayıt, dosya veya iş oluşturmadan isteği reddeder. */
    @Test
    void rejectsBatchContainingNonPdfBeforeSavingAnything() throws Exception {
        List<MultipartFile> files =
                List.of(pdfFile("gecerli.pdf", "tiny.pdf"), pdfFile("gecersiz.pdf", "not-a-pdf.pdf"));

        assertThatThrownBy(() -> sourceService.upload(files, SourceKind.TEXTBOOK, UPLOADER_ID))
                .isInstanceOfSatisfying(
                        ApiException.class,
                        exception -> assertThat(exception.getErrorCode()).isEqualTo(ErrorCode.FILE_NOT_PDF));
        verify(sourceDocumentRepository, never()).save(any(SourceDocument.class));
        verifyNoInteractions(fileStorage, jobQueue);
    }

    /** Boyut sınırını aşan dosyayı FILE_TOO_LARGE koduyla ve yan etkisiz reddeder. */
    @Test
    void rejectsOversizedFileBeforeSavingAnything() {
        MultipartFile oversizedFile = org.mockito.Mockito.mock(MultipartFile.class);
        when(oversizedFile.getSize()).thenReturn(MAXIMUM_FILE_SIZE.toBytes() + 1);

        assertThatThrownBy(() -> sourceService.upload(List.of(oversizedFile), SourceKind.TEXTBOOK, UPLOADER_ID))
                .isInstanceOfSatisfying(
                        ApiException.class,
                        exception -> assertThat(exception.getErrorCode()).isEqualTo(ErrorCode.FILE_TOO_LARGE));
        verify(sourceDocumentRepository, never()).save(any(SourceDocument.class));
        verifyNoInteractions(fileStorage, jobQueue);
    }

    /** Sınıf yolundaki kendimize ait PDF fikstürünü çok parçalı dosyaya dönüştürür. */
    private MockMultipartFile pdfFile(String fileName, String fixtureName) throws IOException {
        try (InputStream fixture = getClass().getResourceAsStream("/fixtures/" + fixtureName)) {
            if (fixture == null) {
                throw new IllegalStateException("Missing PDF test fixture: " + fixtureName);
            }
            return new MockMultipartFile("files", fileName, "application/pdf", fixture.readAllBytes());
        }
    }

    /** Transaction rollback olduğunda daha önce yazılmış dosyaları temizler. */
    @Test
    void deletesPreviouslySavedFilesWhenTransactionRollsBack() throws Exception {
        TransactionSynchronizationManager.initSynchronization();

        try {
            when(sourceDocumentRepository.findBySha256(anyString())).thenReturn(Optional.empty());
            when(sourceDocumentRepository.insertIfAbsent(
                            anyString(), anyString(), anyString(), anyString(), eq(UPLOADER_ID)))
                    .thenReturn(Optional.of(42L), Optional.of(43L));

            doNothing()
                    .doThrow(new ApiException(ErrorCode.INTERNAL_ERROR))
                    .when(fileStorage)
                    .save(anyString(), any(InputStream.class));

            List<MultipartFile> files = List.of(
                    pdfFile("ilk.pdf", "tiny.pdf"),
                    new MockMultipartFile(
                            "files",
                            "ikinci.pdf",
                            "application/pdf",
                            "%PDF-1.4 ikinci test PDF".getBytes(StandardCharsets.US_ASCII)));

            assertThatThrownBy(() -> sourceService.upload(files, SourceKind.TEXTBOOK, UPLOADER_ID))
                    .isInstanceOf(ApiException.class);

            List<TransactionSynchronization> synchronizations = TransactionSynchronizationManager.getSynchronizations();

            synchronizations.forEach(
                    synchronization -> synchronization.afterCompletion(TransactionSynchronization.STATUS_ROLLED_BACK));

            verify(fileStorage).delete("sources/42.pdf");
            verify(fileStorage).delete("sources/43.pdf");
        } finally {
            TransactionSynchronizationManager.clearSynchronization();
        }
    }

    /** Transaction commit olduğunda yüklenen dosyaları korur. */
    @Test
    void keepsFilesWhenTransactionCommits() throws Exception {
        TransactionSynchronizationManager.initSynchronization();

        try {
            when(sourceDocumentRepository.findBySha256(anyString())).thenReturn(Optional.empty());
            when(sourceDocumentRepository.insertIfAbsent(
                            anyString(), anyString(), anyString(), anyString(), eq(UPLOADER_ID)))
                    .thenReturn(Optional.of(42L));

            sourceService.upload(List.of(pdfFile("ders-kitabi.pdf", "tiny.pdf")), SourceKind.TEXTBOOK, UPLOADER_ID);

            List<TransactionSynchronization> synchronizations = TransactionSynchronizationManager.getSynchronizations();

            synchronizations.forEach(
                    synchronization -> synchronization.afterCompletion(TransactionSynchronization.STATUS_COMMITTED));

            verify(fileStorage, never()).delete(anyString());
            verify(fileStorage).save(eq("sources/42.pdf"), any(InputStream.class));
        } finally {
            TransactionSynchronizationManager.clearSynchronization();
        }
    }
}
