package com.hataanalizi.core.admin;

import com.hataanalizi.core.admin.dto.SourceListItem;
import com.hataanalizi.core.admin.dto.UploadResponse;
import com.hataanalizi.core.auth.AuthUser;
import com.hataanalizi.core.common.AppConstants;
import com.hataanalizi.core.common.PageResponse;
import java.util.List;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

/** Yönetici API'si üzerinden PDF kaynaklarını yüklemeye açar. */
@RestController
@RequestMapping("/api/admin/sources")
public class SourceController {

    private final SourceService sourceService;

    /** Kaynak yükleme servisini saklar. */
    public SourceController(SourceService sourceService) {
        this.sourceService = sourceService;
    }

    /** Çoklu PDF yüklemesini başlatır ve kabul edilen dosya sonuçlarını döndürür. */
    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<UploadResponse> upload(
            @RequestParam("files") List<MultipartFile> files, @AuthenticationPrincipal AuthUser authUser) {
        UploadResponse response = sourceService.upload(files, authUser.id());
        return ResponseEntity.accepted().body(response);
    }

    /** Kaynakların yükleme ve hazırlık adımlarını sayfalı döner. */
    @GetMapping
    public PageResponse<SourceListItem> listSources(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = AppConstants.DEFAULT_SOURCE_PAGE_SIZE) int size) {
        return sourceService.listSources(page, size);
    }
}
