package com.hataanalizi.core.admin.dto;

import java.util.List;

/** Çoklu PDF yükleme isteğinin sonuçlarını taşır. */
public record UploadResponse(List<UploadedFile> files) {}
