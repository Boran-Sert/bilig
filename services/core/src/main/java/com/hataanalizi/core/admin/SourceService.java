package com.hataanalizi.core.admin;

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
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.unit.DataSize;
import org.springframework.web.multipart.MultipartFile;
import tools.jackson.databind.ObjectMapper;

/** PDF kaynaklarını doğrular, dosya deposuna yazar ve hazırlık işlerini kuyruğa ekler. */
@Service
public class SourceService {

    private static final byte[] PDF_SIGNATURE = "%PDF".getBytes(StandardCharsets.US_ASCII);
    private static final int DIGEST_BUFFER_SIZE = 8192;

    private final SourceDocumentRepository sourceDocumentRepository;
    private final FileStorage fileStorage;
    private final JobQueue jobQueue;
    private final ObjectMapper objectMapper;
    private final DataSize maximumFileSize;

    /** Kaynak yükleme bağımlılıklarını ve yapılandırılmış dosya sınırını saklar. */
    public SourceService(
            SourceDocumentRepository sourceDocumentRepository,
            FileStorage fileStorage,
            JobQueue jobQueue,
            ObjectMapper objectMapper,
            @Value("${spring.servlet.multipart.max-file-size}") DataSize maximumFileSize) {
        this.sourceDocumentRepository = sourceDocumentRepository;
        this.fileStorage = fileStorage;
        this.jobQueue = jobQueue;
        this.objectMapper = objectMapper;
        this.maximumFileSize = maximumFileSize;
    }

    /** Dosyaları önce doğrular, sonra kaynakları tek transaction içinde kaydeder. */
    @Transactional
    public UploadResponse upload(List<MultipartFile> files, Long uploadedBy) {
        if (files == null || files.isEmpty() || uploadedBy == null) {
            throw new ApiException(ErrorCode.VALIDATION_FAILED);
        }

        List<ValidatedFile> validatedFiles = validateFiles(files);
        return persistFiles(validatedFiles, uploadedBy);
    }

    /** Dosya boyutunu, adını, PDF imzasını ve SHA-256 özetini doğrular. */
    private List<ValidatedFile> validateFiles(List<MultipartFile> files) {
        List<ValidatedFile> validatedFiles = new ArrayList<>(files.size());
        for (MultipartFile file : files) {
            if (file == null) {
                throw new ApiException(ErrorCode.VALIDATION_FAILED);
            }
            if (file.getSize() > maximumFileSize.toBytes()) {
                throw new ApiException(ErrorCode.FILE_TOO_LARGE);
            }
            String fileName = file.getOriginalFilename();
            if (fileName == null || fileName.isBlank()) {
                throw new ApiException(ErrorCode.VALIDATION_FAILED);
            }
            validatedFiles.add(new ValidatedFile(file, fileName, calculateSha256(file)));
        }
        return validatedFiles;
    }

    /** PDF imzasını kontrol eder ve dosyanın SHA-256 özetini hesaplar. */
    private String calculateSha256(MultipartFile file) {
        try (InputStream content = file.getInputStream()) {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] signature = content.readNBytes(PDF_SIGNATURE.length);
            if (!Arrays.equals(signature, PDF_SIGNATURE)) {
                throw new ApiException(ErrorCode.FILE_NOT_PDF);
            }
            digest.update(signature);
            updateDigest(content, digest);
            return HexFormat.of().formatHex(digest.digest());
        } catch (IOException | NoSuchAlgorithmException exception) {
            throw new ApiException(ErrorCode.INTERNAL_ERROR, exception);
        }
    }

    /** Akıştaki kalan baytları özete ekler. */
    private void updateDigest(InputStream content, MessageDigest digest) throws IOException {
        byte[] buffer = new byte[DIGEST_BUFFER_SIZE];
        int bytesRead;
        while ((bytesRead = content.read(buffer)) != -1) {
            digest.update(buffer, 0, bytesRead);
        }
    }

    /** Yeni dosyaları yazar, işlerini sıraya koyar ve yinelenen kimlikleri döndürür. */
    private UploadResponse persistFiles(List<ValidatedFile> files, Long uploadedBy) {
        Map<String, Long> knownSourceIds = new HashMap<>();
        List<UploadedFile> uploadedFiles = new ArrayList<>(files.size());
        for (ValidatedFile file : files) {
            Long existingId = knownSourceIds.get(file.sha256());
            if (existingId == null) {
                existingId = sourceDocumentRepository
                        .findBySha256(file.sha256())
                        .map(SourceDocument::getId)
                        .orElse(null);
            }
            if (existingId != null) {
                knownSourceIds.put(file.sha256(), existingId);
                uploadedFiles.add(new UploadedFile(existingId, file.fileName(), true));
            } else {
                SourceDocument sourceDocument = createSourceDocument(file, uploadedBy);
                long sourceId = sourceDocumentRepository.save(sourceDocument).getId();
                String filePath = "sources/" + sourceId + ".pdf";
                sourceDocument.setFilePath(filePath);
                saveFile(file, filePath);
                enqueueIngestJob(sourceId);
                knownSourceIds.put(file.sha256(), sourceId);
                uploadedFiles.add(new UploadedFile(sourceId, file.fileName(), false));
            }
        }
        return new UploadResponse(uploadedFiles);
    }

    /** Kaynak satırını varsayılan tür, durum ve geçici dosya yolu ile hazırlar. */
    private SourceDocument createSourceDocument(ValidatedFile file, Long uploadedBy) {
        SourceDocument sourceDocument = new SourceDocument();
        sourceDocument.setTitle(file.fileName());
        sourceDocument.setSha256(file.sha256());
        sourceDocument.setFilePath("sources/pending.pdf");
        sourceDocument.setUploadedBy(uploadedBy);
        return sourceDocument;
    }

    /** Doğrulanmış dosya akışını depolama arayüzüne yazar. */
    private void saveFile(ValidatedFile file, String filePath) {
        try (InputStream content = file.multipartFile().getInputStream()) {
            fileStorage.save(filePath, content);
        } catch (IOException exception) {
            throw new ApiException(ErrorCode.INTERNAL_ERROR, exception);
        }
    }

    /** Kaynak kimliğini taşıyan INGEST_SOURCE işini kuyruğa ekler. */
    private void enqueueIngestJob(long sourceId) {
        jobQueue.enqueue(JobType.INGEST_SOURCE, objectMapper.createObjectNode().put("sourceId", sourceId));
    }

    /** Doğrulanmış dosyaları temsil eder. */
    private record ValidatedFile(MultipartFile multipartFile, String fileName, String sha256) {}
}
