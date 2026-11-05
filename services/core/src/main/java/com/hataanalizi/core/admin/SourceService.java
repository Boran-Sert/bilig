package com.hataanalizi.core.admin;

import com.hataanalizi.core.admin.dto.SourceListItem;
import com.hataanalizi.core.admin.dto.UploadResponse;
import com.hataanalizi.core.admin.dto.UploadedFile;
import com.hataanalizi.core.common.ApiException;
import com.hataanalizi.core.common.AppConstants;
import com.hataanalizi.core.common.ErrorCode;
import com.hataanalizi.core.common.PageResponse;
import com.hataanalizi.core.job.JobQueue;
import com.hataanalizi.core.job.JobStatus;
import com.hataanalizi.core.job.JobType;
import com.hataanalizi.core.storage.FileStorage;
import jakarta.persistence.EntityManager;
import jakarta.persistence.LockModeType;
import jakarta.persistence.PersistenceContext;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.util.unit.DataSize;
import org.springframework.web.multipart.MultipartFile;
import tools.jackson.databind.ObjectMapper;

/** PDF kaynaklarını doğrular, dosya deposuna yazar ve hazırlık işlerini kuyruğa ekler. */
@Service
public class SourceService {

    private static final String SOURCE_LIST_QUERY = """
            SELECT totals.total,
                   source.id,
                   source.title,
                   source.kind,
                   source.status,
                   source.created_at,
                   job.last_completed_step,
                   job.last_error
            FROM (
                SELECT count(*) AS total FROM source_document
                WHERE CAST(:kind AS text) IS NULL OR kind = CAST(:kind AS text)
            ) totals
            LEFT JOIN (
                SELECT id, title, kind, status, created_at
                FROM source_document
                WHERE CAST(:kind AS text) IS NULL OR kind = CAST(:kind AS text)
                ORDER BY created_at DESC, id DESC
                LIMIT :size OFFSET :offset
            ) source ON true
            LEFT JOIN LATERAL (
                SELECT last_completed_step, last_error
                FROM background_job
                WHERE job_type = :jobType
                  AND payload->>'sourceId' = CAST(source.id AS text)
                ORDER BY created_at DESC, id DESC
                LIMIT 1
            ) job ON true
            ORDER BY source.created_at DESC, source.id DESC
            """;
    private static final String ACTIVE_JOB_QUERY = """
            SELECT EXISTS (
                SELECT 1
                FROM background_job
                WHERE job_type = :jobType
                  AND payload->>'sourceId' = CAST(:sourceId AS text)
                  AND status IN (:activeStatuses)
            )
            """;
    private static final Logger log = LoggerFactory.getLogger(SourceService.class);
    private static final byte[] PDF_SIGNATURE = "%PDF".getBytes(StandardCharsets.US_ASCII);
    private static final int DIGEST_BUFFER_SIZE = 8192;

    @PersistenceContext
    private EntityManager entityManager;

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
    public UploadResponse upload(List<MultipartFile> files, SourceKind kind, Long answerKeySourceId, Long uploadedBy) {
        if (files == null
                || files.isEmpty()
                || uploadedBy == null
                || kind == null
                || !AppConstants.UPLOADABLE_SOURCE_KINDS.contains(kind.name())) {
            throw new ApiException(ErrorCode.VALIDATION_FAILED);
        }
        validateAnswerKey(kind, answerKeySourceId);

        List<ValidatedFile> validatedFiles = validateFiles(files);

        List<String> filesToCleanup = new ArrayList<>();
        registerRollbackCleanup(filesToCleanup);
        return persistFiles(validatedFiles, kind, answerKeySourceId, uploadedBy, filesToCleanup);
    }

    /** Kaynağı yeniden kuyruğa koyar; anahtar verilirse önce teste bağlar, süren işi bekletir. */
    @Transactional
    public void reprocess(long sourceId, Long answerKeySourceId) {
        SourceDocument source = entityManager.find(SourceDocument.class, sourceId, LockModeType.PESSIMISTIC_WRITE);
        if (source == null) {
            throw new ApiException(ErrorCode.NOT_FOUND);
        }
        if (answerKeySourceId != null) {
            validateAnswerKey(source.getKind(), answerKeySourceId);
            source.setAnswerKeySourceId(answerKeySourceId);
        }
        Boolean busy = (Boolean) entityManager
                .createNativeQuery(ACTIVE_JOB_QUERY)
                .setParameter("jobType", JobType.INGEST_SOURCE.name())
                .setParameter("sourceId", sourceId)
                .setParameter("activeStatuses", List.of(JobStatus.QUEUED.name(), JobStatus.RUNNING.name()))
                .getSingleResult();
        if (Boolean.TRUE.equals(busy)) {
            throw new ApiException(ErrorCode.SOURCE_BUSY);
        }
        source.setStatus(SourceStatus.UPLOADED);
        enqueueIngestJob(sourceId);
    }

