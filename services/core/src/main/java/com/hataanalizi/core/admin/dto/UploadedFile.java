package com.hataanalizi.core.admin.dto;

/** Bir dosyanın yükleme yanıtındaki kimliğini, adını ve tekrar durumunu taşır. */
public record UploadedFile(Long sourceId, String fileName, boolean duplicate) {}