    /** Anahtar sadece teste bağlanır ve bağlanan kaynak cevap anahtarı olmalıdır. */
    private void validateAnswerKey(SourceKind kind, Long answerKeySourceId) {
        if (answerKeySourceId == null) {
            return;
        }
        boolean isAnswerKey = sourceDocumentRepository
                .findById(answerKeySourceId)
                .filter(source -> source.getKind() == SourceKind.ANSWER_KEY)
                .isPresent();
        if (kind != SourceKind.TEST || !isAnswerKey) {
            throw new ApiException(ErrorCode.VALIDATION_FAILED);
        }
    }

    /** Kaynakları ve en güncel hazırlık işlerini tek sorguyla sayfalı döner. */
    @Transactional(readOnly = true)
    public PageResponse<SourceListItem> listSources(int page, int size, SourceKind kind) {
        if (page < 0 || size < 1 || size > AppConstants.MAX_SOURCE_PAGE_SIZE) {
            throw new ApiException(ErrorCode.VALIDATION_FAILED);
        }

        List<?> rows = entityManager
                .createNativeQuery(SOURCE_LIST_QUERY)
                .setParameter("jobType", JobType.INGEST_SOURCE.name())
                .setParameter("kind", kind == null ? null : kind.name())
                .setParameter("size", size)
                .setParameter("offset", (long) page * size)
                .getResultList();
        Object[] firstRow = (Object[]) rows.getFirst();
        long total = ((Number) firstRow[0]).longValue();
        List<SourceListItem> items = rows.stream()
                .map(Object[].class::cast)
                .filter(row -> row[1] != null)
                .map(this::toSourceListItem)
                .toList();
        return new PageResponse<>(items, page, size, total);
    }

    /** Sorgu satırını kaynak listesi DTO'suna dönüştürür. */
    private SourceListItem toSourceListItem(Object[] row) {
        String lastCompletedStepName = (String) row[6];
        IngestStep lastCompletedStep = lastCompletedStepName == null ? null : IngestStep.valueOf(lastCompletedStepName);
        int stepIndex = lastCompletedStep == null ? 0 : lastCompletedStep.ordinal() + 1;
        return new SourceListItem(
                ((Number) row[1]).longValue(),
                (String) row[2],
                SourceKind.valueOf((String) row[3]),
                SourceStatus.valueOf((String) row[4]),
                lastCompletedStep,
                stepIndex,
                IngestStep.values().length,
                (String) row[7],
                (Instant) row[5]);
    }

    /** Transaction rollback olduğunda yazılan dosyaları temizlemek üzere kayıt eder. */
    private void registerRollbackCleanup(List<String> filesToCleanup) {
        if (!TransactionSynchronizationManager.isSynchronizationActive()) {
            return;
        }

        TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
            @Override
            public void afterCompletion(int status) {
                if (status != STATUS_ROLLED_BACK) {
                    return;
                }

                for (String filePath : filesToCleanup) {
                    try {
                        fileStorage.delete(filePath);
                    } catch (RuntimeException exception) {
                        log.error("Failed to clean up file after transaction rollback: {}", filePath, exception);
                    }
                }
            }
        });
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
    private UploadResponse persistFiles(
            List<ValidatedFile> files,
            SourceKind kind,
            Long answerKeySourceId,
            Long uploadedBy,
            List<String> filesToCleanup) {
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
                continue;
            }
            Optional<Long> insertedId = sourceDocumentRepository.insertIfAbsent(
                    file.fileName(), file.sha256(), "sources/pending.pdf", kind.name(), uploadedBy, answerKeySourceId);
            if (insertedId.isEmpty()) {
                existingId = sourceDocumentRepository
                        .findBySha256(file.sha256())
                        .map(SourceDocument::getId)
                        .orElseThrow(() -> new ApiException(ErrorCode.INTERNAL_ERROR));
                knownSourceIds.put(file.sha256(), existingId);
                uploadedFiles.add(new UploadedFile(existingId, file.fileName(), true));
                continue;
            }

            long sourceId = insertedId.get();
            String filePath = "sources/" + sourceId + ".pdf";
            sourceDocumentRepository.updateFilePath(sourceId, filePath);

            filesToCleanup.add(filePath);
            saveFile(file, filePath);

            enqueueIngestJob(sourceId);
            knownSourceIds.put(file.sha256(), sourceId);
            uploadedFiles.add(new UploadedFile(sourceId, file.fileName(), false));
        }
        return new UploadResponse(uploadedFiles);
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
